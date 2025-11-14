"""
Adaptive Rate Limiter for Google Trends with automatic slow mode.
"""

import asyncio
import logging
import time
from collections import deque
from typing import Optional

logger = logging.getLogger(__name__)


class AdaptiveRateLimiter:
    """
    Rate limiter that adapts based on error rates.
    
    Automatically activates slow mode when error rate exceeds threshold.
    """
    
    def __init__(
        self,
        initial_delay: float = 5.0,
        slow_mode_delay: float = 10.0,
        error_threshold: float = 0.5,
        window_size: int = 10
    ):
        """
        Initialize adaptive rate limiter.
        
        Args:
            initial_delay: Default delay between requests in seconds (1/5s = 5s)
            slow_mode_delay: Delay when in slow mode in seconds
            error_threshold: Error rate threshold to trigger slow mode (0.5 = 50%)
            window_size: Number of recent requests to track for error rate
        """
        self.initial_delay = initial_delay
        self.slow_mode_delay = slow_mode_delay
        self.error_threshold = error_threshold
        self.window_size = window_size
        
        # Track recent requests (True = success, False = error)
        self.recent_requests = deque(maxlen=window_size)
        
        # Track last request time
        self.last_request_time: Optional[float] = None
        
        # Slow mode flag
        self.slow_mode_active = False
        
        # Lock for thread safety
        self._lock = asyncio.Lock()
    
    async def acquire(self):
        """
        Acquire permission to make a request.
        
        Blocks until enough time has passed since last request.
        """
        async with self._lock:
            now = time.time()
            
            # Determine current delay
            current_delay = (
                self.slow_mode_delay if self.slow_mode_active 
                else self.initial_delay
            )
            
            # Calculate time to wait
            if self.last_request_time is not None:
                elapsed = now - self.last_request_time
                wait_time = max(0, current_delay - elapsed)
                
                if wait_time > 0:
                    logger.debug(
                        f"Rate limiting: waiting {wait_time:.2f}s "
                        f"(slow_mode: {self.slow_mode_active})"
                    )
                    await asyncio.sleep(wait_time)
            
            # Update last request time
            self.last_request_time = time.time()
    
    def record_success(self):
        """Record a successful request."""
        self.recent_requests.append(True)
        self._update_slow_mode()
    
    def record_error(self):
        """Record a failed request."""
        self.recent_requests.append(False)
        self._update_slow_mode()
    
    def _update_slow_mode(self):
        """Update slow mode based on recent error rate."""
        if len(self.recent_requests) < 3:
            # Not enough data yet
            return
        
        # Calculate error rate
        error_count = sum(1 for success in self.recent_requests if not success)
        error_rate = error_count / len(self.recent_requests)
        
        # Update slow mode
        previous_mode = self.slow_mode_active
        self.slow_mode_active = error_rate > self.error_threshold
        
        # Log mode changes
        if self.slow_mode_active and not previous_mode:
            logger.warning(
                f"Activating slow mode: error rate {error_rate:.1%} "
                f"exceeds threshold {self.error_threshold:.1%}"
            )
        elif not self.slow_mode_active and previous_mode:
            logger.info(
                f"Deactivating slow mode: error rate {error_rate:.1%} "
                f"below threshold {self.error_threshold:.1%}"
            )
    
    def get_error_rate(self) -> float:
        """Get current error rate."""
        if not self.recent_requests:
            return 0.0
        
        error_count = sum(1 for success in self.recent_requests if not success)
        return error_count / len(self.recent_requests)
    
    def is_slow_mode(self) -> bool:
        """Check if slow mode is active."""
        return self.slow_mode_active
    
    def get_stats(self) -> dict:
        """Get rate limiter statistics."""
        return {
            "slow_mode_active": self.slow_mode_active,
            "error_rate": self.get_error_rate(),
            "recent_requests_count": len(self.recent_requests),
            "current_delay": (
                self.slow_mode_delay if self.slow_mode_active 
                else self.initial_delay
            )
        }
    
    def reset(self):
        """Reset the rate limiter state."""
        self.recent_requests.clear()
        self.last_request_time = None
        self.slow_mode_active = False
        logger.info("Rate limiter reset")
