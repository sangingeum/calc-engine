"""GitHub issue 10: the ``two-point`` step-CDF family for ``gof ks``.

The bimodal arm of the 2026-09-21 distribution-family sweep needed a KS
preflight against a step CDF; ``calc gof`` could not express a two-point
mixture, so the KS was computed by a per-repo script. The family added here
ships that exact discrete statistic through the standard house tool.

Pinned conventions (see SKILL.md, ``gof`` section):
- the statistic is the exact two-sided discrete supremum, NOT
  ``scipy.stats.kstest`` — scipy charges the post-jump theoretical value
  against the pre-jump empirical value, which reports the maximum possible D
  (0.5) on data that matches a step CDF perfectly;
- equal data values (ties) collapse to ONE support point;
- the left limit of the theoretical CDF is probed at ``p - 1e-12``
  (precision-12 hygiene rule).
"""

from __future__ import annotations

import re
import types

import numpy as np
import pytest
from scipy import stats as sps

from calc.errors import ArgumentError, MathError
from calc.ops import gof_ops

LOW = 0.25
HIGH = 0.75


def _args(**overrides: object) -> types.SimpleNamespace:
    base: dict[str, object] = dict(
        op="ks",
        operands=["[]", "two-point"],
        field="statistic",
        gof_ddof=0,
        bins=None,
        alpha=None,
        beta=None,
        mu=None,
        sigma=None,
        low=LOW,
        high=HIGH,
        lam=None,
        scale=None,
        shape=None,
        n=None,
        p=None,
        df=None,
        a=None,
        b=None,
        weight_low=0.5,
        weight_high=0.5,
    )
    base.update(overrides)
    return types.SimpleNamespace(**base)


def _ks(data: list[float], **overrides: object) -> float:
    args = _args(**overrides)
    args.operands = ["[" + ",".join(repr(float(v)) for v in data) + "]", "two-point"]
    return gof_ops.gof_command(args)


def _step_cdf(x: object, weight_low: float = 0.5) -> np.ndarray:
    """Vector-safe step CDF (a stand-in for the family's frozen CDF)."""
    arr = np.asarray(x, dtype=float)
    return np.where(arr < LOW, 0.0, np.where(arr < HIGH, weight_low, 1.0))


def _grid_supremum(data: list[float], weight_low: float = 0.5) -> float:
    """Independent formulation: dense-grid supremum of |F(x) - F_n(x)|."""
    ordered = sorted(data)
    n = len(ordered)

    def empirical(x: float) -> float:
        return sum(1 for v in ordered if v <= x) / n

    candidates = set()
    for v in ordered:
        candidates.update((v - 1e-12, v, v + 1e-12))
    candidates.update((LOW - 1e-12, LOW, LOW + 1e-12, HIGH - 1e-12, HIGH, HIGH + 1e-12))
    points = sorted(candidates)
    for a, b in zip(points, points[1:], strict=False):
        candidates.add((a + b) / 2)
    return max(abs(_step_cdf(x, weight_low) - empirical(x)) for x in candidates)


# ---------------------------------------------------------------------------
# The statistic: exact discrete supremum, not the scipy continuous convention
# ---------------------------------------------------------------------------


def test_two_point_perfect_match_reports_exact_zero() -> None:
    """A perfectly matching sample must give D = 0, not scipy's degenerate 0.5."""
    data = [LOW] * 120 + [HIGH] * 120
    assert _ks(data) == 0.0
    # Document the degeneracy the issue flagged: the pinned continuous
    # convention (post-jump vs pre-jump) reports the maximum possible D here.
    scipy_d = float(sps.kstest(np.asarray(data), _step_cdf, method="auto").statistic)
    assert scipy_d == pytest.approx(0.5)


def test_two_point_perfect_weighted_match_reports_exact_zero() -> None:
    """A perfect 25/75 sample against a 25/75 mixture also gives D = 0."""
    assert _ks([LOW] * 60 + [HIGH] * 180, weight_low=0.25, weight_high=0.75) == 0.0


def test_two_point_pinned_statistics() -> None:
    """Pinned exact values (fractions, not approximations)."""
    assert _ks([LOW] * 140 + [HIGH] * 100) == pytest.approx(1.0 / 12.0, abs=1e-12)
    assert _ks([LOW] * 119 + [0.5] + [HIGH] * 120) == pytest.approx(
        1.0 / 240.0, abs=1e-12
    )
    # 50/50 sample against a 25/75 mixture: the whole mass gap.
    assert _ks([LOW] * 120 + [HIGH] * 120, weight_low=0.25, weight_high=0.75) == (
        pytest.approx(0.25, abs=1e-12)
    )


