"""
Source Router for intelligent source selection based on health.
"""

import logging
from typing import Callable, List, Tuple

from .health_monitor import HealthMonitor

logger = logging.getLogger(__name__)


class SourceRouter:
    """
    Routes requests to sources based on health metrics.
    """
    
    def __init__(
        self,
        health_monitor: HealthMonitor,
        unhealthy_threshold: float = 0.3
    ):
        """
        Initialize source router.
        
        Args:
            health_monitor: Health monitor instance
            unhealthy_threshold: Success rate threshold for unhealthy sources
        """
        self.health_monitor = health_monitor
        self.unhealthy_threshold = unhealthy_threshold
    
    def get_ordered_sources(
        self,
        sources: List[Tuple[str, Callable]],
        skip_unhealthy: bool = True
    ) -> List[Tuple[str, Callable]]:
        """
        Order sources by health and priority.
        
        Args:
            sources: List of (source_name, fetch_function) tuples
            skip_unhealthy: If True, skip sources with success_rate < threshold
            
        Returns:
            Ordered list of (source_name, fetch_function) tuples
        """
        # Get health status for all sources
        source_health = []
        
        for source_name, fetch_func in sources:
            health = self.health_monitor.get_health_status(source_name)
            
            # Skip unhealthy sources if requested
            if skip_unhealthy and health.success_rate < self.unhealthy_threshold:
                logger.info(
                    f"Skipping unhealthy source {source_name} "
                    f"(success_rate: {health.success_rate:.2%})"
                )
                continue
            
            source_health.append({
                "name": source_name,
                "func": fetch_func,
                "success_rate": health.success_rate,
                "avg_latency_ms": health.avg_latency_ms,
                "total_requests": health.total_requests
            })
        
        # Sort by priority:
        # 1. Success rate (higher is better)
        # 2. Latency (lower is better)
        # 3. Total requests (more data is better)
        source_health.sort(
            key=lambda x: (
                -x["success_rate"],  # Negative for descending
                x["avg_latency_ms"],  # Ascending
                -x["total_requests"]  # Negative for descending
            )
        )
        
        # Return ordered list
        ordered = [(s["name"], s["func"]) for s in source_health]
        
        if ordered:
            logger.debug(
                f"Ordered sources: {[name for name, _ in ordered]}"
            )
        else:
            # If all sources were filtered out, return original list
            logger.warning(
                "All sources filtered as unhealthy, using original order"
            )
            ordered = sources
        
        return ordered
    
    def filter_healthy_sources(
        self,
        sources: List[Tuple[str, Callable]]
    ) -> List[Tuple[str, Callable]]:
        """
        Filter to only healthy sources.
        
        Args:
            sources: List of (source_name, fetch_function) tuples
            
        Returns:
            Filtered list of healthy sources
        """
        healthy = []
        
        for source_name, fetch_func in sources:
            if self.health_monitor.is_source_healthy(source_name):
                healthy.append((source_name, fetch_func))
            else:
                logger.debug(f"Filtered out unhealthy source: {source_name}")
        
        return healthy if healthy else sources  # Return all if none healthy
    
    def get_best_source(
        self,
        sources: List[Tuple[str, Callable]]
    ) -> Tuple[str, Callable]:
        """
        Get the single best source based on health.
        
        Args:
            sources: List of (source_name, fetch_function) tuples
            
        Returns:
            Best (source_name, fetch_function) tuple
        """
        ordered = self.get_ordered_sources(sources, skip_unhealthy=False)
        return ordered[0] if ordered else sources[0]
