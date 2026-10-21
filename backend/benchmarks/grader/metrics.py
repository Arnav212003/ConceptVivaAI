"""Agreement and consistency metrics (standard library only, so CI needs no numpy)."""
from __future__ import annotations

import math
import random
from statistics import mean, pstdev
from typing import Sequence


def mae(a: Sequence[float], b: Sequence[float]) -> float:
    _check(a, b)
    return mean(abs(x - y) for x, y in zip(a, b))


def rmse(a: Sequence[float], b: Sequence[float]) -> float:
    _check(a, b)
    return math.sqrt(mean((x - y) ** 2 for x, y in zip(a, b)))


def pearson(a: Sequence[float], b: Sequence[float]) -> float | None:
    _check(a, b)
    if len(a) < 2:
        return None
    ma, mb = mean(a), mean(b)
    cov = sum((x - ma) * (y - mb) for x, y in zip(a, b))
    va = math.sqrt(sum((x - ma) ** 2 for x in a))
    vb = math.sqrt(sum((y - mb) ** 2 for y in b))
    if va == 0 or vb == 0:
        return None  # undefined when either side is constant
    return cov / (va * vb)


def average_ranks(values: Sequence[float]) -> list[float]:
    """1-based ranks; ties share the mean of the ranks they span."""
    order = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        shared = (i + j) / 2 + 1
        for k in range(i, j + 1):
            ranks[order[k]] = shared
        i = j + 1
    return ranks


def spearman(a: Sequence[float], b: Sequence[float]) -> float | None:
    _check(a, b)
    return pearson(average_ranks(a), average_ranks(b))


def within(a: Sequence[float], b: Sequence[float], tolerance: float = 1.0) -> float:
    _check(a, b)
    return mean(1.0 if abs(x - y) <= tolerance else 0.0 for x, y in zip(a, b))


def cohen_kappa(a: Sequence[str], b: Sequence[str]) -> float | None:
    _check(a, b)
    labels = sorted(set(a) | set(b))
    n = len(a)
    if n == 0:
        return None
    observed = sum(1 for x, y in zip(a, b) if x == y) / n
    expected = sum((list(a).count(label) / n) * (list(b).count(label) / n) for label in labels)
    if expected == 1:
        return None
    return (observed - expected) / (1 - expected)


def bootstrap_ci(a: Sequence[float], b: Sequence[float], metric=mae, iterations: int = 2000,
                 alpha: float = 0.05, seed: int = 7) -> tuple[float, float] | None:
    """Percentile bootstrap confidence interval for a paired metric."""
    _check(a, b)
    n = len(a)
    if n < 5:
        return None
    rng = random.Random(seed)
    samples = []
    for _ in range(iterations):
        idx = [rng.randrange(n) for _ in range(n)]
        value = metric([a[i] for i in idx], [b[i] for i in idx])
        if value is not None:
            samples.append(value)
    samples.sort()
    low = samples[int((alpha / 2) * len(samples))]
    high = samples[min(len(samples) - 1, int((1 - alpha / 2) * len(samples)))]
    return low, high


def repeatability(runs_per_item: Sequence[Sequence[float]]) -> dict:
    """Score consistency across repeated gradings of the same item."""
    usable = [runs for runs in runs_per_item if len(runs) >= 2]
    if not usable:
        return {"items": 0}
    stds = [pstdev(runs) for runs in usable]
    ranges = [max(runs) - min(runs) for runs in usable]
    return {
        "items": len(usable),
        "mean_std": mean(stds),
        "max_std": max(stds),
        "mean_range": mean(ranges),
        "identical_rate": mean(1.0 if r == 0 else 0.0 for r in ranges),
        "within_1_rate": mean(1.0 if r <= 1.0 else 0.0 for r in ranges),
    }


def _check(a, b):
    if len(a) != len(b):
        raise ValueError("sequences must have the same length")
