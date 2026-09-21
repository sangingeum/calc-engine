"""Unit tests: stat extensions (spec §1). Independent analytical references."""

from __future__ import annotations

import math

import pytest

from calc.errors import ArgumentError, MathError, SyntaxError_
from calc.ops import stat_ops

CLOSE = 1e-9


# covariance -----------------------------------------------------------------
def test_covariance_population() -> None:
    # population covariance of (1,2,3) vs (2,4,6): cov = (2/3) * 2 = 4/3
    assert stat_ops.covariance("[1,2,3]", "[2,4,6]", ddof=0) == pytest.approx(4 / 3, CLOSE)


def test_covariance_sample_ddof1() -> None:
    assert stat_ops.covariance("[1,2,3]", "[2,4,6]", ddof=1) == pytest.approx(2.0, CLOSE)


def test_covariance_invalid_ddof() -> None:
    with pytest.raises(ArgumentError):
        stat_ops.covariance("[1,2,3]", "[2,4,6]", ddof=2)


def test_covariance_length_mismatch() -> None:
    with pytest.raises(ArgumentError):
        stat_ops.covariance("[1,2,3]", "[2,4]")


def test_covariance_too_few_obs() -> None:
    with pytest.raises(ArgumentError):
        stat_ops.covariance("[1]", "[2]")


# pearson --------------------------------------------------------------------
def test_pearson_perfect() -> None:
    assert stat_ops.pearson("[1,2,3]", "[2,4,6]") == pytest.approx(1.0, CLOSE)


def test_pearson_negative_perfect() -> None:
    assert stat_ops.pearson("[1,2,3]", "[6,4,2]") == pytest.approx(-1.0, CLOSE)


def test_pearson_known_value() -> None:
    # X=[1,2,3,4], Y=[2,1,4,3]: r = 0.6 (analytical)
    assert stat_ops.pearson("[1,2,3,4]", "[2,1,4,3]") == pytest.approx(0.6, 1e-12)


def test_pearson_zero_variance_is_math_error() -> None:
    with pytest.raises(MathError):
        stat_ops.pearson("[1,1,1]", "[1,2,3]")


# spearman / rank ------------------------------------------------------------
def test_spearman_example() -> None:
    assert stat_ops.spearman("[1,2,3]", "[30,10,20]") == pytest.approx(-0.5, CLOSE)


def test_rank_average_ties() -> None:
    # [30,10,20,10] -> ranks [4, 1.5, 3, 1.5] (1-based average ranks)
    assert stat_ops.rank("[30,10,20,10]") == pytest.approx([4.0, 1.5, 3.0, 1.5], CLOSE)


def test_spearman_ties_deterministic() -> None:
    # ties get average ranks: ranks [1.5,1.5,3] vs [1,2,3] -> r = sqrt(3)/2
    assert stat_ops.spearman("[1,1,2]", "[5,7,9]") == pytest.approx(math.sqrt(3) / 2, 1e-12)


def test_spearman_constant_input_is_math_error() -> None:
    with pytest.raises(MathError):
        stat_ops.spearman("[1,1,1]", "[1,2,3]")


# regression -----------------------------------------------------------------
def test_regression_slope_intercept() -> None:
    assert stat_ops.regression("[0,1,2,3]", "[1,3,5,7]", "slope") == pytest.approx(2.0, CLOSE)
    assert stat_ops.regression("[0,1,2,3]", "[1,3,5,7]", "intercept") == pytest.approx(
        1.0, CLOSE
    )


def test_regression_r2_perfect() -> None:
    assert stat_ops.regression("[0,1,2,3]", "[1,3,5,7]", "r2") == pytest.approx(1.0, CLOSE)


