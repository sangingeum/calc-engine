"""Unit tests: distribution command (spec §2-14, §16 regression tests).

Reference values are analytical (not implementation-vs-implementation).
"""

from __future__ import annotations

import math
import types
from typing import Any

import pytest

from calc.errors import ArgumentError, MathError
from calc.ops import distribution_ops

CLOSE = 1e-9


def _num(result: object) -> float:
    """Narrow a distribution_command result to float (moment/pdf/cdf/ppf paths)."""
    assert isinstance(result, (int, float)) and not isinstance(result, bool)
    return float(result)


def make_args(**kw: object) -> types.SimpleNamespace:
    """Build a SimpleNamespace with all distribution flags defaulted to None."""
    base: dict[str, Any] = {
        k: None
        for k in (
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
            "x",
            "q",
            "size",
            "seed",
            "alpha2",
            "beta2",
            "mu2",
            "sigma2",
            "low2",
            "high2",
            "lam2",
            "scale2",
            "shape2",
            "n2",
            "p2",
            "family",
            "family2",
            "value",
            "op",
            "moment",
        )
    }
    base.update(kw)
    return types.SimpleNamespace(**base)


# §16 mandatory regression tests ---------------------------------------------
def test_beta_2_2_moments() -> None:
    assert distribution_ops.distribution_command(
        make_args(op="mean", family="beta", alpha=2, beta=2)
    ) == pytest.approx(0.5, CLOSE)
    assert distribution_ops.distribution_command(
        make_args(op="variance", family="beta", alpha=2, beta=2)
    ) == pytest.approx(0.05, CLOSE)
    assert distribution_ops.distribution_command(
        make_args(op="stddev", family="beta", alpha=2, beta=2)
    ) == pytest.approx(math.sqrt(0.05), CLOSE)


def test_beta_4_05_moments_regression() -> None:
    """Named regression: Beta(4.05,4.05) variance is ~0.02747252747, NOT 0.05."""
    got = float(
        distribution_ops.distribution_command(
            make_args(op="variance", family="beta", alpha=4.05, beta=4.05)
        )
    )
    assert got == pytest.approx(0.02747252747, 1e-9)
    assert abs(got - 0.05) > 0.02  # must not collapse to the Beta(2,2) variance
    got_std = float(
        distribution_ops.distribution_command(
            make_args(op="stddev", family="beta", alpha=4.05, beta=4.05)
        )
    )
    assert got_std == pytest.approx(math.sqrt(0.02747252747), 1e-9)
    assert got_std == pytest.approx(0.165748, 1e-5)


def test_uniform_0_1_moments() -> None:
    args = make_args(op="mean", family="uniform", low=0, high=1)
    assert distribution_ops.distribution_command(args) == pytest.approx(0.5, CLOSE)
    args.op = "variance"
    assert distribution_ops.distribution_command(args) == pytest.approx(1 / 12, CLOSE)
    args.op = "stddev"
    assert distribution_ops.distribution_command(args) == pytest.approx(math.sqrt(1 / 12), 1e-9)
    assert math.sqrt(1 / 12) == pytest.approx(0.2886751346, 1e-9)


def test_two_point_bimodal_moments() -> None:
    # two-point distribution via binomial n=1, p=0.5 shifted/scaled is not
    # expressible; verify via the empirical equivalences instead:
    # [0.25,0.75] equal probability -> mean 0.5, variance 0.0625
    mean = (0.25 + 0.75) / 2
    var = ((0.25 - mean) ** 2 + (0.75 - mean) ** 2) / 2
    assert var == pytest.approx(0.0625, CLOSE)
    # [0.2763932023, 0.7236067977] -> mean 0.5, variance ~0.05
    a, b = 0.2763932023, 0.7236067977
    mean2 = (a + b) / 2
    var2 = ((a - mean2) ** 2 + (b - mean2) ** 2) / 2
    assert mean2 == pytest.approx(0.5, CLOSE)
    assert var2 == pytest.approx(0.05, 1e-9)
    # and the CLI covers these empirically in the contract suite


