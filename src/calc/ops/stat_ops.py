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

from scipy import stats as sps

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


_UNIVARIATE_OPS = frozenset(_OPS) | {
    "quantile",
    "rank",
    "skewness",
    "kurtosis",
    "excess-kurtosis",
}
_PAIRWISE_OPS = frozenset({"covariance", "pearson", "spearman", "regression"})


def stat_command(
    op: str,
    datasets: list[str],
    ddof: int = 0,
    field: str | None = None,
    alternative: str | None = None,
    alpha: float | None = None,
    n: float | None = None,
) -> int | float | list[float]:
    """Dispatch the ``stat`` subcommand across univariate and pairwise ops."""
    if op == "critical-r":
        if field is not None:
            raise ArgumentError(
                "stat critical-r does not take --field (prints the critical |r|)"
            )
        return critical_r(
            n=n,
            alpha=alpha,
            alternative=alternative or "two-sided",
        )
    if op in ("skewness", "kurtosis", "excess-kurtosis"):
        if len(datasets) != 1:
            raise ArgumentError(f"stat {op} takes exactly 1 dataset argument")
        return shape_moment(op, datasets[0])
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
            return _correlation_with_significance(
                "pearson", datasets[0], datasets[1], field, alternative or "two-sided"
            )
        if op == "spearman":
            return _correlation_with_significance(
                "spearman", datasets[0], datasets[1], field, alternative or "two-sided"
            )
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


# ---------------------------------------------------------------------------
# R4: correlation significance (pinned: t-approximation, df = n-2)
# ---------------------------------------------------------------------------

_CORRELATION_FIELDS = ("coefficient", "p", "t", "df", "n")
_ALTERNATIVES = ("two-sided", "greater", "less")


def _correlation_with_significance(
    kind: str, x: str, y: str, field: str | None, alternative: str
) -> float:
    """pearson/spearman with optional --field selector (R4).

    Default field is ``coefficient`` (byte-identical legacy output, INV-4).
    p-value method (pinned, documented): t = r*sqrt((n-2)/(1-r^2)), df = n-2;
    for Spearman this is computed on average ranks (scipy.stats.spearmanr
    convention). |r| = 1 => p = 0; n < 3 => MathError.
    """
    field = field or "coefficient"
    if field not in _CORRELATION_FIELDS:
        raise ArgumentError(
            f"unknown {kind} field: {field} "
            f"(expected one of {', '.join(_CORRELATION_FIELDS)})"
        )
    if alternative not in _ALTERNATIVES:
        raise ArgumentError(
            f"unknown alternative: {alternative!r} (expected one of {', '.join(_ALTERNATIVES)})"
        )
    if kind == "pearson":
        r = pearson(x, y)
        xs, _ = _parse_pair(x, y)
    else:
        r = spearman(x, y)
        xs, _ = _parse_pair(x, y)
    n = len(xs)
    if field == "n":
        return float(n)
    if field == "df":
        return float(n - 2)
    if field == "coefficient":
        return r
    if n < 3:
        raise MathError("at least 3 observations are required for significance")
    if abs(r) >= 1.0:
        t_stat = math.copysign(math.inf, r)
        p = 0.0
    else:
        t_stat = r * math.sqrt((n - 2) / (1 - r * r))
        p = _t_pvalue(t_stat, n - 2, alternative)
    if field == "t":
        return t_stat if not math.isinf(t_stat) else math.copysign(1e308, t_stat)
    return p


def _t_pvalue(t_stat: float, dof: int, alternative: str) -> float:
    """Two-sided/greater/less p from the t distribution with ``dof`` df."""
    dist = sps.t(df=dof)
    if alternative == "greater":
        return float(dist.sf(t_stat))
    if alternative == "less":
        return float(dist.cdf(t_stat))
    return float(2.0 * dist.sf(abs(t_stat)))


def critical_r(
    *, n: float | None, alpha: float | None, alternative: str = "two-sided"
) -> float:
    """Smallest |r| significant at level ``alpha`` (R4).

    r_crit = t_crit / sqrt(n - 2 + t_crit^2); two-sided uses the 1-alpha/2
    quantile of t with df = n-2; one-sided uses 1-alpha.
    """
    if n is None:
        raise ArgumentError("stat critical-r requires --n")
    if alpha is None:
        raise ArgumentError("stat critical-r requires --alpha")
    if alternative not in _ALTERNATIVES:
        raise ArgumentError(
            f"unknown alternative: {alternative!r} (expected one of {', '.join(_ALTERNATIVES)})"
        )
    if n != math.floor(n) or n < 3:
        raise MathError("critical-r requires an integer n >= 3")
    if not 0 < alpha < 1:
        raise MathError("alpha must be in (0, 1)")
    dof = int(n) - 2
    quantile = 1 - alpha / 2 if alternative == "two-sided" else 1 - alpha
    t_crit = float(sps.t.ppf(quantile, dof))
    return t_crit / math.sqrt(dof + t_crit * t_crit)


# ---------------------------------------------------------------------------
# R12: dataset shape moments (population/biased, kurtosis NON-excess)
# ---------------------------------------------------------------------------


def shape_moment(op: str, dataset: str) -> float:
    """Population (biased) standardized shape moments of a dataset.

    Same conventions as ``distribution``: skewness = third standardized
    moment; kurtosis = fourth standardized moment, NON-excess (normal = 3);
    excess-kurtosis = kurtosis - 3. These are population moments of the
    sample, not unbiased sample estimators.
    """
    data = _parse_series(dataset)
    n = len(data)
    if n < 2:
        raise MathError("at least 2 observations are required")
    mean = statistics.fmean(data)
    m2 = sum((v - mean) ** 2 for v in data) / n
    if m2 == 0:
        raise MathError("zero variance: shape moments undefined")
    if op == "skewness":
        m3 = sum((v - mean) ** 3 for v in data) / n
        return m3 / m2**1.5
    m4 = sum((v - mean) ** 4 for v in data) / n
    kurtosis = m4 / m2**2
    return kurtosis - 3.0 if op == "excess-kurtosis" else kurtosis


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
