"""Contract tests: stat extensions, distribution, assert (spec §1, §2-15, §16, §20)."""

from __future__ import annotations

from conftest import run_calc


def assert_true(*args: str) -> None:
    proc = run_calc(*args)
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout == "true\n", repr(proc.stdout)
    assert proc.stderr == ""


def assert_failure(*args: str, prefix: str, code: int = 1) -> None:
    proc = run_calc(*args)
    assert proc.returncode == code
    assert proc.stdout == "", repr(proc.stdout)
    assert proc.stderr.startswith(f"{prefix}: "), proc.stderr
    assert proc.stderr.count("\n") == 1  # exactly one stderr line


# spec §1 examples --------------------------------------------------------------
def test_stat_extension_examples_exact_stdout() -> None:
    cases = [
        (["stat", "covariance", "[1,2,3]", "[2,4,6]"], "1.3333"),
        (["stat", "pearson", "[1,2,3]", "[2,4,6]"], "1.0000"),
        (["stat", "spearman", "[1,2,3]", "[30,10,20]"], "-0.5000"),
        (["stat", "regression", "[0,1,2,3]", "[1,3,5,7]", "--field", "slope"], "2.0000"),
        (["stat", "quantile", "[1,2,3,4,5]", "0.5"], "3.0000"),
        (["stat", "rank", "[30,10,20]"], "[3.0000,1.0000,2.0000]"),
    ]
    for args, expected in cases:
        proc = run_calc(*args)
        assert proc.returncode == 0, proc.stderr
        assert proc.stdout == expected + "\n", (args, proc.stdout)
        assert proc.stderr == ""


def test_stat_extension_error_contract() -> None:
    cases = [
        (["stat", "pearson", "[1,2]", "[1,2,3]"], "ArgumentError"),
        (["stat", "pearson", "[1]", "[2]"], "ArgumentError"),
        (["stat", "pearson", "[1,1,1]", "[1,2,3]"], "MathError"),
        (["stat", "regression", "[0,1]", "[1,2]", "--field", "slope"], "ArgumentError"),
        (["stat", "regression", "[0,1,2]", "[1,2,3]"], "ArgumentError"),  # missing --field
        (["stat", "regression", "[0,1,2,3]", "[1,3,5,7]", "--field", "nope"], "ArgumentError"),
        (["stat", "quantile", "[1,2,3]", "1.5"], "ArgumentError"),
        (["stat", "quantile", "[1,2,3]", "abc"], "ArgumentError"),
        (["stat", "quantile", "[]", "0.5"], "MathError"),
        (["stat", "covariance", "[1,2,3]", "[2,4,6]", "--ddof", "2"], "ArgumentError"),
        (["stat", "rank", "[]"], "MathError"),
    ]
    for args, prefix in cases:
        assert_failure(*args, prefix=prefix)


# spec §2-14 distribution examples ----------------------------------------------
def test_distribution_examples_exact_stdout() -> None:
    cases = [
        (["distribution", "mean", "beta", "--alpha", "2", "--beta", "2"], "0.5000"),
        (["distribution", "variance", "beta", "--alpha", "2", "--beta", "2"], "0.0500"),
        (["distribution", "stddev", "beta", "--alpha", "2", "--beta", "2"], "0.2236"),
        (["distribution", "pdf", "beta", "0.5", "--alpha", "2", "--beta", "2"], "1.5000"),
        (["distribution", "cdf", "beta", "0.5", "--alpha", "2", "--beta", "2"], "0.5000"),
        (["distribution", "ppf", "beta", "0.5", "--alpha", "2", "--beta", "2"], "0.5000"),
        (["distribution", "validate", "beta", "--alpha", "2", "--beta", "2"], "true"),
        (["distribution", "validate", "poisson", "--lam", "2"], "true"),
        (["distribution", "mean", "gamma", "--shape", "2", "--scale", "3"], "6.0000"),
        (["distribution", "mean", "binomial", "--n", "10", "--p", "0.5"], "5.0000"),
        (["distribution", "mean", "lognormal", "--mu", "0", "--sigma", "1"], "1.6487"),
        (["distribution", "mean", "uniform", "--low", "0", "--high", "1"], "0.5000"),
        (["distribution", "mean", "exponential", "--scale", "2"], "2.0000"),
        (["distribution", "mean", "normal", "--mu", "5", "--sigma", "2"], "5.0000"),
        (["distribution", "skewness", "beta", "--alpha", "2", "--beta", "2"], "0.0000"),
        (["distribution", "kurtosis", "normal", "--mu", "0", "--sigma", "1"], "3.0000"),
        (["distribution", "excess-kurtosis", "normal", "--mu", "0", "--sigma", "1"], "0.0000"),
    ]
    for args, expected in cases:
        proc = run_calc(*args)
        assert proc.returncode == 0, proc.stderr
        assert proc.stdout == expected + "\n", (args, proc.stdout)
        assert proc.stderr == ""


