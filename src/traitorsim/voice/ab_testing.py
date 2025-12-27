"""A/B Testing Framework for Voice Configuration Experiments.

Enables systematic experimentation with voice parameters to optimize for
quality, latency, and cost. Supports multi-variant tests, statistical
significance analysis, and automatic winner selection.

Key Features:
- Define experiments with multiple voice variants
- Automatic traffic splitting with consistent user assignment
- Real-time metrics collection per variant
- Statistical significance testing (chi-square, t-test)
- Experiment lifecycle management

Usage:
    from traitorsim.voice.ab_testing import (
        ABTestManager,
        Experiment,
        Variant,
    )

    # Create experiment
    experiment = Experiment(
        name="model_comparison",
        variants=[
            Variant("control", {"model": "eleven_v3"}),
            Variant("flash", {"model": "eleven_flash_v2_5"}),
        ],
    )

    # Run experiment
    manager = ABTestManager()
    manager.register_experiment(experiment)

    # Get variant for a user
    variant = manager.get_variant("model_comparison", user_id="player_123")

    # Record outcome
    manager.record_outcome(
        experiment_name="model_comparison",
        user_id="player_123",
        metrics={"latency_ms": 150, "quality_score": 4.5}
    )
"""

import hashlib
import json
import time
import threading
import logging
from pathlib import Path
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
from collections import defaultdict
import statistics
import math

logger = logging.getLogger(__name__)


# =============================================================================
# DATA MODELS
# =============================================================================

class ExperimentStatus(Enum):
    """Status of an A/B test experiment."""
    DRAFT = "draft"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class WinnerCriteria(Enum):
    """Criteria for selecting a winner."""
    LOWEST_LATENCY = "lowest_latency"
    HIGHEST_QUALITY = "highest_quality"
    LOWEST_COST = "lowest_cost"
    BEST_COMPOSITE = "best_composite"


@dataclass
class Variant:
    """A variant in an A/B test."""
    name: str
    config: Dict[str, Any]
    weight: float = 1.0  # Relative traffic weight
    description: Optional[str] = None

    # Metrics (populated during experiment)
    impressions: int = 0
    conversions: int = 0
    total_latency_ms: float = 0.0
    total_quality_score: float = 0.0
    total_cost: float = 0.0
    errors: int = 0

    # Collected metrics lists for statistical analysis
    latencies: List[float] = field(default_factory=list)
    quality_scores: List[float] = field(default_factory=list)
    costs: List[float] = field(default_factory=list)

    def record_outcome(
        self,
        latency_ms: Optional[float] = None,
        quality_score: Optional[float] = None,
        cost: Optional[float] = None,
        success: bool = True,
    ) -> None:
        """Record an outcome for this variant."""
        self.impressions += 1

        if success:
            self.conversions += 1
        else:
            self.errors += 1

        if latency_ms is not None:
            self.total_latency_ms += latency_ms
            self.latencies.append(latency_ms)

        if quality_score is not None:
            self.total_quality_score += quality_score
            self.quality_scores.append(quality_score)

        if cost is not None:
            self.total_cost += cost
            self.costs.append(cost)

    @property
    def avg_latency_ms(self) -> float:
        return self.total_latency_ms / self.impressions if self.impressions > 0 else 0

    @property
    def avg_quality_score(self) -> float:
        return self.total_quality_score / self.conversions if self.conversions > 0 else 0

    @property
    def avg_cost(self) -> float:
        return self.total_cost / self.impressions if self.impressions > 0 else 0

    @property
    def success_rate(self) -> float:
        return (self.conversions / self.impressions * 100) if self.impressions > 0 else 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "config": self.config,
            "weight": self.weight,
            "description": self.description,
            "metrics": {
                "impressions": self.impressions,
                "conversions": self.conversions,
                "errors": self.errors,
                "success_rate": self.success_rate,
                "avg_latency_ms": self.avg_latency_ms,
                "avg_quality_score": self.avg_quality_score,
                "avg_cost": self.avg_cost,
            },
        }


