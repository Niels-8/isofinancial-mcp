"""
Test suite for Trends Source Manager with rate limiting and fallback.

Tests the Google Trends improvements including adaptive rate limiting,
retry with exponential backoff, and multi-source fallback.
"""

import pytest
from datetime import datetime
from typing import Dict, Any

from iso_financial_mcp.datasources.trends_source_manager import (
    TrendsSourceManager,
    PyTrendsDirect,
    PyTrendsWithProxy,
    SerpAPIFallback
)
from iso_financial_mcp.reliability.adaptive_rate_limiter import AdaptiveRateLimiter
from iso_financial_mcp.reliability.models import DataResult, RetryStrategy


class TestTrendsSourceManager:
    """Test suite for Trends Source Manager"""
    
    def test_trends_source_manager_initialization(self):
        """Test that Trends Source Manager initializes correctly"""
        manager = TrendsSourceManager()
        
        assert manager is not None
        assert manager.cache_layer is not None
        assert manager.health_monitor is not None
        assert manager.rate_limiter is not None
        assert manager.retry_strategy is not None
        assert len(manager.sources) == 3
        
        # Verify source names
        source_names = [name for name, _ in manager.sources]
        assert "pytrends_direct" in source_names
        assert "pytrends_proxy" in source_names
        assert "serpapi_fallback" in source_names
    
    def test_pytrends_direct_initialization(self):
        """Test that PyTrends Direct source initializes correctly"""
        source = PyTrendsDirect()
        
        assert source is not None
        assert source.name == "pytrends_direct"
    
    def test_pytrends_proxy_initialization(self):
        """Test that PyTrends Proxy source initializes correctly"""
        source = PyTrendsWithProxy()
        
        assert source is not None
        assert source.name == "pytrends_proxy"
    
    def test_serpapi_fallback_initialization(self):
        """Test that SerpAPI Fallback source initializes correctly"""
        source = SerpAPIFallback()
        
        assert source is not None
        assert source.name == "serpapi_fallback"
        assert source.base_url == "https://serpapi.com/search"


class TestAdaptiveRateLimiter:
    """Test suite for Adaptive Rate Limiter"""
    
    def test_adaptive_rate_limiter_initialization(self):
        """Test that Adaptive Rate Limiter initializes correctly"""
        limiter = AdaptiveRateLimiter(
            initial_delay=5.0,
            slow_mode_delay=10.0,
            error_threshold=0.5,
            window_size=10
        )
        
        assert limiter is not None
        assert limiter.initial_delay == 5.0
        assert limiter.slow_mode_delay == 10.0
        assert limiter.error_threshold == 0.5
        assert limiter.window_size == 10
        assert limiter.slow_mode_active is False
    
    def test_rate_limiter_error_tracking(self):
        """Test that rate limiter tracks errors correctly"""
        limiter = AdaptiveRateLimiter(
            initial_delay=5.0,
            slow_mode_delay=10.0,
            error_threshold=0.5,
            window_size=10
        )
        
        # Record some successes
        limiter.record_success()
        limiter.record_success()
        limiter.record_success()
        
        assert limiter.get_error_rate() == 0.0
        assert limiter.is_slow_mode() is False
        
        # Record errors to trigger slow mode
        for _ in range(6):
            limiter.record_error()
        
        # Should now be in slow mode (6 errors out of 9 = 66% > 50%)
        assert limiter.get_error_rate() > 0.5
        assert limiter.is_slow_mode() is True
    
    def test_rate_limiter_stats(self):
        """Test that rate limiter provides correct stats"""
        limiter = AdaptiveRateLimiter()
        
        limiter.record_success()
        limiter.record_error()
        
        stats = limiter.get_stats()
        
        assert "slow_mode_active" in stats
        assert "error_rate" in stats
        assert "recent_requests_count" in stats
        assert "current_delay" in stats
        assert stats["recent_requests_count"] == 2


class TestRetryStrategy:
    """Test suite for Retry Strategy"""
    
    def test_retry_strategy_initialization(self):
        """Test that Retry Strategy initializes correctly"""
        strategy = RetryStrategy(
            max_attempts=3,
            initial_delay=10.0,
            max_delay=60.0,
            exponential_base=2.0,
            jitter_range=(1.0, 3.0)
        )
        
        assert strategy is not None
        assert strategy.max_attempts == 3
        assert strategy.initial_delay == 10.0
        assert strategy.max_delay == 60.0
        assert strategy.exponential_base == 2.0
        assert strategy.jitter_range == (1.0, 3.0)
    
    def test_retry_strategy_exponential_backoff(self):
        """Test that retry strategy calculates exponential backoff correctly"""
        strategy = RetryStrategy(
            max_attempts=3,
            initial_delay=10.0,
            max_delay=60.0,
            exponential_base=2.0,
            jitter_range=(1.0, 3.0)
        )
        
        # First attempt: 10 * 2^0 = 10 + jitter (1-3) = 11-13
        delay_0 = strategy.get_next_delay(0)
        assert 11.0 <= delay_0 <= 13.0
        
        # Second attempt: 10 * 2^1 = 20 + jitter (1-3) = 21-23
        delay_1 = strategy.get_next_delay(1)
        assert 21.0 <= delay_1 <= 23.0
        
        # Third attempt: 10 * 2^2 = 40 + jitter (1-3) = 41-43
        delay_2 = strategy.get_next_delay(2)
        assert 41.0 <= delay_2 <= 43.0
        
        # Fourth attempt: 10 * 2^3 = 80, but capped at max_delay 60 + jitter = 61-63
        delay_3 = strategy.get_next_delay(3)
        assert 61.0 <= delay_3 <= 63.0
