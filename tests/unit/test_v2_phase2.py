"""Unit tests for Phase 2 (R4-R8) with pinned Appendix A reference values."""

from __future__ import annotations

import math

import numpy as np
import pytest
from scipy import stats as sps

from calc.errors import ArgumentError, MathError
from calc.ops import eval_ops, gof_ops, stat_ops

CLOSE = 1e-9

X8 = "[1,2,3,4,5,6,7,8]"
Y8 = "[2,1,4,3,6,5,8,7]"


# ---------------------------------------------------------------------------
# R4: correlation significance
# ---------------------------------------------------------------------------


def test_r4_spearman_pearson_pinned_values():
    assert stat_ops.stat_command("spearman", [X8, Y8]) == pytest.approx(0.904762, abs=5e-7)
    assert stat_ops.stat_command(
        "spearman", [X8, Y8], field="p"
    ) == pytest.approx(0.002008, abs=5e-7)
    assert stat_ops.stat_command(
        "pearson", [X8, Y8], field="p"
    ) == pytest.approx(0.002008, abs=5e-7)
    assert stat_ops.stat_command("pearson", [X8, Y8], field="df") == 6
    assert stat_ops.stat_command("pearson", [X8, Y8], field="n") == 8


def test_r4_critical_r_pinned():
    assert stat_ops.critical_r(n=240, alpha=0.05) == pytest.approx(0.126666, abs=5e-7)


def test_r4_scipy_crosscheck_random_datasets():
    rng = np.random.default_rng(42)
    for i in range(5):
        n = 20 + i * 7
        x = rng.normal(size=n)
        y = x * 0.4 + rng.normal(size=n) * (0.2 if i % 2 else 1.0)
        if i == 4:
            y = np.round(y, 1)  # ties
        xs = "[" + ",".join(repr(float(v)) for v in x) + "]"
        ys = "[" + ",".join(repr(float(v)) for v in y) + "]"
        expected_p = float(sps.pearsonr(x, y).pvalue)
        assert stat_ops.stat_command("pearson", [xs, ys], field="p") == pytest.approx(
            expected_p, rel=1e-9
        )
        expected_sp = float(sps.spearmanr(x, y).pvalue)
        assert stat_ops.stat_command("spearman", [xs, ys], field="p") == pytest.approx(
            expected_sp, rel=1e-9
        )


def test_r4_one_sided_alternatives():
    p_greater = stat_ops.stat_command(
        "pearson", [X8, Y8], field="p", alternative="greater"
    )
    p_two = stat_ops.stat_command("pearson", [X8, Y8], field="p")
    assert p_greater == pytest.approx(p_two / 2, rel=1e-9)
    assert stat_ops.stat_command(
        "pearson", [X8, Y8], field="p", alternative="less"
    ) == pytest.approx(1 - p_two / 2, rel=1e-9)


def test_r4_perfect_correlation_p_zero():
    xs = "[1,2,3,4]"
    assert stat_ops.stat_command("pearson", [xs, xs], field="p") == 0.0


def test_r4_small_n_matherror():
    with pytest.raises(MathError):
        stat_ops.stat_command("pearson", ["[1,2]", "[2,4]"], field="p")


def test_r4_zero_variance_matherror():
    with pytest.raises(MathError):
        stat_ops.stat_command("pearson", ["[1,1,1]", "[1,2,3]"], field="p")


def test_r4_invalid_field_and_alternative():
    with pytest.raises(ArgumentError):
        stat_ops.stat_command("pearson", [X8, Y8], field="bogus")
    with pytest.raises(MathError):
        stat_ops.critical_r(n=240, alpha=1.5)
    with pytest.raises(ArgumentError):
        stat_ops.critical_r(n=None, alpha=0.05)


# ---------------------------------------------------------------------------
# R5: sf
# ---------------------------------------------------------------------------


