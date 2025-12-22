"""In-memory cache with TTL for game data.

This module provides a simple thread-safe cache to reduce database queries
for frequently accessed game data.
"""

from datetime import datetime, timedelta
from typing import Any, Optional, Dict
import threading
import logging

logger = logging.getLogger(__name__)


class GameCache:
    """Thread-safe in-memory cache with TTL expiration."""

    def __init__(self, ttl_seconds: int = 300):
        """Initialize cache with specified TTL.

        Args:
            ttl_seconds: Time-to-live for cache entries (default 5 minutes)
        """
        self._cache: Dict[str, Any] = {}
        self._timestamps: Dict[str, datetime] = {}
        self._ttl = timedelta(seconds=ttl_seconds)
        self._lock = threading.Lock()

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache if exists and not expired.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found/expired
        """
        with self._lock:
            if key not in self._cache:
                return None

            if datetime.now() - self._timestamps[key] > self._ttl:
                # Entry expired
                del self._cache[key]
                del self._timestamps[key]
                logger.debug(f"Cache miss (expired): {key}")
                return None

            logger.debug(f"Cache hit: {key}")
            return self._cache[key]

    def set(self, key: str, value: Any) -> None:
        """Set value in cache.

        Args:
            key: Cache key
            value: Value to cache
        """
        with self._lock:
            self._cache[key] = value
            self._timestamps[key] = datetime.now()
            logger.debug(f"Cache set: {key}")

    def delete(self, key: str) -> bool:
        """Delete a specific key from cache.

        Args:
            key: Cache key to delete

        Returns:
            True if key was deleted, False if not found
        """
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                del self._timestamps[key]
                logger.debug(f"Cache delete: {key}")
                return True
            return False

    def invalidate(self, pattern: Optional[str] = None) -> int:
        """Invalidate cache entries matching pattern.

        Args:
            pattern: If None, clears entire cache.
                     Otherwise, deletes keys containing the pattern.

        Returns:
            Number of entries deleted
        """
        with self._lock:
            if pattern is None:
                count = len(self._cache)
                self._cache.clear()
                self._timestamps.clear()
                logger.info(f"Cache cleared: {count} entries")
                return count

            keys_to_delete = [k for k in self._cache if pattern in k]
            for k in keys_to_delete:
                del self._cache[k]
                del self._timestamps[k]

            if keys_to_delete:
                logger.info(f"Cache invalidated: {len(keys_to_delete)} entries matching '{pattern}'")

            return len(keys_to_delete)

    def stats(self) -> Dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dict with cache stats (size, oldest entry, etc.)
        """
        with self._lock:
            if not self._timestamps:
                return {
                    "size": 0,
                    "oldest_entry": None,
                    "newest_entry": None,
                    "ttl_seconds": self._ttl.total_seconds(),
                }

            oldest = min(self._timestamps.values())
            newest = max(self._timestamps.values())

            return {
                "size": len(self._cache),
                "oldest_entry": oldest.isoformat(),
                "newest_entry": newest.isoformat(),
                "ttl_seconds": self._ttl.total_seconds(),
            }


# Global cache instance (5 minute TTL)
cache = GameCache(ttl_seconds=300)


# Convenience functions
def get_cached(key: str) -> Optional[Any]:
    """Get value from global cache."""
    return cache.get(key)


def set_cached(key: str, value: Any) -> None:
    """Set value in global cache."""
    cache.set(key, value)


def invalidate_game(game_id: str) -> int:
    """Invalidate all cache entries for a specific game."""
    return cache.invalidate(game_id)


def invalidate_all() -> int:
    """Clear entire cache."""
    return cache.invalidate()