def test_regression_stderr_alias_and_residual() -> None:
    # perfect fit -> slope_stderr = residual_stderr = residual_variance = 0
    assert stat_ops.regression("[0,1,2,3]", "[1,3,5,7]", "stderr") == 0.0
    assert stat_ops.regression("[0,1,2,3]", "[1,3,5,7]", "slope_stderr") == 0.0
    assert stat_ops.regression("[0,1,2,3]", "[1,3,5,7]", "residual_stderr") == 0.0
    assert stat_ops.regression("[0,1,2,3]", "[1,3,5,7]", "residual_variance") == 0.0
    # noisy fit: X=[0,1,2,3], Y=[1,3,4,7]
    # slope=1.9, intercept=1.0; SSR = 0.7; residual_variance = 0.7/2 = 0.35
    # slope_stderr = sqrt(0.35/5) = sqrt(0.07)
    assert stat_ops.regression("[0,1,2,3]", "[1,3,4,7]", "residual_variance") == pytest.approx(
        0.35, CLOSE
    )
    assert stat_ops.regression("[0,1,2,3]", "[1,3,4,7]", "slope_stderr") == pytest.approx(
        math.sqrt(0.07), CLOSE
    )
    assert stat_ops.regression("[0,1,2,3]", "[1,3,4,7]", "stderr") == pytest.approx(
        math.sqrt(0.07), CLOSE
    )


def test_regression_unknown_field() -> None:
    with pytest.raises(ArgumentError):
        stat_ops.regression("[0,1,2,3]", "[1,3,5,7]", "nope")


def test_regression_too_few_obs() -> None:
    with pytest.raises(ArgumentError):
        stat_ops.regression("[0,1]", "[1,2]", "slope")


def test_regression_zero_x_variance() -> None:
    with pytest.raises(MathError):
        stat_ops.regression("[1,1,1]", "[1,2,3]", "slope")


# quantile -------------------------------------------------------------------
def test_quantile_median_odd() -> None:
    assert stat_ops.quantile("[1,2,3,4,5]", 0.5) == pytest.approx(3.0, CLOSE)


def test_quantile_linear_interpolation() -> None:
    # h = (5-1)*0.25 = 1.0 -> x[1] = 2 ; h = 1*0.5 = 1.5 -> 2.5
    assert stat_ops.quantile("[1,2,3,4,5]", 0.25) == pytest.approx(2.0, CLOSE)
    assert stat_ops.quantile("[1,2,3,4,5]", 0.5 + 0.5 - 0.5) == pytest.approx(3.0, CLOSE)
    assert stat_ops.quantile("[1,2]", 0.5) == pytest.approx(1.5, CLOSE)


def test_quantile_boundaries() -> None:
    assert stat_ops.quantile("[3,1,2]", 0.0) == pytest.approx(1.0, CLOSE)
    assert stat_ops.quantile("[3,1,2]", 1.0) == pytest.approx(3.0, CLOSE)


def test_quantile_out_of_range() -> None:
    with pytest.raises(ArgumentError):
        stat_ops.quantile("[1,2,3]", 1.5)


def test_quantile_empty() -> None:
    with pytest.raises(MathError):
        stat_ops.quantile("[]", 0.5)


# parse errors ---------------------------------------------------------------
def test_invalid_json_series() -> None:
    with pytest.raises(SyntaxError_):
        stat_ops.pearson("[1,2", "[1,2]")


def test_non_numeric_series() -> None:
    with pytest.raises(SyntaxError_):
        stat_ops.pearson('["a",2]', "[1,2]")


def test_backward_compat_stat_mean() -> None:
    assert stat_ops.stat_command("mean", ["[1,2,3,4]"]) == pytest.approx(2.5, CLOSE)


def test_stat_command_dispatch_quantile() -> None:
    assert stat_ops.stat_command("quantile", ["[1,2,3,4,5]", "0.5"]) == pytest.approx(
        3.0, CLOSE
    )


def test_stat_command_dispatch_regression() -> None:
    assert stat_ops.stat_command(
        "regression", ["[0,1,2,3]", "[1,3,5,7]"], field="slope"
    ) == pytest.approx(2.0, CLOSE)


def test_stat_command_unknown_op() -> None:
    with pytest.raises(ArgumentError):
        stat_ops.stat_command("nope", ["[1,2,3]"])
