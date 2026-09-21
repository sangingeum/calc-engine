"""Unit tests for Phase 3 (R9 fit, R10 sym, R11 --exact, R12 shape moments)."""

from __future__ import annotations

import types

import numpy as np
import pytest
from scipy import stats as sps

from calc.errors import ArgumentError, MathError, SyntaxError_
from calc.ops import distribution_ops, eval_ops, stat_ops, sym_ops


def _dist_args(op: str, family: str, **params: object) -> types.SimpleNamespace:
    base: dict[str, object] = dict(
        op=op,
        family=family,
        value=None,
        family2=None,
        alpha=None,
        beta=None,
        mu=None,
        sigma=None,
        low=None,
        high=None,
        lam=None,
        scale=None,
        shape=None,
        n=None,
        p=None,
        df=None,
        a=None,
        b=None,
        mean=None,
        variance=None,
        fit_param=None,
    )
    base.update(params)
    return types.SimpleNamespace(**base)


# ---------------------------------------------------------------------------
# R9: distribution fit
# ---------------------------------------------------------------------------


def test_r9_beta_fit_pinned():
    alpha = distribution_ops.distribution_command(
        _dist_args("fit", "beta", mean=0.5, variance=0.05, fit_param="alpha")
    )
    beta = distribution_ops.distribution_command(
        _dist_args("fit", "beta", mean=0.5, variance=0.05, fit_param="beta")
    )
    assert alpha == pytest.approx(2.0, rel=1e-9)
    assert beta == pytest.approx(2.0, rel=1e-9)
    alpha = distribution_ops.distribution_command(
        _dist_args("fit", "beta", mean=0.5, variance=0.0625, fit_param="alpha")
    )
    assert alpha == pytest.approx(1.5, rel=1e-9)


def test_r9_beta_infeasible():
    with pytest.raises(MathError):
        distribution_ops.distribution_command(
            _dist_args("fit", "beta", mean=0.5, variance=0.25, fit_param="alpha")
        )


def test_r9_unsupported_family():
    with pytest.raises(ArgumentError):
        distribution_ops.distribution_command(
            _dist_args("fit", "kumaraswamy", mean=0.5, variance=0.05, fit_param="alpha")
        )


@pytest.mark.parametrize(
    "family,params",
    [
        ("beta", dict(alpha=2.0, beta=2.0)),
        ("gamma", dict(shape=3.0, scale=0.7)),
        ("normal", dict(mu=-1.0, sigma=2.0)),
        ("lognormal", dict(mu=0.2, sigma=0.5)),
        ("uniform", dict(low=-1.0, high=2.0)),
    ],
)
def test_r9_roundtrip_matches_true_moments(family: str, params: dict):
    dists = {
        "beta": sps.beta(2, 2),
        "gamma": sps.gamma(3, scale=0.7),
        "normal": sps.norm(-1, 2),
        "lognormal": sps.lognorm(0.5, scale=2.718281828**0.2),
        "uniform": sps.uniform(-1, 3),
    }
    d = dists[family]
    m = float(d.mean())
    v = float(d.var())
    fitted = {}
    for field in distribution_ops._FIT_FIELDS[family]:
        fitted[field] = distribution_ops.distribution_command(
            _dist_args("fit", family, mean=m, variance=v, fit_param=field)
        )
    refit = distribution_ops._scipy_dist(
        distribution_ops._Params(family, {**params, **fitted})
    )
    assert float(refit.mean()) == pytest.approx(m, rel=1e-9), family
    assert float(refit.var()) == pytest.approx(v, rel=1e-9), family


# ---------------------------------------------------------------------------
# R10: sym
# ---------------------------------------------------------------------------


def _sym_args(op: str, exprs: list[str], vars_: list[str]) -> types.SimpleNamespace:
    return types.SimpleNamespace(op=op, exprs=exprs, var=vars_)


def test_r10_equiv_true_pinned():
    assert (
        sym_ops.sym_command(
            _sym_args(
                "equiv", ["-0.35*(1+0.5*(0.5-A)*2)", "-0.525+0.35*A"], ["A"]
            )
        )
        == "true"
    )


def test_r10_equiv_false_pinned():
    assert (
        sym_ops.sym_command(_sym_args("equiv", ["(x+1)**2", "x**2+1"], ["x"]))
        == "false"
    )


