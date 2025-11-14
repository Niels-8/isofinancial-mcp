"""
SEC Source Manager with multi-source fallback.
Orchestrates fetching from multiple SEC data sources with automatic fallback.
"""

import asyncio
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional

from ..reliability.data_manager import DataManager
from ..reliability.error_handler import ErrorHandler
from ..reliability.models import DataResult
from .sec_source import _fetch_sec_filings, _get_cik_for_ticker
from .sec_rss_source import SECRSSFeed
from .sec_xbrl_source import SECXBRLApi

logger = logging.getLogger(__name__)


class SECSourceManager:
    """
    Manages multiple SEC data sources with automatic fallback.
    
    Strategy:
    1. Try EDGAR API (primary source)
    2. If fails or returns 0 results, try RSS Feed
    3. If still fails, try XBRL API
    4. If no results with initial lookback, extend to 90 days
    5. As last resort, return stale cache data
    """
    
    def __init__(
        self,
        data_manager: Optional[DataManager] = None,
        error_handler: Optional[ErrorHandler] = None
    ):
        """
        Initialize SEC source manager.
        
        Args:
            data_manager: DataManager instance for orchestration
            error_handler: ErrorHandler instance for error classification
        """
        self.data_manager = data_manager or DataManager()
        self.error_handler = error_handler or ErrorHandler()
        self.rss_feed = SECRSSFeed()
        self.xbrl_api = SECXBRLApi()
        
        # Source priority order
        self.sources = [
            ("sec_edgar_api", self._fetch_from_edgar),
            ("sec_rss_feed", self._fetch_from_rss),
            ("sec_xbrl_api", self._fetch_from_xbrl)
        ]
    
    async def fetch_filings(
        self,
        ticker: str,
        form_types: Optional[List[str]] = None,
        lookback_days: int = 30
    ) -> DataResult:
        """
        Fetch SEC filings with automatic fallback and lookback extension.
        
        Args:
            ticker: Stock ticker symbol
            form_types: List of form types to filter
            lookback_days: Initial number of days to look back
            
        Returns:
            DataResult with filings data and metadata
        """
        if form_types is None:
            form_types = ["8-K", "S-3", "424B", "10-Q", "10-K"]
        
        # Generate cache key
        cache_key = f"sec_filings_{ticker}_{'-'.join(form_types)}_{lookback_days}"
        
        # Try fetching with initial lookback period
        result = await self.data_manager.fetch_with_fallback(
            cache_key=cache_key,
            sources=self.sources,
            ticker=ticker,
            form_types=form_types,
            lookback_days=lookback_days
        )
        
        # If no results and lookback < 90 days, extend lookback
        if (result.data is None or len(result.data) == 0) and lookback_days < 90:
            logger.info(
                f"No SEC filings found for {ticker} with {lookback_days} days lookback, "
                f"extending to 90 days"
            )
            
            extended_cache_key = f"sec_filings_{ticker}_{'-'.join(form_types)}_90"
            
            result = await self.data_manager.fetch_with_fallback(
                cache_key=extended_cache_key,
                sources=self.sources,
                ticker=ticker,
                form_types=form_types,
                lookback_days=90
            )
        
        return result
    
    async def _fetch_from_edgar(
        self,
        ticker: str,
        form_types: List[str],
        lookback_days: int
    ) -> List[Dict[str, Any]]:
        """
        Fetch from EDGAR API (primary source).
        
        This wraps the existing _fetch_sec_filings function.
        """
        try:
            # Import aiohttp for session management
            import aiohttp
            
            # Get CIK first
            headers = {
                "User-Agent": "IsoFinancial-MCP/1.0 (contact@example.com)",
                "Accept": "application/json"
            }
            
            async with aiohttp.ClientSession(headers=headers) as session:
                cik = await _get_cik_for_ticker(session, ticker)
                if not cik:
                    raise Exception(f"Could not find CIK for ticker {ticker}")
            
            # Fetch filings using existing function
            filings = await _fetch_sec_filings(ticker, form_types, lookback_days)
            
            if not filings:
                raise Exception(f"No filings found for {ticker}")
            
            logger.info(
                f"EDGAR API fetched {len(filings)} filings for {ticker}"
            )
            return filings
            
        except Exception as e:
            logger.warning(f"EDGAR API failed for {ticker}: {e}")
            raise
    
    async def _fetch_from_rss(
        self,
        ticker: str,
        form_types: List[str],
        lookback_days: int
    ) -> List[Dict[str, Any]]:
        """
        Fetch from RSS Feed (secondary source).
        """
        try:
            filings = await self.rss_feed.fetch_filings(
                ticker=ticker,
                form_types=form_types,
                lookback_days=lookback_days
            )
            
            if not filings:
                raise Exception(f"No filings found in RSS feed for {ticker}")
            
            return filings
            
        except Exception as e:
            logger.warning(f"RSS Feed failed for {ticker}: {e}")
            raise
    
    async def _fetch_from_xbrl(
        self,
        ticker: str,
        form_types: List[str],
        lookback_days: int
    ) -> List[Dict[str, Any]]:
        """
        Fetch from XBRL API (tertiary source).
        """
        try:
            filings = await self.xbrl_api.fetch_filings(
                ticker=ticker,
                form_types=form_types,
                lookback_days=lookback_days
            )
            
            if not filings:
                raise Exception(f"No filings found in XBRL API for {ticker}")
            
            return filings
            
        except Exception as e:
            logger.warning(f"XBRL API failed for {ticker}: {e}")
            raise
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get health status of all SEC sources."""
        return self.data_manager.get_health_status()
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return await self.data_manager.get_cache_stats()
