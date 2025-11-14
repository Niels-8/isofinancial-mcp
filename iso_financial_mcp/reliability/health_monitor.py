"""
Health Monitor for tracking data source reliability.
"""

import asyncio
import json
import logging
import os
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

import aiofiles

from .models import HealthStatus

logger = logging.getLogger(__name__)


class HealthMonitor:
    """
    Monitors health of data sources with metrics tracking.
    """
    
    def __init__(
        self,
        window_size: int = 100,
        unhealthy_threshold: float = 0.3,
        metrics_retention_days: int = 7,
        log_path: Optional[str] = None
    ):
        """
        Initialize health monitor.
        
        Args:
            window_size: Number of recent requests to track
            unhealthy_threshold: Failure rate threshold for unhealthy status
            metrics_retention_days: Days to retain metrics
            log_path: Path for metrics log file
        """
        self.window_size = window_size
        self.unhealthy_threshold = unhealthy_threshold
        self.metrics_retention_days = metrics_retention_days
        
        # Set up log path
        if log_path is None:
            log_path = os.path.expanduser("~/.iso_financial_mcp/health_metrics.jsonl")
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Metrics storage: source -> deque of (success, latency_ms, timestamp)
        self._metrics: Dict[str, deque] = {}
        
        # Recent errors: source -> list of error messages
        self._recent_errors: Dict[str, deque] = {}
        
        # Last success timestamp: source -> datetime
        self._last_success: Dict[str, datetime] = {}
        
        self._lock = asyncio.Lock()
    
    def record_request(
        self,
        source: str,
        success: bool,
        latency_ms: int,
        error_type: Optional[str] = None
    ):
        """
        Record a request result.
        
        Args:
            source: Source name
            success: Whether request succeeded
            latency_ms: Request latency in milliseconds
            error_type: Type of error if failed
        """
        timestamp = datetime.now()
        
        # Initialize source metrics if needed
        if source not in self._metrics:
            self._metrics[source] = deque(maxlen=self.window_size)
            self._recent_errors[source] = deque(maxlen=10)
        
        # Record metric
        self._metrics[source].append((success, latency_ms, timestamp))
        
        # Update last success
        if success:
            self._last_success[source] = timestamp
        else:
            # Record error
            if error_type:
                self._recent_errors[source].append(error_type)
        
        # Log to file asynchronously
        asyncio.create_task(self._log_metric(source, success, latency_ms, error_type))
    
    async def _log_metric(
        self,
        source: str,
        success: bool,
        latency_ms: int,
        error_type: Optional[str]
    ):
        """Log metric to JSONL file."""
        try:
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "source": source,
                "success": success,
                "latency_ms": latency_ms,
                "error_type": error_type
            }
            
            async with aiofiles.open(self.log_path, 'a') as f:
                await f.write(json.dumps(log_entry) + '\n')
        except Exception as e:
            logger.error(f"Error logging metric: {e}")
    
    def get_health_status(self, source: str) -> HealthStatus:
        """
        Get health status for a source.
        
        Args:
            source: Source name
            
        Returns:
            HealthStatus object
        """
        if source not in self._metrics or not self._metrics[source]:
            return HealthStatus(
                source=source,
                success_rate=0.0,
                avg_latency_ms=0,
                total_requests=0,
                recent_errors=[],
                last_success=None,
                status="unknown"
            )
        
        metrics = self._metrics[source]
        
        # Calculate success rate
        successes = sum(1 for success, _, _ in metrics if success)
        total = len(metrics)
        success_rate = successes / total if total > 0 else 0.0
        
        # Calculate average latency
        latencies = [latency for _, latency, _ in metrics]
        avg_latency_ms = int(sum(latencies) / len(latencies)) if latencies else 0
        
        # Get recent errors
        recent_errors = list(self._recent_errors.get(source, []))
        
        # Get last success
        last_success = self._last_success.get(source)
        
        # Determine status
        if success_rate >= 0.7:
            status = "healthy"
        elif success_rate >= self.unhealthy_threshold:
            status = "degraded"
        else:
            status = "unhealthy"
        
        # Log warning for unhealthy sources
        if status == "unhealthy":
            logger.warning(
                f"Source {source} is unhealthy: "
                f"success_rate={success_rate:.2%}, "
                f"recent_errors={recent_errors[:3]}"
            )
        
        return HealthStatus(
            source=source,
            success_rate=success_rate,
            avg_latency_ms=avg_latency_ms,
            total_requests=total,
            recent_errors=recent_errors,
            last_success=last_success,
            status=status
        )
    
    def get_all_health_status(self) -> Dict[str, HealthStatus]:
        """
        Get health status for all sources.
        
        Returns:
            Dictionary mapping source names to HealthStatus
        """
        return {
            source: self.get_health_status(source)
            for source in self._metrics.keys()
        }
    
    def is_source_healthy(self, source: str) -> bool:
        """
        Check if a source is healthy.
        
        Args:
            source: Source name
            
        Returns:
            True if source is healthy or degraded, False if unhealthy
        """
        status = self.get_health_status(source)
        return status.status in ("healthy", "degraded")
    
    async def cleanup_old_metrics(self):
        """Clean up old metrics from log file."""
        try:
            if not self.log_path.exists():
                return
            
            cutoff_date = datetime.now().timestamp() - (
                self.metrics_retention_days * 24 * 3600
            )
            
            # Read and filter log entries
            temp_path = self.log_path.with_suffix('.tmp')
            kept_count = 0
            
            async with aiofiles.open(self.log_path, 'r') as infile:
                async with aiofiles.open(temp_path, 'w') as outfile:
                    async for line in infile:
                        try:
                            entry = json.loads(line)
                            entry_time = datetime.fromisoformat(
                                entry['timestamp']
                            ).timestamp()
                            
                            if entry_time >= cutoff_date:
                                await outfile.write(line)
                                kept_count += 1
                        except Exception as e:
                            logger.error(f"Error processing log entry: {e}")
            
            # Replace old file with filtered file
            temp_path.replace(self.log_path)
            logger.info(
                f"Cleaned up metrics log, kept {kept_count} recent entries"
            )
            
        except Exception as e:
            logger.error(f"Error cleaning up metrics: {e}")