def test_r5_sf_normal_pinned():
    import types

    from calc.ops import distribution_ops

    args = types.SimpleNamespace(
        op="sf", family="normal", value=8, family2=None, x=None,
        mu=0, sigma=1, alpha=None, beta=None, low=None, high=None,
        lam=None, scale=None, shape=None, n=None, p=None, df=None, a=None, b=None,
    )
    value = distribution_ops.distribution_command(args)
    assert value == pytest.approx(6.22096e-16, rel=1e-5)


def test_r5_sf_plus_cdf_approx_one_all_families():
    import types

    from calc.ops import distribution_ops

    cases = [
        ("normal", dict(mu=0, sigma=1), 1.5),
        ("uniform", dict(low=0, high=1), 0.3),
        ("beta", dict(alpha=2, beta=2), 0.6),
        ("lognormal", dict(mu=0, sigma=1), 1.2),
        ("exponential", dict(scale=2.0), 1.1),
        ("gamma", dict(shape=2, scale=1), 2.0),
        ("t", dict(df=5), 1.0),
        ("chi2", dict(df=4), 3.0),
        ("kumaraswamy", dict(a=2, b=3), 0.4),
        ("binomial", dict(n=10, p=0.5), 4),
        ("poisson", dict(lam=3.0), 2),
    ]
    for family, params, x in cases:
        base = dict(
            op="sf", family=family, value=x, family2=None, x=None,
            alpha=None, beta=None, low=None, high=None, mu=None, sigma=None,
            lam=None, scale=None, shape=None, n=None, p=None, df=None, a=None, b=None,
        )
        base.update(params)
        sf = distribution_ops.distribution_command(types.SimpleNamespace(**base))
        base["op"] = "cdf"
        cdf = distribution_ops.distribution_command(types.SimpleNamespace(**base))
        assert sf + cdf == pytest.approx(1.0, abs=1e-12), family


# ---------------------------------------------------------------------------
# R6: t / chi2 / kumaraswamy
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "family,params,op,x,expected",
    [
        ("t", dict(df=238), "cdf", 1.5, 0.932530),
        ("t", dict(df=10), "ppf", 0.975, 2.228139),
        ("chi2", dict(df=5), "cdf", 3.0, 0.300014),
        ("kumaraswamy", dict(a=2, b=2), "cdf", 0.3, 0.1719),
        ("kumaraswamy", dict(a=2, b=2), "ppf", 0.5, 0.541196),
    ],
)
def test_r6_pinned_cdf_ppf(family, params, op, x, expected):
    import types

    from calc.ops import distribution_ops

    base = dict(
        op=op, family=family, value=x, family2=None, x=None,
        alpha=None, beta=None, low=None, high=None, mu=None, sigma=None,
        lam=None, scale=None, shape=None, n=None, p=None, df=None, a=None, b=None,
    )
    base.update(params)
    value = distribution_ops.distribution_command(types.SimpleNamespace(**base))
    assert value == pytest.approx(expected, abs=5e-5)


def test_r6_kumaraswamy_moments():
    import types

    from calc.ops import distribution_ops

    base = dict(
        op="mean", family="kumaraswamy", value=None, family2=None,
        alpha=None, beta=None, low=None, high=None, mu=None, sigma=None,
        lam=None, scale=None, shape=None, n=None, p=None, df=None, a=2, b=2,
    )
    mean = distribution_ops.distribution_command(types.SimpleNamespace(**base))
    base["op"] = "variance"
    var = distribution_ops.distribution_command(types.SimpleNamespace(**base))
    assert mean == pytest.approx(0.533333, abs=5e-5)
    assert var == pytest.approx(0.048889, abs=5e-5)


def test_r6_kumaraswamy_skewness_standardized():
    """Fix round: stats('s') must be STANDARDIZED skewness mu3/sigma^3.

    Pinned against exact sympy integration and closed-form raw moments
    (agreement verified in review): -0.1253034159 for a=2, b=2. The
    pre-fix code returned the raw third central moment (-0.0013544974).
    """
    import types

    from calc.ops import distribution_ops

    args = types.SimpleNamespace(
        op="skewness", family="kumaraswamy", value=None, family2=None,
        alpha=None, beta=None, low=None, high=None, mu=None, sigma=None,
        lam=None, scale=None, shape=None, n=None, p=None, df=None, a=2, b=2,
    )
    value = distribution_ops.distribution_command(args)
    assert value == pytest.approx(-0.1253034159, abs=5e-10)
    # kurtosis path was already correct; keep it pinned here too
    args.op = "kurtosis"
    assert distribution_ops.distribution_command(args) == pytest.approx(
        2.1800472255, abs=5e-10
    )


