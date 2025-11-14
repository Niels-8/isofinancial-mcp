"""
Data models for reliability infrastructure.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
import random


@dataclass
class ErrorInfo:
    """Information about an error."""
    source: str
    error_type: str  # "rate_limit", "timeout", "not_found", "api_error"
    error_message: str
    is_temporary: bool
    suggested_action: str
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class DataResult:
    """Result of a data fetch operation."""
    data: Any
    source_used: str
    is_cached: bool
    cache_age_seconds: Optional[int] = None
    is_stale: bool = False
    attempted_sources: List[str] = field(default_factory=list)
    successful_sources: List[str] = field(default_factory=list)
    failed_sources: List[str] = field(default_factory=list)
    errors: List[ErrorInfo] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)
    partial_data: bool = False
    last_successful_update: Optional[datetime] = None


@dataclass
class CachedData:
    """Cached data with metadata."""
    data: Any
    cached_at: datetime
    expires_at: datetime
    is_stale: bool
    source: str


@dataclass
class HealthStatus:
    """Health status of a data source."""
    source: str
    success_rate: float  # 0.0 to 1.0
    avg_latency_ms: int
    total_requests: int
    recent_errors: List[str]
    last_success: Optional[datetime]
    status: str  # "healthy", "degraded", "unhealthy"


@dataclass
class SourceConfig:
    """Configuration for a data source."""
    name: str
    enabled: bool = True
    priority: int = 1  # 1 = highest
    timeout_seconds: int = 10
    max_retries: int = 2
    retry_delay_seconds: float = 1.0
    rate_limit_per_second: float = 1.0
    requires_api_key: bool = False
    api_key_env_var: Optional[str] = None


@dataclass
class RetryStrategy:
    """Retry strategy for a source."""
    max_attempts: int = 3
    initial_delay: float = 10.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter_range: Tuple[float, float] = (1.0, 3.0)
    
    def get_next_delay(self, attempt: int) -> float:
        """Calculate delay for next retry attempt."""
        base_delay = min(
            self.initial_delay * (self.exponential_base ** attempt),
            self.max_delay
        )
        jitter = random.uniform(*self.jitter_range)
        return base_delay + jitter
