"""
SEC EDGAR API client for retrieving SEC filings
Handles form type filtering, caching, and rate limiting
"""

import asyncio
import aiohttp
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from cachetools import TTLCache
from asyncio_throttle import Throttler
import logging
from .validation import validate_ticker, validate_form_types, validate_positive_integer, ValidationError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Cache with 6-hour TTL as per requirements
sec_cache = TTLCache(maxsize=1000, ttl=21600)  # 6 hours = 21600 seconds

# Rate limiter for SEC EDGAR API (10 requests per second max)
sec_throttler = Throttler(rate_limit=10, period=1.0)

class SECError(Exception):
    """Custom exception for SEC API errors"""
    pass

async def get_sec_filings(
    ticker: str,
    form_types: List[str] = None,
    lookback_days: int = 30
) -> List[Dict[str, Any]]:
    """
    Retrieve SEC filings from EDGAR API with caching and rate limiting.
    
    Args:
        ticker: Stock ticker symbol
        form_types: List of form types to filter (default: ["8-K", "S-3", "424B", "10-Q", "10-K"])
        lookback_days: Number of days to look back for filings (default: 30)
    
    Returns:
        List of filing dictionaries with date, form, url, and title
    """
    try:
        # Validate inputs
        ticker = validate_ticker(ticker)
        
        if form_types is None:
            form_types = ["8-K", "S-3", "424B", "10-Q", "10-K"]
        form_types = validate_form_types(form_types)
        
        lookback_days = validate_positive_integer(lookback_days, "lookback_days", min_value=1, max_value=3650)
        
        # Create cache key
        cache_key = f"sec_filings_{ticker}_{'-'.join(form_types)}_{lookback_days}"
        
        # Check cache first
        if cache_key in sec_cache:
            logger.info(f"SEC filings cache hit for {ticker}")
            return sec_cache[cache_key]
        
        # Apply rate limiting
        async with sec_throttler:
            filings = await _fetch_sec_filings(ticker, form_types, lookback_days)
            
        # Cache the results
        sec_cache[cache_key] = filings
        logger.info(f"SEC filings fetched and cached for {ticker}: {len(filings)} filings")
        
        return filings
        
    except ValidationError as e:
        logger.error(f"Validation error for SEC filings {ticker}: {e}")
        return []
    except Exception as e:
        logger.error(f"Error fetching SEC filings for {ticker}: {e}")
        # Return empty list on error for graceful degradation
        return []

async def _fetch_sec_filings(
    ticker: str,
    form_types: List[str],
    lookback_days: int
) -> List[Dict[str, Any]]:
    """
    Internal function to fetch SEC filings from EDGAR API.
    """
    # Calculate date range
    end_date = datetime.now()
    start_date = end_date - timedelta(days=lookback_days)
    
    # SEC EDGAR API endpoint for company filings
    base_url = "https://data.sec.gov/submissions"
    
    headers = {
        "User-Agent": "IsoFinancial-MCP/1.0 (contact@example.com)",  # Required by SEC
        "Accept": "application/json"
    }
    
    async with aiohttp.ClientSession(headers=headers) as session:
        # First, get the CIK for the ticker
        cik = await _get_cik_for_ticker(session, ticker)
        if not cik:
            logger.warning(f"Could not find CIK for ticker {ticker}")
            return []
        
        # Get company submissions
        url = f"{base_url}/CIK{cik:010d}.json"
        
        async with session.get(url) as response:
            if response.status != 200:
                raise SECError(f"SEC API returned status {response.status}")
            
            data = await response.json()
            
        # Parse filings
        filings = []
        recent_filings = data.get("filings", {}).get("recent", {})
        
        if not recent_filings:
            return []
        
        # Extract filing data
        forms = recent_filings.get("form", [])
        filing_dates = recent_filings.get("filingDate", [])
        accession_numbers = recent_filings.get("accessionNumber", [])
        primary_documents = recent_filings.get("primaryDocument", [])
        
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
            
            filing_url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession_no}/{primary_doc}"
            
            filing_info = {
                "date": filing_dates[i],
                "form": form,
                "url": filing_url,
                "title": f"{form} Filing for {ticker}",
                "accession_number": accession_numbers[i]
            }
            
            filings.append(filing_info)
        
        # Sort by date (most recent first)
        filings.sort(key=lambda x: x["date"], reverse=True)
        
        return filings

async def _get_cik_for_ticker(session: aiohttp.ClientSession, ticker: str) -> Optional[int]:
    """
    Get the CIK (Central Index Key) for a given ticker symbol.
    """
    try:
        # Use SEC company tickers JSON endpoint
        url = "https://www.sec.gov/files/company_tickers.json"
        
        async with session.get(url) as response:
            if response.status != 200:
                return None
            
            data = await response.json()
            
        # Search for ticker in the data
        for entry in data.values():
            if isinstance(entry, dict) and entry.get("ticker", "").upper() == ticker.upper():
                return entry.get("cik_str")
        
        return None
        
    except Exception as e:
        logger.error(f"Error getting CIK for {ticker}: {e}")
        return None

# Utility function for cache management
def clear_sec_cache():
    """Clear the SEC filings cache"""
    sec_cache.clear()
    logger.info("SEC filings cache cleared")

def get_cache_stats() -> Dict[str, Any]:
    """Get SEC cache statistics"""
    return {
        "cache_size": len(sec_cache),
        "max_size": sec_cache.maxsize,
        "ttl": sec_cache.ttl,
        "hits": getattr(sec_cache, 'hits', 0),
        "misses": getattr(sec_cache, 'misses', 0)
    }