@dataclass
class Experiment:
    """An A/B test experiment."""
    name: str
    variants: List[Variant]
    description: Optional[str] = None

    # Experiment configuration
    status: ExperimentStatus = ExperimentStatus.DRAFT
    winner_criteria: WinnerCriteria = WinnerCriteria.BEST_COMPOSITE
    min_sample_size: int = 100  # Minimum samples per variant
    confidence_level: float = 0.95  # Statistical significance threshold

    # Timing
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    max_duration_hours: Optional[float] = None

    # Results
    winner: Optional[str] = None
    significance_achieved: bool = False

    def __post_init__(self):
        # Normalize weights
        total_weight = sum(v.weight for v in self.variants)
        if total_weight > 0:
            for v in self.variants:
                v.weight = v.weight / total_weight

    def get_variant(self, user_id: str) -> Variant:
        """Get the variant for a user (consistent hashing)."""
        # Use consistent hashing for stable assignment
        hash_input = f"{self.name}:{user_id}"
        hash_value = int(hashlib.md5(hash_input.encode()).hexdigest(), 16)
        random_value = (hash_value % 10000) / 10000.0

        cumulative = 0.0
        for variant in self.variants:
            cumulative += variant.weight
            if random_value < cumulative:
                return variant

        return self.variants[-1]  # Fallback to last variant

    def is_complete(self) -> bool:
        """Check if experiment has enough data."""
        if all(v.impressions >= self.min_sample_size for v in self.variants):
            return True

        if self.max_duration_hours and self.started_at:
            elapsed = datetime.now() - self.started_at
            if elapsed.total_seconds() / 3600 >= self.max_duration_hours:
                return True

        return False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "status": self.status.value,
            "winner_criteria": self.winner_criteria.value,
            "variants": [v.to_dict() for v in self.variants],
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
            "winner": self.winner,
            "significance_achieved": self.significance_achieved,
        }


@dataclass
class ExperimentResults:
    """Results and analysis of an experiment."""
    experiment_name: str
    variants: List[Dict[str, Any]]
    winner: Optional[str]
    significance_achieved: bool
    p_value: Optional[float]
    confidence_interval: Optional[Tuple[float, float]]
    analysis: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "experiment_name": self.experiment_name,
            "variants": self.variants,
            "winner": self.winner,
            "significance_achieved": self.significance_achieved,
            "p_value": self.p_value,
            "confidence_interval": self.confidence_interval,
            "analysis": self.analysis,
        }


# =============================================================================
# STATISTICAL ANALYSIS
# =============================================================================

def calculate_t_test(
    sample1: List[float],
    sample2: List[float],
) -> Tuple[float, float]:
    """Perform Welch's t-test for two samples.

    Returns:
        Tuple of (t-statistic, p-value)
    """
    n1, n2 = len(sample1), len(sample2)
    if n1 < 2 or n2 < 2:
        return 0.0, 1.0

    mean1, mean2 = statistics.mean(sample1), statistics.mean(sample2)
    var1, var2 = statistics.variance(sample1), statistics.variance(sample2)

    # Welch's t-test
    se = math.sqrt(var1 / n1 + var2 / n2)
    if se == 0:
        return 0.0, 1.0

    t_stat = (mean1 - mean2) / se

    # Approximate degrees of freedom (Welch-Satterthwaite)
    num = (var1 / n1 + var2 / n2) ** 2
    denom = (var1 / n1) ** 2 / (n1 - 1) + (var2 / n2) ** 2 / (n2 - 1)
    df = num / denom if denom > 0 else 1

    # Approximate p-value using normal distribution for large samples
    # For more accurate results, would need scipy.stats.t
    p_value = 2 * (1 - _normal_cdf(abs(t_stat)))

    return t_stat, p_value


def _normal_cdf(x: float) -> float:
    """Approximation of standard normal CDF."""
    # Abramowitz and Stegun approximation
    a1, a2, a3, a4, a5 = 0.254829592, -0.284496736, 1.421413741, -1.453152027, 1.061405429
    p = 0.3275911

    sign = 1 if x >= 0 else -1
    x = abs(x) / math.sqrt(2)

    t = 1.0 / (1.0 + p * x)
    y = 1.0 - (((((a5 * t + a4) * t) + a3) * t + a2) * t + a1) * t * math.exp(-x * x)

    return 0.5 * (1.0 + sign * y)


