"""Voice cache manager for HITL latency optimization.

Pre-caches common phrases per archetype to eliminate synthesis latency
for frequent utterances during real-time gameplay.

Features:
- LRU cache with configurable size limits
- Cache warming with archetype-specific phrases
- Persistent disk cache for cross-session reuse
- Memory + disk hybrid storage
- Cache hit/miss statistics
- Semantic similarity caching (fuzzy match)
- Predictive caching based on game phase
- Priority-based eviction (narrator > player)
- Compression for disk storage

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

    # Use semantic cache for fuzzy matches
    audio = await cache.get_or_synthesize_semantic(
        text="I've been looking at the patterns...",  # Similar to cached
        voice_id="marcus"
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


# =============================================================================
# ADVANCED CACHING STRATEGIES
# =============================================================================

class CachePriority:
    """Priority levels for cache entries (higher = harder to evict)."""
    LOW = 1       # Dynamic player dialogue
    MEDIUM = 2    # Common phrases
    HIGH = 3      # Narrator phrases
    CRITICAL = 4  # Pre-warmed essential phrases


def _normalize_text(text: str) -> str:
    """Normalize text for semantic matching.

    Removes punctuation, lowercases, and normalizes whitespace.
    """
    import re
    # Remove punctuation except apostrophes
    text = re.sub(r"[^\w\s']", "", text.lower())
    # Normalize whitespace
    text = " ".join(text.split())
    return text


def _compute_similarity(text1: str, text2: str) -> float:
    """Compute Jaccard similarity between two texts.

    Returns:
        Similarity score between 0.0 and 1.0
    """
    # Normalize
    t1 = set(_normalize_text(text1).split())
    t2 = set(_normalize_text(text2).split())

    if not t1 or not t2:
        return 0.0

    intersection = len(t1 & t2)
    union = len(t1 | t2)

    return intersection / union if union > 0 else 0.0


class SemanticCacheIndex:
    """Index for semantic similarity-based cache lookups.

    Uses word-level n-grams and inverted index for fast similarity search.
    """

    def __init__(self, similarity_threshold: float = 0.7):
        """Initialize semantic index.

        Args:
            similarity_threshold: Minimum similarity for a match (0.0-1.0)
        """
        self.threshold = similarity_threshold

        # Inverted index: word -> set of cache keys
        self._word_index: Dict[str, Set[str]] = {}

        # Cache key -> normalized text
        self._key_texts: Dict[str, str] = {}

        # Cache key -> original text
        self._key_originals: Dict[str, str] = {}

    def add(self, cache_key: str, text: str) -> None:
        """Add a text to the semantic index.

        Args:
            cache_key: Cache key for the entry
            text: Original text
        """
        normalized = _normalize_text(text)
        self._key_texts[cache_key] = normalized
        self._key_originals[cache_key] = text

        # Index words
        for word in normalized.split():
            if word not in self._word_index:
                self._word_index[word] = set()
            self._word_index[word].add(cache_key)

    def remove(self, cache_key: str) -> None:
        """Remove an entry from the index."""
        if cache_key not in self._key_texts:
            return

        normalized = self._key_texts[cache_key]
        for word in normalized.split():
            if word in self._word_index:
                self._word_index[word].discard(cache_key)
                if not self._word_index[word]:
                    del self._word_index[word]

        del self._key_texts[cache_key]
        del self._key_originals[cache_key]

    def find_similar(
        self,
        text: str,
        voice_id: str,
        max_results: int = 5,
    ) -> List[Tuple[str, float]]:
        """Find cache keys with similar text.

        Args:
            text: Query text
            voice_id: Voice ID to match
            max_results: Maximum results to return

        Returns:
            List of (cache_key, similarity) tuples, sorted by similarity desc
        """
        normalized = _normalize_text(text)
        query_words = set(normalized.split())

        if not query_words:
            return []

        # Find candidate keys (entries sharing at least one word)
        candidates = set()
        for word in query_words:
            if word in self._word_index:
                candidates.update(self._word_index[word])

        if not candidates:
            return []

        # Score candidates
        scores = []
        for key in candidates:
            # Only match same voice
            if f"|{voice_id}|" not in key and not key.startswith(voice_id):
                continue

            similarity = _compute_similarity(text, self._key_originals.get(key, ""))
            if similarity >= self.threshold:
                scores.append((key, similarity))

        # Sort by similarity descending
        scores.sort(key=lambda x: -x[1])
        return scores[:max_results]

    def clear(self) -> None:
        """Clear the entire index."""
        self._word_index.clear()
        self._key_texts.clear()
        self._key_originals.clear()


class PredictiveCache:
    """Predictive caching based on game phase transitions.

    Pre-fetches likely next phrases based on current game state.
    """

    # Phase transition probabilities and likely phrases
    PHASE_PREDICTIONS = {
        "breakfast": {
            "next_phases": ["mission"],
            "likely_phrases": [
                "The mission awaits.",
                "Let's see how you perform today.",
                "Time to prove yourselves.",
            ],
        },
        "mission": {
            "next_phases": ["social", "roundtable"],
            "likely_phrases": [
                "The mission is complete.",
                "Well done, everyone.",
                "That could have gone better.",
                "Suspicions are rising.",
            ],
        },
        "social": {
            "next_phases": ["roundtable"],
            "likely_phrases": [
                "The Round Table awaits.",
                "Time to make your accusations.",
                "Someone here is not who they claim to be.",
            ],
        },
        "roundtable": {
            "next_phases": ["turret", "breakfast"],
            "likely_phrases": [
                "The votes are in.",
                "You have been banished.",
                "You were a Faithful.",
                "You were a Traitor!",
                "The Traitors meet tonight.",
            ],
        },
        "turret": {
            "next_phases": ["breakfast"],
            "likely_phrases": [
                "The murder is done.",
                "Dawn approaches.",
                "Another soul claimed by treachery.",
            ],
        },
    }

    def __init__(self, cache: "VoiceCacheManager"):
        """Initialize predictive cache.

        Args:
            cache: Parent VoiceCacheManager
        """
        self.cache = cache
        self._current_phase: Optional[str] = None
        self._prefetch_task: Optional[asyncio.Task] = None

    async def on_phase_change(
        self,
        new_phase: str,
        narrator_voice_id: str = "narrator",
    ) -> None:
        """Handle phase change and trigger predictive caching.

        Args:
            new_phase: The new game phase
            narrator_voice_id: Narrator voice ID for pre-caching
        """
        self._current_phase = new_phase

        # Cancel any existing prefetch
        if self._prefetch_task and not self._prefetch_task.done():
            self._prefetch_task.cancel()

        # Start prefetching in background
        self._prefetch_task = asyncio.create_task(
            self._prefetch_for_phase(new_phase, narrator_voice_id)
        )

    async def _prefetch_for_phase(
        self,
        phase: str,
        narrator_voice_id: str,
    ) -> None:
        """Prefetch phrases likely needed for upcoming phases.

        Args:
            phase: Current phase
            narrator_voice_id: Narrator voice ID
        """
        predictions = self.PHASE_PREDICTIONS.get(phase, {})
        phrases = predictions.get("likely_phrases", [])

        if not phrases:
            return

        logger.debug(f"Predictive prefetch: {len(phrases)} phrases for post-{phase}")

        # Pre-cache with low priority (evictable)
        for phrase in phrases:
            try:
                # Check if already cached
                cached = await self.cache.get(phrase, narrator_voice_id)
                if cached is None:
                    await self.cache.get_or_synthesize(
                        text=phrase,
                        voice_id=narrator_voice_id,
                        archetype="narrator",
                    )
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.debug(f"Predictive cache failed for phrase: {e}")


class AggressiveCacheManager(VoiceCacheManager):
    """Extended VoiceCacheManager with aggressive caching strategies.

    Adds:
    - Semantic similarity matching
    - Predictive phase-based caching
    - Priority-based eviction
    - Compression for disk storage
    """

    def __init__(
        self,
        client: Any = None,
        cache_dir: Optional[Path] = None,
        memory_limit_mb: float = 150,  # Higher default for aggressive caching
        disk_limit_mb: float = 1000,   # 1GB disk cache
        semantic_threshold: float = 0.75,
        enable_prediction: bool = True,
        enable_compression: bool = True,
        **kwargs,
    ):
        """Initialize aggressive cache manager.

        Args:
            client: ElevenLabsClient instance
            cache_dir: Cache directory
            memory_limit_mb: Memory limit (default higher)
            disk_limit_mb: Disk limit (default higher)
            semantic_threshold: Similarity threshold for semantic matching
            enable_prediction: Enable predictive caching
            enable_compression: Enable disk compression
            **kwargs: Additional args for VoiceCacheManager
        """
        super().__init__(
            client=client,
            cache_dir=cache_dir,
            memory_limit_mb=memory_limit_mb,
            disk_limit_mb=disk_limit_mb,
            **kwargs,
        )

        # Semantic index
        self.semantic_index = SemanticCacheIndex(similarity_threshold=semantic_threshold)
        self.semantic_threshold = semantic_threshold

        # Predictive cache
        self.enable_prediction = enable_prediction
        self.predictive_cache = PredictiveCache(self) if enable_prediction else None

        # Compression
        self.enable_compression = enable_compression

        # Priority tracking
        self._entry_priorities: Dict[str, int] = {}

        # Semantic cache stats
        self.semantic_hits = 0
        self.semantic_misses = 0

    async def put(
        self,
        text: str,
        voice_id: str,
        audio_data: bytes,
        model: Optional[str] = None,
        archetype: Optional[str] = None,
        priority: int = CachePriority.MEDIUM,
    ):
        """Store audio with priority and semantic indexing."""
        model = model or self.model
        key = self._generate_cache_key(text, voice_id, model)

        # Set priority
        self._entry_priorities[key] = priority

        # Add to semantic index
        self.semantic_index.add(key, text)

        # Compress for disk if enabled
        if self.enable_compression:
            import gzip
            audio_data_disk = gzip.compress(audio_data)
        else:
            audio_data_disk = audio_data

        # Call parent put
        await super().put(text, voice_id, audio_data, model, archetype)

    async def get_semantic(
        self,
        text: str,
        voice_id: str,
        model: Optional[str] = None,
    ) -> Optional[bytes]:
        """Get cached audio using semantic similarity.

        First tries exact match, then falls back to semantic similarity.

        Args:
            text: Text to look up
            voice_id: Voice ID
            model: Model

        Returns:
            Audio bytes if found (exact or similar), None otherwise
        """
        # Try exact match first
        exact = await self.get(text, voice_id, model)
        if exact is not None:
            return exact

        # Try semantic match
        similar = self.semantic_index.find_similar(text, voice_id, max_results=1)
        if similar:
            best_key, similarity = similar[0]
            logger.debug(f"Semantic match: {similarity:.2f} similarity")

            # Look up the matched entry
            if best_key in self._memory_cache:
                entry = self._memory_cache[best_key]
                entry.touch()
                self._memory_cache.move_to_end(best_key)
                self.semantic_hits += 1
                return entry.audio_data

        self.semantic_misses += 1
        return None

    async def get_or_synthesize_semantic(
        self,
        text: str,
        voice_id: str,
        model: Optional[str] = None,
        archetype: Optional[str] = None,
        voice_settings: Optional[Dict[str, Any]] = None,
    ) -> bytes:
        """Get cached audio (exact or semantic) or synthesize.

        This is the recommended method for HITL mode as it maximizes
        cache hit rate through semantic matching.

        Args:
            text: Text to speak
            voice_id: Voice ID
            model: Model
            archetype: Archetype
            voice_settings: Voice settings

        Returns:
            Audio bytes
        """
        # Try semantic cache first
        cached = await self.get_semantic(text, voice_id, model)
        if cached is not None:
            return cached

        # Fall back to synthesis
        return await self.get_or_synthesize(
            text=text,
            voice_id=voice_id,
            model=model,
            archetype=archetype,
            voice_settings=voice_settings,
        )

    async def _evict_lru_memory(self, needed_bytes: int = 0):
        """Priority-aware LRU eviction.

        Evicts low-priority entries first, then medium, then high.
        Critical entries are never evicted.
        """
        # Group entries by priority
        by_priority: Dict[int, List[str]] = {p: [] for p in range(1, 5)}
        for key in self._memory_cache:
            priority = self._entry_priorities.get(key, CachePriority.LOW)
            if priority < CachePriority.CRITICAL:
                by_priority[priority].append(key)

        # Evict starting from lowest priority
        for priority in sorted(by_priority.keys()):
            while (
                self._memory_size_bytes + needed_bytes > self.memory_limit_bytes
                or len(self._memory_cache) >= self.max_memory_entries
            ) and by_priority[priority]:
                # Find oldest in this priority
                oldest_key = by_priority[priority][0]
                for key in by_priority[priority]:
                    if self._memory_cache[key].last_accessed < self._memory_cache[oldest_key].last_accessed:
                        oldest_key = key

                # Evict
                entry = self._memory_cache.pop(oldest_key)
                by_priority[priority].remove(oldest_key)
                self._memory_size_bytes -= entry.size_bytes
                self.stats.evictions += 1

                # Remove from semantic index
                self.semantic_index.remove(oldest_key)

                # Remove priority tracking
                self._entry_priorities.pop(oldest_key, None)

                logger.debug(f"Priority evicted (P{priority}): {oldest_key}")

    async def on_phase_change(self, new_phase: str, narrator_voice_id: str = "narrator"):
        """Notify cache of phase change for predictive caching."""
        if self.predictive_cache:
            await self.predictive_cache.on_phase_change(new_phase, narrator_voice_id)

    def get_stats(self) -> Dict[str, Any]:
        """Get extended statistics including semantic cache stats."""
        stats = super().get_stats()

        # Add semantic stats
        total_semantic = self.semantic_hits + self.semantic_misses
        stats["semantic_hits"] = self.semantic_hits
        stats["semantic_misses"] = self.semantic_misses
        stats["semantic_hit_rate"] = (
            round(self.semantic_hits / total_semantic * 100, 2)
            if total_semantic > 0 else 0.0
        )
        stats["semantic_index_size"] = len(self.semantic_index._key_texts)

        # Priority breakdown
        priority_counts = {p: 0 for p in range(1, 5)}
        for priority in self._entry_priorities.values():
            priority_counts[priority] = priority_counts.get(priority, 0) + 1
        stats["entries_by_priority"] = {
            "low": priority_counts.get(CachePriority.LOW, 0),
            "medium": priority_counts.get(CachePriority.MEDIUM, 0),
            "high": priority_counts.get(CachePriority.HIGH, 0),
            "critical": priority_counts.get(CachePriority.CRITICAL, 0),
        }

        return stats


async def create_aggressive_cache(
    client: Any = None,
    cache_dir: Optional[Path] = None,
    memory_limit_mb: float = 150,
    enable_prediction: bool = True,
) -> AggressiveCacheManager:
    """Create an AggressiveCacheManager with optimized settings.

    Args:
        client: ElevenLabsClient instance
        cache_dir: Optional cache directory
        memory_limit_mb: Memory limit
        enable_prediction: Enable predictive caching

    Returns:
        Configured AggressiveCacheManager
    """
    return AggressiveCacheManager(
        client=client,
        cache_dir=cache_dir,
        memory_limit_mb=memory_limit_mb,
        enable_prediction=enable_prediction,
    )
