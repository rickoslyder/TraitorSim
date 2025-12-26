"""Voice cache manager for HITL latency optimization.

Pre-caches common phrases per archetype to eliminate synthesis latency
for frequent utterances during real-time gameplay.

Features:
- LRU cache with configurable size limits
- Cache warming with archetype-specific phrases
- Persistent disk cache for cross-session reuse
- Memory + disk hybrid storage
- Cache hit/miss statistics

Usage:
    from traitorsim.voice import VoiceCacheManager

    cache = VoiceCacheManager(client=elevenlabs_client)

    # Warm cache for upcoming game
    await cache.warm_cache_for_players(players)

    # Get cached audio (instant) or synthesize (fallback)
    audio = await cache.get_or_synthesize(
        text="I've been analyzing the patterns...",
        voice_id="marcus",
        archetype="prodigy"
    )
"""

import os
import asyncio
import hashlib
import json
import logging
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Set
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """A cached audio entry."""
    key: str                          # Cache key (hash of text+voice+model)
    audio_data: bytes                 # Audio bytes (MP3)
    text: str                         # Original text
    voice_id: str                     # Voice used
    model: str                        # Model used
    archetype: Optional[str] = None   # Archetype for categorization
    created_at: float = field(default_factory=time.time)
    last_accessed: float = field(default_factory=time.time)
    access_count: int = 0
    size_bytes: int = 0

    def __post_init__(self):
        self.size_bytes = len(self.audio_data)

    def touch(self):
        """Update access time and count."""
        self.last_accessed = time.time()
        self.access_count += 1