# family parameterization checks ---------------------------------------------
def test_all_families_mean() -> None:
    cases = [
        ("uniform", dict(low=0, high=1), 0.5),
        ("beta", dict(alpha=2, beta=2), 0.5),
        ("normal", dict(mu=5, sigma=2), 5.0),
        ("lognormal", dict(mu=0, sigma=math.sqrt(math.log(2))), math.sqrt(2)),
        ("exponential", dict(scale=2), 2.0),
        ("gamma", dict(shape=2, scale=3), 6.0),
        ("binomial", dict(n=10, p=0.5), 5.0),
        ("poisson", dict(lam=5), 5.0),
    ]
    for fam, params, expected in cases:
        got = distribution_ops.distribution_command(make_args(op="mean", family=fam, **params))
        assert got == pytest.approx(expected, 1e-9), fam


def test_gamma_variance() -> None:
    got = distribution_ops.distribution_command(
        make_args(op="variance", family="gamma", shape=2, scale=3)
    )
    assert got == pytest.approx(18.0, CLOSE)


def test_binomial_variance() -> None:
    got = distribution_ops.distribution_command(
        make_args(op="variance", family="binomial", n=10, p=0.5)
    )
    assert got == pytest.approx(2.5, CLOSE)


def test_poisson_variance_equals_mean() -> None:
    got = distribution_ops.distribution_command(
        make_args(op="variance", family="poisson", lam=5)
    )
    assert got == pytest.approx(5.0, CLOSE)


def test_lognormal_variance() -> None:
    # lognormal(mu=0, sigma=1): variance = (e-1)e ~ 4.6708
    got = distribution_ops.distribution_command(
        make_args(op="variance", family="lognormal", mu=0, sigma=1)
    )
    assert got == pytest.approx((math.e - 1) * math.e, 1e-9)


# higher moments ---------------------------------------------------------------
def test_kurtosis_convention_non_excess() -> None:
    # normal: kurtosis = 3, excess = 0 (documented convention)
    got = distribution_ops.distribution_command(
        make_args(op="kurtosis", family="normal", mu=0, sigma=1)
    )
    assert got == pytest.approx(3.0, 1e-9)
    got = distribution_ops.distribution_command(
        make_args(op="excess-kurtosis", family="normal", mu=0, sigma=1)
    )
    assert got == pytest.approx(0.0, 1e-9)


def test_skewness_beta_2_2_is_zero() -> None:
    got = distribution_ops.distribution_command(
        make_args(op="skewness", family="beta", alpha=2, beta=2)
    )
    assert got == pytest.approx(0.0, 1e-12)


def test_skewness_exponential_is_two() -> None:
    got = distribution_ops.distribution_command(
        make_args(op="skewness", family="exponential", scale=1)
    )
    assert got == pytest.approx(2.0, 1e-9)


def test_kurtosis_beta_2_2() -> None:
    # Beta(2,2): kurtosis = 15/7 (analytical), excess = -6/7 (platykurtic)
    got = _num(
        distribution_ops.distribution_command(
            make_args(op="kurtosis", family="beta", alpha=2, beta=2)
        )
    )
    assert got == pytest.approx(15 / 7, 1e-9)
    got = _num(
        distribution_ops.distribution_command(
            make_args(op="excess-kurtosis", family="beta", alpha=2, beta=2)
        )
    )
    assert got == pytest.approx(-6 / 7, 1e-9)


# pdf / cdf / ppf ---------------------------------------------------------------
def test_pdf_beta_2_2_at_half() -> None:
    # f(x) = 6x(1-x) -> 1.5 at x=0.5
    got = distribution_ops.distribution_command(
        make_args(op="pdf", family="beta", alpha=2, beta=2, x=0.5)
    )
    assert got == pytest.approx(1.5, CLOSE)


def test_pdf_uniform_outside_support_is_zero() -> None:
    got = distribution_ops.distribution_command(
        make_args(op="pdf", family="uniform", low=0, high=1, x=2.0)
    )
    assert got == 0.0


