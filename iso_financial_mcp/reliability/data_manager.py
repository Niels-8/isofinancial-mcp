"""
Data Manager for orchestrating data fetches with fallback.
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from .cache_layer import CacheLayer
from .health_monitor import HealthMonitor
from .error_handler import ErrorHandler
from .models import DataResult, ErrorInfo

logger = logging.getLogger(__name__)


class DataManager:
    """
    Orchestrates data fetching with automatic fallback and caching.
    """
    
    def __init__(
        self,
        cache_layer: Optional[CacheLayer] = None,
        health_monitor: Optional[HealthMonitor] = None,
        error_handler: Optional[ErrorHandler] = None
    ):
        """
        Initialize data manager.
        
        Args:
            cache_layer: Cache layer instance (creates default if None)
            health_monitor: Health monitor instance (creates default if None)
            error_handler: Error handler instance (creates default if None)
        """
        self.cache_layer = cache_layer or CacheLayer()
        self.health_monitor = health_monitor or HealthMonitor()
        self.error_handler = error_handler or ErrorHandler()
    
    async def fetch_with_fallback(
        self,
        cache_key: str,
        sources: List[tuple[str, Callable]],
        **kwargs
    ) -> DataResult:
        """
        Fetch data with automatic fallback between sources.
        
        Args:
            cache_key: Key for caching the result
            sources: List of (source_name, fetch_function) tuples
            **kwargs: Arguments to pass to fetch functions
            
        Returns:
            DataResult with data and metadata
        """
        attempted_sources = []
        errors = []
        
        # Check cache first
        cached_data = await self.cache_layer.get(cache_key, allow_stale=False)
        if cached_data is not None and not cached_data.is_stale:
            cache_age = int(
                (datetime.now() - cached_data.cached_at).total_seconds()
            )
            logger.debug(
                f"Cache hit for {cache_key} (age: {cache_age}s, "
                f"source: {cached_data.source})"
            )
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
                timestamp=datetime.now(),
                partial_data=False,
                last_successful_update=cached_data.cached_at
            )
        
        # Try each source in order
        for source_name, fetch_func in sources:
            attempted_sources.append(source_name)
            
            try:
                start_time = datetime.now()
                
                # Call fetch function
                data = await fetch_func(**kwargs)
                
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
                
                # Cache the result
                await self.cache_layer.set(
                    key=cache_key,
                    data=data,
                    source=source_name
                )
                
                logger.info(
                    f"Successfully fetched from {source_name} "
                    f"(latency: {latency_ms}ms)"
                )
                
                # Determine if we have partial data (some sources failed before success)
                partial_data = len(errors) > 0
                failed_sources = [err.source for err in errors]
                
                return DataResult(
                    data=data,
                    source_used=source_name,
                    is_cached=False,
                    cache_age_seconds=None,
                    is_stale=False,
                    attempted_sources=attempted_sources,
                    successful_sources=[source_name],
                    failed_sources=failed_sources,
                    errors=errors,
                    timestamp=datetime.now(),
                    partial_data=partial_data,
                    last_successful_update=datetime.now()
                )
                
            except Exception as e:
                # Calculate latency
                latency_ms = int(
                    (datetime.now() - start_time).total_seconds() * 1000
                )
                
                # Classify error using ErrorHandler
                error_info = self.error_handler.classify_error(source_name, e)
                errors.append(error_info)
                
                # Record failure
                self.health_monitor.record_request(
                    source=source_name,
                    success=False,
                    latency_ms=latency_ms,
                    error_type=error_info.error_type
                )
                
                logger.warning(
                    f"Failed to fetch from {source_name}: {error_info.error_message}"
                )
                
                # Continue to next source
                continue
        
        # All sources failed - try stale cache as last resort
        cached_data = await self.cache_layer.get(cache_key, allow_stale=True)
        if cached_data is not None:
            cache_age = int(
                (datetime.now() - cached_data.cached_at).total_seconds()
            )
            logger.warning(
                f"All sources failed, returning stale cache for {cache_key} "
                f"(age: {cache_age}s)"
            )
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
                timestamp=datetime.now(),
                partial_data=True,  # Stale data is partial data
                last_successful_update=cached_data.cached_at
            )
        
        # No data available at all
        logger.error(
            f"All sources failed and no cache available for {cache_key}"
        )
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
            timestamp=datetime.now(),
            partial_data=False,
            last_successful_update=None
        )
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return await self.cache_layer.get_cache_stats()
    
    def get_health_status(self, source: Optional[str] = None) -> Dict[str, Any]:
        """
        Get health status for sources.
        
        Args:
            source: Specific source name, or None for all sources
            
        Returns:
            Health status dictionary
        """
        if source:
            status = self.health_monitor.get_health_status(source)
            return {
                "source": status.source,
                "success_rate": status.success_rate,
                "avg_latency_ms": status.avg_latency_ms,
                "total_requests": status.total_requests,
                "status": status.status,
                "last_success": status.last_success.isoformat() if status.last_success else None
            }
        else:
            all_status = self.health_monitor.get_all_health_status()
            return {
                name: {
                    "success_rate": status.success_rate,
                    "avg_latency_ms": status.avg_latency_ms,
                    "total_requests": status.total_requests,
                    "status": status.status,
                    "last_success": status.last_success.isoformat() if status.last_success else None
                }
                for name, status in all_status.items()
            }