def test_r10_expand_pinned():
    assert (
        sym_ops.sym_command(_sym_args("expand", ["(x+1)**2"], ["x"]))
        == "x**2 + 2*x + 1"
    )


def test_r10_undeclared_symbol():
    with pytest.raises(SyntaxError_):
        sym_ops.sym_command(_sym_args("equiv", ["y", "x"], ["x"]))


def test_r10_simplify():
    assert (
        sym_ops.sym_command(_sym_args("simplify", ["(x**2-1)/(x-1)"], ["x"]))
        == "x + 1"
    )


def test_r10_rational_decimals_hold_exactly():
    # 0.1 + 0.2 == 0.3 exactly with rational parsing
    assert (
        sym_ops.sym_command(_sym_args("equiv", ["0.1+0.2", "0.3"], [])) == "true"
    )


def test_r10_wrong_expr_counts():
    with pytest.raises(ArgumentError):
        sym_ops.sym_command(_sym_args("equiv", ["x"], ["x"]))
    with pytest.raises(ArgumentError):
        sym_ops.sym_command(_sym_args("expand", ["x", "y"], ["x", "y"]))


# ---------------------------------------------------------------------------
# R11: eval --exact
# ---------------------------------------------------------------------------


def test_r11_exact_pinned():
    assert str(eval_ops.evaluate("-0.35*(1+0.5*(0.5-0.25)*2)", exact=True)) == "-7/16"
    assert str(eval_ops.evaluate("1/3+1/6", exact=True)) == "1/2"
    assert str(eval_ops.evaluate("2**-2", exact=True)) == "1/4"
    assert str(eval_ops.evaluate("1/2", exact=True)) == "1/2"
    assert str(eval_ops.evaluate("4/2", exact=True)) == "2"
    assert str(eval_ops.evaluate("2**2", exact=True)) == "4"


def test_r11_exact_inexact_representable():
    with pytest.raises(MathError):
        eval_ops.evaluate("sqrt(2)", exact=True)
    with pytest.raises(MathError):
        eval_ops.evaluate("2**0.5", exact=True)
    with pytest.raises(MathError):
        eval_ops.evaluate("1/0", exact=True)


def test_r11_exact_rejects_functions_and_names():
    with pytest.raises(MathError):
        eval_ops.evaluate("sqrt(2)", exact=True)
    with pytest.raises(MathError):
        eval_ops.evaluate("pi", exact=True)


# ---------------------------------------------------------------------------
# R12: stat shape moments
# ---------------------------------------------------------------------------


def test_r12_pinned_dataset():
    ds = "[1,2,3,4,10]"
    assert stat_ops.stat_command("skewness", [ds]) == pytest.approx(1.138420, abs=5e-7)
    assert stat_ops.stat_command("kurtosis", [ds]) == pytest.approx(2.788000, abs=5e-7)
    assert stat_ops.stat_command("excess-kurtosis", [ds]) == pytest.approx(
        -0.212000, abs=5e-7
    )


def test_r12_population_moment_convention():
    # Direct check: population (biased) moments, non-excess kurtosis.
    data = [1.0, 2.0, 3.0, 4.0, 10.0]
    mean = sum(data) / len(data)
    m2 = sum((v - mean) ** 2 for v in data) / len(data)
    m4 = sum((v - mean) ** 4 for v in data) / len(data)
    assert stat_ops.stat_command("kurtosis", ["[1,2,3,4,10]"]) == pytest.approx(
        m4 / m2**2, rel=1e-12
    )


def test_r12_large_normal_sample_property():
    rng = np.random.default_rng(99)
    sample = rng.normal(size=20000)
    ds = "[" + ",".join(repr(float(v)) for v in sample) + "]"
    skew = stat_ops.stat_command("skewness", [ds])
    kurt = stat_ops.stat_command("kurtosis", [ds])
    assert abs(skew) < 0.05
    assert abs(kurt - 3) < 0.1


def test_r12_edge_cases():
    with pytest.raises(MathError):
        stat_ops.stat_command("skewness", ["[5]"])
    with pytest.raises(MathError):
        stat_ops.stat_command("kurtosis", ["[3,3,3]"])  # zero variance
