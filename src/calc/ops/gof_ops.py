"""Goodness-of-fit tests (R7): ``gof ks``, ``gof chi2``, ``gof chi2-bins``.

Conventions (pinned by reference tests against scipy):
- ks: one-sample two-sided Kolmogorov-Smirnov, same result as
  ``scipy.stats.kstest(data, cdf, method='auto')``. Continuous families only.
- ks on the step-CDF family ``two-point`` (issue 10): point masses have no
  density, so the pinned continuous convention does not apply. The statistic is
  the exact discrete two-sided supremum (the route the reference bimodal
  preflight uses), and ``--field p`` is an ``ArgumentError`` (no pinned p
  convention for a step CDF; the continuous asymptotic p is conservative under
  ties). Ties / duplicate support points are documented under ``two-point`` in
  SKILL.md.
- chi2: OBSERVED vs EXPECTED count arrays; sums must match; df = k - 1 - ddof.
- chi2-bins: K equiprobable bins via the family's PPF at i/K; expected count
  n/K per bin; data outside support => MathError; df = K - 1 - ddof;
  requires n/K >= 5.

INV-1 forbids multi-value output, so ``--field`` is REQUIRED for every op.
"""

from __future__ import annotations

import json
import types
from typing import Any

import numpy as np
from scipy import stats as sps

from calc.errors import ArgumentError, MathError, SyntaxError_

_KS_FAMILIES = frozenset(
    {
        "uniform",
        "beta",
        "normal",
        "lognormal",
        "exponential",
        "gamma",
        "t",
        "chi2",
        "kumaraswamy",
    }
)

# Step-CDF families (issue 10): point masses rather than a density, so the
# pinned scipy.kstest convention does not apply (see the module docstring).
_STEP_FAMILIES = frozenset({"two-point"})

# Precision-12 hygiene (calc-engine #10, per the #4 resolution): the exact
# step-CDF KS takes the left limit of the theoretical CDF one part in 10^12
# below each support point (the reference preflight's ``p - 1e-12`` rule).
# The offset is the authored rule; support points and weights are used as
# given rather than pre-rounded.
_STEP_LEFT_LIMIT = 1e-12


class _TwoPointStep:
    """Step CDF of a two-point mixture: masses at ``low`` and ``high``.

    ``F(x) = 0`` for ``x < low``; ``weight_low`` for ``low <= x < high``;
    ``1`` for ``x >= high`` (``weight_high = 1 - weight_low``). Vector-safe,
    like the kumaraswamy closed form, so a numpy array round-trips through
    ``cdf``.
    """

    def __init__(
        self, low: float, high: float, weight_low: float, weight_high: float
    ) -> None:
        if not low < high:
            raise MathError("two-point requires low < high")
        if weight_low <= 0 or weight_high <= 0:
            raise MathError("two-point requires positive weights")
        if abs(weight_low + weight_high - 1.0) > 1e-9:
            raise MathError("two-point requires weight-low + weight-high = 1")
        self.low = float(low)
        self.high = float(high)
        self.weight_low = float(weight_low)

    def cdf(self, x: Any) -> Any:
        x = np.asarray(x, dtype=float)
        vals = np.where(
            x < self.low, 0.0, np.where(x < self.high, self.weight_low, 1.0)
        )
        return vals if vals.ndim else float(vals)


def _parse_counts(raw: str, name: str) -> list[float]:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SyntaxError_(f"invalid JSON {name}: {exc}") from None
    if not isinstance(data, list) or not data:
        raise SyntaxError_(f"{name} must be a non-empty JSON array of counts")
    if any(
        isinstance(x, bool) or not isinstance(x, (int, float)) or x < 0 for x in data
    ):
        raise SyntaxError_(f"{name} must contain only non-negative numbers")
    return [float(x) for x in data]


def _parse_data(raw: str) -> list[float]:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SyntaxError_(f"invalid JSON dataset: {exc}") from None
    if not isinstance(data, list) or not data:
        raise SyntaxError_("dataset must be a non-empty JSON array of numbers")
    if any(isinstance(x, bool) or not isinstance(x, (int, float)) for x in data):
        raise SyntaxError_("dataset must contain only numbers")
    return [float(x) for x in data]


def _family_cdf(family: str, args: types.SimpleNamespace):
    """Build the frozen scipy CDF for a continuous family (shared with R6)."""
    from calc.ops import distribution_ops

    if family in _STEP_FAMILIES:
        raise ArgumentError(
            f"{family} is a step CDF (point masses, no PPF); only gof ks "
            "--field statistic supports it"
        )
    if family not in _KS_FAMILIES:
        if family in ("binomial", "poisson"):
            raise ArgumentError(
                f"gof ks supports continuous families only; {family} is discrete"
            )
        raise ArgumentError(f"unknown distribution family: {family}")
    kwargs = {
        key: getattr(args, key)
        for key in (
            "alpha",
            "beta",
            "mu",
            "sigma",
            "low",
            "high",
            "lam",
            "scale",
            "shape",
            "n",
            "p",
            "df",
            "a",
            "b",
        )
    }
    # lam/n/p are never valid for continuous families; drop None entries only.
    params = distribution_ops._Params(family, kwargs)
    return distribution_ops._scipy_dist(params)