def test_r6_ppf_cdf_roundtrip_new_families():
    import types

    from calc.ops import distribution_ops

    for family, params in (
        ("t", dict(df=7)),
        ("chi2", dict(df=3)),
        ("kumaraswamy", dict(a=1.5, b=2.5)),
    ):
        for q in (0.1, 0.5, 0.9):
            base = dict(
                op="ppf", family=family, value=q, family2=None,
                alpha=None, beta=None, low=None, high=None, mu=None, sigma=None,
                lam=None, scale=None, shape=None, n=None, p=None,
                a=None, b=None,
            )
            base.update(params)
            x = distribution_ops.distribution_command(types.SimpleNamespace(**base))
            base["op"] = "cdf"
            base["value"] = x
            roundtrip = distribution_ops.distribution_command(
                types.SimpleNamespace(**base)
            )
            assert roundtrip == pytest.approx(q, abs=1e-9), (family, q)


def test_r6_kumaraswamy_invalid_params():
    import types

    from calc.ops import distribution_ops

    args = types.SimpleNamespace(
        op="mean", family="kumaraswamy", value=None, family2=None,
        alpha=None, beta=None, low=None, high=None, mu=None, sigma=None,
        lam=None, scale=None, shape=None, n=None, p=None, df=None, a=2, b=-1,
    )
    with pytest.raises(MathError):
        distribution_ops.distribution_command(args)


def test_r6_t_moment_undefined_and_infinite():
    import types

    from calc.ops import distribution_ops

    def make(op, df):
        return types.SimpleNamespace(
            op=op, family="t", value=None, family2=None,
            alpha=None, beta=None, low=None, high=None, mu=None, sigma=None,
            lam=None, scale=None, shape=None, n=None, p=None, df=df, a=None, b=None,
        )

    with pytest.raises(MathError):
        distribution_ops.distribution_command(make("mean", 0))
    with pytest.raises(MathError):
        distribution_ops.distribution_command(make("mean", 1))
    with pytest.raises(MathError):
        distribution_ops.distribution_command(make("mean", 0.5))
    var = distribution_ops.distribution_command(make("variance", 1.5))
    assert math.isinf(var)  # infinite by definition (1 < df <= 2): renders inf


def test_r6_sample_seeded_pinned():
    import types

    from calc.ops import distribution_ops

    args = types.SimpleNamespace(
        op="sample", family="kumaraswamy", value=None, family2=None,
        alpha=None, beta=None, low=None, high=None, mu=None, sigma=None,
        lam=None, scale=None, shape=None, n=None, p=None, df=None, a=2, b=2,
        size=5, seed=123,
    )
    vals = distribution_ops.distribution_command(args)
    assert len(vals) == 5
    # determinism: same seed, same stream
    args2 = types.SimpleNamespace(**vars(args))
    assert distribution_ops.distribution_command(args2) == vals
    # literal pin (computed with numpy PCG64 + spec-pinned inverse-CDF method)
    assert vals == pytest.approx(
        [0.66060365, 0.16517470, 0.34209308, 0.31125334, 0.30365064], abs=1e-7
    )


# ---------------------------------------------------------------------------
# R7: gof
# ---------------------------------------------------------------------------


def test_r7_ks_pinned():
    import types

    args = types.SimpleNamespace(
        op="ks",
        operands=["[0.05,0.2,0.35,0.5,0.65,0.8,0.95]", "uniform"],
        field="statistic",
        gof_ddof=0,
        bins=None,
        alpha=None, beta=None, mu=None, sigma=None, low=0, high=1,
        lam=None, scale=None, shape=None, n=None, p=None, df=None, a=None, b=None,
    )
    assert gof_ops.gof_command(args) == pytest.approx(0.092857, abs=5e-5)