@dataclass
class CacheStats:
    """Cache statistics for monitoring."""
    hits: int = 0
    misses: int = 0
    total_size_bytes: int = 0
    entry_count: int = 0
    evictions: int = 0
    warm_entries: int = 0

    # Per-archetype stats
    hits_by_archetype: Dict[str, int] = field(default_factory=dict)
    misses_by_archetype: Dict[str, int] = field(default_factory=dict)

    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate."""
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0

    @property
    def size_mb(self) -> float:
        """Size in megabytes."""
        return self.total_size_bytes / (1024 * 1024)

    def record_hit(self, archetype: Optional[str] = None):
        """Record a cache hit."""
        self.hits += 1
        if archetype:
            self.hits_by_archetype[archetype] = self.hits_by_archetype.get(archetype, 0) + 1

    def record_miss(self, archetype: Optional[str] = None):
        """Record a cache miss."""
        self.misses += 1
        if archetype:
            self.misses_by_archetype[archetype] = self.misses_by_archetype.get(archetype, 0) + 1

    def to_dict(self) -> Dict[str, Any]:
        """Export as dictionary."""
        return {
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": round(self.hit_rate * 100, 2),
            "total_size_mb": round(self.size_mb, 2),
            "entry_count": self.entry_count,
            "evictions": self.evictions,
            "warm_entries": self.warm_entries,
            "hits_by_archetype": self.hits_by_archetype,
            "misses_by_archetype": self.misses_by_archetype,
        }


class VoiceCacheManager:
    """Manages voice synthesis cache for HITL latency optimization.

    Uses a two-tier cache:
    1. Memory cache (LRU) for instant access
    2. Disk cache for persistence across sessions

    Warming priority:
    1. Common phrases for each archetype in the game
    2. Player names and common responses
    3. Narrator phrases
    """

    # Default configuration
    DEFAULT_MEMORY_LIMIT_MB = 100  # 100 MB memory cache
    DEFAULT_DISK_LIMIT_MB = 500    # 500 MB disk cache
    DEFAULT_MAX_ENTRIES = 1000     # Max entries in memory

    def __init__(
        self,
        client: Any = None,  # ElevenLabsClient
        cache_dir: Optional[Path] = None,
        memory_limit_mb: float = DEFAULT_MEMORY_LIMIT_MB,
        disk_limit_mb: float = DEFAULT_DISK_LIMIT_MB,
        max_memory_entries: int = DEFAULT_MAX_ENTRIES,
        model: str = "eleven_flash_v2_5",  # Default to low-latency model
        enable_disk_cache: bool = True,
    ):
        """Initialize the voice cache manager.

        Args:
            client: ElevenLabsClient instance for synthesis
            cache_dir: Directory for disk cache (default: ~/.traitorsim/voice_cache)
            memory_limit_mb: Maximum memory cache size in MB
            disk_limit_mb: Maximum disk cache size in MB
            max_memory_entries: Maximum entries in memory cache
            model: Default model for synthesis
            enable_disk_cache: Whether to use disk caching
        """
        self.client = client
        self.model = model
        self.memory_limit_bytes = int(memory_limit_mb * 1024 * 1024)
        self.disk_limit_bytes = int(disk_limit_mb * 1024 * 1024)
        self.max_memory_entries = max_memory_entries
        self.enable_disk_cache = enable_disk_cache

        # Set up cache directory
        if cache_dir is None:
            cache_dir = Path.home() / ".traitorsim" / "voice_cache"
        self.cache_dir = Path(cache_dir)
        if self.enable_disk_cache:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            self._index_file = self.cache_dir / "index.json"

        # Memory cache (LRU using OrderedDict)
        self._memory_cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._memory_size_bytes = 0

        # Disk cache index (loaded on init)
        self._disk_index: Dict[str, Dict[str, Any]] = {}
        if self.enable_disk_cache:
            self._load_disk_index()

        # Statistics
        self.stats = CacheStats()

        # Lock for thread safety
        self._lock = asyncio.Lock()

        logger.info(
            f"VoiceCacheManager initialized: "
            f"memory_limit={memory_limit_mb}MB, "
            f"disk_limit={disk_limit_mb}MB, "
            f"cache_dir={self.cache_dir}"
        )

    def _generate_cache_key(
        self,
        text: str,
        voice_id: str,
        model: Optional[str] = None,
    ) -> str:
        """Generate a unique cache key for text+voice+model combination.

        Uses SHA-256 hash for consistent, collision-resistant keys.
        """
        model = model or self.model
        key_string = f"{text}|{voice_id}|{model}"
        return hashlib.sha256(key_string.encode()).hexdigest()[:16]

    def _load_disk_index(self):
        """Load disk cache index from file."""
        if self._index_file.exists():
            try:
                with open(self._index_file, 'r') as f:
                    self._disk_index = json.load(f)
                logger.info(f"Loaded disk cache index: {len(self._disk_index)} entries")
            except Exception as e:
                logger.warning(f"Failed to load disk cache index: {e}")
                self._disk_index = {}

    def _save_disk_index(self):
        """Save disk cache index to file."""
        if not self.enable_disk_cache:
            return
        try:
            with open(self._index_file, 'w') as f:
                json.dump(self._disk_index, f)
        except Exception as e:
            logger.warning(f"Failed to save disk cache index: {e}")

    def _get_disk_path(self, key: str) -> Path:
        """Get disk cache file path for a key."""
        # Use first 2 chars as subdirectory for better file distribution
        subdir = key[:2]
        return self.cache_dir / subdir / f"{key}.mp3"

    async def _evict_lru_memory(self, needed_bytes: int = 0):
        """Evict least recently used entries from memory cache.

        Args:
            needed_bytes: Ensure this many bytes are available after eviction
        """
        while (
            self._memory_size_bytes + needed_bytes > self.memory_limit_bytes
            or len(self._memory_cache) >= self.max_memory_entries
        ) and self._memory_cache:
            # Pop oldest (first) item
            key, entry = self._memory_cache.popitem(last=False)
            self._memory_size_bytes -= entry.size_bytes
            self.stats.evictions += 1
            logger.debug(f"Evicted from memory cache: {key} ({entry.size_bytes} bytes)")

    async def _evict_lru_disk(self, needed_bytes: int = 0):
        """Evict least recently used entries from disk cache."""
        if not self.enable_disk_cache:
            return

        # Calculate current disk usage
        current_size = sum(
            entry.get("size_bytes", 0)
            for entry in self._disk_index.values()
        )

        while current_size + needed_bytes > self.disk_limit_bytes and self._disk_index:
            # Find oldest entry
            oldest_key = min(
                self._disk_index.keys(),
                key=lambda k: self._disk_index[k].get("last_accessed", 0)
            )
            entry = self._disk_index.pop(oldest_key)

            # Delete file
            file_path = self._get_disk_path(oldest_key)
            if file_path.exists():
                file_path.unlink()

            current_size -= entry.get("size_bytes", 0)
            logger.debug(f"Evicted from disk cache: {oldest_key}")

        self._save_disk_index()

    async def _store_to_memory(self, entry: CacheEntry):
        """Store an entry in memory cache."""
        async with self._lock:
            # Evict if needed
            await self._evict_lru_memory(entry.size_bytes)

            # Store (moves to end of OrderedDict = most recently used)
            self._memory_cache[entry.key] = entry
            self._memory_cache.move_to_end(entry.key)
            self._memory_size_bytes += entry.size_bytes

            self.stats.entry_count = len(self._memory_cache)
            self.stats.total_size_bytes = self._memory_size_bytes

    async def _store_to_disk(self, entry: CacheEntry):
        """Store an entry in disk cache."""
        if not self.enable_disk_cache:
            return

        # Evict if needed
        await self._evict_lru_disk(entry.size_bytes)

        # Write file
        file_path = self._get_disk_path(entry.key)
        file_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(file_path, 'wb') as f:
                f.write(entry.audio_data)

            # Update index
            self._disk_index[entry.key] = {
                "text": entry.text,
                "voice_id": entry.voice_id,
                "model": entry.model,
                "archetype": entry.archetype,
                "created_at": entry.created_at,
                "last_accessed": entry.last_accessed,
                "size_bytes": entry.size_bytes,
            }
            self._save_disk_index()

        except Exception as e:
            logger.warning(f"Failed to write to disk cache: {e}")

    async def _load_from_disk(self, key: str) -> Optional[CacheEntry]:
        """Load an entry from disk cache."""
        if not self.enable_disk_cache or key not in self._disk_index:
            return None

        file_path = self._get_disk_path(key)
        if not file_path.exists():
            # Clean up stale index entry
            del self._disk_index[key]
            self._save_disk_index()
            return None

        try:
            with open(file_path, 'rb') as f:
                audio_data = f.read()

            index_entry = self._disk_index[key]
            entry = CacheEntry(
                key=key,
                audio_data=audio_data,
                text=index_entry["text"],
                voice_id=index_entry["voice_id"],
                model=index_entry["model"],
                archetype=index_entry.get("archetype"),
                created_at=index_entry.get("created_at", time.time()),
                last_accessed=time.time(),
            )

            # Update last accessed in index
            self._disk_index[key]["last_accessed"] = time.time()
            self._save_disk_index()

            return entry

        except Exception as e:
            logger.warning(f"Failed to read from disk cache: {e}")
            return None

    async def get(
        self,
        text: str,
        voice_id: str,
        model: Optional[str] = None,
        archetype: Optional[str] = None,
    ) -> Optional[bytes]:
        """Get cached audio if available.

        Args:
            text: Text to look up
            voice_id: Voice ID
            model: Model (uses default if not specified)
            archetype: Archetype for stats tracking

        Returns:
            Audio bytes if cached, None otherwise
        """
        model = model or self.model
        key = self._generate_cache_key(text, voice_id, model)

        # Check memory cache first
        if key in self._memory_cache:
            entry = self._memory_cache[key]
            entry.touch()
            self._memory_cache.move_to_end(key)  # LRU update
            self.stats.record_hit(archetype)
            logger.debug(f"Cache hit (memory): {key}")
            return entry.audio_data

        # Check disk cache
        entry = await self._load_from_disk(key)
        if entry:
            # Promote to memory cache
            await self._store_to_memory(entry)
            self.stats.record_hit(archetype)
            logger.debug(f"Cache hit (disk): {key}")
            return entry.audio_data

        self.stats.record_miss(archetype)
        logger.debug(f"Cache miss: {key}")
        return None

    async def put(
        self,
        text: str,
        voice_id: str,
        audio_data: bytes,
        model: Optional[str] = None,
        archetype: Optional[str] = None,
    ):
        """Store audio in cache.

        Args:
            text: Original text
            voice_id: Voice ID used
            audio_data: Audio bytes to cache
            model: Model used
            archetype: Archetype for categorization
        """
        model = model or self.model
        key = self._generate_cache_key(text, voice_id, model)

        entry = CacheEntry(
            key=key,
            audio_data=audio_data,
            text=text,
            voice_id=voice_id,
            model=model,
            archetype=archetype,
        )

        # Store in memory
        await self._store_to_memory(entry)

        # Store in disk (async, don't block)
        asyncio.create_task(self._store_to_disk(entry))

    async def get_or_synthesize(
        self,
        text: str,
        voice_id: str,
        model: Optional[str] = None,
        archetype: Optional[str] = None,
        voice_settings: Optional[Dict[str, Any]] = None,
    ) -> bytes:
        """Get cached audio or synthesize if not cached.

        This is the primary method for HITL mode - returns instantly
        if cached, otherwise synthesizes and caches the result.

        Args:
            text: Text to speak
            voice_id: Voice ID to use
            model: Model (uses default if not specified)
            archetype: Archetype for tracking
            voice_settings: Optional voice settings for synthesis

        Returns:
            Audio bytes (MP3)
        """
        # Try cache first
        cached = await self.get(text, voice_id, model, archetype)
        if cached is not None:
            return cached

        # Synthesize
        if self.client is None:
            raise ValueError("No ElevenLabs client configured - cannot synthesize")

        model = model or self.model

        try:
            result = await self.client.text_to_speech(
                text=text,
                voice_id=voice_id,
                model=model,
                voice_settings=voice_settings,
            )

            # Cache the result
            await self.put(
                text=text,
                voice_id=voice_id,
                audio_data=result.audio_data,
                model=model,
                archetype=archetype,
            )

            return result.audio_data

        except Exception as e:
            logger.error(f"Synthesis failed: {e}")
            raise

    async def warm_cache(
        self,
        phrases: List[str],
        voice_id: str,
        archetype: Optional[str] = None,
        concurrent_limit: int = 5,
    ) -> int:
        """Pre-warm cache with a list of phrases.

        Args:
            phrases: List of phrases to pre-cache
            voice_id: Voice to use
            archetype: Archetype for categorization
            concurrent_limit: Max concurrent synthesis requests

        Returns:
            Number of phrases newly cached
        """
        cached_count = 0
        semaphore = asyncio.Semaphore(concurrent_limit)

        async def cache_phrase(phrase: str):
            nonlocal cached_count
            async with semaphore:
                # Check if already cached
                if await self.get(phrase, voice_id, archetype=archetype) is not None:
                    return  # Already cached

                try:
                    await self.get_or_synthesize(
                        text=phrase,
                        voice_id=voice_id,
                        archetype=archetype,
                    )
                    cached_count += 1
                    logger.debug(f"Warmed cache: '{phrase[:30]}...'")
                except Exception as e:
                    logger.warning(f"Failed to cache phrase: {e}")

        # Run warming tasks
        tasks = [cache_phrase(phrase) for phrase in phrases]
        await asyncio.gather(*tasks, return_exceptions=True)

        self.stats.warm_entries += cached_count
        logger.info(f"Cache warming complete: {cached_count} new phrases cached")

        return cached_count

    async def warm_cache_for_archetype(
        self,
        archetype: str,
        voice_id: str,
    ) -> int:
        """Pre-warm cache with common phrases for an archetype.

        Args:
            archetype: Archetype ID (e.g., "prodigy", "charming_sociopath")
            voice_id: Voice ID to use

        Returns:
            Number of phrases cached
        """
        # Import here to avoid circular imports
        from .voice_library import COMMON_PHRASES_BY_ARCHETYPE, get_cacheable_phrases

        # Get archetype-specific phrases
        phrases = get_cacheable_phrases(archetype)
        if not phrases:
            logger.warning(f"No common phrases found for archetype: {archetype}")
            return 0

        return await self.warm_cache(
            phrases=phrases,
            voice_id=voice_id,
            archetype=archetype,
        )

    async def warm_cache_for_players(
        self,
        players: List[Dict[str, Any]],
        concurrent_limit: int = 3,
    ) -> Dict[str, int]:
        """Pre-warm cache for all players in a game.

        Args:
            players: List of player dicts with 'archetype', 'voice_id' keys
            concurrent_limit: Max concurrent archetype warming tasks

        Returns:
            Dict mapping archetype to phrases cached
        """
        results = {}
        semaphore = asyncio.Semaphore(concurrent_limit)

        async def warm_player(player: Dict[str, Any]):
            async with semaphore:
                archetype = player.get("archetype", "")
                voice_id = player.get("voice_id", "")

                if not archetype or not voice_id:
                    logger.warning(f"Player missing archetype or voice_id: {player}")
                    return

                if archetype in results:
                    return  # Already warmed this archetype

                count = await self.warm_cache_for_archetype(archetype, voice_id)
                results[archetype] = count

        tasks = [warm_player(p) for p in players]
        await asyncio.gather(*tasks, return_exceptions=True)

        total = sum(results.values())
        logger.info(f"Warmed cache for {len(results)} archetypes: {total} phrases total")

        return results

    async def warm_narrator_cache(
        self,
        narrator_voice_id: str = "narrator",
    ) -> int:
        """Pre-warm cache with common narrator phrases.

        Args:
            narrator_voice_id: Voice ID for narrator

        Returns:
            Number of phrases cached
        """
        narrator_phrases = [
            "Previously on The Traitors...",
            "Day begins at the castle.",
            "The Faithful gathered for breakfast.",
            "But one chair remained empty.",
            "The Round Table awaits.",
            "Who will be banished tonight?",
            "The votes are in.",
            "A Faithful has been banished.",
            "A Traitor has been revealed!",
            "The Traitors have struck again.",
            "Another soul lost to treachery.",
            "The Traitors convened in secret.",
            "A new Traitor rises.",
            "The murder is complete.",
            "Dawn approaches.",
            "Victory for the Faithful!",
            "The Traitors have won.",
            "And so our tale concludes.",
            "But who can truly be trusted?",
            "The game continues...",
        ]

        return await self.warm_cache(
            phrases=narrator_phrases,
            voice_id=narrator_voice_id,
            archetype="narrator",
        )

    def clear_memory_cache(self):
        """Clear all entries from memory cache."""
        self._memory_cache.clear()
        self._memory_size_bytes = 0
        self.stats.entry_count = 0
        self.stats.total_size_bytes = 0
        logger.info("Memory cache cleared")

    def clear_disk_cache(self):
        """Clear all entries from disk cache."""
        if not self.enable_disk_cache:
            return

        import shutil
        try:
            # Remove all subdirectories
            for item in self.cache_dir.iterdir():
                if item.is_dir() and len(item.name) == 2:  # Cache subdirs are 2 chars
                    shutil.rmtree(item)

            self._disk_index.clear()
            self._save_disk_index()
            logger.info("Disk cache cleared")
        except Exception as e:
            logger.error(f"Failed to clear disk cache: {e}")

    def clear_all(self):
        """Clear both memory and disk caches."""
        self.clear_memory_cache()
        self.clear_disk_cache()
        self.stats = CacheStats()  # Reset stats

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics.

        Returns:
            Statistics dictionary
        """
        # Calculate disk usage
        disk_size = 0
        disk_entries = 0
        if self.enable_disk_cache:
            disk_size = sum(
                entry.get("size_bytes", 0)
                for entry in self._disk_index.values()
            )
            disk_entries = len(self._disk_index)

        stats = self.stats.to_dict()
        stats.update({
            "memory_size_mb": round(self._memory_size_bytes / (1024 * 1024), 2),
            "memory_entries": len(self._memory_cache),
            "memory_limit_mb": round(self.memory_limit_bytes / (1024 * 1024), 2),
            "disk_size_mb": round(disk_size / (1024 * 1024), 2),
            "disk_entries": disk_entries,
            "disk_limit_mb": round(self.disk_limit_bytes / (1024 * 1024), 2),
        })

        return stats

    def export_warm_report(self) -> Dict[str, Any]:
        """Export a report of cached entries by archetype.

        Returns:
            Report dictionary
        """
        report = {
            "generated_at": datetime.now().isoformat(),
            "stats": self.get_stats(),
            "entries_by_archetype": {},
        }

        # Group memory cache entries by archetype
        for entry in self._memory_cache.values():
            arch = entry.archetype or "unknown"
            if arch not in report["entries_by_archetype"]:
                report["entries_by_archetype"][arch] = {
                    "count": 0,
                    "size_bytes": 0,
                    "sample_phrases": [],
                }
            report["entries_by_archetype"][arch]["count"] += 1
            report["entries_by_archetype"][arch]["size_bytes"] += entry.size_bytes

            # Add up to 3 sample phrases
            if len(report["entries_by_archetype"][arch]["sample_phrases"]) < 3:
                report["entries_by_archetype"][arch]["sample_phrases"].append(
                    entry.text[:50] + "..." if len(entry.text) > 50 else entry.text
                )

        return report


