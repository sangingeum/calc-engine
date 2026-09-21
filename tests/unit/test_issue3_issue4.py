"""Regression tests for GitHub issues 3 and 4 (fix round 3, 2026-09-21)."""

from __future__ import annotations

import types

import numpy as np
import pytest
from scipy import stats as sps

from calc.ops import distribution_ops, gof_ops

_KS_DATA = [0.05, 0.2, 0.35, 0.5, 0.65, 0.8, 0.95]


def _ks_args(family: str, field: str, **params: object) -> types.SimpleNamespace:
    base: dict[str, object] = dict(
        op="ks",
        operands=[f"[{','.join(str(v) for v in _KS_DATA)}]", family],
        field=field,
        gof_ddof=0,
        bins=None,
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
    )
    base.update(params)
    return types.SimpleNamespace(**base)


# ---------------------------------------------------------------------------
# Issue 3: kumaraswamy methods must be numpy-vector-safe (kstest passes arrays)
# ---------------------------------------------------------------------------


def test_kumaraswamy_methods_accept_numpy_arrays():
    k = distribution_ops._Kumaraswamy(2, 3)
    arr = np.array([0.05, 0.5, 0.95])
    # These raised "ValueError: ambiguous truth value" before the fix.
    assert len(k.cdf(arr)) == 3
    assert len(k.pdf(arr)) == 3
    assert len(k.sf(arr)) == 3
    # Scalar inputs still return scalars (render path).
    assert isinstance(k.cdf(0.3), float)
    assert k.cdf(0.3) == pytest.approx(1 - (1 - 0.3**2) ** 3, abs=1e-12)


def test_kumaraswamy_cdf_support_boundaries():
    k = distribution_ops._Kumaraswamy(2, 3)
    arr = np.array([-1.0, 0.0, 0.5, 1.0, 2.0])
    vals = k.cdf(arr)
    assert vals[0] == 0.0 and vals[1] == 0.0
    assert vals[3] == 1.0 and vals[4] == 1.0
    assert 0 < vals[2] < 1


def test_kumaraswamy_sf_matches_one_minus_cdf_array():
    k = distribution_ops._Kumaraswamy(2, 3)
    arr = np.array([0.1, 0.4, 0.7])
    assert np.allclose(k.sf(arr), 1.0 - k.cdf(arr), atol=1e-12)


def test_issue3_gof_ks_kumaraswamy_pinned():
    """gof ks on kumaraswamy must equal the closed-form KS computation.

    Pre-fix this raised MathError: internal computation failure (scalar-only
    cdf receiving an array). Pinned against both scipy.kstest on our own cdf
    and the manual closed-form statistic with F(x) = 1 - (1 - x^a)^b.
    """
    a, b = 2, 3
    data = np.array(_KS_DATA)
    F = np.sort(1 - (1 - data**a) ** b)
    n = len(data)
    d_manual = max(
        np.max(np.arange(1, n + 1) / n - F),
        np.max(F - np.arange(0, n) / n),
    )
    assert gof_ops.gof_command(_ks_args("kumaraswamy", "statistic", a=a, b=b)) == (
        pytest.approx(float(d_manual), rel=1e-9)
    )
    # scipy-equivalent pinned literals (kstest on the same closed-form cdf)
    assert gof_ops.gof_command(
        _ks_args("kumaraswamy", "statistic", a=a, b=b)
    ) == pytest.approx(0.23905828571428578, abs=1e-9)
    assert gof_ops.gof_command(
        _ks_args("kumaraswamy", "p", a=a, b=b)
    ) == pytest.approx(0.7390716150969578, abs=1e-9)
    # --a 2 --b 2 variant from the issue's repro command
    assert gof_ops.gof_command(_ks_args("kumaraswamy", "p", a=2, b=2)) == (
        pytest.approx(0.8697, abs=5e-5)
    )


def test_issue3_gof_ks_t_chi2_still_work():
    """scipy families are already vectorized; keep them pinned post-fix."""
    expected_t = float(
        sps.kstest(np.array(_KS_DATA), sps.t(df=10).cdf, method="auto").pvalue
    )
    assert gof_ops.gof_command(_ks_args("t", "p", df=10)) == pytest.approx(
        expected_t, rel=1e-9
    )
    expected_c = float(
        sps.kstest(np.array(_KS_DATA), sps.chi2(df=4).cdf, method="auto").pvalue
    )
    assert gof_ops.gof_command(_ks_args("chi2", "p", df=4)) == pytest.approx(
        expected_c, rel=1e-9
    )


# ---------------------------------------------------------------------------
# Issue 4: seed-20260921 beta(2,2) n=200 stream — calc matches scipy exactly
# ---------------------------------------------------------------------------


def test_issue4_seed_20260921_stream_matches_scipy():
    """anna reported p=0.0087 vs ~0.667; the exact stream gives 0.6599 (scipy).

    Rounded-to-4dp input (what a JSON paste carries) gives 0.6590 — calc's
    value. The reported 0.0087 is not reproducible on this stream in any
    rounding; it is consistent with an invocation mismatch (wrong family/
    wrong cdf), per the butler's 6-stream table in the issue body.
    """
    import subprocess

    rng = np.random.default_rng(20260921)
    data = rng.beta(2, 2, 200)
    ref = sps.kstest(data, sps.beta(2, 2).cdf, method="auto")

    out = subprocess.run(
        [
            "uv", "run", "calc", "distribution", "sample", "beta",
            "--alpha", "2", "--beta", "2", "--size", "200", "--seed", "20260921",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert out.returncode == 0, out.stderr
    sample = np.array(__import__("json").loads(out.stdout))
    # sample output renders at --precision 4 by default: same stream, rounded
    assert np.allclose(sample, data, atol=5e-5)

    arr = "[" + ",".join(repr(float(v)) for v in sample) + "]"
    p_proc = subprocess.run(
        ["uv", "run", "calc", "gof", "ks", arr, "beta",
         "--alpha", "2", "--beta", "2", "--field", "p"],
        capture_output=True, text=True, check=False,
    )
    assert p_proc.returncode == 0, p_proc.stderr
    calc_p = float(p_proc.stdout)
    assert calc_p == pytest.approx(float(ref.pvalue), abs=1e-3)  # 0.6590 vs 0.659855

    # The rounded-4dp stream reproduces calc's 0.6590 exactly (input rounding).
    rounded_ref = sps.kstest(np.round(data, 4), sps.beta(2, 2).cdf, method="auto")
    assert calc_p == pytest.approx(round(rounded_ref.pvalue, 4), abs=1e-9)
    assert calc_p == pytest.approx(0.6590, abs=5e-5)
