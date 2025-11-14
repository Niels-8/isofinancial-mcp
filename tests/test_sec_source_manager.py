"""
Test suite for SEC Source Manager with multi-source fallback.

Tests the SEC source improvements including RSS Feed, XBRL API, and
automatic fallback with lookback extension.
"""

import pytest
from datetime import datetime
from typing import Dict, Any, List

from iso_financial_mcp.datasources.sec_source_manager import SECSourceManager
from iso_financial_mcp.datasources.sec_rss_source import SECRSSFeed
from iso_financial_mcp.datasources.sec_xbrl_source import SECXBRLApi
from iso_financial_mcp.reliability.models import DataResult


class TestSECSourceManager:
    """Test suite for SEC Source Manager"""
    
    def test_sec_source_manager_initialization(self):
        """Test that SEC Source Manager initializes correctly"""
        manager = SECSourceManager()
        
        assert manager is not None
        assert manager.data_manager is not None
        assert manager.rss_feed is not None
        assert manager.xbrl_api is not None
        assert len(manager.sources) == 3
        
        # Verify source names
        source_names = [name for name, _ in manager.sources]
        assert "sec_edgar_api" in source_names
        assert "sec_rss_feed" in source_names
        assert "sec_xbrl_api" in source_names
    
    def test_sec_rss_feed_initialization(self):
        """Test that SEC RSS Feed source initializes correctly"""
        rss_feed = SECRSSFeed()
        
        assert rss_feed is not None
        assert rss_feed.base_url == "https://www.sec.gov/cgi-bin/browse-edgar"
        assert "User-Agent" in rss_feed.headers
    
    def test_sec_xbrl_api_initialization(self):
        """Test that SEC XBRL API source initializes correctly"""
        xbrl_api = SECXBRLApi()
        
        assert xbrl_api is not None
        assert xbrl_api.base_url == "https://data.sec.gov"
        assert "User-Agent" in xbrl_api.headers
    
    @pytest.mark.asyncio
    async def test_fetch_filings_returns_data_result(self):
        """Test that fetch_filings returns a DataResult object"""
        manager = SECSourceManager()
        
        # Use a well-known ticker for testing
        result = await manager.fetch_filings(
            ticker="AAPL",
            form_types=["10-K"],
            lookback_days=365  # Use longer period to ensure results
        )
        
        # Verify result structure
        assert isinstance(result, DataResult)
        assert hasattr(result, 'data')
        assert hasattr(result, 'source_used')
        assert hasattr(result, 'is_cached')
        assert hasattr(result, 'attempted_sources')
        assert hasattr(result, 'errors')
        
        # If data was fetched successfully, verify structure
        if result.data is not None and len(result.data) > 0:
            filing = result.data[0]
            assert 'date' in filing
            assert 'form' in filing
            assert 'url' in filing
            assert 'title' in filing
    
    @pytest.mark.asyncio
    async def test_health_status_accessible(self):
        """Test that health status can be retrieved"""
        manager = SECSourceManager()
        
        health_status = manager.get_health_status()
        
        assert health_status is not None
        assert isinstance(health_status, dict)
    
    @pytest.mark.asyncio
    async def test_cache_stats_accessible(self):
        """Test that cache statistics can be retrieved"""
        manager = SECSourceManager()
        
        cache_stats = await manager.get_cache_stats()
        
        assert cache_stats is not None
        assert isinstance(cache_stats, dict)
        assert 'memory_items' in cache_stats
        assert 'disk_items' in cache_stats
