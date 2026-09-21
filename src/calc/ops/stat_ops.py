"""Statistics over a JSON dataset via the stdlib ``statistics`` module.

Pairwise extensions (spec §1): covariance, pearson, spearman, regression,
quantile, rank. Conventions (documented in SKILL.md):
- covariance: population by default, ``--ddof 1`` for the sample estimator;
- spearman/rank: average ranks for ties;
- quantile: NumPy-compatible 'linear' interpolation, h = (n-1)*q;
- regression: OLS; ``stderr`` is an explicit alias of ``slope_stderr``,
  ``residual_variance`` divides SSR by (n-2).
"""

from __future__ import annotations

import json
import math
import statistics

from calc.errors import ArgumentError, MathError, SyntaxError_

_OPS = (
    "mean",
    "median",
    "mode",
    "stdev",
    "variance",
    "pvariance",
    "sum",
    "min",
    "max",
    "count",
    "geometric_mean",
    "harmonic_mean",
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
        raise ArgumentError(f"unknown stat operation: {op} (expected one of {', '.join(_OPS)})")
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


_UNIVARIATE_OPS = frozenset(_OPS) | {"quantile", "rank"}
_PAIRWISE_OPS = frozenset({"covariance", "pearson", "spearman", "regression"})


def stat_command(
    op: str, datasets: list[str], ddof: int = 0, field: str | None = None
) -> int | float | list[float]:
    """Dispatch the ``stat`` subcommand across univariate and pairwise ops."""
    if op in _UNIVARIATE_OPS:
        if op == "quantile":
            if len(datasets) != 2:
                raise ArgumentError("stat quantile takes exactly a dataset and a q value")
            try:
                q = float(datasets[1])
            except ValueError:
                raise ArgumentError("stat quantile q must be a number in [0, 1]") from None
            return quantile(datasets[0], q)
        if len(datasets) != 1:
            expected = 2 if op in _PAIRWISE_OPS else 1
            raise ArgumentError(f"stat {op} takes exactly {expected} dataset argument(s)")
        if op == "rank":
            return rank(datasets[0])
        return stat(op, datasets[0])
    if op in _PAIRWISE_OPS:
        if len(datasets) != 2:
            raise ArgumentError(f"stat {op} takes exactly 2 dataset arguments (X and Y)")
        if op == "covariance":
            return covariance(datasets[0], datasets[1], ddof=ddof)
        if op == "pearson":
            return pearson(datasets[0], datasets[1])
        if op == "spearman":
            return spearman(datasets[0], datasets[1])
        # regression
        if field is None:
            raise ArgumentError("stat regression requires --field")
        return regression(datasets[0], datasets[1], field)
    raise ArgumentError(
        f"unknown stat operation: {op} "
        f"(expected one of {', '.join(sorted(_UNIVARIATE_OPS | _PAIRWISE_OPS))})"
    )


# ---------------------------------------------------------------------------
# Pairwise helpers (spec §1)
# ---------------------------------------------------------------------------


def _parse_series(raw: str, name: str = "dataset") -> list[float]:
    """Parse one JSON array of numbers into a float series."""
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SyntaxError_(f"invalid JSON {name}: {exc}") from None
    if not isinstance(data, list):
        raise SyntaxError_(f"{name} must be a JSON array of numbers")
    if any(isinstance(x, bool) or not isinstance(x, (int, float)) for x in data):
        raise SyntaxError_(f"{name} must contain only numbers")
    return [float(x) for x in data]


def _parse_pair(x_raw: str, y_raw: str) -> tuple[list[float], list[float]]:
    x = _parse_series(x_raw, "X dataset")
    y = _parse_series(y_raw, "Y dataset")
    if len(x) != len(y):
        raise ArgumentError(f"X and Y must have equal length (got {len(x)} and {len(y)})")
    if len(x) < 2:
        raise ArgumentError("at least 2 paired observations are required")
    return x, y


def covariance(x: str, y: str, ddof: int = 0) -> float:
    """Population covariance by default; ``ddof=1`` gives the sample estimator."""
    if ddof not in (0, 1):
        raise ArgumentError(f"ddof must be 0 or 1 (got {ddof})")
    xs, ys = _parse_pair(x, y)
    if len(xs) - ddof < 1:
        raise MathError("ddof too large for the number of observations")
    mx = statistics.fmean(xs)
    my = statistics.fmean(ys)
    sxy = sum((a - mx) * (b - my) for a, b in zip(xs, ys, strict=True))
    return sxy / (len(xs) - ddof)


def pearson(x: str, y: str) -> float:
    """Pearson product-moment correlation coefficient."""
    xs, ys = _parse_pair(x, y)
    mx = statistics.fmean(xs)
    my = statistics.fmean(ys)
    sxy = sum((a - mx) * (b - my) for a, b in zip(xs, ys, strict=True))
    sxx = sum((a - mx) ** 2 for a in xs)
    syy = sum((b - my) ** 2 for b in ys)
    if sxx == 0 or syy == 0:
        raise MathError("zero variance: correlation undefined")
    return sxy / math.sqrt(sxx * syy)


def _average_ranks(values: list[float]) -> list[float]:
    """Average ranks (1-based) with deterministic tie handling."""
    order = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        avg_rank = (i + 1 + j + 1) / 2
        for k in range(i, j + 1):
            ranks[order[k]] = avg_rank
        i = j + 1
    return ranks


def rank(raw: str) -> list[float]:
    """Average ranks of a dataset (1-based)."""
    data = _parse_series(raw)
    if len(data) < 1:
        raise MathError("empty dataset")
    return _average_ranks(data)


def spearman(x: str, y: str) -> float:
    """Spearman rank correlation: Pearson on average ranks."""
    xs, ys = _parse_pair(x, y)
    if len(set(xs)) == 1 or len(set(ys)) == 1:
        raise MathError("zero rank variance: correlation undefined")
    return pearson(json.dumps(_average_ranks(xs)), json.dumps(_average_ranks(ys)))


_REGRESSION_FIELDS = (
    "slope",
    "intercept",
    "r2",
    "stderr",
    "slope_stderr",
    "residual_stderr",
    "residual_variance",
)


def regression(x: str, y: str, field: str) -> float:
    """OLS simple linear regression on (X, Y).

    Field conventions (documented): ``stderr`` is an explicit alias of
    ``slope_stderr``; ``residual_stderr`` is sqrt(residual_variance) with
    residual_variance = SSR/(n-2); ``r2`` is the coefficient of determination.
    """
    if field not in _REGRESSION_FIELDS:
        raise ArgumentError(
            f"unknown regression field: {field} "
            f"(expected one of {', '.join(_REGRESSION_FIELDS)})"
        )
    xs, ys = _parse_pair(x, y)
    n = len(xs)
    if n < 3:
        raise ArgumentError("at least 3 paired observations are required for regression")
    mx = statistics.fmean(xs)
    my = statistics.fmean(ys)
    sxx = sum((a - mx) ** 2 for a in xs)
    sxy = sum((a - mx) * (b - my) for a, b in zip(xs, ys, strict=True))
    syy = sum((b - my) ** 2 for b in ys)
    if sxx == 0:
        raise MathError("zero variance in X: slope undefined")
    slope = sxy / sxx
    intercept = my - slope * mx
    if field == "slope":
        return slope
    if field == "intercept":
        return intercept
    sst = syy
    ssr = sum((ys[i] - (intercept + slope * xs[i])) ** 2 for i in range(n))
    if field == "r2":
        if sst == 0:
            raise MathError("zero variance in Y: r2 undefined")
        return 1 - ssr / sst
    dof = n - 2
    if dof < 1:
        raise MathError("at least 3 observations are required for stderr estimates")
    residual_variance = ssr / dof
    if field == "residual_variance":
        return residual_variance
    if field == "residual_stderr":
        return math.sqrt(residual_variance)
    # stderr / slope_stderr
    return math.sqrt(residual_variance / sxx)


def quantile(raw: str, q: float) -> float:
    """NumPy-compatible 'linear' interpolation: h = (n-1)*q."""
    if not 0 <= q <= 1:
        raise ArgumentError(f"q must be in [0, 1] (got {q})")
    data = _parse_series(raw)
    if not data:
        raise MathError("empty dataset")
    s = sorted(data)
    h = (len(s) - 1) * q
    lo = math.floor(h)
    hi = math.ceil(h)
    if lo == hi:
        return s[lo]
    return s[lo] + (h - lo) * (s[hi] - s[lo])