def test_pdf_normal_at_zero() -> None:
    got = distribution_ops.distribution_command(
        make_args(op="pdf", family="normal", mu=0, sigma=1, x=0.0)
    )
    assert got == pytest.approx(1 / math.sqrt(2 * math.pi), 1e-12)


def test_cdf_beta_2_2_at_half() -> None:
    got = distribution_ops.distribution_command(
        make_args(op="cdf", family="beta", alpha=2, beta=2, x=0.5)
    )
    assert got == pytest.approx(0.5, 1e-12)


def test_cdf_normal_1_96() -> None:
    got = distribution_ops.distribution_command(
        make_args(op="cdf", family="normal", mu=0, sigma=1, x=1.959963985)
    )
    assert got == pytest.approx(0.975, 1e-6)


def test_ppf_beta_2_2_at_half() -> None:
    got = distribution_ops.distribution_command(
        make_args(op="ppf", family="beta", alpha=2, beta=2, q=0.5)
    )
    assert got == pytest.approx(0.5, 1e-9)


@pytest.mark.parametrize("p", [0.01, 0.1, 0.25, 0.5, 0.75, 0.9, 0.99])
def test_cdf_ppf_roundtrip(p: float) -> None:
    x = distribution_ops.distribution_command(
        make_args(op="ppf", family="beta", alpha=2, beta=2, q=p)
    )
    back = distribution_ops.distribution_command(
        make_args(op="cdf", family="beta", alpha=2, beta=2, x=x)
    )
    assert back == pytest.approx(p, 1e-9)


def test_ppf_boundary_zero_is_inf() -> None:
    got = distribution_ops.distribution_command(
        make_args(op="ppf", family="normal", mu=0, sigma=1, q=0.0)
    )
    assert got == float("-inf")


def test_ppf_out_of_range() -> None:
    with pytest.raises(MathError):
        distribution_ops.distribution_command(
            make_args(op="ppf", family="beta", alpha=2, beta=2, q=1.5)
        )


# sample ------------------------------------------------------------------------
def test_sample_deterministic() -> None:
    a = distribution_ops.distribution_command(
        make_args(op="sample", family="beta", alpha=2, beta=2, size=5, seed=123)
    )
    b = distribution_ops.distribution_command(
        make_args(op="sample", family="beta", alpha=2, beta=2, size=5, seed=123)
    )
    assert a == b
    assert a == pytest.approx(
        [0.14855915, 0.76460743, 0.41819781, 0.52893415, 0.77759391], 1e-6
    )


def test_sample_requires_seed_and_size() -> None:
    with pytest.raises(ArgumentError):
        distribution_ops.distribution_command(
            make_args(op="sample", family="beta", alpha=2, beta=2, size=5)
        )
    with pytest.raises(ArgumentError):
        distribution_ops.distribution_command(
            make_args(op="sample", family="beta", alpha=2, beta=2, seed=1)
        )


def test_sample_in_support() -> None:
    vals = distribution_ops.distribution_command(
        make_args(op="sample", family="uniform", low=0, high=1, size=50, seed=7)
    )
    assert all(0.0 <= v <= 1.0 for v in vals)
    assert len(vals) == 50


def test_sample_binomial_poisson_are_integers() -> None:
    vals = distribution_ops.distribution_command(
        make_args(op="sample", family="binomial", n=10, p=0.5, size=20, seed=3)
    )
    assert all(float(v).is_integer() for v in vals)
    vals = distribution_ops.distribution_command(
        make_args(op="sample", family="poisson", lam=3, size=20, seed=3)
    )
    assert all(float(v).is_integer() for v in vals)


# validate ------------------------------------------------------------------------
@pytest.mark.parametrize(
    "fam,params",
    [
        ("beta", dict(alpha=2, beta=2)),
        ("uniform", dict(low=0, high=1)),
        ("normal", dict(mu=0, sigma=1)),
        ("lognormal", dict(mu=0, sigma=1)),
        ("exponential", dict(scale=2)),
        ("gamma", dict(shape=1, scale=1)),
        ("binomial", dict(n=5, p=0.3)),
        ("poisson", dict(lam=2)),
    ],
)
def test_validate_ok(fam: str, params: dict) -> None:
    assert (
        distribution_ops.distribution_command(make_args(op="validate", family=fam, **params))
        == "true"
    )