def calculate_chi_square(
    successes1: int,
    total1: int,
    successes2: int,
    total2: int,
) -> Tuple[float, float]:
    """Perform chi-square test for success rates.

    Returns:
        Tuple of (chi-square statistic, p-value)
    """
    if total1 == 0 or total2 == 0:
        return 0.0, 1.0

    # Expected frequencies
    total = total1 + total2
    total_successes = successes1 + successes2
    total_failures = total - total_successes

    e11 = total1 * total_successes / total  # expected successes in group 1
    e12 = total1 * total_failures / total   # expected failures in group 1
    e21 = total2 * total_successes / total  # expected successes in group 2
    e22 = total2 * total_failures / total   # expected failures in group 2

    # Observed frequencies
    o11 = successes1
    o12 = total1 - successes1
    o21 = successes2
    o22 = total2 - successes2

    # Chi-square statistic
    chi2 = 0
    for o, e in [(o11, e11), (o12, e12), (o21, e21), (o22, e22)]:
        if e > 0:
            chi2 += (o - e) ** 2 / e

    # Approximate p-value (1 degree of freedom)
    # Using chi-square CDF approximation
    p_value = 1 - _chi2_cdf(chi2, 1)

    return chi2, p_value


def _chi2_cdf(x: float, df: int) -> float:
    """Approximation of chi-square CDF."""
    if x <= 0:
        return 0.0
    # Wilson-Hilferty approximation
    if df > 0:
        z = ((x / df) ** (1/3) - (1 - 2/(9*df))) / math.sqrt(2/(9*df))
        return _normal_cdf(z)
    return 0.0


def calculate_confidence_interval(
    sample: List[float],
    confidence: float = 0.95,
) -> Tuple[float, float]:
    """Calculate confidence interval for sample mean.

    Returns:
        Tuple of (lower bound, upper bound)
    """
    if len(sample) < 2:
        if sample:
            return sample[0], sample[0]
        return 0.0, 0.0

    n = len(sample)
    mean = statistics.mean(sample)
    stderr = statistics.stdev(sample) / math.sqrt(n)

    # Z-score for confidence level
    z_scores = {0.90: 1.645, 0.95: 1.96, 0.99: 2.576}
    z = z_scores.get(confidence, 1.96)

    margin = z * stderr
    return mean - margin, mean + margin


# =============================================================================
# A/B TEST MANAGER
# =============================================================================

