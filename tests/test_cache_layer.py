"""
Test suite for Cache Layer with two-level caching.

Tests memory cache, disk cache, TTL expiration, and stale data fallback.
Requirements: 5.1, 5.2, 5.3, 5.4, 5.5
"""

import pytest
import asyncio
import tempfile
import shutil
from datetime import datetime, timedelta
from pathlib import Path

from iso_financial_mcp.reliability.cache_layer import CacheLayer
from iso_financial_mcp.reliability.models import CachedData

# Configure pytest for anyio
pytestmark = pytest.mark.anyio


class TestCacheLayerInitialization:
    """Test cache layer initialization"""
    
    def test_cache_layer_init_default(self):
        """Test cache layer initializes with default parameters"""
        cache = CacheLayer()
        
        assert cache is not None
        assert cache.memory_cache is not None
        assert cache.memory_ttl == 3600
        assert cache.disk_ttl == 604800
        assert cache.disk_path.exists()
    
    def test_cache_layer_init_custom(self):
        """Test cache layer initializes with custom parameters"""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = CacheLayer(
                memory_maxsize=500,
                memory_ttl=1800,
                disk_ttl=86400,
                disk_path=tmpdir,
                max_disk_size_mb=100
            )
            
            assert cache.memory_cache.maxsize == 500
            assert cache.memory_ttl == 1800
            assert cache.disk_ttl == 86400
            assert str(cache.disk_path) == tmpdir
            assert cache.max_disk_size_mb == 100


class TestMemoryCache:
    """Test memory cache with TTL expiration - Requirement 5.1"""
    
    @pytest.mark.anyio
    async def test_memory_cache_set_and_get(self):
        """Test basic memory cache set and get operations"""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = CacheLayer(disk_path=tmpdir)
            
            # Set data in cache
            await cache.set(
                key="test_key",
                data={"value": 123},
                source="test_source"
            )
            
            # Get data from cache
            cached_data = await cache.get("test_key")
            
            assert cached_data is not None
            assert cached_data.data == {"value": 123}
            assert cached_data.source == "test_source"
            assert cached_data.is_stale is False
    
    @pytest.mark.anyio
    async def test_memory_cache_ttl_expiration(self):
        """Test memory cache TTL expiration - Requirement 5.1"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create cache with very short TTL (1 second)
            cache = CacheLayer(
                memory_ttl=1,
                disk_path=tmpdir
            )
            
            # Set data
            await cache.set(
                key="test_key",
                data={"value": 123},
                source="test_source"
            )
            
            # Should be available immediately
            cached_data = await cache.get("test_key")
            assert cached_data is not None
            
            # Wait for TTL to expire
            await asyncio.sleep(1.5)
            
            # Memory cache should be expired, but disk cache should still have it
            cached_data = await cache.get("test_key")
            # Will get from disk cache
            assert cached_data is not None
    
    @pytest.mark.anyio
    async def test_memory_cache_miss(self):
        """Test memory cache miss returns None"""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = CacheLayer(disk_path=tmpdir)
            
            # Try to get non-existent key
            cached_data = await cache.get("nonexistent_key")
            
            assert cached_data is None


class TestDiskCache:
    """Test disk cache persistence - Requirement 5.3"""
    
    @pytest.mark.anyio
    async def test_disk_cache_persistence(self):
        """Test disk cache persists data across cache instances"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create first cache instance and store data
            cache1 = CacheLayer(disk_path=tmpdir)
            await cache1.set(
                key="persistent_key",
                data={"value": "persistent_data"},
                source="test_source"
            )
            
            # Create second cache instance (simulates restart)
            cache2 = CacheLayer(disk_path=tmpdir)
            
            # Should retrieve from disk
            cached_data = await cache2.get("persistent_key")
            
            assert cached_data is not None
            assert cached_data.data == {"value": "persistent_data"}
            assert cached_data.source == "test_source"
    
    @pytest.mark.anyio
    async def test_disk_cache_file_creation(self):
        """Test disk cache creates cache files"""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = CacheLayer(disk_path=tmpdir)
            
            await cache.set(
                key="test_key",
                data={"value": 123},
                source="test_source"
            )
            
            # Check that cache file was created
            cache_files = list(Path(tmpdir).glob("*.cache"))
            assert len(cache_files) == 1
    
    @pytest.mark.anyio
    async def test_disk_cache_multiple_keys(self):
        """Test disk cache handles multiple keys"""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = CacheLayer(disk_path=tmpdir)
            
            # Store multiple keys
            for i in range(5):
                await cache.set(
                    key=f"key_{i}",
                    data={"value": i},
                    source="test_source"
                )
            
            # Verify all keys are retrievable
            for i in range(5):
                cached_data = await cache.get(f"key_{i}")
                assert cached_data is not None
                assert cached_data.data == {"value": i}


