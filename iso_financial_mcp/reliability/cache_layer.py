"""
Cache Layer with two-level caching (memory + disk).
"""

import asyncio
import hashlib
import json
import logging
import os
import pickle
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

import aiofiles
from cachetools import TTLCache

from .models import CachedData

logger = logging.getLogger(__name__)


class CacheLayer:
    """
    Two-level cache system (memory + disk) with stale data fallback.
    """
    
    def __init__(
        self,
        memory_maxsize: int = 1000,
        memory_ttl: int = 3600,  # 1 hour
        disk_ttl: int = 604800,  # 7 days
        disk_path: Optional[str] = None,
        max_disk_size_mb: int = 500
    ):
        """
        Initialize cache layer.
        
        Args:
            memory_maxsize: Maximum number of items in memory cache
            memory_ttl: TTL for memory cache in seconds
            disk_ttl: TTL for disk cache in seconds
            disk_path: Path for disk cache (default: ~/.iso_financial_mcp/cache)
            max_disk_size_mb: Maximum disk cache size in MB
        """
        self.memory_cache = TTLCache(maxsize=memory_maxsize, ttl=memory_ttl)
        self.memory_ttl = memory_ttl
        self.disk_ttl = disk_ttl
        self.max_disk_size_mb = max_disk_size_mb
        
        # Set up disk cache directory
        if disk_path is None:
            disk_path = os.path.expanduser("~/.iso_financial_mcp/cache")
        self.disk_path = Path(disk_path)
        self.disk_path.mkdir(parents=True, exist_ok=True)
        
        self._lock = asyncio.Lock()
        
    def _generate_cache_key(self, key: str) -> str:
        """Generate a cache key hash."""
        return hashlib.sha256(key.encode()).hexdigest()
    
    def _get_disk_file_path(self, cache_key: str) -> Path:
        """Get disk cache file path for a key."""
        return self.disk_path / f"{cache_key}.cache"
    
    async def get(
        self,
        key: str,
        allow_stale: bool = False
    ) -> Optional[CachedData]:
        """
        Retrieve data from cache.
        
        Args:
            key: Cache key
            allow_stale: If True, return expired data if available
            
        Returns:
            CachedData or None if not found
        """
        cache_key = self._generate_cache_key(key)
        
        # Try memory cache first
        if cache_key in self.memory_cache:
            cached_data = self.memory_cache[cache_key]
            logger.debug(f"Memory cache hit for key: {key}")
            return cached_data
        
        # Try disk cache
        disk_file = self._get_disk_file_path(cache_key)
        if disk_file.exists():
            try:
                async with aiofiles.open(disk_file, 'rb') as f:
                    content = await f.read()
                    cached_data = pickle.loads(content)
                
                # Check if expired
                now = datetime.now()
                is_stale = now > cached_data.expires_at
                
                if not is_stale or allow_stale:
                    # Update stale flag
                    cached_data.is_stale = is_stale
                    
                    # Restore to memory cache if not stale
                    if not is_stale:
                        self.memory_cache[cache_key] = cached_data
                    
                    logger.debug(
                        f"Disk cache {'stale ' if is_stale else ''}hit for key: {key}"
                    )
                    return cached_data
                else:
                    # Expired and stale not allowed
                    logger.debug(f"Disk cache expired for key: {key}")
                    return None
                    
            except Exception as e:
                logger.error(f"Error reading disk cache for key {key}: {e}")
                return None
        
        logger.debug(f"Cache miss for key: {key}")
        return None
    
    async def set(
        self,
        key: str,
        data: Any,
        source: str,
        ttl_memory: Optional[int] = None,
        ttl_disk: Optional[int] = None
    ):
        """
        Store data in both memory and disk cache.
        
        Args:
            key: Cache key
            data: Data to cache
            source: Source of the data
            ttl_memory: TTL for memory cache (uses default if None)
            ttl_disk: TTL for disk cache (uses default if None)
        """
        cache_key = self._generate_cache_key(key)
        
        if ttl_memory is None:
            ttl_memory = self.memory_ttl
        if ttl_disk is None:
            ttl_disk = self.disk_ttl
        
        now = datetime.now()
        
        # Create cached data object
        cached_data = CachedData(
            data=data,
            cached_at=now,
            expires_at=now + timedelta(seconds=ttl_disk),
            is_stale=False,
            source=source
        )
        
        # Store in memory cache
        self.memory_cache[cache_key] = cached_data
        
        # Store in disk cache asynchronously
        try:
            disk_file = self._get_disk_file_path(cache_key)
            async with aiofiles.open(disk_file, 'wb') as f:
                content = pickle.dumps(cached_data)
                await f.write(content)
            
            logger.debug(f"Cached data for key: {key}")
        except Exception as e:
            logger.error(f"Error writing disk cache for key {key}: {e}")
    
    async def clear(self, key: Optional[str] = None):
        """
        Clear cache.
        
        Args:
            key: Specific key to clear, or None to clear all
        """
        if key is None:
            # Clear all
            self.memory_cache.clear()
            for cache_file in self.disk_path.glob("*.cache"):
                try:
                    cache_file.unlink()
                except Exception as e:
                    logger.error(f"Error deleting cache file {cache_file}: {e}")
            logger.info("Cleared all cache")
        else:
            # Clear specific key
            cache_key = self._generate_cache_key(key)
            if cache_key in self.memory_cache:
                del self.memory_cache[cache_key]
            
            disk_file = self._get_disk_file_path(cache_key)
            if disk_file.exists():
                try:
                    disk_file.unlink()
                except Exception as e:
                    logger.error(f"Error deleting cache file {disk_file}: {e}")
            
            logger.debug(f"Cleared cache for key: {key}")
    
    async def get_cache_stats(self) -> dict:
        """Get cache statistics."""
        memory_size = len(self.memory_cache)
        
        # Calculate disk cache size
        disk_files = list(self.disk_path.glob("*.cache"))
        disk_size_bytes = sum(f.stat().st_size for f in disk_files if f.exists())
        disk_size_mb = disk_size_bytes / (1024 * 1024)
        
        return {
            "memory_items": memory_size,
            "memory_maxsize": self.memory_cache.maxsize,
            "disk_items": len(disk_files),
            "disk_size_mb": round(disk_size_mb, 2),
            "disk_max_size_mb": self.max_disk_size_mb,
        }