class ABTestManager:
    """Manager for A/B test experiments."""

    def __init__(
        self,
        storage_path: Optional[str] = None,
        auto_save: bool = True,
    ):
        """Initialize A/B test manager.

        Args:
            storage_path: Directory for experiment data
            auto_save: Automatically save experiments on changes
        """
        self.storage_path = Path(storage_path) if storage_path else None
        self.auto_save = auto_save

        self._experiments: Dict[str, Experiment] = {}
        self._lock = threading.RLock()

        if self.storage_path:
            self.storage_path.mkdir(parents=True, exist_ok=True)
            self._load_experiments()

    def register_experiment(self, experiment: Experiment) -> None:
        """Register a new experiment."""
        with self._lock:
            if experiment.name in self._experiments:
                raise ValueError(f"Experiment already exists: {experiment.name}")

            self._experiments[experiment.name] = experiment
            logger.info(f"Registered experiment: {experiment.name}")

            if self.auto_save:
                self._save_experiment(experiment)

    def start_experiment(self, name: str) -> None:
        """Start an experiment."""
        with self._lock:
            experiment = self._get_experiment(name)
            experiment.status = ExperimentStatus.RUNNING
            experiment.started_at = datetime.now()

            logger.info(f"Started experiment: {name}")

            if self.auto_save:
                self._save_experiment(experiment)

    def pause_experiment(self, name: str) -> None:
        """Pause an experiment."""
        with self._lock:
            experiment = self._get_experiment(name)
            experiment.status = ExperimentStatus.PAUSED

            if self.auto_save:
                self._save_experiment(experiment)

    def complete_experiment(self, name: str) -> ExperimentResults:
        """Complete an experiment and determine winner."""
        with self._lock:
            experiment = self._get_experiment(name)
            experiment.status = ExperimentStatus.COMPLETED
            experiment.ended_at = datetime.now()

            results = self._analyze_experiment(experiment)

            experiment.winner = results.winner
            experiment.significance_achieved = results.significance_achieved

            logger.info(f"Completed experiment: {name}, winner: {results.winner}")

            if self.auto_save:
                self._save_experiment(experiment)
                self._save_results(results)

            return results

    def get_variant(self, experiment_name: str, user_id: str) -> Optional[Variant]:
        """Get the variant for a user in an experiment.

        Args:
            experiment_name: Name of the experiment
            user_id: User identifier for consistent assignment

        Returns:
            Variant or None if experiment not running
        """
        with self._lock:
            experiment = self._experiments.get(experiment_name)
            if not experiment or experiment.status != ExperimentStatus.RUNNING:
                return None

            return experiment.get_variant(user_id)

    def get_config(self, experiment_name: str, user_id: str) -> Optional[Dict[str, Any]]:
        """Get configuration for a user in an experiment.

        Convenience method that returns the variant's config dict.
        """
        variant = self.get_variant(experiment_name, user_id)
        return variant.config if variant else None

    def record_outcome(
        self,
        experiment_name: str,
        user_id: str,
        latency_ms: Optional[float] = None,
        quality_score: Optional[float] = None,
        cost: Optional[float] = None,
        success: bool = True,
    ) -> None:
        """Record an outcome for a user's variant.

        Args:
            experiment_name: Name of the experiment
            user_id: User identifier
            latency_ms: Request latency in milliseconds
            quality_score: Quality metric (e.g., 1-5 rating)
            cost: Cost in credits or dollars
            success: Whether the request succeeded
        """
        with self._lock:
            experiment = self._experiments.get(experiment_name)
            if not experiment or experiment.status != ExperimentStatus.RUNNING:
                return

            variant = experiment.get_variant(user_id)
            variant.record_outcome(
                latency_ms=latency_ms,
                quality_score=quality_score,
                cost=cost,
                success=success,
            )

            # Check if experiment is complete
            if experiment.is_complete():
                self.complete_experiment(experiment_name)

    def get_experiment_status(self, name: str) -> Dict[str, Any]:
        """Get current status of an experiment."""
        with self._lock:
            experiment = self._get_experiment(name)
            return experiment.to_dict()

    def list_experiments(
        self,
        status: Optional[ExperimentStatus] = None,
    ) -> List[Dict[str, Any]]:
        """List all experiments, optionally filtered by status."""
        with self._lock:
            experiments = list(self._experiments.values())
            if status:
                experiments = [e for e in experiments if e.status == status]

            return [e.to_dict() for e in experiments]

    def _get_experiment(self, name: str) -> Experiment:
        """Get experiment by name or raise error."""
        experiment = self._experiments.get(name)
        if not experiment:
            raise ValueError(f"Experiment not found: {name}")
        return experiment

    def _analyze_experiment(self, experiment: Experiment) -> ExperimentResults:
        """Analyze experiment results and determine winner."""
        variants_data = [v.to_dict() for v in experiment.variants]

        analysis = {
            "by_latency": {},
            "by_quality": {},
            "by_cost": {},
            "by_success_rate": {},
            "statistical_tests": {},
        }

        # Sort variants by each metric
        sorted_by_latency = sorted(
            experiment.variants,
            key=lambda v: v.avg_latency_ms if v.latencies else float('inf')
        )
        sorted_by_quality = sorted(
            experiment.variants,
            key=lambda v: -v.avg_quality_score if v.quality_scores else float('-inf')
        )
        sorted_by_cost = sorted(
            experiment.variants,
            key=lambda v: v.avg_cost if v.costs else float('inf')
        )
        sorted_by_success = sorted(
            experiment.variants,
            key=lambda v: -v.success_rate
        )

        analysis["by_latency"] = {
            "ranking": [v.name for v in sorted_by_latency],
            "best": sorted_by_latency[0].name if sorted_by_latency else None,
        }
        analysis["by_quality"] = {
            "ranking": [v.name for v in sorted_by_quality],
            "best": sorted_by_quality[0].name if sorted_by_quality else None,
        }
        analysis["by_cost"] = {
            "ranking": [v.name for v in sorted_by_cost],
            "best": sorted_by_cost[0].name if sorted_by_cost else None,
        }
        analysis["by_success_rate"] = {
            "ranking": [v.name for v in sorted_by_success],
            "best": sorted_by_success[0].name if sorted_by_success else None,
        }

        # Statistical tests between first two variants (if they exist)
        p_value = None
        significance_achieved = False
        confidence_interval = None

        if len(experiment.variants) >= 2:
            v1, v2 = experiment.variants[0], experiment.variants[1]

            # T-test on latency
            if v1.latencies and v2.latencies:
                t_stat, p_lat = calculate_t_test(v1.latencies, v2.latencies)
                analysis["statistical_tests"]["latency_t_test"] = {
                    "t_statistic": t_stat,
                    "p_value": p_lat,
                    "significant": p_lat < (1 - experiment.confidence_level),
                }
                p_value = p_lat

            # Chi-square on success rate
            chi2, p_success = calculate_chi_square(
                v1.conversions, v1.impressions,
                v2.conversions, v2.impressions,
            )
            analysis["statistical_tests"]["success_chi_square"] = {
                "chi_square": chi2,
                "p_value": p_success,
                "significant": p_success < (1 - experiment.confidence_level),
            }

            # Confidence interval for latency difference
            if v1.latencies and v2.latencies:
                diff = [a - b for a, b in zip(v1.latencies[:len(v2.latencies)],
                                              v2.latencies[:len(v1.latencies)])]
                if diff:
                    confidence_interval = calculate_confidence_interval(
                        diff, experiment.confidence_level
                    )
                    analysis["statistical_tests"]["latency_diff_ci"] = {
                        "lower": confidence_interval[0],
                        "upper": confidence_interval[1],
                        "significant": not (confidence_interval[0] <= 0 <= confidence_interval[1]),
                    }

            # Check significance
            if p_value and p_value < (1 - experiment.confidence_level):
                significance_achieved = True

        # Determine winner based on criteria
        winner = None
        if experiment.winner_criteria == WinnerCriteria.LOWEST_LATENCY:
            winner = analysis["by_latency"].get("best")
        elif experiment.winner_criteria == WinnerCriteria.HIGHEST_QUALITY:
            winner = analysis["by_quality"].get("best")
        elif experiment.winner_criteria == WinnerCriteria.LOWEST_COST:
            winner = analysis["by_cost"].get("best")
        elif experiment.winner_criteria == WinnerCriteria.BEST_COMPOSITE:
            # Composite score: normalize and combine metrics
            scores = {}
            for v in experiment.variants:
                lat_score = 1 / (1 + v.avg_latency_ms / 100)  # Lower is better
                qual_score = v.avg_quality_score / 5.0 if v.quality_scores else 0.5
                cost_score = 1 / (1 + v.avg_cost) if v.costs else 0.5
                success_score = v.success_rate / 100

                # Weighted composite (adjust weights as needed)
                scores[v.name] = (
                    0.3 * lat_score +
                    0.3 * qual_score +
                    0.2 * cost_score +
                    0.2 * success_score
                )

            winner = max(scores, key=scores.get) if scores else None
            analysis["composite_scores"] = scores

        return ExperimentResults(
            experiment_name=experiment.name,
            variants=variants_data,
            winner=winner,
            significance_achieved=significance_achieved,
            p_value=p_value,
            confidence_interval=confidence_interval,
            analysis=analysis,
        )

    def _save_experiment(self, experiment: Experiment) -> None:
        """Save experiment to storage."""
        if not self.storage_path:
            return

        filepath = self.storage_path / f"{experiment.name}.json"
        with open(filepath, "w") as f:
            json.dump(experiment.to_dict(), f, indent=2)

    def _save_results(self, results: ExperimentResults) -> None:
        """Save experiment results to storage."""
        if not self.storage_path:
            return

        filepath = self.storage_path / f"{results.experiment_name}_results.json"
        with open(filepath, "w") as f:
            json.dump(results.to_dict(), f, indent=2)

    def _load_experiments(self) -> None:
        """Load experiments from storage."""
        if not self.storage_path:
            return

        for filepath in self.storage_path.glob("*.json"):
            if filepath.name.endswith("_results.json"):
                continue

            try:
                with open(filepath, "r") as f:
                    data = json.load(f)

                # Reconstruct experiment
                variants = [
                    Variant(
                        name=v["name"],
                        config=v["config"],
                        weight=v.get("weight", 1.0),
                        description=v.get("description"),
                    )
                    for v in data["variants"]
                ]

                experiment = Experiment(
                    name=data["name"],
                    variants=variants,
                    description=data.get("description"),
                    status=ExperimentStatus(data.get("status", "draft")),
                    winner_criteria=WinnerCriteria(
                        data.get("winner_criteria", "best_composite")
                    ),
                )

                if data.get("created_at"):
                    experiment.created_at = datetime.fromisoformat(data["created_at"])
                if data.get("started_at"):
                    experiment.started_at = datetime.fromisoformat(data["started_at"])
                if data.get("ended_at"):
                    experiment.ended_at = datetime.fromisoformat(data["ended_at"])

                experiment.winner = data.get("winner")
                experiment.significance_achieved = data.get("significance_achieved", False)

                self._experiments[experiment.name] = experiment

            except Exception as e:
                logger.error(f"Failed to load experiment from {filepath}: {e}")


