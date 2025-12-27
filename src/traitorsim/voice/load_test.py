"""Load Testing Framework for TraitorSim Voice Integration.

Provides tools for simulating concurrent HITL games and measuring system
performance under load. Supports stress testing, soak testing, and
capacity planning.

Key Features:
- Concurrent game simulation with configurable parameters
- Latency measurement at each stage of the voice pipeline
- Resource utilization monitoring (CPU, memory, connections)
- Bottleneck identification and reporting
- Integration with VoiceAnalytics for detailed metrics

Usage:
    from traitorsim.voice.load_test import LoadTestRunner, LoadTestConfig

    # Configure test
    config = LoadTestConfig(
        concurrent_games=5,
        players_per_game=22,
        duration_seconds=300,
        tts_model="eleven_flash_v2_5",
    )

    # Run test
    runner = LoadTestRunner(config)
    results = await runner.run()

    # Analyze results
    print(f"Peak latency: {results.peak_latency_ms}ms")
    print(f"Error rate: {results.error_rate}%")
"""

import asyncio
import time
import random
import logging
import threading
import json
from pathlib import Path
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Tuple
from enum import Enum
from collections import defaultdict
import statistics

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

from .analytics import VoiceAnalytics, MetricsCollector, LatencyStats

logger = logging.getLogger(__name__)


# =============================================================================
# CONFIGURATION
# =============================================================================

@dataclass
class LoadTestConfig:
    """Configuration for load testing."""

    # Concurrency settings
    concurrent_games: int = 1
    players_per_game: int = 22
    traitors_per_game: int = 3

    # Test duration
    duration_seconds: int = 300  # 5 minutes default
    warmup_seconds: int = 30
    cooldown_seconds: int = 30

    # Request patterns
    requests_per_second_target: float = 10.0
    burst_mode: bool = False
    burst_size: int = 20
    burst_interval_seconds: float = 5.0

    # Simulated latencies (for mock mode)
    mock_tts_latency_ms: Tuple[float, float] = (50, 200)  # min, max
    mock_stt_latency_ms: Tuple[float, float] = (30, 100)
    mock_llm_latency_ms: Tuple[float, float] = (200, 500)

    # TTS settings
    tts_model: str = "eleven_flash_v2_5"
    avg_text_length: int = 150
    text_length_stddev: int = 50

    # Error simulation
    error_rate: float = 0.01  # 1% simulated errors
    timeout_rate: float = 0.005  # 0.5% simulated timeouts
    timeout_ms: float = 5000

    # Resource monitoring
    monitor_resources: bool = True
    resource_sample_interval_seconds: float = 1.0

    # Output
    output_dir: Optional[str] = None
    verbose: bool = False


class TestPhase(Enum):
    """Phases of a load test."""
    WARMUP = "warmup"
    MAIN = "main"
    COOLDOWN = "cooldown"
    COMPLETED = "completed"


# =============================================================================
# DATA MODELS
# =============================================================================

@dataclass
class RequestResult:
    """Result of a single simulated request."""
    request_id: str
    game_id: str
    player_id: str
    request_type: str  # "tts", "stt", "llm"
    start_time: float
    end_time: float
    latency_ms: float
    success: bool
    error: Optional[str] = None
    text_length: Optional[int] = None
    phase: Optional[str] = None

    @property
    def duration_ms(self) -> float:
        return (self.end_time - self.start_time) * 1000


@dataclass
class GameSimulation:
    """State for a simulated game."""
    game_id: str
    players: List[str]
    traitors: List[str]
    current_day: int = 1
    current_phase: str = "breakfast"
    alive_players: List[str] = field(default_factory=list)
    start_time: Optional[float] = None
    requests_made: int = 0

    def __post_init__(self):
        if not self.alive_players:
            self.alive_players = list(self.players)


@dataclass
class ResourceSample:
    """Resource utilization sample."""
    timestamp: float
    cpu_percent: float
    memory_percent: float
    memory_mb: float
    active_connections: int
    open_files: int