class TestStaleDataFallback:
    """Test stale data fallback - Requirements 5.2, 5.5"""
    
    @pytest.mark.anyio
    async def test_stale_data_fallback_allowed(self):
        """Test stale data is returned when allow_stale=True - Requirement 5.2"""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = CacheLayer(
                memory_ttl=1,
                disk_ttl=1,
                disk_path=tmpdir
            )
            
            # Set data
            await cache.set(
                key="test_key",
                data={"value": "stale_data"},
                source="test_source"
            )
            
            # Wait for expiration
            await asyncio.sleep(1.5)
            
            # Get with allow_stale=True
            cached_data = await cache.get("test_key", allow_stale=True)
            
            assert cached_data is not None
            assert cached_data.data == {"value": "stale_data"}
            assert cached_data.is_stale is True
    
    @pytest.mark.anyio
    async def test_stale_data_not_returned_by_default(self):
        """Test stale data is not returned when allow_stale=False"""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = CacheLayer(
                memory_ttl=1,
                disk_ttl=1,
                disk_path=tmpdir
            )
            
            # Set data
            await cache.set(
                key="test_key",
                data={"value": "stale_data"},
                source="test_source"
            )
            
            # Wait for expiration
            await asyncio.sleep(1.5)
            
            # Get with allow_stale=False (default)
            cached_data = await cache.get("test_key", allow_stale=False)
            
            # Should return None for expired data
            assert cached_data is None
    
    @pytest.mark.anyio
    async def test_fresh_data_not_marked_stale(self):
        """Test fresh data is not marked as stale"""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = CacheLayer(disk_path=tmpdir)
            
            await cache.set(
                key="test_key",
                data={"value": "fresh_data"},
                source="test_source"
            )
            
            # Get immediately
            cached_data = await cache.get("test_key")
            
            assert cached_data is not None
            assert cached_data.is_stale is False


class TestCacheKeyGeneration:
    """Test cache key generation - Requirement 5.4"""
    
    @pytest.mark.anyio
    async def test_cache_key_generation_consistent(self):
        """Test cache key generation is consistent"""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = CacheLayer(disk_path=tmpdir)
            
            # Set data with a key
            await cache.set(
                key="ticker_AAPL",
                data={"value": 123},
                source="test_source"
            )
            
            # Retrieve with same key
            cached_data = await cache.get("ticker_AAPL")
            
            assert cached_data is not None
            assert cached_data.data == {"value": 123}
    
    @pytest.mark.anyio
    async def test_cache_key_generation_unique(self):
        """Test different keys generate different cache entries"""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = CacheLayer(disk_path=tmpdir)
            
            # Set data with different keys
            await cache.set(
                key="key1",
                data={"value": 1},
                source="source1"
            )
            await cache.set(
                key="key2",
                data={"value": 2},
                source="source2"
            )
            
            # Retrieve both
            data1 = await cache.get("key1")
            data2 = await cache.get("key2")
            
            assert data1.data == {"value": 1}
            assert data2.data == {"value": 2}
            assert data1.source == "source1"
            assert data2.source == "source2"


class TestCacheClear:
    """Test cache clearing operations"""
    
    @pytest.mark.anyio
    async def test_clear_specific_key(self):
        """Test clearing a specific cache key"""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = CacheLayer(disk_path=tmpdir)
            
            # Set multiple keys
            await cache.set("key1", {"value": 1}, "source1")
            await cache.set("key2", {"value": 2}, "source2")
            
            # Clear one key
            await cache.clear("key1")
            
            # key1 should be gone, key2 should remain
            assert await cache.get("key1") is None
            assert await cache.get("key2") is not None
    
    @pytest.mark.anyio
    async def test_clear_all_cache(self):
        """Test clearing all cache"""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = CacheLayer(disk_path=tmpdir)
            
            # Set multiple keys
            await cache.set("key1", {"value": 1}, "source1")
            await cache.set("key2", {"value": 2}, "source2")
            
            # Clear all
            await cache.clear()
            
            # All keys should be gone
            assert await cache.get("key1") is None
            assert await cache.get("key2") is None


class TestCacheStats:
    """Test cache statistics"""
    
    @pytest.mark.anyio
    async def test_cache_stats_structure(self):
        """Test cache stats returns correct structure"""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = CacheLayer(disk_path=tmpdir)
            
            stats = await cache.get_cache_stats()
            
            assert "memory_items" in stats
            assert "memory_maxsize" in stats
            assert "disk_items" in stats
            assert "disk_size_mb" in stats
            assert "disk_max_size_mb" in stats
    
    @pytest.mark.anyio
    async def test_cache_stats_counts(self):
        """Test cache stats counts items correctly"""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = CacheLayer(disk_path=tmpdir)
            
            # Add some items
            for i in range(3):
                await cache.set(f"key_{i}", {"value": i}, "source")
            
            stats = await cache.get_cache_stats()
            
            assert stats["memory_items"] == 3
            assert stats["disk_items"] == 3


class TestCustomTTL:
    """Test custom TTL values"""
    
    @pytest.mark.anyio
    async def test_custom_memory_ttl(self):
        """Test setting custom memory TTL"""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = CacheLayer(disk_path=tmpdir)
            
            # Set with custom TTL
            await cache.set(
                key="test_key",
                data={"value": 123},
                source="test_source",
                ttl_memory=2,  # 2 seconds
                ttl_disk=3600
            )
            
            # Should be available immediately
            assert await cache.get("test_key") is not None
    
    @pytest.mark.anyio
    async def test_custom_disk_ttl(self):
        """Test setting custom disk TTL"""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = CacheLayer(disk_path=tmpdir)
            
            # Set with custom disk TTL
            await cache.set(
                key="test_key",
                data={"value": 123},
                source="test_source",
                ttl_memory=3600,
                ttl_disk=7200  # 2 hours
            )
            
            # Should be available
            cached_data = await cache.get("test_key")
            assert cached_data is not None