# =============================================================================
# PREDEFINED EXPERIMENTS
# =============================================================================

def create_model_comparison_experiment(
    name: str = "tts_model_comparison",
) -> Experiment:
    """Create experiment comparing TTS models."""
    return Experiment(
        name=name,
        description="Compare ElevenLabs v3 vs Flash for latency and quality",
        variants=[
            Variant(
                name="eleven_v3",
                config={"model": "eleven_v3", "optimize_streaming_latency": 0},
                description="High quality, higher latency",
            ),
            Variant(
                name="flash_v2_5",
                config={"model": "eleven_flash_v2_5", "optimize_streaming_latency": 3},
                description="Lower quality, lower latency",
            ),
        ],
        winner_criteria=WinnerCriteria.BEST_COMPOSITE,
        min_sample_size=50,
    )


def create_stability_experiment(
    name: str = "voice_stability",
) -> Experiment:
    """Create experiment testing voice stability settings."""
    return Experiment(
        name=name,
        description="Test voice stability parameter impact on quality",
        variants=[
            Variant(
                name="stability_low",
                config={"stability": 0.3},
                description="More expressive, less consistent",
            ),
            Variant(
                name="stability_medium",
                config={"stability": 0.5},
                description="Balanced",
            ),
            Variant(
                name="stability_high",
                config={"stability": 0.75},
                description="More consistent, less expressive",
            ),
        ],
        winner_criteria=WinnerCriteria.HIGHEST_QUALITY,
        min_sample_size=30,
    )