# Convenience functions

async def create_cache_manager(
    client: Any = None,
    cache_dir: Optional[Path] = None,
    memory_limit_mb: float = 100,
    enable_disk_cache: bool = True,
) -> VoiceCacheManager:
    """Create and return a VoiceCacheManager instance.

    Args:
        client: ElevenLabsClient instance
        cache_dir: Optional cache directory
        memory_limit_mb: Memory limit in MB
        enable_disk_cache: Whether to enable disk caching

    Returns:
        Configured VoiceCacheManager
    """
    return VoiceCacheManager(
        client=client,
        cache_dir=cache_dir,
        memory_limit_mb=memory_limit_mb,
        enable_disk_cache=enable_disk_cache,
    )


async def warm_game_cache(
    cache: VoiceCacheManager,
    players: List[Dict[str, Any]],
    include_narrator: bool = True,
    narrator_voice_id: str = "narrator",
) -> Dict[str, Any]:
    """Convenience function to warm cache for a game.

    Args:
        cache: VoiceCacheManager instance
        players: List of player dicts
        include_narrator: Whether to warm narrator phrases
        narrator_voice_id: Narrator voice ID

    Returns:
        Warming report with statistics
    """
    report = {
        "started_at": datetime.now().isoformat(),
        "player_archetypes": {},
        "narrator": 0,
    }

    # Warm player caches
    report["player_archetypes"] = await cache.warm_cache_for_players(players)

    # Warm narrator cache
    if include_narrator:
        report["narrator"] = await cache.warm_narrator_cache(narrator_voice_id)

    report["completed_at"] = datetime.now().isoformat()
    report["total_phrases_cached"] = sum(report["player_archetypes"].values()) + report["narrator"]
    report["final_stats"] = cache.get_stats()

    return report