def test_distribution_invalid_parameters_typed_errors() -> None:
    cases = [
        (["distribution", "mean", "beta", "--alpha", "0", "--beta", "2"], "MathError"),
        (["distribution", "mean", "uniform", "--low", "1", "--high", "0"], "MathError"),
        (["distribution", "mean", "normal", "--mu", "0", "--sigma", "-1"], "MathError"),
        (["distribution", "mean", "exponential", "--scale", "0"], "MathError"),
        (["distribution", "mean", "gamma", "--shape", "-1", "--scale", "2"], "MathError"),
        (["distribution", "mean", "binomial", "--n", "5.5", "--p", "0.5"], "MathError"),
        (["distribution", "mean", "binomial", "--n", "5", "--p", "1.5"], "MathError"),
        (["distribution", "mean", "poisson", "--lam", "0"], "MathError"),
        (["distribution", "mean", "beta"], "ArgumentError"),  # missing parameter
        (["distribution", "mean", "cauchy"], "ArgumentError"),
        (
            ["distribution", "frobnicate", "beta", "--alpha", "1", "--beta", "1"],
            "ArgumentError",
        ),
        (["distribution", "describe", "beta", "--alpha", "2", "--beta", "2"], "ArgumentError"),
        (["distribution", "ppf", "beta", "1.5", "--alpha", "2", "--beta", "2"], "MathError"),
    ]
    for args, prefix in cases:
        assert_failure(*args, prefix=prefix)


def test_distribution_sample_deterministic_and_exact() -> None:
    expected = "[0.1486,0.7646,0.4182,0.5289,0.7776]"
    for _ in range(2):
        proc = run_calc(
            "distribution",
            "sample",
            "beta",
            "--alpha",
            "2",
            "--beta",
            "2",
            "--size",
            "5",
            "--seed",
            "123",
        )
        assert proc.returncode == 0
        assert proc.stdout == expected + "\n", proc.stdout


def test_distribution_sample_requires_seed() -> None:
    assert_failure(
        "distribution",
        "sample",
        "beta",
        "--alpha",
        "2",
        "--beta",
        "2",
        "--size",
        "5",
        prefix="ArgumentError",
    )


def test_compare_moments_boolean_interface() -> None:
    assert_true(
        "distribution",
        "compare-moments",
        "beta",
        "--alpha",
        "2",
        "--beta",
        "2",
        "uniform",
        "--low",
        "0",
        "--high",
        "1",
        "--moment",
        "mean",
    )
    proc = run_calc(
        "distribution",
        "compare-moments",
        "beta",
        "--alpha",
        "2",
        "--beta",
        "2",
        "uniform",
        "--low",
        "0",
        "--high",
        "1",
        "--moment",
        "variance",
    )
    assert proc.stdout == "false\n"
    assert proc.returncode == 0  # 'false' is a valid result, not a failure