def create_caching_experiment(
    name: str = "cache_strategy",
) -> Experiment:
    """Create experiment testing caching strategies."""
    return Experiment(
        name=name,
        description="Compare caching strategies for latency reduction",
        variants=[
            Variant(
                name="no_cache",
                config={"cache_enabled": False},
                description="No caching",
            ),
            Variant(
                name="phrase_cache",
                config={"cache_enabled": True, "cache_type": "phrase"},
                description="Cache common phrases",
            ),
            Variant(
                name="semantic_cache",
                config={"cache_enabled": True, "cache_type": "semantic"},
                description="Cache semantically similar content",
            ),
        ],
        winner_criteria=WinnerCriteria.LOWEST_LATENCY,
        min_sample_size=100,
    )


# =============================================================================
# INTEGRATION HELPER
# =============================================================================

class ABTestVoiceConfig:
    """Helper for integrating A/B tests with voice configuration."""

    def __init__(
        self,
        manager: ABTestManager,
        base_config: Dict[str, Any],
    ):
        """Initialize helper.

        Args:
            manager: ABTestManager instance
            base_config: Base voice configuration
        """
        self.manager = manager
        self.base_config = base_config

    def get_config(
        self,
        user_id: str,
        experiment_names: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Get voice configuration with A/B test overrides.

        Args:
            user_id: User identifier for consistent assignment
            experiment_names: Experiments to check (all running if not specified)

        Returns:
            Configuration dict with experiment overrides applied
        """
        config = self.base_config.copy()

        if experiment_names is None:
            running = self.manager.list_experiments(ExperimentStatus.RUNNING)
            experiment_names = [e["name"] for e in running]

        for exp_name in experiment_names:
            variant_config = self.manager.get_config(exp_name, user_id)
            if variant_config:
                config.update(variant_config)

        return config

    def record_request(
        self,
        user_id: str,
        latency_ms: float,
        quality_score: Optional[float] = None,
        cost: Optional[float] = None,
        success: bool = True,
        experiment_names: Optional[List[str]] = None,
    ) -> None:
        """Record request outcome for all active experiments.

        Args:
            user_id: User identifier
            latency_ms: Request latency
            quality_score: Optional quality metric
            cost: Optional cost metric
            success: Whether request succeeded
            experiment_names: Experiments to record to
        """
        if experiment_names is None:
            running = self.manager.list_experiments(ExperimentStatus.RUNNING)
            experiment_names = [e["name"] for e in running]

        for exp_name in experiment_names:
            self.manager.record_outcome(
                experiment_name=exp_name,
                user_id=user_id,
                latency_ms=latency_ms,
                quality_score=quality_score,
                cost=cost,
                success=success,
            )