def test_r7_chi2_pinned():
    import types

    args = types.SimpleNamespace(
        op="chi2",
        operands=["[18,22,20,20]", "[20,20,20,20]"],
        field="statistic",
        gof_ddof=0,
        bins=None,
        alpha=None, beta=None, mu=None, sigma=None, low=None, high=None,
        lam=None, scale=None, shape=None, n=None, p=None, df=None, a=None, b=None,
    )
    assert gof_ops.gof_command(args) == pytest.approx(0.4, rel=1e-9)
    args.field = "p"
    assert gof_ops.gof_command(args) == pytest.approx(0.940242, abs=5e-7)
    args.field = "df"
    assert gof_ops.gof_command(args) == 3


def test_r7_scipy_crosschecks():
    import types

    rng = np.random.default_rng(7)
    data = rng.uniform(-1, 2, size=60)
    ds = "[" + ",".join(repr(float(v)) for v in data) + "]"
    args = types.SimpleNamespace(
        op="ks",
        operands=[ds, "uniform"],
        field="statistic",
        gof_ddof=0,
        bins=None,
        alpha=None, beta=None, mu=None, sigma=None, low=-1, high=2,
        lam=None, scale=None, shape=None, n=None, p=None, df=None, a=None, b=None,
    )
    expected = float(sps.kstest(data, sps.uniform(loc=-1, scale=3).cdf).statistic)
    assert gof_ops.gof_command(args) == pytest.approx(expected, rel=1e-9)

    obs = rng.multinomial(80, [0.25] * 4)
    exp = np.full(4, 20.0)
    args = types.SimpleNamespace(
        op="chi2",
        operands=[
            "[" + ",".join(str(int(v)) for v in obs) + "]",
            "[20,20,20,20]",
        ],
        field="statistic",
        gof_ddof=0,
        bins=None,
        alpha=None, beta=None, mu=None, sigma=None, low=None, high=None,
        lam=None, scale=None, shape=None, n=None, p=None, df=None, a=None, b=None,
    )
    expected = float(sps.chisquare(obs, exp).statistic)
    assert gof_ops.gof_command(args) == pytest.approx(expected, rel=1e-9)


def test_r7_chi2_bins_matches_histogram_and_scipy():
    import types

    from calc.ops import distribution_ops

    rng = np.random.default_rng(11)
    data = rng.beta(2, 2, size=240)
    ds = "[" + ",".join(repr(float(v)) for v in data) + "]"
    k = 8
    dist = sps.beta(2, 2)
    edges = [float(dist.ppf(i / k)) for i in range(k + 1)]
    counts, _ = np.histogram(data, bins=edges)
    expected = float(sps.chisquare(counts, np.full(k, 240 / k)).statistic)

    args = types.SimpleNamespace(
        op="chi2-bins",
        operands=[ds, "beta"],
        field="statistic",
        gof_ddof=0,
        bins=k,
        alpha=2, beta=2, mu=None, sigma=None, low=None, high=None,
        lam=None, scale=None, shape=None, n=None, p=None, df=None, a=None, b=None,
    )
    assert gof_ops.gof_command(args) == pytest.approx(expected, rel=1e-9)

    # internal PPF equals scipy PPF
    ours = distribution_ops._scipy_dist(distribution_ops._Params("beta", {
        "alpha": 2, "beta": 2, "mu": None, "sigma": None, "low": None, "high": None,
        "lam": None, "scale": None, "shape": None, "n": None, "p": None,
        "df": None, "a": None, "b": None,
    }))
    assert float(ours.ppf(0.25)) == pytest.approx(float(dist.ppf(0.25)), rel=1e-12)


