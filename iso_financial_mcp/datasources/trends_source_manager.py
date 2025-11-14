"""
Trends Source Manager with multi-source fallback and retry logic.

This module consolidates all trends-related functionality including:
- Individual data source implementations (PyTrends Direct, PyTrends with Proxy, SerpAPI)
- Multi-source manager with fallback and retry logic
- Adaptive rate limiting and health monitoring
"""

import asyncio
import httpx
import logging
import os
import pandas as pd
import random
from datetime import datetime, timedelta
from pytrends.request import TrendReq
from typing import Any, Dict, List, Optional

from ..reliability.adaptive_rate_limiter import AdaptiveRateLimiter
from ..reliability.cache_layer import CacheLayer
from ..reliability.error_handler import ErrorHandler
from ..reliability.health_monitor import HealthMonitor
from ..reliability.models import DataResult, ErrorInfo, RetryStrategy

logger = logging.getLogger(__name__)


# ============================================================================
# Data Source Classes (from trends_sources.py)
# ============================================================================

class PyTrendsDirect:
    """
    Direct PyTrends implementation (primary source).
    """
    
    def __init__(self):
        self.name = "pytrends_direct"
    
    async def fetch_trends(
        self,
        term: str,
        window_days: int = 30
    ) -> Dict[str, Any]:
        """
        Fetch trends data using direct PyTrends.
        
        Args:
            term: Search term
            window_days: Time window in days
            
        Returns:
            Dictionary with trends data
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self._fetch_sync,
            term,
            window_days
        )
    
    def _fetch_sync(self, term: str, window_days: int) -> Dict[str, Any]:
        """Synchronous fetch to run in executor."""
        try:
            # Add jitter to avoid detection
            jitter = random.uniform(0.5, 2.0)
            import time
            time.sleep(jitter)
            
            # Initialize pytrends
            pytrends = TrendReq(hl='en-US', tz=360)
            
            # Determine timeframe
            timeframe = self._get_timeframe(window_days)
            
            # Build payload
            pytrends.build_payload([term], cat=0, timeframe=timeframe, geo='US', gprop='')
            
            # Get interest over time
            interest_df = pytrends.interest_over_time()
            
            if interest_df.empty or term not in interest_df.columns:
                return self._empty_result(term)
            
            return self._format_result(term, interest_df, timeframe)
            
        except Exception as e:
            logger.error(f"PyTrendsDirect error for {term}: {e}")
            raise
    
    def _get_timeframe(self, window_days: int) -> str:
        """Get timeframe string for PyTrends."""
        if window_days <= 7:
            return 'now 7-d'
        elif window_days <= 30:
            return 'today 1-m'
        elif window_days <= 90:
            return 'today 3-m'
        else:
            return 'today 12-m'
    
    def _format_result(
        self,
        term: str,
        interest_df: pd.DataFrame,
        timeframe: str
    ) -> Dict[str, Any]:
        """Format PyTrends result."""
        series_data = []
        values = interest_df[term].tolist()
        dates = interest_df.index.tolist()
        
        for date, value in zip(dates, values):
            series_data.append({
                "date": date.strftime("%Y-%m-%d") if hasattr(date, 'strftime') else str(date),
                "value": int(value) if pd.notna(value) else 0
            })
        
        valid_values = [v for v in values if pd.notna(v)]
        
        if not valid_values:
            return self._empty_result(term)
        
        latest_value = valid_values[-1] if valid_values else 0
        average_value = sum(valid_values) / len(valid_values)
        peak_value = max(valid_values)
        peak_index = values.index(peak_value)
        peak_date = dates[peak_index].strftime("%Y-%m-%d") if hasattr(dates[peak_index], 'strftime') else str(dates[peak_index])
        
        return {
            "series": series_data,
            "latest": int(latest_value),
            "average": round(average_value, 1),
            "peak_value": int(peak_value),
            "peak_date": peak_date,
            "timeframe": timeframe,
            "total_points": len(series_data)
        }
    
    def _empty_result(self, term: str) -> Dict[str, Any]:
        """Return empty result structure."""
        return {
            "series": [],
            "latest": 0,
            "average": 0,
            "peak_value": 0,
            "peak_date": None,
            "timeframe": "unknown",
            "total_points": 0
        }


class PyTrendsWithProxy:
    """
    PyTrends with proxy support (secondary source).
    """
    
    def __init__(self, proxy: Optional[str] = None):
        """
        Initialize PyTrends with proxy.
        
        Args:
            proxy: Proxy URL (e.g., 'http://proxy.example.com:8080')
                   If None, reads from TRENDS_PROXY environment variable
        """
        self.name = "pytrends_proxy"
        self.proxy = proxy or os.getenv('TRENDS_PROXY')
        
        if not self.proxy:
            logger.warning("No proxy configured for PyTrendsWithProxy")
    
    async def fetch_trends(
        self,
        term: str,
        window_days: int = 30
    ) -> Dict[str, Any]:
        """
        Fetch trends data using PyTrends with proxy.
        
        Args:
            term: Search term
            window_days: Time window in days
            
        Returns:
            Dictionary with trends data
        """
        if not self.proxy:
            raise ValueError("Proxy not configured for PyTrendsWithProxy")
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self._fetch_sync,
            term,
            window_days
        )
    
    def _fetch_sync(self, term: str, window_days: int) -> Dict[str, Any]:
        """Synchronous fetch with proxy."""
        try:
            # Add jitter
            jitter = random.uniform(0.5, 2.0)
            import time
            time.sleep(jitter)
            
            # Initialize pytrends with proxy
            proxies = [self.proxy]
            pytrends = TrendReq(
                hl='en-US',
                tz=360,
                proxies=proxies,
                timeout=(10, 25)
            )
            
            # Determine timeframe
            timeframe = self._get_timeframe(window_days)
            
            # Build payload
            pytrends.build_payload([term], cat=0, timeframe=timeframe, geo='US', gprop='')
            
            # Get interest over time
            interest_df = pytrends.interest_over_time()
            
            if interest_df.empty or term not in interest_df.columns:
                return self._empty_result(term)
            
            return self._format_result(term, interest_df, timeframe)
            
        except Exception as e:
            logger.error(f"PyTrendsWithProxy error for {term}: {e}")
            raise
    
    def _get_timeframe(self, window_days: int) -> str:
        """Get timeframe string for PyTrends."""
        if window_days <= 7:
            return 'now 7-d'
        elif window_days <= 30:
            return 'today 1-m'
        elif window_days <= 90:
            return 'today 3-m'
        else:
            return 'today 12-m'
    
    def _format_result(
        self,
        term: str,
        interest_df: pd.DataFrame,
        timeframe: str
    ) -> Dict[str, Any]:
        """Format PyTrends result."""
        series_data = []
        values = interest_df[term].tolist()
        dates = interest_df.index.tolist()
        
        for date, value in zip(dates, values):
            series_data.append({
                "date": date.strftime("%Y-%m-%d") if hasattr(date, 'strftime') else str(date),
                "value": int(value) if pd.notna(value) else 0
            })
        
        valid_values = [v for v in values if pd.notna(v)]
        
        if not valid_values:
            return self._empty_result(term)
        
        latest_value = valid_values[-1] if valid_values else 0
        average_value = sum(valid_values) / len(valid_values)
        peak_value = max(valid_values)
        peak_index = values.index(peak_value)
        peak_date = dates[peak_index].strftime("%Y-%m-%d") if hasattr(dates[peak_index], 'strftime') else str(dates[peak_index])
        
        return {
            "series": series_data,
            "latest": int(latest_value),
            "average": round(average_value, 1),
            "peak_value": int(peak_value),
            "peak_date": peak_date,
            "timeframe": timeframe,
            "total_points": len(series_data)
        }
    
    def _empty_result(self, term: str) -> Dict[str, Any]:
        """Return empty result structure."""
        return {
            "series": [],
            "latest": 0,
            "average": 0,
            "peak_value": 0,
            "peak_date": None,
            "timeframe": "unknown",
            "total_points": 0
        }


class SerpAPISource:
    """
    SerpAPI for Google Trends data (primary if configured).
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize SerpAPI source.
        
        Args:
            api_key: SerpAPI key. If None, reads from SERPAPI_KEY environment variable
        """
        self.name = "serpapi"
        self.api_key = api_key or os.getenv('SERPAPI_KEY')
        self.base_url = "https://serpapi.com/search"
        
        if not self.api_key:
            logger.info("No API key configured for SerpAPI - will be skipped")
    
    async def fetch_trends(
        self,
        term: str,
        window_days: int = 30
    ) -> Dict[str, Any]:
        """
        Fetch trends data using SerpAPI.
        
        Args:
            term: Search term
            window_days: Time window in days
            
        Returns:
            Dictionary with trends data
        """
        if not self.api_key:
            raise ValueError("API key not configured for SerpAPI")
        
        try:
            # Determine date range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=window_days)
            
            # Build SerpAPI request
            params = {
                "engine": "google_trends",
                "q": term,
                "data_type": "TIMESERIES",
                "date": f"{start_date.strftime('%Y-%m-%d')} {end_date.strftime('%Y-%m-%d')}",
                "geo": "US",
                "api_key": self.api_key
            }
            
            # Make async request
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(self.base_url, params=params)
                response.raise_for_status()
                data = response.json()
            
            # Parse SerpAPI response
            return self._parse_serpapi_response(term, data, window_days)
            
        except Exception as e:
            logger.error(f"SerpAPIFallback error for {term}: {e}")
            raise
    
    def _parse_serpapi_response(
        self,
        term: str,
        data: Dict[str, Any],
        window_days: int
    ) -> Dict[str, Any]:
        """
        Parse SerpAPI response into standard format.
        
        Args:
            term: Search term
            data: SerpAPI response data
            window_days: Time window in days
            
        Returns:
            Formatted trends data
        """
        try:
            # Extract interest over time data
            interest_over_time = data.get("interest_over_time", {})
            timeline_data = interest_over_time.get("timeline_data", [])
            
            if not timeline_data:
                return self._empty_result(term)
            
            # Format series data
            series_data = []
            values = []
            
            for point in timeline_data:
                date_str = point.get("date", "")
                # SerpAPI returns values as list with extracted values
                value_data = point.get("values", [])
                value = value_data[0].get("extracted_value", 0) if value_data else 0
                
                series_data.append({
                    "date": date_str,
                    "value": int(value)
                })
                values.append(value)
            
            # Calculate metrics
            if not values:
                return self._empty_result(term)
            
            latest_value = values[-1] if values else 0
            average_value = sum(values) / len(values)
            peak_value = max(values)
            peak_index = values.index(peak_value)
            peak_date = series_data[peak_index]["date"]
            
            # Determine timeframe
            timeframe = self._get_timeframe(window_days)
            
            return {
                "series": series_data,
                "latest": int(latest_value),
                "average": round(average_value, 1),
                "peak_value": int(peak_value),
                "peak_date": peak_date,
                "timeframe": timeframe,
                "total_points": len(series_data),
                "source": "serpapi"
            }
            
        except Exception as e:
            logger.error(f"Error parsing SerpAPI response for {term}: {e}")
            return self._empty_result(term)
    
    def _get_timeframe(self, window_days: int) -> str:
        """Get timeframe string."""
        if window_days <= 7:
            return 'now 7-d'
        elif window_days <= 30:
            return 'today 1-m'
        elif window_days <= 90:
            return 'today 3-m'
        else:
            return 'today 12-m'
    
    def _empty_result(self, term: str) -> Dict[str, Any]:
        """Return empty result structure."""
        return {
            "series": [],
            "latest": 0,
            "average": 0,
            "peak_value": 0,
            "peak_date": None,
            "timeframe": "unknown",
            "total_points": 0,
            "source": "serpapi"
        }


class DuckDuckGoSearchFallback:
    """
    DuckDuckGo search as free fallback for trend estimation.
    Uses search result counts as proxy for interest level.
    """
    
    def __init__(self):
        self.name = "duckduckgo"
        self.base_url = "https://api.duckduckgo.com/"
    
    async def fetch_trends(
        self,
        term: str,
        window_days: int = 30
    ) -> Dict[str, Any]:
        """
        Fetch trend estimation using DuckDuckGo search.
        
        Note: This provides a simplified trend estimation based on
        search results, not actual search volume data like Google Trends.
        
        Args:
            term: Search term
            window_days: Time window in days (used for timeframe label only)
            
        Returns:
            Dictionary with estimated trend data
        """
        try:
            # Query DuckDuckGo instant answer API
            params = {
                "q": term,
                "format": "json",
                "no_html": 1,
                "skip_disambig": 1
            }
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(self.base_url, params=params)
                response.raise_for_status()
                data = response.json()
            
            # Check if we got meaningful results
            has_results = bool(
                data.get("Abstract") or 
                data.get("RelatedTopics") or
                data.get("Results")
            )
            
            # Generate simplified trend data
            # Since DDG doesn't provide time series, we return a single point
            timeframe = self._get_timeframe(window_days)
            
            if has_results:
                # Estimate interest based on result richness
                abstract_score = 30 if data.get("Abstract") else 0
                related_score = min(len(data.get("RelatedTopics", [])) * 5, 40)
                results_score = min(len(data.get("Results", [])) * 10, 30)
                
                estimated_value = abstract_score + related_score + results_score
                estimated_value = min(estimated_value, 100)  # Cap at 100
                
                return {
                    "series": [{
                        "date": datetime.now().strftime("%Y-%m-%d"),
                        "value": estimated_value
                    }],
                    "latest": estimated_value,
                    "average": estimated_value,
                    "peak_value": estimated_value,
                    "peak_date": datetime.now().strftime("%Y-%m-%d"),
                    "timeframe": timeframe,
                    "total_points": 1,
                    "source": "duckduckgo",
                    "note": "Estimated trend based on search result richness"
                }
            else:
                return self._empty_result(term)
                
        except Exception as e:
            logger.error(f"DuckDuckGo search error for {term}: {e}")
            raise
    
    def _get_timeframe(self, window_days: int) -> str:
        """Get timeframe string."""
        if window_days <= 7:
            return 'now 7-d'
        elif window_days <= 30:
            return 'today 1-m'
        elif window_days <= 90:
            return 'today 3-m'
        else:
            return 'today 12-m'
    
    def _empty_result(self, term: str) -> Dict[str, Any]:
        """Return empty result structure."""
        return {
            "series": [],
            "latest": 0,
            "average": 0,
            "peak_value": 0,
            "peak_date": None,
            "timeframe": "unknown",
            "total_points": 0,
            "source": "duckduckgo",
            "note": "No search results found"
        }


# ============================================================================
# Trends Source Manager (original content)
# ============================================================================


class TrendsSourceManager:
    """
    Manages multiple Google Trends sources with intelligent fallback.
    """
    
    def __init__(
        self,
        cache_layer: Optional[CacheLayer] = None,
        health_monitor: Optional[HealthMonitor] = None,
        rate_limiter: Optional[AdaptiveRateLimiter] = None,
        retry_strategy: Optional[RetryStrategy] = None,
        error_handler: Optional[ErrorHandler] = None
    ):
        """
        Initialize Trends Source Manager.
        
        Args:
            cache_layer: Cache layer instance
            health_monitor: Health monitor instance
            rate_limiter: Adaptive rate limiter instance
            retry_strategy: Retry strategy configuration
            error_handler: Error handler instance for error classification
        """
        self.cache_layer = cache_layer or CacheLayer()
        self.health_monitor = health_monitor or HealthMonitor()
        self.error_handler = error_handler or ErrorHandler()
        self.rate_limiter = rate_limiter or AdaptiveRateLimiter(
            initial_delay=5.0,
            slow_mode_delay=10.0,
            error_threshold=0.5,
            window_size=10
        )
        self.retry_strategy = retry_strategy or RetryStrategy(
            max_attempts=3,
            initial_delay=10.0,
            max_delay=60.0,
            exponential_base=2.0,
            jitter_range=(1.0, 3.0)
        )
        
        # Initialize sources in priority order
        # 1. SerpAPI (if configured) - most reliable
        # 2. DuckDuckGo - free fallback
        # 3. PyTrends - kept as last resort but often fails with 429
        sources_list = []
        
        # Try SerpAPI first if configured
        serpapi = SerpAPISource()
        if serpapi.api_key:
            sources_list.append(("serpapi", serpapi))
            logger.info("SerpAPI configured and will be used as primary trends source")
        
        # DuckDuckGo as free fallback
        sources_list.append(("duckduckgo", DuckDuckGoSearchFallback()))
        
        # PyTrends as last resort (often gets 429 errors)
        sources_list.append(("pytrends_direct", PyTrendsDirect()))
        
        # PyTrends with proxy if configured
        pytrends_proxy = PyTrendsWithProxy()
        if pytrends_proxy.proxy:
            sources_list.append(("pytrends_proxy", pytrends_proxy))
        
        self.sources = sources_list
        logger.info(f"Trends sources initialized: {[name for name, _ in self.sources]}")
    
    async def fetch_trends(
        self,
        term: str,
        window_days: int = 30
    ) -> DataResult:
        """
        Fetch trends data with automatic fallback and retry.
        
        Args:
            term: Search term
            window_days: Time window in days
            
        Returns:
            DataResult with trends data and metadata
        """
        cache_key = f"trends_{term}_{window_days}"
        attempted_sources = []
        errors = []
        
        # Check cache first
        cached_data = await self.cache_layer.get(cache_key, allow_stale=False)
        if cached_data is not None and not cached_data.is_stale:
            cache_age = int(
                (datetime.now() - cached_data.cached_at).total_seconds()
            )
            logger.debug(f"Cache hit for trends {term}")
            return DataResult(
                data=cached_data.data,
                source_used=cached_data.source,
                is_cached=True,
                cache_age_seconds=cache_age,
                is_stale=False,
                attempted_sources=[],
                successful_sources=[cached_data.source],
                failed_sources=[],
                errors=[],
                partial_data=False,
                last_successful_update=cached_data.cached_at
            )
        
        # Try each source with retry logic
        for source_name, source_instance in self.sources:
            attempted_sources.append(source_name)
            
            # Try with retry and backoff
            result = await self._fetch_with_retry(
                source_name,
                source_instance,
                term,
                window_days
            )
            
            if result is not None:
                # Success - cache and return
                await self.cache_layer.set(
                    key=cache_key,
                    data=result,
                    source=source_name,
                    ttl_disk=86400  # 24 hours
                )
                
                logger.info(f"Successfully fetched trends for {term} from {source_name}")
                
                # Determine partial data status
                partial_data = len(errors) > 0
                failed_sources = [err.source for err in errors]
                
                return DataResult(
                    data=result,
                    source_used=source_name,
                    is_cached=False,
                    cache_age_seconds=None,
                    is_stale=False,
                    attempted_sources=attempted_sources,
                    successful_sources=[source_name],
                    failed_sources=failed_sources,
                    errors=errors,
                    partial_data=partial_data,
                    last_successful_update=datetime.now()
                )
            else:
                # Failed - classify error and continue to next source
                error_info = self.error_handler.classify_error(
                    source=source_name,
                    error=Exception(f"Failed to fetch from {source_name}"),
                    context=f"trends fetch for {term}"
                )
                errors.append(error_info)
                continue
        
        # All sources failed - try stale cache
        cached_data = await self.cache_layer.get(cache_key, allow_stale=True)
        if cached_data is not None:
            cache_age = int(
                (datetime.now() - cached_data.cached_at).total_seconds()
            )
            logger.warning(f"All sources failed, returning stale cache for {term}")
            failed_sources = [err.source for err in errors]
            return DataResult(
                data=cached_data.data,
                source_used=cached_data.source,
                is_cached=True,
                cache_age_seconds=cache_age,
                is_stale=True,
                attempted_sources=attempted_sources,
                successful_sources=[],
                failed_sources=failed_sources,
                errors=errors,
                partial_data=True,
                last_successful_update=cached_data.cached_at
            )
        
        # No data available
        logger.error(f"All sources failed and no cache for {term}")
        failed_sources = [err.source for err in errors]
        return DataResult(
            data=None,
            source_used="none",
            is_cached=False,
            cache_age_seconds=None,
            is_stale=False,
            attempted_sources=attempted_sources,
            successful_sources=[],
            failed_sources=failed_sources,
            errors=errors,
            partial_data=False,
            last_successful_update=None
        )
    
    async def _fetch_with_retry(
        self,
        source_name: str,
        source_instance: Any,
        term: str,
        window_days: int
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch from a source with retry and exponential backoff.
        
        PyTrends sources get only 1 attempt since retries don't help with 429 errors.
        Other sources use full retry strategy.
        
        Args:
            source_name: Name of the source
            source_instance: Source instance to fetch from
            term: Search term
            window_days: Time window in days
            
        Returns:
            Trends data or None if all retries failed
        """
        # PyTrends sources: only 1 attempt (retries don't help with 429)
        max_attempts = 1 if 'pytrends' in source_name else self.retry_strategy.max_attempts
        
        for attempt in range(max_attempts):
            try:
                # Apply rate limiting
                await self.rate_limiter.acquire()
                
                # Record start time
                start_time = datetime.now()
                
                # Fetch data
                data = await source_instance.fetch_trends(term, window_days)
                
                # Calculate latency
                latency_ms = int(
                    (datetime.now() - start_time).total_seconds() * 1000
                )
                
                # Record success
                self.health_monitor.record_request(
                    source=source_name,
                    success=True,
                    latency_ms=latency_ms
                )
                self.rate_limiter.record_success()
                
                return data
                
            except Exception as e:
                error_msg = str(e).lower()
                
                # Calculate latency
                latency_ms = int(
                    (datetime.now() - start_time).total_seconds() * 1000
                )
                
                # Check if it's a 429 rate limit error
                is_rate_limit = (
                    '429' in error_msg or 
                    'rate' in error_msg or 
                    'quota' in error_msg
                )
                
                # Record failure
                error_type = "rate_limit" if is_rate_limit else "api_error"
                self.health_monitor.record_request(
                    source=source_name,
                    success=False,
                    latency_ms=latency_ms,
                    error_type=error_type
                )
                self.rate_limiter.record_error()
                
                # For PyTrends 429 errors, skip retry and move to next source
                if 'pytrends' in source_name and is_rate_limit:
                    logger.warning(
                        f"PyTrends rate limit (429) for {term} - skipping retries, "
                        f"will try next source"
                    )
                    return None
                
                # Handle other errors with retry
                if attempt < max_attempts - 1:
                    delay = self.retry_strategy.get_next_delay(attempt)
                    logger.warning(
                        f"Error on {source_name} for {term}, "
                        f"retrying in {delay:.1f}s (attempt {attempt + 1}/{max_attempts})"
                    )
                    await asyncio.sleep(delay)
                    continue
                else:
                    # Final attempt failed
                    logger.error(
                        f"Error fetching from {source_name} for {term}: {e}"
                    )
                    return None
        
        # All retries exhausted
        logger.error(
            f"All {max_attempts} retry attempts exhausted for {source_name}"
        )
        return None
    
    def get_rate_limiter_stats(self) -> Dict[str, Any]:
        """Get rate limiter statistics."""
        return self.rate_limiter.get_stats()
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get health status of all sources."""
        all_status = self.health_monitor.get_all_health_status()
        return {
            name: {
                "success_rate": status.success_rate,
                "avg_latency_ms": status.avg_latency_ms,
                "total_requests": status.total_requests,
                "status": status.status,
                "last_success": (
                    status.last_success.isoformat() 
                    if status.last_success else None
                )
            }
            for name, status in all_status.items()
        }
