"""
SEC RSS Feed source for retrieving SEC filings via RSS feeds.
Alternative source when EDGAR API fails.
"""

import asyncio
import aiohttp
import logging
import feedparser
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class SECRSSFeed:
    """
    SEC RSS Feed source implementation.
    Parses SEC RSS feeds for company filings.
    """
    
    def __init__(self):
        self.base_url = "https://www.sec.gov/cgi-bin/browse-edgar"
        self.headers = {
            "User-Agent": "IsoFinancial-MCP/1.0 (contact@example.com)",
            "Accept": "application/rss+xml"
        }
    
    async def fetch_filings(
        self,
        ticker: str,
        form_types: List[str],
        lookback_days: int
    ) -> List[Dict[str, Any]]:
        """
        Fetch SEC filings from RSS feed.
        
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
                logger.warning(f"Could not find CIK for ticker {ticker} via RSS")
                return []
            
            # Calculate date range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=lookback_days)
            
            # Fetch RSS feed
            filings = await self._fetch_rss_feed(
                cik=cik,
                ticker=ticker,
                form_types=form_types,
                start_date=start_date,
                end_date=end_date
            )
            
            logger.info(
                f"SEC RSS Feed fetched {len(filings)} filings for {ticker}"
            )
            return filings
            
        except Exception as e:
            logger.error(f"Error fetching SEC RSS feed for {ticker}: {e}")
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
    
    async def _fetch_rss_feed(
        self,
        cik: int,
        ticker: str,
        form_types: List[str],
        start_date: datetime,
        end_date: datetime
    ) -> List[Dict[str, Any]]:
        """Fetch and parse RSS feed for company filings."""
        try:
            # Build RSS feed URL
            # SEC RSS feed parameters: action=getcompany, CIK, type, count, output=atom
            params = {
                "action": "getcompany",
                "CIK": f"{cik:010d}",
                "type": "",  # Empty to get all types
                "count": "100",  # Get last 100 filings
                "output": "atom"
            }
            
            # Build URL with parameters
            url = f"{self.base_url}?{'&'.join(f'{k}={v}' for k, v in params.items())}"
            
            # Fetch RSS feed
            async with aiohttp.ClientSession(headers=self.headers) as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        raise Exception(f"RSS feed returned status {response.status}")
                    
                    feed_content = await response.text()
            
            # Parse RSS feed using feedparser
            feed = feedparser.parse(feed_content)
            
            filings = []
            
            # Process each entry
            for entry in feed.entries:
                try:
                    # Extract form type from title
                    # Title format: "8-K - Current Report"
                    title = entry.get("title", "")
                    form_type = title.split("-")[0].strip() if "-" in title else ""
                    
                    # Filter by form type
                    if form_type not in form_types:
                        continue
                    
                    # Parse filing date
                    # RSS uses 'updated' or 'published' field
                    date_str = entry.get("updated", entry.get("published", ""))
                    if not date_str:
                        continue
                    
                    # Parse date (format: 2024-01-15T12:00:00-05:00)
                    filing_date = datetime.fromisoformat(
                        date_str.replace("Z", "+00:00")
                    )
                    
                    # Filter by date range
                    if filing_date < start_date or filing_date > end_date:
                        continue
                    
                    # Extract filing URL
                    filing_url = entry.get("link", "")
                    
                    # Extract accession number from summary or link
                    summary = entry.get("summary", "")
                    accession_number = self._extract_accession_number(
                        summary, filing_url
                    )
                    
                    filing_info = {
                        "date": filing_date.strftime("%Y-%m-%d"),
                        "form": form_type,
                        "url": filing_url,
                        "title": f"{form_type} Filing for {ticker}",
                        "accession_number": accession_number
                    }
                    
                    filings.append(filing_info)
                    
                except Exception as e:
                    logger.debug(f"Error parsing RSS entry: {e}")
                    continue
            
            # Sort by date (most recent first)
            filings.sort(key=lambda x: x["date"], reverse=True)
            
            return filings
            
        except Exception as e:
            logger.error(f"Error fetching RSS feed: {e}")
            raise
    
    def _extract_accession_number(
        self,
        summary: str,
        url: str
    ) -> str:
        """Extract accession number from summary or URL."""
        # Try to extract from URL
        # URL format: .../Archives/edgar/data/CIK/ACCESSION/...
        if "/Archives/edgar/data/" in url:
            parts = url.split("/")
            for i, part in enumerate(parts):
                if part == "data" and i + 2 < len(parts):
                    # Accession number is typically after CIK
                    accession = parts[i + 2]
                    # Format: 0000000000-00-000000
                    if len(accession) >= 18:
                        return accession[:20]
        
        # Try to extract from summary
        # Look for pattern like "Acc-no: 0000000000-00-000000"
        if "Acc-no:" in summary:
            start = summary.find("Acc-no:") + 7
            end = start + 20
            return summary[start:end].strip()
        
        return ""
