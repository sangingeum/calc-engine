"""Statistics over a JSON dataset via the stdlib ``statistics`` module."""

from __future__ import annotations

import json
import statistics

from calc.errors import ArgumentError, MathError, SyntaxError_

_OPS = (
    "mean", "median", "mode", "stdev", "variance", "pvariance",
    "sum", "min", "max", "count", "geometric_mean", "harmonic_mean",
)


def _parse_dataset(dataset: str) -> list[float]:
    try:
        data = json.loads(dataset)
    except json.JSONDecodeError as exc:
        raise SyntaxError_(f"invalid JSON dataset: {exc}") from None
    if not isinstance(data, list):
        raise SyntaxError_("dataset must be a JSON array of numbers")
    if any(isinstance(x, bool) or not isinstance(x, (int, float)) for x in data):
        raise SyntaxError_("dataset must contain only numbers")
    return data  # preserve ints so integer-valued ops render bare


def stat(op: str, dataset: str) -> int | float:
    """Apply a statistics operation to a JSON array of numbers."""
    data = _parse_dataset(dataset)
    if op not in _OPS:
        raise ArgumentError(
            f"unknown stat operation: {op} (expected one of {', '.join(_OPS)})"
        )
    if op == "count":
        return len(data)
    if not data:
        raise MathError("empty dataset")
    try:
        if op == "mode":
            # Ratified: first mode only on multimodal data (single-value stdout).
            return statistics.multimode(data)[0]
        if op == "mean":
            return statistics.mean(data)
        if op == "median":
            return statistics.median(data)
        if op == "stdev":
            return statistics.stdev(data)
        if op == "variance":
            return statistics.variance(data)
        if op == "pvariance":
            return statistics.pvariance(data)
        if op == "geometric_mean":
            return statistics.geometric_mean(data)
        if op == "harmonic_mean":
            return statistics.harmonic_mean(data)
    except statistics.StatisticsError as exc:
        raise MathError(str(exc)) from None
    if op == "sum":
        return sum(data)
    if op == "min":
        return min(data)
    return max(data)  # op == "max"