def test_r7_ks_beta_sanity_uniform_rejects():
    import subprocess

    proc = subprocess.run(
        ["uv", "run", "calc", "distribution", "sample", "beta",
         "--alpha", "2", "--beta", "2", "--size", "240", "--seed", "42"],
        capture_output=True, text=True, check=False,
    )
    assert proc.returncode == 0, proc.stderr
    data = proc.stdout.strip()

    out = subprocess.run(
        ["uv", "run", "calc", "gof", "ks", data, "beta",
         "--alpha", "2", "--beta", "2", "--field", "p"],
        capture_output=True, text=True, check=False,
    )
    assert out.returncode == 0, out.stderr
    p_beta = float(out.stdout)
    assert p_beta > 0.01

    out = subprocess.run(
        ["uv", "run", "calc", "gof", "ks", data, "uniform",
         "--low", "0", "--high", "1", "--field", "p"],
        capture_output=True, text=True, check=False,
    )
    assert out.returncode == 0, out.stderr
    p_uniform = float(out.stdout)
    assert p_uniform < 0.05


def test_r7_ks_discrete_rejected():
    import types

    args = types.SimpleNamespace(
        op="ks",
        operands=["[1,2,3]", "poisson"],
        field="p",
        gof_ddof=0,
        bins=None,
        alpha=None, beta=None, mu=None, sigma=None, low=None, high=None,
        lam=2, scale=None, shape=None, n=None, p=None, df=None, a=None, b=None,
    )
    with pytest.raises(ArgumentError):
        gof_ops.gof_command(args)


def test_r7_chi2_sum_mismatch():
    import types

    args = types.SimpleNamespace(
        op="chi2",
        operands=["[18,22,20,20]", "[10,20,20,20]"],
        field="statistic",
        gof_ddof=0,
        bins=None,
        alpha=None, beta=None, mu=None, sigma=None, low=None, high=None,
        lam=None, scale=None, shape=None, n=None, p=None, df=None, a=None, b=None,
    )
    with pytest.raises(MathError):
        gof_ops.gof_command(args)


def test_r7_chi2_bins_expected_count_too_small():
    import types

    args = types.SimpleNamespace(
        op="chi2-bins",
        operands=["[0.1,0.2,0.3]", "uniform"],
        field="statistic",
        gof_ddof=0,
        bins=10,
        alpha=None, beta=None, mu=None, sigma=None, low=0, high=1,
        lam=None, scale=None, shape=None, n=None, p=None, df=None, a=None, b=None,
    )
    with pytest.raises(MathError, match="expected count per bin < 5"):
        gof_ops.gof_command(args)


# ---------------------------------------------------------------------------
# R8: eval special functions and --let
# ---------------------------------------------------------------------------


def test_r8_special_functions_pinned():
    assert eval_ops.evaluate("erf(1)") == pytest.approx(0.842701, abs=5e-7)
    assert eval_ops.evaluate("erfc(1)") == pytest.approx(0.157299, abs=5e-7)
    assert eval_ops.evaluate("gamma(5)") == 24
    assert eval_ops.evaluate("lgamma(5)") == pytest.approx(3.178054, abs=5e-7)
    assert eval_ops.evaluate("comb(5,2)") == 10
    assert eval_ops.evaluate("perm(5,2)") == 20


def test_r8_comb_negative_matherror():
    with pytest.raises(MathError):
        eval_ops.evaluate("comb(-1,2)")


def test_r8_let_bindings():
    assert eval_ops.evaluate("a*b", let_bindings=["a=2", "b=3"]) == 6.0
    with pytest.raises(ArgumentError):
        eval_ops.evaluate("a*b", let_bindings=["sqrt=2"])
    with pytest.raises(ArgumentError):
        eval_ops.evaluate("a*b", let_bindings=["a=2+3"])
    with pytest.raises(ArgumentError):
        eval_ops.evaluate("a*b", let_bindings=["a=2", "a=3"])
    with pytest.raises(ArgumentError):
        eval_ops.evaluate("a*b", let_bindings=["1bad=2"])


def test_r8_unbound_name_still_syntaxerror():
    from calc.errors import SyntaxError_

    with pytest.raises(SyntaxError_):
        eval_ops.evaluate("z+1")
