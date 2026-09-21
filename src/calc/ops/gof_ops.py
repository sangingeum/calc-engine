"""Goodness-of-fit tests (R7): ``gof ks``, ``gof chi2``, ``gof chi2-bins``.

Conventions (pinned by reference tests against scipy):
- ks: one-sample two-sided Kolmogorov-Smirnov, same result as
  ``scipy.stats.kstest(data, cdf, method='auto')``. Continuous families only.
- chi2: OBSERVED vs EXPECTED count arrays; sums must match; df = k - 1 - ddof.
- chi2-bins: K equiprobable bins via the family's PPF at i/K; expected count
  n/K per bin; data outside support => MathError; df = K - 1 - ddof;
  requires n/K >= 5.

INV-1 forbids multi-value output, so ``--field`` is REQUIRED for every op.
"""

from __future__ import annotations

import json
import types

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


def _gof_ks(args: types.SimpleNamespace) -> float:
    if len(args.operands) != 2:
        raise ArgumentError("gof ks takes exactly a dataset and a family")
    field = _check_field(args, ("statistic", "p"))
    data = _parse_data(args.operands[0])
    dist = _family_cdf(args.operands[1], args)
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