def _check_field(args: types.SimpleNamespace, allowed: tuple[str, ...]) -> str:
    field = args.field
    if field not in allowed:
        raise ArgumentError(
            f"unknown gof field: {field} (expected one of {', '.join(allowed)})"
        )
    return field


def gof_command(args: types.SimpleNamespace) -> int | float:
    """Dispatch the ``gof`` subcommand."""
    op = args.op
    if op == "ks":
        return _gof_ks(args)
    if op == "chi2":
        return _gof_chi2(args)
    if op == "chi2-bins":
        return _gof_chi2_bins(args)
    raise ArgumentError(f"unknown gof operation: {op} (expected ks|chi2|chi2-bins)")


def _two_point_dist(args: types.SimpleNamespace) -> _TwoPointStep:
    """Build the step CDF from the authored mass locations and weights."""
    if args.low is None or args.high is None:
        raise ArgumentError("two-point requires --low and --high (the mass locations)")
    if args.weight_low is None or args.weight_high is None:
        raise ArgumentError("two-point requires --weight-low and --weight-high")
    return _TwoPointStep(args.low, args.high, args.weight_low, args.weight_high)


def _step_ks_statistic(data: list[float], dist: _TwoPointStep) -> float:
    """Exact two-sided KS statistic of a sample against a step CDF.

    Ties collapse: equal data values form ONE support point, so duplicate
    values contribute a single (post-jump, pre-jump) pair rather than k
    separate steps. At every distinct value ``p`` the statistic charges the
    post-jump theoretical value against the post-jump empirical CDF and the
    pre-jump (left-limit, ``p - _STEP_LEFT_LIMIT``) theoretical value against
    the pre-jump empirical CDF — the exact discrete supremum, NOT
    ``scipy.stats.kstest`` (whose post-jump/pre-jump pairing is wrong for a
    step CDF).
    """
    ordered = sorted(data)
    n = len(ordered)
    statistic = 0.0
    cumulative = 0
    i = 0
    while i < n:
        j = i
        while j + 1 < n and ordered[j + 1] == ordered[i]:
            j += 1
        count = j - i + 1
        point = ordered[i]
        statistic = max(
            statistic,
            abs(float(dist.cdf(point)) - (cumulative + count) / n),
            abs(float(dist.cdf(point - _STEP_LEFT_LIMIT)) - cumulative / n),
        )
        cumulative += count
        i = j + 1
    return statistic


def _gof_ks(args: types.SimpleNamespace) -> float:
    if len(args.operands) != 2:
        raise ArgumentError("gof ks takes exactly a dataset and a family")
    field = _check_field(args, ("statistic", "p"))
    data = _parse_data(args.operands[0])
    family = args.operands[1]
    if family in _STEP_FAMILIES:
        if field != "statistic":
            raise ArgumentError(
                "two-point is a step CDF: --field p has no pinned convention "
                "(the continuous asymptotic p is conservative under ties); use "
                "--field statistic"
            )
        return _step_ks_statistic(data, _two_point_dist(args))
    dist = _family_cdf(family, args)
    result = sps.kstest(np.asarray(data), dist.cdf, method="auto")
    return float(result.statistic if field == "statistic" else result.pvalue)


def _gof_chi2(args: types.SimpleNamespace) -> float:
    if len(args.operands) != 2:
        raise ArgumentError("gof chi2 takes exactly OBSERVED and EXPECTED")
    field = _check_field(args, ("statistic", "p", "df"))
    observed = _parse_counts(args.operands[0], "OBSERVED")
    expected = _parse_counts(args.operands[1], "EXPECTED")
    if len(observed) != len(expected):
        raise MathError("OBSERVED and EXPECTED must have equal length")
    if abs(sum(observed) - sum(expected)) > 1e-9 * max(1.0, sum(expected)):
        raise MathError("OBSERVED and EXPECTED sums must match")
    if any(e <= 0 for e in expected):
        raise MathError("expected counts must be positive")
    statistic, pvalue = sps.chisquare(
        np.asarray(observed), np.asarray(expected)
    )
    if field == "statistic":
        return float(statistic)
    if field == "p":
        return float(pvalue)
    return len(observed) - 1 - args.gof_ddof  # df: integer by nature (issue 8)


def _gof_chi2_bins(args: types.SimpleNamespace) -> float:
    if len(args.operands) != 2:
        raise ArgumentError("gof chi2-bins takes exactly a dataset and a family")
    field = _check_field(args, ("statistic", "p", "df"))
    if args.bins is None:
        raise ArgumentError("gof chi2-bins requires --bins K")
    k = int(args.bins)
    if k < 2:
        raise MathError("chi2-bins requires at least 2 bins")
    data = _parse_data(args.operands[0])
    dist = _family_cdf(args.operands[1], args)
    n = len(data)
    if n / k < 5:
        raise MathError("expected count per bin < 5")
    # Equiprobable bin edges from the family PPF at i/K.
    edges = [float(dist.ppf(i / k)) for i in range(k + 1)]
    lo, hi = edges[0], edges[-1]
    if any(v < lo or v > hi for v in data):
        raise MathError("data outside the family's support")
    counts, _ = np.histogram(np.asarray(data), bins=edges)
    expected = n / k
    statistic, pvalue = sps.chisquare(
        counts, np.full(k, expected)
    )
    if field == "statistic":
        return float(statistic)
    if field == "p":
        return float(pvalue)
    return k - 1 - args.gof_ddof  # df: integer by nature (issue 8)