def test_compare_moments_beta_4_05_variance_regression() -> None:
    """Acceptance §22.2: Beta(4.05,4.05) variance ~0.02747252747, not 0.05."""
    proc = run_calc(
        "distribution",
        "variance",
        "beta",
        "--alpha",
        "4.05",
        "--beta",
        "4.05",
        "--precision",
        "11",
    )
    assert proc.returncode == 0
    assert proc.stdout == "0.02747252747\n"
    # and it must NOT compare equal to 0.05
    proc = run_calc(
        "distribution",
        "compare-moments",
        "beta",
        "--alpha",
        "4.05",
        "--beta",
        "4.05",
        "beta",
        "--alpha2",
        "2",
        "--beta2",
        "2",
        "--moment",
        "variance",
    )
    assert proc.stdout == "false\n"


def test_two_point_bimodal_empirical_moments() -> None:
    # [0.25, 0.75]: mean 0.5, variance 0.0625, stddev 0.25
    proc = run_calc("stat", "mean", "[0.25,0.75]")
    assert proc.stdout == "0.5000\n"
    proc = run_calc("stat", "pvariance", "[0.25,0.75]")
    assert proc.stdout == "0.0625\n"
    proc = run_calc("stat", "stdev", "[0.25,0.75]")
    # Spec §16 quotes population stddev = 0.25 for {0.25,0.75}; the pre-existing
    # `stat stdev` op is the SAMPLE stdev (ddof=1) = sqrt(0.125) = 0.3536.
    # The population value is verified above via `pvariance`; sqrt(0.0625)=0.25.
    assert proc.stdout == "0.3536\n"
    # [0.2763932023, 0.7236067977]: mean 0.5, variance ~0.05
    proc = run_calc("stat", "mean", "[0.2763932023,0.7236067977]")
    assert proc.stdout == "0.5000\n"
    proc = run_calc("stat", "pvariance", "[0.2763932023,0.7236067977]", "--precision", "8")
    assert proc.stdout == "0.05000000\n"


# spec §15 assert examples ---------------------------------------------------------
def test_assert_examples() -> None:
    assert_true("assert", "approx", "0.5", "0.4999999")
    assert_true("assert", "equal", "1", "1")
    assert_true("assert", "between", "0.5", "0", "1")
    assert_true("assert", "sign", "0.35", "positive")
    assert_true("assert", "abs-lt", "0.01", "0.05")
    assert_true("assert", "abs-gt", "0.10", "0.05")


def test_assert_failures_are_domain_failures() -> None:
    cases = [
        ["assert", "approx", "1", "2"],
        ["assert", "equal", "1", "2"],
        ["assert", "between", "2", "0", "1"],
        ["assert", "sign", "-1", "positive"],
        ["assert", "abs-lt", "0.1", "0.05"],
        ["assert", "abs-gt", "0.01", "0.05"],
    ]
    for args in cases:
        assert_failure(*args, prefix="AssertionError")


def test_assert_boundary_cases() -> None:
    # between endpoints are inclusive
    assert_true("assert", "between", "0", "0", "1")
    assert_true("assert", "between", "1", "0", "1")
    assert_true("assert", "sign", "0", "zero")
    assert_true("assert", "sign", "0", "nonnegative")
    assert_true("assert", "sign", "0", "nonpositive")
    assert_true("assert", "approx", "1", "1.000001", "--atol", "1e-5")


def test_assert_usage_errors() -> None:
    cases = [
        ["assert", "sign", "1", "sideways"],
        ["assert", "approx", "1"],
        ["assert", "between", "0.5", "1", "0"],
    ]
    for args in cases:
        assert_failure(*args, prefix="ArgumentError")


# cdf(ppf(p)) ≈ p roundtrip through the CLI ----------------------------------------
def test_cdf_ppf_roundtrip_cli() -> None:
    for p in ("0.1", "0.5", "0.9"):
        x = run_calc("distribution", "ppf", "beta", p, "--alpha", "2", "--beta", "2").stdout
        back = run_calc("distribution", "cdf", "beta", x.strip(), "--alpha", "2", "--beta", "2")
        assert back.stdout == f"{float(p):.4f}\n", (p, x, back.stdout)


# exit code 2 for usage errors ------------------------------------------------------
def test_usage_error_exit_code_2() -> None:
    proc = run_calc("distribution", "mean")  # missing family
    assert proc.returncode == 2
    proc = run_calc("assert")  # missing op
    assert proc.returncode == 2
