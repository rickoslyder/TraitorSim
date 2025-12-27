"""Voice Analytics Module for TraitorSim.

Provides comprehensive metrics collection, cost tracking, and usage analytics
for the voice integration system. Supports real-time dashboards and historical
analysis for cost optimization.

Key Features:
- Per-request latency tracking with percentile analysis
- Character/credit cost tracking per model and per player
- Session-level aggregation for game analysis
- Export to JSON/CSV for external analytics tools
- Real-time metrics streaming via callbacks

Usage:
    from traitorsim.voice.analytics import VoiceAnalytics, MetricsCollector

    # Initialize analytics
    analytics = VoiceAnalytics(export_path="/data/voice_metrics")

    # Track a TTS request
    with analytics.track_tts_request(
        voice_id="george",
        model="eleven_v3",
        text_length=150
    ) as tracker:
        audio = await client.synthesize(text)
        tracker.set_audio_duration(len(audio))

    # Get cost summary
    summary = analytics.get_session_summary()
    print(f"Session cost: ${summary.total_cost:.2f}")
"""

import time
import json
import csv
import logging
import threading
from pathlib import Path
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Iterator
from enum import Enum
from contextlib import contextmanager
from collections import defaultdict
import statistics

logger = logging.getLogger(__name__)


# =============================================================================
# PRICING CONSTANTS (ElevenLabs December 2025)
# =============================================================================

class ElevenLabsModel(Enum):
    """ElevenLabs model identifiers with credit costs."""
    ELEVEN_V3 = "eleven_v3"                    # 1.0 credits/char
    FLASH_V2_5 = "eleven_flash_v2_5"           # 0.5 credits/char
    MULTILINGUAL_V2 = "eleven_multilingual_v2" # 1.0 credits/char
    TURBO_V2_5 = "eleven_turbo_v2_5"           # 0.5 credits/char


MODEL_CREDIT_COSTS = {
    ElevenLabsModel.ELEVEN_V3.value: 1.0,
    ElevenLabsModel.FLASH_V2_5.value: 0.5,
    ElevenLabsModel.MULTILINGUAL_V2.value: 1.0,
    ElevenLabsModel.TURBO_V2_5.value: 0.5,
}

# Cost per 1000 credits at different plan levels
PLAN_PRICING = {
    "starter": {"monthly": 5, "credits": 30_000, "overage": 0.30},
    "creator": {"monthly": 22, "credits": 100_000, "overage": 0.30},
    "pro": {"monthly": 99, "credits": 500_000, "overage": 0.24},
    "scale": {"monthly": 330, "credits": 2_000_000, "overage": 0.18},
    "business": {"monthly": 1320, "credits": 11_000_000, "overage": 0.12},
}


# =============================================================================
# DATA MODELS
# =============================================================================

