"""
SEC XBRL API source for retrieving SEC filings via XBRL data.
Third fallback source when EDGAR API and RSS feeds fail.
"""

import asyncio
import aiohttp
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class SECXBRLApi:
    """
    SEC XBRL API source implementation.
    Uses SEC's XBRL data API for structured financial data.
    """
    
    def __init__(self):
        self.base_url = "https://data.sec.gov"
        self.headers = {
            "User-Agent": "IsoFinancial-MCP/1.0 (contact@example.com)",
            "Accept": "application/json"
        }
    
    async def fetch_filings(
        self,
        ticker: str,
        form_types: List[str],
        lookback_days: int
    ) -> List[Dict[str, Any]]:
        """
        Fetch SEC filings from XBRL API.
        
        Args:
            ticker: Stock ticker symbol
            form_types: List of form types to filter
            lookback_days: Number of days to look back
            
        Returns:
            List of filing dictionaries
        """
        try:
            # Get CIK for ticker
            cik = await self._get_cik_for_ticker(ticker)
            if not cik:
                logger.warning(f"Could not find CIK for ticker {ticker} via XBRL")
                return []
            
            # Calculate date range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=lookback_days)
            
            # Fetch filings from company facts
            filings = await self._fetch_company_filings(
                cik=cik,
                ticker=ticker,
                form_types=form_types,
                start_date=start_date,
                end_date=end_date
            )
            
            logger.info(
                f"SEC XBRL API fetched {len(filings)} filings for {ticker}"
            )
            return filings
            
        except Exception as e:
            logger.error(f"Error fetching SEC XBRL data for {ticker}: {e}")
            raise
    
    async def _get_cik_for_ticker(self, ticker: str) -> Optional[int]:
        """Get CIK for ticker from SEC company tickers JSON."""
        try:
            url = "https://www.sec.gov/files/company_tickers.json"
            
            async with aiohttp.ClientSession(headers=self.headers) as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        return None
                    
                    data = await response.json()
            
            # Search for ticker
            for entry in data.values():
                if isinstance(entry, dict) and entry.get("ticker", "").upper() == ticker.upper():
                    return entry.get("cik_str")
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting CIK for {ticker}: {e}")
            return None
    
    async def _fetch_company_filings(
        self,
        cik: int,
        ticker: str,
        form_types: List[str],
        start_date: datetime,
        end_date: datetime
    ) -> List[Dict[str, Any]]:
        """Fetch company filings from XBRL submissions endpoint."""
        try:
            # Use submissions endpoint which provides filing history
            url = f"{self.base_url}/submissions/CIK{cik:010d}.json"
            
            async with aiohttp.ClientSession(headers=self.headers) as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        raise Exception(f"XBRL API returned status {response.status}")
                    
                    data = await response.json()
            
            # Parse filings from recent submissions
            filings = []
            recent_filings = data.get("filings", {}).get("recent", {})
            
            if not recent_filings:
                return []
            
            # Extract filing data
            forms = recent_filings.get("form", [])
            filing_dates = recent_filings.get("filingDate", [])
            accession_numbers = recent_filings.get("accessionNumber", [])
            primary_documents = recent_filings.get("primaryDocument", [])
            report_dates = recent_filings.get("reportDate", [])
            
            for i, form in enumerate(forms):
                if i >= len(filing_dates) or i >= len(accession_numbers):
                    continue
                
                # Filter by form type
                if form not in form_types:
                    continue
                
                # Parse filing date
                try:
                    filing_date = datetime.strptime(filing_dates[i], "%Y-%m-%d")
                except (ValueError, IndexError):
                    continue
                
                # Filter by date range
                if filing_date < start_date or filing_date > end_date:
                    continue
                
                # Build filing URL
                accession_no = accession_numbers[i].replace("-", "")
                primary_doc = primary_documents[i] if i < len(primary_documents) else ""
                
                filing_url = (
                    f"https://www.sec.gov/Archives/edgar/data/{cik}/"
                    f"{accession_no}/{primary_doc}"
                )
                
                # Get report date if available
                report_date = None
                if i < len(report_dates) and report_dates[i]:
                    report_date = report_dates[i]
                
                filing_info = {
                    "date": filing_dates[i],
                    "form": form,
                    "url": filing_url,
                    "title": f"{form} Filing for {ticker}",
                    "accession_number": accession_numbers[i],
                    "report_date": report_date
                }
                
                filings.append(filing_info)
            
            # Sort by date (most recent first)
            filings.sort(key=lambda x: x["date"], reverse=True)
            
            return filings
            
        except Exception as e:
            logger.error(f"Error fetching XBRL company filings: {e}")
            raise