def test_two_point_matches_independent_grid_supremum() -> None:
    """Cross-check the two-pair formula against a dense-grid supremum."""
    rng = np.random.default_rng(20260921)
    for _ in range(5):
        data = [
            float(LOW) if u < 0.6 else float(HIGH)
            for u in rng.random(200)
        ]
        assert _ks(data) == pytest.approx(_grid_supremum(data), abs=1e-9)


# ---------------------------------------------------------------------------
# Ties / duplicate support points
# ---------------------------------------------------------------------------


def test_two_point_ties_collapse_to_one_support_point() -> None:
    """Duplicate values are one support point, so D is scale-invariant."""
    assert _ks([LOW, HIGH]) == 0.0
    assert _ks([LOW] * 120 + [HIGH] * 120) == 0.0
    # Repeats of a non-support value likewise collapse: the D depends only on
    # the distinct values and their counts.
    single = _ks([LOW, 0.5, HIGH])
    repeated = _ks([LOW] * 10 + [0.5] * 10 + [HIGH] * 10)
    assert single == pytest.approx(repeated, abs=1e-12)


def test_two_point_left_limit_rule_uses_one_part_in_10_to_the_12() -> None:
    """The left limit is probed at ``p - 1e-12`` (precision-12 hygiene rule)."""
    assert gof_ops._STEP_LEFT_LIMIT == 1e-12
    # A sample landing exactly on a support point only scores 0 because the
    # pre-jump theoretical value is taken just below that point.
    data = [LOW] * 120 + [HIGH] * 120
    assert _ks(data) == 0.0


# ---------------------------------------------------------------------------
# Parameter surface
# ---------------------------------------------------------------------------


def test_two_point_cdf_is_vector_safe_and_stepped() -> None:
    dist = gof_ops._TwoPointStep(LOW, HIGH, 0.5, 0.5)
    arr = dist.cdf(np.array([0.0, LOW, 0.5, HIGH, 1.0]))
    assert list(arr) == [0.0, 0.5, 0.5, 1.0, 1.0]
    assert isinstance(dist.cdf(LOW), float)


def test_two_point_cdf_reflects_authored_weight() -> None:
    dist = gof_ops._TwoPointStep(LOW, HIGH, 0.25, 0.75)
    assert dist.cdf(0.5) == pytest.approx(0.25)


@pytest.mark.parametrize(
    "kwargs, message",
    [
        ({"low": 0.75, "high": 0.25}, "two-point requires low < high"),
        ({"low": 0.5, "high": 0.5}, "two-point requires low < high"),
        ({"weight_low": -0.5, "weight_high": 1.5}, "two-point requires positive weights"),
        ({"weight_low": 0.0, "weight_high": 1.0}, "two-point requires positive weights"),
        (
            {"weight_low": 0.4, "weight_high": 0.4},
            "two-point requires weight-low + weight-high = 1",
        ),
    ],
)
def test_two_point_rejects_invalid_support_or_weights(
    kwargs: dict[str, object], message: str
) -> None:
    with pytest.raises(MathError, match=re.escape(message)):
        _ks([LOW, HIGH], **kwargs)


@pytest.mark.parametrize(
    "kwargs, message",
    [
        ({"low": None}, "two-point requires --low and --high"),
        ({"high": None}, "two-point requires --low and --high"),
        ({"weight_low": None}, "two-point requires --weight-low and --weight-high"),
        ({"weight_high": None}, "two-point requires --weight-low and --weight-high"),
    ],
)
def test_two_point_requires_authored_locations_and_weights(
    kwargs: dict[str, object], message: str
) -> None:
    with pytest.raises(ArgumentError, match=message):
        _ks([LOW, HIGH], **kwargs)


def test_two_point_p_field_has_no_pinned_convention() -> None:
    args = _args(field="p")
    args.operands = ["[0.25,0.75]", "two-point"]
    with pytest.raises(ArgumentError, match="step CDF"):
        gof_ops.gof_command(args)


def test_two_point_rejected_by_chi2_bins() -> None:
    args = _args()
    args.op = "chi2-bins"
    args.bins = 2
    args.operands = ["[0.25,0.75]", "two-point"]
    with pytest.raises(ArgumentError, match="step CDF"):
        gof_ops.gof_command(args)


def test_continuous_families_unchanged() -> None:
    """The new branch must not disturb the pinned scipy-backed families."""
    data = [0.05, 0.2, 0.35, 0.5, 0.65, 0.8, 0.95]
    cases = (
        ("uniform", {"low": 0, "high": 1}, sps.uniform(loc=0, scale=1).cdf),
        ("normal", {"mu": 0, "sigma": 1}, sps.norm().cdf),
    )
    for family, params, cdf in cases:
        args = _args(**params)
        args.operands = ["[" + ",".join(repr(v) for v in data) + "]", family]
        got = gof_ops.gof_command(args)
        expected = float(sps.kstest(np.asarray(data), cdf, method="auto").statistic)
        assert got == pytest.approx(expected, rel=1e-12)
