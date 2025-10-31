"""
Caching service for expensive operations like forecasts and web searches.
Implements TTL-based LRU cache to improve performance on repeated queries.
"""
from datetime import datetime, timedelta
from typing import Any, Optional
import hashlib
import json
import logging

logger = logging.getLogger(__name__)


class TTLCache:
    """Time-To-Live cache with LRU eviction"""
    
    def __init__(self, ttl_minutes: int = 15, max_entries: int = 256):
        """
        Initialize TTL cache.
        
        Args:
            ttl_minutes: Time to live in minutes
            max_entries: Maximum number of cache entries (LRU eviction)
        """
        self.ttl = timedelta(minutes=ttl_minutes)
        self.max_entries = max_entries
        self.cache = {}  # key -> (value, timestamp)
        logger.info(f"Initialized TTL cache: {ttl_minutes}min TTL, {max_entries} max entries")
    
    def _generate_key(self, *args, **kwargs) -> str:
        """Generate cache key from arguments"""
        # Create deterministic string from args and kwargs
        key_data = {
            'args': args,
            'kwargs': sorted(kwargs.items())  # Sort for consistency
        }
        key_str = json.dumps(key_data, sort_keys=True, default=str)
        return hashlib.sha256(key_str.encode()).hexdigest()[:16]
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache if exists and not expired.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found/expired
        """
        if key not in self.cache:
            return None
        
        value, timestamp = self.cache[key]
        
        # Check if expired
        if datetime.now() - timestamp > self.ttl:
            del self.cache[key]
            logger.debug(f"Cache expired: {key}")
            return None
        
        logger.debug(f"Cache hit: {key}")
        return value
    
    def set(self, key: str, value: Any):
        """
        Set value in cache with current timestamp.
        
        Args:
            key: Cache key
            value: Value to cache
        """
        # LRU eviction if over max entries
        if len(self.cache) >= self.max_entries:
            # Find and remove oldest entry
            oldest_key = min(self.cache.items(), key=lambda x: x[1][1])[0]
            del self.cache[oldest_key]
            logger.debug(f"Cache evicted (LRU): {oldest_key}")
        
        self.cache[key] = (value, datetime.now())
        logger.debug(f"Cache set: {key}")
    
    def invalidate(self, key: str):
        """Remove specific key from cache"""
        if key in self.cache:
            del self.cache[key]
            logger.debug(f"Cache invalidated: {key}")
    
    def clear(self):
        """Clear all cache entries"""
        count = len(self.cache)
        self.cache.clear()
        logger.info(f"Cache cleared: {count} entries removed")
    
    def stats(self) -> dict:
        """Get cache statistics"""
        now = datetime.now()
        expired = sum(1 for _, ts in self.cache.values() if now - ts > self.ttl)
        
        return {
            'total_entries': len(self.cache),
            'expired_entries': expired,
            'active_entries': len(self.cache) - expired,
            'max_entries': self.max_entries,
            'ttl_minutes': self.ttl.total_seconds() / 60
        }


class ForecastCache(TTLCache):
    """Specialized cache for forecast results"""
    
    def __init__(self):
        super().__init__(ttl_minutes=15, max_entries=100)
    
    def get_forecast_key(self, indicator: str, periods: int, method: str, data_hash: str) -> str:
        """Generate forecast-specific cache key"""
        return self._generate_key('forecast', indicator, periods, method, data_hash)
    
    def get_forecast(self, indicator: str, periods: int, method: str, data_hash: str) -> Optional[str]:
        """Get cached forecast result"""
        key = self.get_forecast_key(indicator, periods, method, data_hash)
        return self.get(key)
    
    def set_forecast(self, indicator: str, periods: int, method: str, data_hash: str, result: str):
        """Cache forecast result"""
        key = self.get_forecast_key(indicator, periods, method, data_hash)
        self.set(key, result)


class SearchCache(TTLCache):
    """Specialized cache for web search results"""
    
    def __init__(self):
        super().__init__(ttl_minutes=30, max_entries=256)
    
    def get_search_key(self, query: str, search_type: str = 'web') -> str:
        """Generate search-specific cache key"""
        return self._generate_key('search', search_type, query.lower().strip())
    
    def get_search(self, query: str, search_type: str = 'web') -> Optional[str]:
        """Get cached search result"""
        key = self.get_search_key(query, search_type)
        return self.get(key)
    
    def set_search(self, query: str, result: str, search_type: str = 'web'):
        """Cache search result"""
        key = self.get_search_key(query, search_type)
        self.set(key, result)


# Global cache instances
_forecast_cache = None
_search_cache = None


def get_forecast_cache() -> ForecastCache:
    """Get global forecast cache instance"""
    global _forecast_cache
    if _forecast_cache is None:
        _forecast_cache = ForecastCache()
    return _forecast_cache


def get_search_cache() -> SearchCache:
    """Get global search cache instance"""
    global _search_cache
    if _search_cache is None:
        _search_cache = SearchCache()
    return _search_cache