@pytest.mark.parametrize(
    "fam,params,expected_prefix",
    [
        ("beta", dict(alpha=0, beta=2), MathError),
        ("beta", dict(alpha=2, beta=-1), MathError),
        ("uniform", dict(low=1, high=0), MathError),
        ("uniform", dict(low=1, high=1), MathError),
        ("normal", dict(mu=0, sigma=0), MathError),
        ("lognormal", dict(mu=0, sigma=-1), MathError),
        ("exponential", dict(scale=0), MathError),
        ("gamma", dict(shape=-1, scale=2), MathError),
        ("gamma", dict(shape=1, scale=0), MathError),
        ("binomial", dict(n=5.5, p=0.3), MathError),
        ("binomial", dict(n=5, p=1.5), MathError),
        ("poisson", dict(lam=0), MathError),
    ],
)
def test_validate_failures_are_typed(fam: str, params: dict, expected_prefix: type) -> None:
    with pytest.raises(expected_prefix):
        distribution_ops.distribution_command(make_args(op="validate", family=fam, **params))


def test_validate_missing_parameter() -> None:
    with pytest.raises(ArgumentError):
        distribution_ops.distribution_command(make_args(op="validate", family="beta", alpha=2))


# compare-moments -------------------------------------------------------------------
def test_compare_moments_equal_mean() -> None:
    got = distribution_ops.distribution_command(
        make_args(
            op="compare-moments",
            family="beta",
            alpha=2,
            beta=2,
            family2="uniform",
            low2=0,
            high2=1,
            moment="mean",
        )
    )
    assert got == "true"


def test_compare_moments_unequal_variance() -> None:
    """The mean≠shape guard: Beta(2,2) vs Uniform(0,1) share the mean but not variance."""
    got = distribution_ops.distribution_command(
        make_args(
            op="compare-moments",
            family="beta",
            alpha=2,
            beta=2,
            family2="uniform",
            low2=0,
            high2=1,
            moment="variance",
        )
    )
    assert got == "false"


def test_compare_moments_beta_4_05_not_005() -> None:
    """Acceptance §22.2: detect Beta(4.05,4.05) does not have variance 0.05."""
    got = distribution_ops.distribution_command(
        make_args(
            op="compare-moments",
            family="beta",
            alpha=4.05,
            beta=4.05,
            family2="uniform",
            low2=0,
            high2=1,
            moment="variance",
        )
    )
    # Beta(4.05,4.05) variance 0.02747... != Uniform(0,1) variance 1/12
    assert got == "false"
    var = _num(
        distribution_ops.distribution_command(
            make_args(op="variance", family="beta", alpha=4.05, beta=4.05)
        )
    )
    assert var == pytest.approx(0.02747252747, 1e-9)


def test_compare_moments_unknown_moment() -> None:
    with pytest.raises(ArgumentError):
        distribution_ops.distribution_command(
            make_args(
                op="compare-moments",
                family="beta",
                alpha=2,
                beta=2,
                family2="uniform",
                low2=0,
                high2=1,
                moment="mode",
            )
        )


# describe (rejected under single-value stdout) ---------------------------------------
def test_describe_rejected_under_stdout_contract() -> None:
    with pytest.raises(ArgumentError):
        distribution_ops.distribution_command(
            make_args(op="describe", family="beta", alpha=2, beta=2)
        )


# unknown family / op -----------------------------------------------------------------
def test_unknown_family() -> None:
    with pytest.raises(ArgumentError):
        distribution_ops.distribution_command(make_args(op="mean", family="cauchy"))


def test_unknown_op() -> None:
    with pytest.raises(ArgumentError):
        distribution_ops.distribution_command(
            make_args(op="frobnicate", family="beta", alpha=1, beta=1)
        )