@dataclass
class LoadTestResults:
    """Results from a load test run."""
    config: LoadTestConfig
    start_time: datetime
    end_time: datetime
    duration_seconds: float

    # Request statistics
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    timed_out_requests: int = 0

    # Latency statistics
    latencies_ms: List[float] = field(default_factory=list)
    latency_by_type: Dict[str, List[float]] = field(default_factory=dict)

    # Throughput
    requests_per_second: float = 0.0
    peak_requests_per_second: float = 0.0

    # Resource usage
    resource_samples: List[ResourceSample] = field(default_factory=list)
    peak_cpu_percent: float = 0.0
    peak_memory_mb: float = 0.0

    # Error analysis
    error_counts: Dict[str, int] = field(default_factory=dict)

    # Game statistics
    games_simulated: int = 0
    total_simulated_credits: float = 0.0

    def success_rate(self) -> float:
        """Calculate success rate percentage."""
        if self.total_requests == 0:
            return 100.0
        return (self.successful_requests / self.total_requests) * 100

    def error_rate(self) -> float:
        """Calculate error rate percentage."""
        return 100.0 - self.success_rate()

    def latency_stats(self) -> Optional[LatencyStats]:
        """Calculate latency statistics."""
        if not self.latencies_ms:
            return None

        sorted_latencies = sorted(self.latencies_ms)
        n = len(sorted_latencies)

        def percentile(p: float) -> float:
            k = (n - 1) * p / 100
            f = int(k)
            c = min(f + 1, n - 1)
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

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON export."""
        stats = self.latency_stats()

        return {
            "config": asdict(self.config),
            "timing": {
                "start_time": self.start_time.isoformat(),
                "end_time": self.end_time.isoformat(),
                "duration_seconds": self.duration_seconds,
            },
            "requests": {
                "total": self.total_requests,
                "successful": self.successful_requests,
                "failed": self.failed_requests,
                "timed_out": self.timed_out_requests,
                "success_rate": self.success_rate(),
                "error_rate": self.error_rate(),
            },
            "throughput": {
                "requests_per_second": self.requests_per_second,
                "peak_requests_per_second": self.peak_requests_per_second,
            },
            "latency": {
                "min_ms": stats.min_ms if stats else 0,
                "max_ms": stats.max_ms if stats else 0,
                "mean_ms": stats.mean_ms if stats else 0,
                "median_ms": stats.median_ms if stats else 0,
                "p50_ms": stats.p50_ms if stats else 0,
                "p75_ms": stats.p75_ms if stats else 0,
                "p90_ms": stats.p90_ms if stats else 0,
                "p95_ms": stats.p95_ms if stats else 0,
                "p99_ms": stats.p99_ms if stats else 0,
            },
            "latency_by_type": {
                req_type: {
                    "mean_ms": statistics.mean(lats) if lats else 0,
                    "p95_ms": sorted(lats)[int(len(lats) * 0.95)] if lats else 0,
                }
                for req_type, lats in self.latency_by_type.items()
            },
            "resources": {
                "peak_cpu_percent": self.peak_cpu_percent,
                "peak_memory_mb": self.peak_memory_mb,
                "samples": len(self.resource_samples),
            },
            "errors": self.error_counts,
            "games": {
                "simulated": self.games_simulated,
                "total_credits": self.total_simulated_credits,
            },
        }

    def print_summary(self) -> str:
        """Generate a human-readable summary."""
        stats = self.latency_stats()

        lines = [
            "=" * 60,
            "LOAD TEST RESULTS",
            "=" * 60,
            f"Duration: {self.duration_seconds:.1f}s",
            f"Games simulated: {self.games_simulated}",
            "",
            "REQUESTS:",
            f"  Total: {self.total_requests}",
            f"  Successful: {self.successful_requests} ({self.success_rate():.1f}%)",
            f"  Failed: {self.failed_requests}",
            f"  Timed out: {self.timed_out_requests}",
            "",
            "THROUGHPUT:",
            f"  Average: {self.requests_per_second:.1f} req/s",
            f"  Peak: {self.peak_requests_per_second:.1f} req/s",
            "",
            "LATENCY:",
        ]

        if stats:
            lines.extend([
                f"  Min: {stats.min_ms:.1f}ms",
                f"  Mean: {stats.mean_ms:.1f}ms",
                f"  Median: {stats.median_ms:.1f}ms",
                f"  P95: {stats.p95_ms:.1f}ms",
                f"  P99: {stats.p99_ms:.1f}ms",
                f"  Max: {stats.max_ms:.1f}ms",
            ])
        else:
            lines.append("  No latency data")

        lines.extend([
            "",
            "RESOURCES:",
            f"  Peak CPU: {self.peak_cpu_percent:.1f}%",
            f"  Peak Memory: {self.peak_memory_mb:.1f}MB",
            "",
            "COST ESTIMATE:",
            f"  Credits used: {self.total_simulated_credits:.0f}",
            "=" * 60,
        ])

        return "\n".join(lines)


# =============================================================================
# MOCK CLIENTS (for testing without real APIs)
# =============================================================================

class MockTTSClient:
    """Mock TTS client for load testing."""

    def __init__(self, config: LoadTestConfig):
        self.config = config

    async def synthesize(self, text: str, voice_id: str) -> Tuple[bytes, float]:
        """Simulate TTS synthesis.

        Returns:
            Tuple of (mock audio bytes, latency in ms)
        """
        # Simulate latency
        latency_ms = random.uniform(*self.config.mock_tts_latency_ms)
        await asyncio.sleep(latency_ms / 1000)

        # Simulate errors
        if random.random() < self.config.error_rate:
            raise Exception("Simulated TTS error")
        if random.random() < self.config.timeout_rate:
            raise asyncio.TimeoutError("Simulated timeout")

        # Mock audio (just bytes for size estimation)
        audio_size = int(len(text) * 100)  # ~100 bytes per character
        return b"\x00" * audio_size, latency_ms


class MockSTTClient:
    """Mock STT client for load testing."""

    def __init__(self, config: LoadTestConfig):
        self.config = config

    async def transcribe(self, audio_duration_ms: int) -> Tuple[str, float]:
        """Simulate STT transcription.

        Returns:
            Tuple of (transcript, latency in ms)
        """
        latency_ms = random.uniform(*self.config.mock_stt_latency_ms)
        await asyncio.sleep(latency_ms / 1000)

        if random.random() < self.config.error_rate:
            raise Exception("Simulated STT error")

        # Mock transcript
        words_per_second = 2.5
        word_count = int((audio_duration_ms / 1000) * words_per_second)
        transcript = " ".join(["word"] * word_count)

        return transcript, latency_ms


class MockLLMClient:
    """Mock LLM client for load testing."""

    def __init__(self, config: LoadTestConfig):
        self.config = config

    async def generate(self, prompt: str) -> Tuple[str, float]:
        """Simulate LLM response generation.

        Returns:
            Tuple of (response, latency in ms)
        """
        latency_ms = random.uniform(*self.config.mock_llm_latency_ms)
        await asyncio.sleep(latency_ms / 1000)

        if random.random() < self.config.error_rate:
            raise Exception("Simulated LLM error")

        # Mock response
        response = "This is a simulated agent response for load testing purposes."
        return response, latency_ms


# =============================================================================
# LOAD TEST RUNNER
# =============================================================================

class LoadTestRunner:
    """Main load test runner."""

    def __init__(
        self,
        config: LoadTestConfig,
        analytics: Optional[VoiceAnalytics] = None,
    ):
        """Initialize load test runner.

        Args:
            config: Test configuration
            analytics: Optional analytics instance for metrics
        """
        self.config = config
        self.analytics = analytics or VoiceAnalytics()

        # Clients
        self.tts_client = MockTTSClient(config)
        self.stt_client = MockSTTClient(config)
        self.llm_client = MockLLMClient(config)

        # State
        self._phase = TestPhase.WARMUP
        self._games: Dict[str, GameSimulation] = {}
        self._results: List[RequestResult] = []
        self._resource_samples: List[ResourceSample] = []

        # Synchronization
        self._lock = threading.Lock()
        self._stop_event = asyncio.Event()

        # Throughput tracking
        self._request_times: List[float] = []

    async def run(self) -> LoadTestResults:
        """Run the load test.

        Returns:
            LoadTestResults with all metrics
        """
        start_time = datetime.now()
        test_start = time.time()

        logger.info(f"Starting load test: {self.config.concurrent_games} games, "
                    f"{self.config.duration_seconds}s duration")

        # Start analytics session
        self.analytics.start_session(
            session_id=f"loadtest_{int(time.time())}",
            mode="hitl",
        )

        try:
            # Initialize games
            await self._initialize_games()

            # Start resource monitoring
            resource_task = None
            if self.config.monitor_resources and HAS_PSUTIL:
                resource_task = asyncio.create_task(self._monitor_resources())

            # Run test phases
            await self._run_warmup()
            await self._run_main_test()
            await self._run_cooldown()

            # Stop resource monitoring
            self._stop_event.set()
            if resource_task:
                await resource_task

        finally:
            self.analytics.end_session()

        end_time = datetime.now()
        duration = time.time() - test_start

        # Compile results
        results = self._compile_results(start_time, end_time, duration)

        # Export if configured
        if self.config.output_dir:
            self._export_results(results)

        logger.info(f"Load test completed: {results.total_requests} requests, "
                    f"{results.success_rate():.1f}% success rate")

        return results

    async def _initialize_games(self) -> None:
        """Initialize simulated games."""
        for i in range(self.config.concurrent_games):
            game_id = f"game_{i}"
            players = [f"player_{i}_{j}" for j in range(self.config.players_per_game)]
            traitors = random.sample(players, self.config.traitors_per_game)

            self._games[game_id] = GameSimulation(
                game_id=game_id,
                players=players,
                traitors=traitors,
                start_time=time.time(),
            )

        logger.info(f"Initialized {len(self._games)} games")

    async def _run_warmup(self) -> None:
        """Run warmup phase."""
        self._phase = TestPhase.WARMUP
        logger.info(f"Warmup phase: {self.config.warmup_seconds}s")

        warmup_end = time.time() + self.config.warmup_seconds
        rate = self.config.requests_per_second_target * 0.5  # Half rate for warmup

        while time.time() < warmup_end:
            await self._generate_requests(rate)
            await asyncio.sleep(0.1)

    async def _run_main_test(self) -> None:
        """Run main test phase."""
        self._phase = TestPhase.MAIN
        logger.info(f"Main test phase: {self.config.duration_seconds}s")

        main_end = time.time() + self.config.duration_seconds

        while time.time() < main_end:
            if self.config.burst_mode:
                await self._generate_burst()
                await asyncio.sleep(self.config.burst_interval_seconds)
            else:
                await self._generate_requests(self.config.requests_per_second_target)
                await asyncio.sleep(0.1)

    async def _run_cooldown(self) -> None:
        """Run cooldown phase."""
        self._phase = TestPhase.COOLDOWN
        logger.info(f"Cooldown phase: {self.config.cooldown_seconds}s")

        cooldown_end = time.time() + self.config.cooldown_seconds
        rate = self.config.requests_per_second_target * 0.25

        while time.time() < cooldown_end:
            await self._generate_requests(rate)
            await asyncio.sleep(0.1)

        self._phase = TestPhase.COMPLETED

    async def _generate_requests(self, rate: float) -> None:
        """Generate requests at the specified rate."""
        # Calculate how many requests to generate in this interval (0.1s)
        expected = rate * 0.1
        actual = int(expected) + (1 if random.random() < (expected - int(expected)) else 0)

        tasks = []
        for _ in range(actual):
            game = random.choice(list(self._games.values()))
            if game.alive_players:
                player = random.choice(game.alive_players)
                request_type = random.choice(["tts", "tts", "tts", "stt", "llm"])
                tasks.append(self._simulate_request(game, player, request_type))

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _generate_burst(self) -> None:
        """Generate a burst of requests."""
        tasks = []
        for _ in range(self.config.burst_size):
            game = random.choice(list(self._games.values()))
            if game.alive_players:
                player = random.choice(game.alive_players)
                request_type = random.choice(["tts", "stt", "llm"])
                tasks.append(self._simulate_request(game, player, request_type))

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _simulate_request(
        self,
        game: GameSimulation,
        player: str,
        request_type: str,
    ) -> None:
        """Simulate a single request."""
        request_id = f"req_{int(time.time() * 1000)}_{random.randint(0, 9999)}"
        start_time = time.time()

        try:
            if request_type == "tts":
                text_length = max(10, int(random.gauss(
                    self.config.avg_text_length,
                    self.config.text_length_stddev
                )))
                text = "x" * text_length

                _, latency_ms = await asyncio.wait_for(
                    self.tts_client.synthesize(text, f"voice_{player}"),
                    timeout=self.config.timeout_ms / 1000
                )

                result = RequestResult(
                    request_id=request_id,
                    game_id=game.game_id,
                    player_id=player,
                    request_type="tts",
                    start_time=start_time,
                    end_time=time.time(),
                    latency_ms=latency_ms,
                    success=True,
                    text_length=text_length,
                    phase=game.current_phase,
                )

            elif request_type == "stt":
                audio_duration = random.randint(1000, 5000)  # 1-5 seconds
                _, latency_ms = await asyncio.wait_for(
                    self.stt_client.transcribe(audio_duration),
                    timeout=self.config.timeout_ms / 1000
                )

                result = RequestResult(
                    request_id=request_id,
                    game_id=game.game_id,
                    player_id=player,
                    request_type="stt",
                    start_time=start_time,
                    end_time=time.time(),
                    latency_ms=latency_ms,
                    success=True,
                    phase=game.current_phase,
                )

            else:  # llm
                prompt = "Generate agent response"
                _, latency_ms = await asyncio.wait_for(
                    self.llm_client.generate(prompt),
                    timeout=self.config.timeout_ms / 1000
                )

                result = RequestResult(
                    request_id=request_id,
                    game_id=game.game_id,
                    player_id=player,
                    request_type="llm",
                    start_time=start_time,
                    end_time=time.time(),
                    latency_ms=latency_ms,
                    success=True,
                    phase=game.current_phase,
                )

        except asyncio.TimeoutError:
            result = RequestResult(
                request_id=request_id,
                game_id=game.game_id,
                player_id=player,
                request_type=request_type,
                start_time=start_time,
                end_time=time.time(),
                latency_ms=self.config.timeout_ms,
                success=False,
                error="timeout",
                phase=game.current_phase,
            )

        except Exception as e:
            result = RequestResult(
                request_id=request_id,
                game_id=game.game_id,
                player_id=player,
                request_type=request_type,
                start_time=start_time,
                end_time=time.time(),
                latency_ms=(time.time() - start_time) * 1000,
                success=False,
                error=str(e),
                phase=game.current_phase,
            )

        with self._lock:
            self._results.append(result)
            self._request_times.append(time.time())
            game.requests_made += 1

    async def _monitor_resources(self) -> None:
        """Monitor system resources."""
        process = psutil.Process()

        while not self._stop_event.is_set():
            try:
                sample = ResourceSample(
                    timestamp=time.time(),
                    cpu_percent=process.cpu_percent(),
                    memory_percent=process.memory_percent(),
                    memory_mb=process.memory_info().rss / (1024 * 1024),
                    active_connections=len(process.connections()),
                    open_files=len(process.open_files()),
                )

                with self._lock:
                    self._resource_samples.append(sample)

            except Exception as e:
                logger.warning(f"Resource monitoring error: {e}")

            await asyncio.sleep(self.config.resource_sample_interval_seconds)

    def _compile_results(
        self,
        start_time: datetime,
        end_time: datetime,
        duration: float,
    ) -> LoadTestResults:
        """Compile results from the test run."""
        results = LoadTestResults(
            config=self.config,
            start_time=start_time,
            end_time=end_time,
            duration_seconds=duration,
            games_simulated=len(self._games),
        )

        # Process request results
        for r in self._results:
            results.total_requests += 1
            results.latencies_ms.append(r.latency_ms)

            if r.request_type not in results.latency_by_type:
                results.latency_by_type[r.request_type] = []
            results.latency_by_type[r.request_type].append(r.latency_ms)

            if r.success:
                results.successful_requests += 1
                if r.text_length:
                    # Estimate credits (Flash model = 0.5 credits/char)
                    results.total_simulated_credits += r.text_length * 0.5
            else:
                results.failed_requests += 1
                if r.error == "timeout":
                    results.timed_out_requests += 1
                if r.error:
                    results.error_counts[r.error] = results.error_counts.get(r.error, 0) + 1

        # Calculate throughput
        if duration > 0:
            results.requests_per_second = results.total_requests / duration

        # Calculate peak throughput (1-second windows)
        if self._request_times:
            window_counts = defaultdict(int)
            for t in self._request_times:
                window = int(t)
                window_counts[window] += 1
            if window_counts:
                results.peak_requests_per_second = max(window_counts.values())

        # Process resource samples
        results.resource_samples = self._resource_samples
        if self._resource_samples:
            results.peak_cpu_percent = max(s.cpu_percent for s in self._resource_samples)
            results.peak_memory_mb = max(s.memory_mb for s in self._resource_samples)

        return results

    def _export_results(self, results: LoadTestResults) -> None:
        """Export results to files."""
        output_dir = Path(self.config.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # JSON summary
        json_path = output_dir / f"loadtest_{timestamp}.json"
        with open(json_path, "w") as f:
            json.dump(results.to_dict(), f, indent=2)

        # Text summary
        txt_path = output_dir / f"loadtest_{timestamp}.txt"
        with open(txt_path, "w") as f:
            f.write(results.print_summary())

        logger.info(f"Results exported to: {output_dir}")


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

async def run_quick_test(
    concurrent_games: int = 1,
    duration_seconds: int = 60,
) -> LoadTestResults:
    """Run a quick load test with default settings.

    Args:
        concurrent_games: Number of concurrent games to simulate
        duration_seconds: Test duration in seconds

    Returns:
        LoadTestResults
    """
    config = LoadTestConfig(
        concurrent_games=concurrent_games,
        duration_seconds=duration_seconds,
        warmup_seconds=10,
        cooldown_seconds=10,
    )

    runner = LoadTestRunner(config)
    return await runner.run()


async def run_stress_test(
    max_concurrent_games: int = 10,
    ramp_up_seconds: int = 60,
) -> List[LoadTestResults]:
    """Run a stress test with increasing load.

    Args:
        max_concurrent_games: Maximum games to simulate
        ramp_up_seconds: Time to ramp up to max load

    Returns:
        List of results at each concurrency level
    """
    results = []
    step_duration = ramp_up_seconds // max_concurrent_games

    for n in range(1, max_concurrent_games + 1):
        logger.info(f"Stress test: {n} concurrent games")

        config = LoadTestConfig(
            concurrent_games=n,
            duration_seconds=step_duration,
            warmup_seconds=5,
            cooldown_seconds=5,
        )

        runner = LoadTestRunner(config)
        result = await runner.run()
        results.append(result)

        # Stop if error rate is too high
        if result.error_rate() > 10:
            logger.warning(f"Stopping stress test: error rate {result.error_rate():.1f}%")
            break

    return results


async def run_soak_test(
    concurrent_games: int = 3,
    duration_hours: float = 1.0,
) -> LoadTestResults:
    """Run a soak test for extended duration.

    Args:
        concurrent_games: Number of concurrent games
        duration_hours: Test duration in hours

    Returns:
        LoadTestResults
    """
    config = LoadTestConfig(
        concurrent_games=concurrent_games,
        duration_seconds=int(duration_hours * 3600),
        warmup_seconds=60,
        cooldown_seconds=60,
        requests_per_second_target=5.0,  # Lower rate for soak
    )

    runner = LoadTestRunner(config)
    return await runner.run()


def analyze_bottlenecks(results: LoadTestResults) -> Dict[str, Any]:
    """Analyze load test results to identify bottlenecks.

    Args:
        results: LoadTestResults from a test run

    Returns:
        Analysis with identified bottlenecks
    """
    analysis = {
        "bottlenecks": [],
        "recommendations": [],
        "risk_level": "low",
    }

    stats = results.latency_stats()

    # Check latency
    if stats:
        if stats.p95_ms > 500:
            analysis["bottlenecks"].append({
                "type": "high_latency",
                "metric": "p95_latency_ms",
                "value": stats.p95_ms,
                "threshold": 500,
            })
            analysis["recommendations"].append(
                "Consider using Flash model for lower latency"
            )
            analysis["risk_level"] = "medium"

        if stats.p99_ms > 1000:
            analysis["bottlenecks"].append({
                "type": "tail_latency",
                "metric": "p99_latency_ms",
                "value": stats.p99_ms,
                "threshold": 1000,
            })
            analysis["recommendations"].append(
                "Implement request timeouts and retries"
            )
            analysis["risk_level"] = "high"

    # Check error rate
    if results.error_rate() > 1:
        analysis["bottlenecks"].append({
            "type": "high_error_rate",
            "metric": "error_rate",
            "value": results.error_rate(),
            "threshold": 1,
        })
        analysis["recommendations"].append(
            "Implement circuit breaker pattern"
        )
        analysis["risk_level"] = "high"

    # Check throughput
    target_rps = results.config.requests_per_second_target
    actual_rps = results.requests_per_second
    if actual_rps < target_rps * 0.8:
        analysis["bottlenecks"].append({
            "type": "throughput_limit",
            "metric": "requests_per_second",
            "value": actual_rps,
            "target": target_rps,
        })
        analysis["recommendations"].append(
            "Scale horizontally or optimize request handling"
        )
        analysis["risk_level"] = "medium"

    # Check resources
    if results.peak_cpu_percent > 80:
        analysis["bottlenecks"].append({
            "type": "cpu_saturation",
            "metric": "peak_cpu_percent",
            "value": results.peak_cpu_percent,
            "threshold": 80,
        })
        analysis["recommendations"].append(
            "Add CPU resources or optimize processing"
        )

    if results.peak_memory_mb > 1000:
        analysis["bottlenecks"].append({
            "type": "memory_pressure",
            "metric": "peak_memory_mb",
            "value": results.peak_memory_mb,
            "threshold": 1000,
        })
        analysis["recommendations"].append(
            "Review memory usage and implement caching limits"
        )

    # By request type analysis
    for req_type, latencies in results.latency_by_type.items():
        if latencies:
            avg = statistics.mean(latencies)
            if req_type == "tts" and avg > 200:
                analysis["recommendations"].append(
                    f"TTS latency ({avg:.0f}ms) high - consider voice caching"
                )
            elif req_type == "stt" and avg > 150:
                analysis["recommendations"].append(
                    f"STT latency ({avg:.0f}ms) high - use streaming transcription"
                )
            elif req_type == "llm" and avg > 400:
                analysis["recommendations"].append(
                    f"LLM latency ({avg:.0f}ms) high - consider smaller model or caching"
                )

    return analysis
