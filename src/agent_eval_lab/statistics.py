"""Uncertainty for a small, hand-authored dataset.

Two rules follow from the design of this benchmark. The scenario, not the trial,
is the unit of evidence: repeats of one scenario are the same task asked again,
and at temperature 0 they are often the same answer. And the dataset is small
enough that the honest statement is usually "this run cannot tell": the exact
sign test below needs six scenarios to flip in one direction before a difference
clears 5%, which on 27 development scenarios is 22 percentage points.

Nothing here turns a synthetic diagnostic suite into a population estimate.
"""

from __future__ import annotations

import math
import random
from collections.abc import Mapping, Sequence
from dataclasses import dataclass


@dataclass(frozen=True)
class Interval:
    estimate: float
    low: float
    high: float

    def describe(self) -> str:
        return f"{self.estimate:.0%} ({self.low:.0%}–{self.high:.0%})"


def wilson(successes: float, total: int, z: float = 1.96) -> Interval:
    """Wilson score interval; stays inside [0, 1] at small n and near the edges."""
    if total <= 0:
        return Interval(0.0, 0.0, 1.0)
    p = successes / total
    denominator = 1 + z * z / total
    centre = (p + z * z / (2 * total)) / denominator
    margin = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / denominator
    return Interval(p, max(0.0, centre - margin), min(1.0, centre + margin))


def scenario_rates(outcomes: Mapping[str, Sequence[bool]]) -> dict[str, float]:
    return {
        scenario: sum(results) / len(results) for scenario, results in outcomes.items() if results
    }


def pass_rate(outcomes: Mapping[str, Sequence[bool]]) -> Interval:
    """Pass rate whose interval counts scenarios, not trials.

    Exact when every scenario passes all of its repeats or none of them, and
    wider than it needs to be when repeats of a scenario disagree.
    """
    rates = scenario_rates(outcomes)
    if not rates:
        return Interval(0.0, 0.0, 1.0)
    return wilson(sum(rates.values()), len(rates))


def sign_test_exact(improved: int, regressed: int) -> float:
    """Two-sided exact p for paired scenarios that changed direction.

    The scenario-level analogue of McNemar's test: only scenarios that moved
    carry information, and under the null each is equally likely to move either
    way. Returns 1.0 when nothing moved.
    """
    if improved < 0 or regressed < 0:
        raise ValueError("Counts must not be negative")
    discordant = improved + regressed
    if discordant == 0:
        return 1.0
    smaller = min(improved, regressed)
    tail = sum(math.comb(discordant, i) for i in range(smaller + 1)) * 0.5**discordant
    return min(1.0, 2 * tail)


def minimum_detectable_flips(alpha: float = 0.05) -> int:
    """Smallest number of same-direction scenario flips the sign test can call.

    Independent of the dataset size: with k flips all in one direction the exact
    two-sided p is 2 * 0.5**k, so k = 6 is the first that clears 5%.
    """
    flips = 1
    while 2 * 0.5**flips > alpha:
        flips += 1
    return flips


def paired_delta(
    before: Mapping[str, Sequence[bool]],
    after: Mapping[str, Sequence[bool]],
    *,
    iterations: int = 4000,
    seed: int = 20260921,
    confidence: float = 0.95,
) -> Interval:
    """Change in pass rate, resampling scenarios rather than trials.

    Only scenarios present in both runs are compared, and each contributes its
    own before/after difference, so the pairing survives the resampling.
    """
    shared = sorted(set(before) & set(after))
    if not shared:
        return Interval(0.0, 0.0, 0.0)
    left, right = scenario_rates(before), scenario_rates(after)
    deltas = [right[scenario] - left[scenario] for scenario in shared]
    observed = sum(deltas) / len(deltas)
    generator = random.Random(seed)
    samples = sorted(
        sum(deltas[generator.randrange(len(deltas))] for _ in deltas) / len(deltas)
        for _ in range(iterations)
    )
    tail = (1 - confidence) / 2
    low = samples[int(tail * iterations)]
    high = samples[min(iterations - 1, int((1 - tail) * iterations))]
    return Interval(observed, low, high)