@dataclass
class TTSRequestMetrics:
    """Metrics for a single TTS request."""
    request_id: str
    timestamp: datetime
    voice_id: str
    model: str
    text_length: int
    audio_duration_ms: Optional[int] = None
    latency_ms: Optional[float] = None
    credits_used: float = 0.0
    cache_hit: bool = False
    error: Optional[str] = None
    player_id: Optional[str] = None
    phase: Optional[str] = None
    segment_type: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON export."""
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        return data


@dataclass
class STTRequestMetrics:
    """Metrics for a single STT request."""
    request_id: str
    timestamp: datetime
    audio_duration_ms: int
    transcript_length: int
    latency_ms: float
    model: str = "nova-3"
    confidence: Optional[float] = None
    is_final: bool = True
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        return data


@dataclass
class SessionMetrics:
    """Aggregated metrics for a game session."""
    session_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    game_id: Optional[str] = None
    mode: str = "episode"  # "episode" or "hitl"

    # TTS metrics
    tts_requests: int = 0
    tts_total_chars: int = 0
    tts_total_credits: float = 0.0
    tts_cache_hits: int = 0
    tts_avg_latency_ms: float = 0.0
    tts_p95_latency_ms: float = 0.0
    tts_errors: int = 0

    # STT metrics (HITL only)
    stt_requests: int = 0
    stt_total_audio_ms: int = 0
    stt_avg_latency_ms: float = 0.0
    stt_errors: int = 0

    # Per-model breakdown
    credits_by_model: Dict[str, float] = field(default_factory=dict)

    # Per-player breakdown
    credits_by_player: Dict[str, float] = field(default_factory=dict)
    chars_by_player: Dict[str, int] = field(default_factory=dict)

    # Per-phase breakdown
    credits_by_phase: Dict[str, float] = field(default_factory=dict)

    def duration_seconds(self) -> float:
        """Calculate session duration in seconds."""
        end = self.end_time or datetime.now()
        return (end - self.start_time).total_seconds()

    def cache_hit_rate(self) -> float:
        """Calculate cache hit rate as percentage."""
        if self.tts_requests == 0:
            return 0.0
        return (self.tts_cache_hits / self.tts_requests) * 100

    def estimated_cost(self, plan: str = "pro") -> float:
        """Estimate cost based on plan pricing."""
        plan_info = PLAN_PRICING.get(plan, PLAN_PRICING["pro"])

        if self.tts_total_credits <= plan_info["credits"]:
            # Within plan limits - prorate monthly cost
            return (self.tts_total_credits / plan_info["credits"]) * plan_info["monthly"]
        else:
            # Over limit - add overage
            overage_credits = self.tts_total_credits - plan_info["credits"]
            overage_cost = (overage_credits / 1000) * plan_info["overage"]
            return plan_info["monthly"] + overage_cost

    def to_dict(self) -> Dict[str, Any]:
        data = {
            "session_id": self.session_id,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "game_id": self.game_id,
            "mode": self.mode,
            "duration_seconds": self.duration_seconds(),
            "tts": {
                "requests": self.tts_requests,
                "total_chars": self.tts_total_chars,
                "total_credits": self.tts_total_credits,
                "cache_hits": self.tts_cache_hits,
                "cache_hit_rate": self.cache_hit_rate(),
                "avg_latency_ms": self.tts_avg_latency_ms,
                "p95_latency_ms": self.tts_p95_latency_ms,
                "errors": self.tts_errors,
            },
            "stt": {
                "requests": self.stt_requests,
                "total_audio_ms": self.stt_total_audio_ms,
                "avg_latency_ms": self.stt_avg_latency_ms,
                "errors": self.stt_errors,
            },
            "breakdown": {
                "by_model": self.credits_by_model,
                "by_player": self.credits_by_player,
                "chars_by_player": self.chars_by_player,
                "by_phase": self.credits_by_phase,
            },
            "cost_estimate": {
                plan: self.estimated_cost(plan)
                for plan in PLAN_PRICING.keys()
            },
        }
        return data


@dataclass
class LatencyStats:
    """Latency statistics with percentiles."""
    count: int
    min_ms: float
    max_ms: float
    mean_ms: float
    median_ms: float
    p50_ms: float
    p75_ms: float
    p90_ms: float
    p95_ms: float
    p99_ms: float
    std_dev_ms: float


# =============================================================================
# METRICS COLLECTOR
# =============================================================================

class MetricsCollector:
    """Thread-safe metrics collector with rolling window support."""

    def __init__(
        self,
        max_requests: int = 10000,
        rolling_window_minutes: int = 60,
    ):
        """Initialize collector.

        Args:
            max_requests: Maximum requests to keep in memory
            rolling_window_minutes: Window for rolling statistics
        """
        self._lock = threading.RLock()
        self._max_requests = max_requests
        self._window = timedelta(minutes=rolling_window_minutes)

        self._tts_requests: List[TTSRequestMetrics] = []
        self._stt_requests: List[STTRequestMetrics] = []
        self._latencies: List[float] = []

        # Real-time counters
        self._total_credits = 0.0
        self._total_chars = 0
        self._total_requests = 0
        self._cache_hits = 0
        self._errors = 0

        # Callbacks for real-time streaming
        self._callbacks: List[Callable[[Dict[str, Any]], None]] = []

    def add_tts_request(self, metrics: TTSRequestMetrics) -> None:
        """Add a TTS request to the collector."""
        with self._lock:
            self._tts_requests.append(metrics)
            self._total_requests += 1
            self._total_chars += metrics.text_length
            self._total_credits += metrics.credits_used

            if metrics.cache_hit:
                self._cache_hits += 1
            if metrics.error:
                self._errors += 1
            if metrics.latency_ms:
                self._latencies.append(metrics.latency_ms)

            # Trim old requests
            if len(self._tts_requests) > self._max_requests:
                self._tts_requests = self._tts_requests[-self._max_requests:]
            if len(self._latencies) > self._max_requests:
                self._latencies = self._latencies[-self._max_requests:]

            # Notify callbacks
            self._notify_callbacks({
                "type": "tts_request",
                "data": metrics.to_dict(),
            })

    def add_stt_request(self, metrics: STTRequestMetrics) -> None:
        """Add an STT request to the collector."""
        with self._lock:
            self._stt_requests.append(metrics)

            if len(self._stt_requests) > self._max_requests:
                self._stt_requests = self._stt_requests[-self._max_requests:]

            self._notify_callbacks({
                "type": "stt_request",
                "data": metrics.to_dict(),
            })

    def register_callback(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """Register a callback for real-time metrics streaming."""
        with self._lock:
            self._callbacks.append(callback)

    def unregister_callback(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """Unregister a callback."""
        with self._lock:
            if callback in self._callbacks:
                self._callbacks.remove(callback)

    def _notify_callbacks(self, data: Dict[str, Any]) -> None:
        """Notify all registered callbacks."""
        for callback in self._callbacks:
            try:
                callback(data)
            except Exception as e:
                logger.warning(f"Callback error: {e}")

    def get_latency_stats(self) -> Optional[LatencyStats]:
        """Calculate latency statistics."""
        with self._lock:
            if not self._latencies:
                return None

            sorted_latencies = sorted(self._latencies)
            n = len(sorted_latencies)

            def percentile(p: float) -> float:
                k = (n - 1) * p / 100
                f = int(k)
                c = f + 1 if f + 1 < n else f
                return sorted_latencies[f] + (k - f) * (sorted_latencies[c] - sorted_latencies[f])

            return LatencyStats(
                count=n,
                min_ms=sorted_latencies[0],
                max_ms=sorted_latencies[-1],
                mean_ms=statistics.mean(sorted_latencies),
                median_ms=statistics.median(sorted_latencies),
                p50_ms=percentile(50),
                p75_ms=percentile(75),
                p90_ms=percentile(90),
                p95_ms=percentile(95),
                p99_ms=percentile(99),
                std_dev_ms=statistics.stdev(sorted_latencies) if n > 1 else 0.0,
            )

    def get_rolling_stats(self) -> Dict[str, Any]:
        """Get statistics for the rolling window."""
        with self._lock:
            cutoff = datetime.now() - self._window

            recent_tts = [r for r in self._tts_requests if r.timestamp > cutoff]
            recent_stt = [r for r in self._stt_requests if r.timestamp > cutoff]

            return {
                "window_minutes": self._window.total_seconds() / 60,
                "tts_requests": len(recent_tts),
                "tts_credits": sum(r.credits_used for r in recent_tts),
                "tts_chars": sum(r.text_length for r in recent_tts),
                "tts_cache_hits": sum(1 for r in recent_tts if r.cache_hit),
                "stt_requests": len(recent_stt),
                "stt_audio_ms": sum(r.audio_duration_ms for r in recent_stt),
            }

    def get_breakdown_by_model(self) -> Dict[str, Dict[str, Any]]:
        """Get credit/char breakdown by model."""
        with self._lock:
            breakdown = defaultdict(lambda: {"credits": 0.0, "chars": 0, "requests": 0})

            for r in self._tts_requests:
                breakdown[r.model]["credits"] += r.credits_used
                breakdown[r.model]["chars"] += r.text_length
                breakdown[r.model]["requests"] += 1

            return dict(breakdown)

    def get_breakdown_by_player(self) -> Dict[str, Dict[str, Any]]:
        """Get credit/char breakdown by player."""
        with self._lock:
            breakdown = defaultdict(lambda: {"credits": 0.0, "chars": 0, "requests": 0})

            for r in self._tts_requests:
                if r.player_id:
                    breakdown[r.player_id]["credits"] += r.credits_used
                    breakdown[r.player_id]["chars"] += r.text_length
                    breakdown[r.player_id]["requests"] += 1

            return dict(breakdown)

    def get_breakdown_by_phase(self) -> Dict[str, Dict[str, Any]]:
        """Get credit/char breakdown by game phase."""
        with self._lock:
            breakdown = defaultdict(lambda: {"credits": 0.0, "chars": 0, "requests": 0})

            for r in self._tts_requests:
                phase = r.phase or "unknown"
                breakdown[phase]["credits"] += r.credits_used
                breakdown[phase]["chars"] += r.text_length
                breakdown[phase]["requests"] += 1

            return dict(breakdown)

    def reset(self) -> None:
        """Reset all metrics."""
        with self._lock:
            self._tts_requests.clear()
            self._stt_requests.clear()
            self._latencies.clear()
            self._total_credits = 0.0
            self._total_chars = 0
            self._total_requests = 0
            self._cache_hits = 0
            self._errors = 0


# =============================================================================
# REQUEST TRACKER (CONTEXT MANAGER)
# =============================================================================

class TTSRequestTracker:
    """Context manager for tracking a TTS request."""

    def __init__(
        self,
        collector: MetricsCollector,
        voice_id: str,
        model: str,
        text_length: int,
        player_id: Optional[str] = None,
        phase: Optional[str] = None,
        segment_type: Optional[str] = None,
    ):
        self._collector = collector
        self._request_id = f"tts_{int(time.time() * 1000)}_{id(self)}"
        self._start_time: Optional[float] = None
        self._audio_duration_ms: Optional[int] = None
        self._cache_hit = False
        self._error: Optional[str] = None

        self._metrics = TTSRequestMetrics(
            request_id=self._request_id,
            timestamp=datetime.now(),
            voice_id=voice_id,
            model=model,
            text_length=text_length,
            player_id=player_id,
            phase=phase,
            segment_type=segment_type,
        )

    def __enter__(self) -> "TTSRequestTracker":
        self._start_time = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if self._start_time:
            latency_ms = (time.perf_counter() - self._start_time) * 1000
            self._metrics.latency_ms = latency_ms

        if exc_val:
            self._metrics.error = str(exc_val)

        self._metrics.audio_duration_ms = self._audio_duration_ms
        self._metrics.cache_hit = self._cache_hit

        # Calculate credits
        credit_rate = MODEL_CREDIT_COSTS.get(self._metrics.model, 1.0)
        self._metrics.credits_used = self._metrics.text_length * credit_rate

        self._collector.add_tts_request(self._metrics)

    def set_audio_duration(self, duration_ms: int) -> None:
        """Set the audio duration in milliseconds."""
        self._audio_duration_ms = duration_ms

    def set_cache_hit(self, hit: bool = True) -> None:
        """Mark this request as a cache hit."""
        self._cache_hit = hit
        if hit:
            # Cache hits use zero credits
            self._metrics.credits_used = 0.0

    def set_error(self, error: str) -> None:
        """Set an error message."""
        self._error = error


# =============================================================================
# VOICE ANALYTICS (MAIN CLASS)
# =============================================================================

class VoiceAnalytics:
    """Main analytics interface for voice integration.

    Provides session management, export capabilities, and cost projections.
    """

    def __init__(
        self,
        export_path: Optional[str] = None,
        auto_export: bool = True,
        export_interval_seconds: int = 300,
    ):
        """Initialize analytics.

        Args:
            export_path: Directory for metric exports
            auto_export: Automatically export metrics periodically
            export_interval_seconds: Interval between auto-exports
        """
        self.export_path = Path(export_path) if export_path else None
        self.auto_export = auto_export
        self.export_interval = export_interval_seconds

        self.collector = MetricsCollector()

        self._sessions: Dict[str, SessionMetrics] = {}
        self._current_session_id: Optional[str] = None
        self._lock = threading.RLock()

        self._export_thread: Optional[threading.Thread] = None
        self._stop_export = threading.Event()

        if self.export_path:
            self.export_path.mkdir(parents=True, exist_ok=True)

        if auto_export and export_path:
            self._start_auto_export()

    def _start_auto_export(self) -> None:
        """Start the auto-export background thread."""
        def export_loop():
            while not self._stop_export.wait(self.export_interval):
                try:
                    self.export_current_session()
                except Exception as e:
                    logger.error(f"Auto-export error: {e}")

        self._export_thread = threading.Thread(target=export_loop, daemon=True)
        self._export_thread.start()

    def start_session(
        self,
        session_id: Optional[str] = None,
        game_id: Optional[str] = None,
        mode: str = "episode",
    ) -> str:
        """Start a new analytics session.

        Args:
            session_id: Custom session ID (auto-generated if not provided)
            game_id: Associated game ID
            mode: "episode" or "hitl"

        Returns:
            The session ID
        """
        with self._lock:
            if session_id is None:
                session_id = f"session_{int(time.time() * 1000)}"

            session = SessionMetrics(
                session_id=session_id,
                start_time=datetime.now(),
                game_id=game_id,
                mode=mode,
            )

            self._sessions[session_id] = session
            self._current_session_id = session_id
            self.collector.reset()

            logger.info(f"Started analytics session: {session_id}")
            return session_id

    def end_session(self, session_id: Optional[str] = None) -> SessionMetrics:
        """End an analytics session and finalize metrics.

        Args:
            session_id: Session to end (current session if not specified)

        Returns:
            Finalized session metrics
        """
        with self._lock:
            session_id = session_id or self._current_session_id
            if not session_id or session_id not in self._sessions:
                raise ValueError(f"Session not found: {session_id}")

            session = self._sessions[session_id]
            session.end_time = datetime.now()

            # Aggregate metrics from collector
            latency_stats = self.collector.get_latency_stats()

            session.tts_requests = self.collector._total_requests
            session.tts_total_chars = self.collector._total_chars
            session.tts_total_credits = self.collector._total_credits
            session.tts_cache_hits = self.collector._cache_hits
            session.tts_errors = self.collector._errors

            if latency_stats:
                session.tts_avg_latency_ms = latency_stats.mean_ms
                session.tts_p95_latency_ms = latency_stats.p95_ms

            # Get breakdowns
            model_breakdown = self.collector.get_breakdown_by_model()
            session.credits_by_model = {
                m: d["credits"] for m, d in model_breakdown.items()
            }

            player_breakdown = self.collector.get_breakdown_by_player()
            session.credits_by_player = {
                p: d["credits"] for p, d in player_breakdown.items()
            }
            session.chars_by_player = {
                p: d["chars"] for p, d in player_breakdown.items()
            }

            phase_breakdown = self.collector.get_breakdown_by_phase()
            session.credits_by_phase = {
                p: d["credits"] for p, d in phase_breakdown.items()
            }

            # Export if configured
            if self.export_path:
                self._export_session(session)

            if session_id == self._current_session_id:
                self._current_session_id = None

            logger.info(f"Ended session: {session_id}, credits: {session.tts_total_credits:.0f}")
            return session

    @contextmanager
    def track_tts_request(
        self,
        voice_id: str,
        model: str,
        text_length: int,
        player_id: Optional[str] = None,
        phase: Optional[str] = None,
        segment_type: Optional[str] = None,
    ) -> Iterator[TTSRequestTracker]:
        """Context manager for tracking a TTS request.

        Usage:
            with analytics.track_tts_request(
                voice_id="george",
                model="eleven_v3",
                text_length=150
            ) as tracker:
                audio = await client.synthesize(text)
                tracker.set_audio_duration(len(audio))
        """
        tracker = TTSRequestTracker(
            collector=self.collector,
            voice_id=voice_id,
            model=model,
            text_length=text_length,
            player_id=player_id,
            phase=phase,
            segment_type=segment_type,
        )
        try:
            yield tracker
        finally:
            pass  # __exit__ handles metrics recording

    def record_stt_request(
        self,
        audio_duration_ms: int,
        transcript_length: int,
        latency_ms: float,
        model: str = "nova-3",
        confidence: Optional[float] = None,
        is_final: bool = True,
        error: Optional[str] = None,
    ) -> None:
        """Record an STT request."""
        metrics = STTRequestMetrics(
            request_id=f"stt_{int(time.time() * 1000)}",
            timestamp=datetime.now(),
            audio_duration_ms=audio_duration_ms,
            transcript_length=transcript_length,
            latency_ms=latency_ms,
            model=model,
            confidence=confidence,
            is_final=is_final,
            error=error,
        )
        self.collector.add_stt_request(metrics)

    def get_session_summary(self, session_id: Optional[str] = None) -> SessionMetrics:
        """Get current session summary (without ending the session)."""
        with self._lock:
            session_id = session_id or self._current_session_id
            if not session_id or session_id not in self._sessions:
                raise ValueError(f"Session not found: {session_id}")

            session = self._sessions[session_id]

            # Update with current metrics
            session.tts_requests = self.collector._total_requests
            session.tts_total_chars = self.collector._total_chars
            session.tts_total_credits = self.collector._total_credits
            session.tts_cache_hits = self.collector._cache_hits

            return session

    def get_real_time_stats(self) -> Dict[str, Any]:
        """Get real-time statistics."""
        latency_stats = self.collector.get_latency_stats()
        rolling_stats = self.collector.get_rolling_stats()

        return {
            "current_session": self._current_session_id,
            "total_requests": self.collector._total_requests,
            "total_credits": self.collector._total_credits,
            "total_chars": self.collector._total_chars,
            "cache_hit_rate": (
                (self.collector._cache_hits / self.collector._total_requests * 100)
                if self.collector._total_requests > 0 else 0.0
            ),
            "error_rate": (
                (self.collector._errors / self.collector._total_requests * 100)
                if self.collector._total_requests > 0 else 0.0
            ),
            "latency": {
                "mean_ms": latency_stats.mean_ms if latency_stats else 0,
                "p95_ms": latency_stats.p95_ms if latency_stats else 0,
                "p99_ms": latency_stats.p99_ms if latency_stats else 0,
            } if latency_stats else None,
            "rolling_window": rolling_stats,
        }

    def project_season_cost(
        self,
        days: int = 10,
        players: int = 22,
        mode: str = "episode",
        plan: str = "pro",
    ) -> Dict[str, Any]:
        """Project costs for a full season based on current usage patterns.

        Args:
            days: Expected season length
            players: Starting player count
            mode: "episode" or "hitl"
            plan: ElevenLabs plan for pricing

        Returns:
            Cost projection with breakdown
        """
        # Use player decay formula from design doc
        # Average survival: (22 + 20 + 18 + ... + 4) / 10 = ~13 players/day
        avg_players_per_day = sum(range(4, players + 1, 2)) / days
        player_days = avg_players_per_day * days

        # Estimate chars per player per day (from design doc)
        chars_per_player_day = 877  # Average scenario
        narrator_chars_per_day = 1800
        turret_chars_per_day = 450

        total_player_chars = player_days * chars_per_player_day
        total_narrator_chars = days * narrator_chars_per_day
        total_turret_chars = days * turret_chars_per_day * 0.7  # Not all days have full turret

        total_chars = total_player_chars + total_narrator_chars + total_turret_chars

        # Calculate credits based on mode
        if mode == "hitl":
            credits = total_chars * 0.5  # Flash model
        else:
            # Hybrid: narrator v3, players flash
            credits = total_narrator_chars * 1.0 + (total_player_chars + total_turret_chars) * 0.5

        # Calculate cost
        plan_info = PLAN_PRICING[plan]
        if credits <= plan_info["credits"]:
            cost = (credits / plan_info["credits"]) * plan_info["monthly"]
        else:
            base_cost = plan_info["monthly"]
            overage = (credits - plan_info["credits"]) / 1000 * plan_info["overage"]
            cost = base_cost + overage

        return {
            "season_days": days,
            "starting_players": players,
            "avg_players_per_day": avg_players_per_day,
            "player_days": player_days,
            "mode": mode,
            "plan": plan,
            "estimates": {
                "total_chars": int(total_chars),
                "player_chars": int(total_player_chars),
                "narrator_chars": int(total_narrator_chars),
                "turret_chars": int(total_turret_chars),
                "total_credits": int(credits),
            },
            "cost": {
                "estimated_usd": round(cost, 2),
                "plan_monthly": plan_info["monthly"],
                "plan_credits": plan_info["credits"],
                "credits_used_pct": round(credits / plan_info["credits"] * 100, 1),
            },
            "seasons_per_month": round(plan_info["credits"] / credits, 1),
        }

    def _export_session(self, session: SessionMetrics) -> None:
        """Export session to JSON file."""
        if not self.export_path:
            return

        filepath = self.export_path / f"{session.session_id}.json"
        with open(filepath, "w") as f:
            json.dump(session.to_dict(), f, indent=2)

        logger.info(f"Exported session to: {filepath}")

    def export_current_session(self) -> Optional[Path]:
        """Export current session metrics to file."""
        if not self._current_session_id or not self.export_path:
            return None

        session = self.get_session_summary()
        filepath = self.export_path / f"{session.session_id}_current.json"

        with open(filepath, "w") as f:
            json.dump(session.to_dict(), f, indent=2)

        return filepath

    def export_all_sessions_csv(self, filepath: str) -> None:
        """Export all sessions to a CSV file."""
        with self._lock:
            if not self._sessions:
                return

            with open(filepath, "w", newline="") as f:
                writer = csv.writer(f)

                # Header
                writer.writerow([
                    "session_id", "game_id", "mode", "start_time", "end_time",
                    "duration_seconds", "tts_requests", "tts_total_chars",
                    "tts_total_credits", "tts_cache_hits", "cache_hit_rate",
                    "tts_avg_latency_ms", "tts_p95_latency_ms", "tts_errors",
                    "cost_estimate_pro",
                ])

                # Data
                for session in self._sessions.values():
                    writer.writerow([
                        session.session_id,
                        session.game_id,
                        session.mode,
                        session.start_time.isoformat(),
                        session.end_time.isoformat() if session.end_time else "",
                        session.duration_seconds(),
                        session.tts_requests,
                        session.tts_total_chars,
                        session.tts_total_credits,
                        session.tts_cache_hits,
                        f"{session.cache_hit_rate():.1f}%",
                        session.tts_avg_latency_ms,
                        session.tts_p95_latency_ms,
                        session.tts_errors,
                        session.estimated_cost("pro"),
                    ])

        logger.info(f"Exported {len(self._sessions)} sessions to: {filepath}")

    def shutdown(self) -> None:
        """Shutdown analytics and export any remaining data."""
        self._stop_export.set()
        if self._export_thread:
            self._export_thread.join(timeout=5)

        # End current session if active
        if self._current_session_id:
            try:
                self.end_session()
            except Exception as e:
                logger.error(f"Error ending session on shutdown: {e}")


# =============================================================================
# FACTORY FUNCTIONS
# =============================================================================

def create_analytics(
    export_path: Optional[str] = None,
    auto_export: bool = True,
) -> VoiceAnalytics:
    """Create a VoiceAnalytics instance with default configuration.

    Args:
        export_path: Directory for metric exports
        auto_export: Enable automatic periodic exports

    Returns:
        Configured VoiceAnalytics instance
    """
    return VoiceAnalytics(
        export_path=export_path,
        auto_export=auto_export,
    )


def calculate_credits(text_length: int, model: str = "eleven_v3") -> float:
    """Calculate credits for a given text length and model.

    Args:
        text_length: Number of characters
        model: ElevenLabs model ID

    Returns:
        Credits that will be consumed
    """
    rate = MODEL_CREDIT_COSTS.get(model, 1.0)
    return text_length * rate


def estimate_cost(credits: float, plan: str = "pro") -> float:
    """Estimate cost for a given number of credits.

    Args:
        credits: Number of credits
        plan: ElevenLabs plan name

    Returns:
        Estimated cost in USD
    """
    plan_info = PLAN_PRICING.get(plan, PLAN_PRICING["pro"])

    if credits <= plan_info["credits"]:
        return (credits / plan_info["credits"]) * plan_info["monthly"]
    else:
        overage = credits - plan_info["credits"]
        return plan_info["monthly"] + (overage / 1000) * plan_info["overage"]
