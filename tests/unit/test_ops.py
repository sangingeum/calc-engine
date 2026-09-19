"""Per-module unit tests: math correctness, precision, edge inputs."""

from __future__ import annotations

import math

import pytest

from calc.errors import ArgumentError, MathError, SyntaxError_, UnitError
from calc.ops import (
    base_ops,
    calculus_ops,
    eval_ops,
    finance_ops,
    matrix_ops,
    physics_ops,
    stat_ops,
    unit_ops,
    vector_ops,
)
from calc.render import render


class TestEvalOps:
    def test_integer_result(self) -> None:
        assert eval_ops.evaluate("2+2") == 4

    def test_float_result(self) -> None:
        assert eval_ops.evaluate("1/2") == 0.5

    def test_precedence(self) -> None:
        assert eval_ops.evaluate("2+3*4") == 14

    def test_functions(self) -> None:
        assert eval_ops.evaluate("sqrt(9)") == 3.0
        assert eval_ops.evaluate("factorial(5)") == 120

    def test_constants(self) -> None:
        assert eval_ops.evaluate("pi") == pytest.approx(math.pi)

    def test_division_by_zero(self) -> None:
        with pytest.raises(MathError):
            eval_ops.evaluate("1/0")

    def test_unclosed_paren(self) -> None:
        with pytest.raises(SyntaxError_):
            eval_ops.evaluate("(2+3")

    def test_dunder_blocked(self) -> None:
        with pytest.raises(SyntaxError_):
            eval_ops.evaluate("().__class__")

    def test_import_blocked(self) -> None:
        with pytest.raises(SyntaxError_):
            eval_ops.evaluate("__import__('os')")


class TestRender:
    def test_int(self) -> None:
        assert render(4) == "4"

    def test_float_precision(self) -> None:
        assert render(1 / 3, 6) == "0.333333"
        assert render(1 / 3) == "0.3333"

    def test_negative_zero_avoided(self) -> None:
        assert render(0.0) == "0.0000"

    def test_zero_inside_band_renders_fixed_point(self) -> None:
        # Exact zero stays fixed-point even at precision 0.
        assert render(0.0, 0) == "0"

    def test_inf_nan_passthrough(self) -> None:
        assert render(float("inf")) == "inf"
        assert render(float("-inf")) == "-inf"
        assert render(float("nan")) == "nan"

    def test_small_magnitude_uses_general_format(self) -> None:
        assert render(6.6743e-11, 4) == "6.674e-11"
        assert render(1e-5) == "1e-05"

    def test_large_magnitude_uses_general_format(self) -> None:
        assert render(1.23e17, 4) == "1.23e+17"

    def test_band_edges_use_fixed_point(self) -> None:
        assert render(1e-4) == "0.0001"
        assert render(9.999e15) == "9999000000000000.0000"

    def test_nested_list(self) -> None:
        assert render([[1.0, 2.0], [3.0, 4.0]], 0) == "[[1,2],[3,4]]"

    def test_string_passthrough(self) -> None:
        assert render("x**3/3") == "x**3/3"


class TestStatOps:
    def test_mean(self) -> None:
        assert stat_ops.stat("mean", "[1,2,3,4]") == 2.5

    def test_mode_first_on_multimodal(self) -> None:
        # multimode returns values in first-occurrence order; 2 appears first.
        assert stat_ops.stat("mode", "[2,1,1,2]") == 2
        assert stat_ops.stat("mode", "[1,2,2,3]") == 2

    def test_stdev(self) -> None:
        assert stat_ops.stat("stdev", "[1,2,3,4]") == pytest.approx(1.2909944)

    def test_count(self) -> None:
        assert stat_ops.stat("count", "[1,2,3]") == 3

    def test_min_max_sum(self) -> None:
        assert stat_ops.stat("min", "[3,1,2]") == 1.0
        assert stat_ops.stat("max", "[3,1,2]") == 3.0
        assert stat_ops.stat("sum", "[3,1,2]") == 6.0

    def test_single_element_variance_is_error(self) -> None:
        with pytest.raises(MathError):
            stat_ops.stat("variance", "[1]")

    def test_empty_dataset(self) -> None:
        with pytest.raises(MathError):
            stat_ops.stat("mean", "[]")

    def test_unknown_op(self) -> None:
        with pytest.raises(ArgumentError):
            stat_ops.stat("bogus", "[1]")

    def test_invalid_json(self) -> None:
        with pytest.raises(SyntaxError_):
            stat_ops.stat("mean", "[1,2")


class TestFinanceOps:
    def test_fv(self) -> None:
        result = finance_ops.finance("fv", rate=0.05, periods=10, pv=1000)
        assert result == pytest.approx(-1628.8946, abs=1e-3)

    def test_pv(self) -> None:
        result = finance_ops.finance("pv", rate=0.05, periods=10, fv=1628.8946)
        assert result == pytest.approx(-1000.0, abs=1e-3)

    def test_pmt_with_principal(self) -> None:
        result = finance_ops.finance("pmt", rate=0.05, periods=10, principal=1000)
        assert result == pytest.approx(-129.5046, abs=1e-3)

    def test_pmt_pv_alias(self) -> None:
        result = finance_ops.finance("pmt", rate=0.05, periods=10, pv=1000)
        assert result == pytest.approx(-129.5046, abs=1e-3)

    def test_pmt_pv_and_principal_rejected(self) -> None:
        with pytest.raises(ArgumentError):
            finance_ops.finance("pmt", rate=0.05, periods=10, pv=1000, principal=1000)

    def test_missing_argument(self) -> None:
        with pytest.raises(ArgumentError):
            finance_ops.finance("fv", rate=0.05, periods=10)

    def test_extra_argument(self) -> None:
        with pytest.raises(ArgumentError):
            finance_ops.finance("fv", rate=0.05, periods=10, pv=1000, fv=1)

    def test_unknown_op(self) -> None:
        with pytest.raises(ArgumentError):
            finance_ops.finance("irr")


class TestMatrixOps:
    def test_multiply(self) -> None:
        assert matrix_ops.matrix("multiply", ["[[1,2],[3,4]]", "[[1],[2]]"]) == [
            [5.0],
            [11.0],
        ]

    def test_add(self) -> None:
        assert matrix_ops.matrix("add", ["[[1,2]]", "[[3,4]]"]) == [[4.0, 6.0]]

    def test_subtract(self) -> None:
        assert matrix_ops.matrix("subtract", ["[[1,2]]", "[[3,4]]"]) == [[-2.0, -2.0]]

    def test_transpose(self) -> None:
        assert matrix_ops.matrix("transpose", ["[[1,2],[3,4]]"]) == [
            [1.0, 3.0],
            [2.0, 4.0],
        ]

    def test_determinant(self) -> None:
        assert matrix_ops.matrix("determinant", ["[[1,2],[3,4]]"]) == pytest.approx(-2.0)

    def test_inverse(self) -> None:
        result = matrix_ops.matrix("inverse", ["[[4,7],[2,6]]"])
        assert isinstance(result, list) and isinstance(result[0], list)
        assert result[0] == pytest.approx([0.6, -0.7])

    def test_dimension_mismatch(self) -> None:
        with pytest.raises(MathError):
            matrix_ops.matrix("multiply", ["[[1,2]]", "[[1,2]]"])

    def test_singular_inverse(self) -> None:
        # [[2,4],[1,2]] has rank 1 -> det 0 -> no inverse.
        with pytest.raises(MathError):
            matrix_ops.matrix("inverse", ["[[2,4],[1,2]]"])

    def test_invalid_json(self) -> None:
        with pytest.raises(SyntaxError_):
            matrix_ops.matrix("multiply", ["not-json", "[[1]]"])

    def test_ragged_rows(self) -> None:
        with pytest.raises(SyntaxError_):
            matrix_ops.matrix("determinant", ["[[1,2],[3]]"])

    def test_wrong_arity(self) -> None:
        with pytest.raises(ArgumentError):
            matrix_ops.matrix("multiply", ["[[1,2],[3,4]]"])

    def test_unknown_op(self) -> None:
        with pytest.raises(ArgumentError):
            matrix_ops.matrix("frobnicate", ["[[1]]"])


class TestBaseOps:
    def test_dec_to_hex(self) -> None:
        assert base_ops.convert("255", "dec", "hex") == "ff"

    def test_hex_to_bin_case_insensitive(self) -> None:
        assert base_ops.convert("FF", "hex", "bin") == "11111111"

    def test_bin_to_dec(self) -> None:
        assert base_ops.convert("1010", "bin", "dec") == "10"

    def test_negative(self) -> None:
        assert base_ops.convert("-42", "dec", "hex") == "-2a"

    def test_numeric_bases(self) -> None:
        assert base_ops.convert("7", "10", "2") == "111"

    def test_base_36_roundtrip(self) -> None:
        assert base_ops.convert("zz", "36", "dec") == "1295"

    def test_fractional_rejected(self) -> None:
        with pytest.raises(MathError):
            base_ops.convert("1.5", "dec", "hex")

    def test_invalid_digit(self) -> None:
        with pytest.raises(SyntaxError_):
            base_ops.convert("ff", "dec", "hex")

    def test_invalid_base_name(self) -> None:
        with pytest.raises(ArgumentError):
            base_ops.convert("10", "bogus", "hex")

    def test_base_out_of_range(self) -> None:
        with pytest.raises(ArgumentError):
            base_ops.convert("10", "37", "hex")

    def test_zero(self) -> None:
        assert base_ops.convert("0", "dec", "bin") == "0"


class TestUnitOps:
    def test_length(self) -> None:
        assert unit_ops.convert(1, "miles", "km") == pytest.approx(1.609344)

    def test_temperature_offset(self) -> None:
        assert unit_ops.convert(100, "degC", "degF") == pytest.approx(212.0)

    def test_temperature_offset_reverse(self) -> None:
        assert unit_ops.convert(32, "degF", "degC") == pytest.approx(0.0)

    def test_same_unit(self) -> None:
        assert unit_ops.convert(5, "m", "m") == 5.0

    def test_unknown_unit(self) -> None:
        with pytest.raises(UnitError):
            unit_ops.convert(1, "blorp", "km")

    def test_dimensionality_error(self) -> None:
        with pytest.raises(UnitError):
            unit_ops.convert(1, "m", "kg")


class TestCalculusOps:
    def test_derive(self) -> None:
        assert calculus_ops.calculus("derive", "x**2", "x") == "2*x"

    def test_indefinite_integrate(self) -> None:
        assert calculus_ops.calculus("integrate", "x**2", "x") == "x**3/3"

    def test_definite_integrate(self) -> None:
        result = calculus_ops.calculus("integrate", "x**2", "x", lower=0, upper=1)
        assert result == pytest.approx(1 / 3)

    def test_limit_finite(self) -> None:
        result = calculus_ops.calculus("limit", "(x**2-1)/(x-1)", "x", approach=1)
        assert result == pytest.approx(2.0)

    def test_limit_infinity(self) -> None:
        assert calculus_ops.calculus("limit", "1/x", "x", approach=0) == math.inf

    def test_unknown_op(self) -> None:
        with pytest.raises(ArgumentError):
            calculus_ops.calculus("frobnicate", "x", "x")

    def test_half_bounds_rejected(self) -> None:
        with pytest.raises(ArgumentError):
            calculus_ops.calculus("integrate", "x**2", "x", lower=0)

    def test_bad_expression(self) -> None:
        with pytest.raises(SyntaxError_):
            calculus_ops.calculus("derive", "(((", "x")


class TestPhysicsConstant:
    def test_speed_of_light(self) -> None:
        assert physics_ops.constant("c") == pytest.approx(299792458.0)

    def test_gravity(self) -> None:
        assert physics_ops.constant("g") == pytest.approx(9.80665)

    def test_unknown(self) -> None:
        with pytest.raises(UnitError):
            physics_ops.constant("notathing")


class TestPhysicsSolve:
    def test_kinematics_d(self) -> None:
        result = physics_ops.solve("kinematics", "d", {"v0": 10, "t": 2, "a": 3})
        assert result == pytest.approx(26.0)

    def test_kinematics_v(self) -> None:
        result = physics_ops.solve("kinematics", "v", {"v0": 10, "t": 2, "a": 3})
        assert result == pytest.approx(16.0)

    def test_kinematics_v0_from_d(self) -> None:
        result = physics_ops.solve("kinematics", "v0", {"d": 26, "t": 2, "a": 3})
        assert result == pytest.approx(10.0)

    def test_force(self) -> None:
        assert physics_ops.solve("force", "F", {"m": 5, "a": 2}) == pytest.approx(10.0)

    def test_force_solve_for_a(self) -> None:
        assert physics_ops.solve("force", "a", {"F": 10, "m": 5}) == pytest.approx(2.0)

    def test_kinetic_energy(self) -> None:
        result = physics_ops.solve("energy", "KE", {"m": 2, "v": 3})
        assert result == pytest.approx(9.0)

    def test_work(self) -> None:
        assert physics_ops.solve("energy", "W", {"F": 4, "d": 3}) == pytest.approx(12.0)

    def test_potential_energy_default_g(self) -> None:
        result = physics_ops.solve("energy", "PE", {"m": 2, "h": 5})
        assert result == pytest.approx(2 * 5 * 9.80665)

    def test_potential_energy_custom_g(self) -> None:
        assert physics_ops.solve("energy", "PE", {"m": 2, "h": 5, "g": 10}) == pytest.approx(
            100.0
        )

    def test_v_squared_quadratic_positive_root(self) -> None:
        result = physics_ops.solve("kinematics", "v", {"v0": 0, "a": 3, "d": 27})
        assert result == pytest.approx(math.sqrt(2 * 3 * 27))

    def test_missing_knowns(self) -> None:
        with pytest.raises(ArgumentError):
            physics_ops.solve("kinematics", "d", {"v0": 10})

    def test_unknown_symbol(self) -> None:
        with pytest.raises(ArgumentError):
            physics_ops.solve("kinematics", "d", {"v0": 10, "t": 1, "a": 1, "q": 1})

    def test_unknown_domain(self) -> None:
        with pytest.raises(ArgumentError):
            physics_ops.solve("thermo", "d", {})

    def test_unknown_target(self) -> None:
        with pytest.raises(ArgumentError):
            physics_ops.solve("kinematics", "q", {"v0": 1, "t": 1, "a": 1})


class TestVectorOps:
    def test_dot(self) -> None:
        assert vector_ops.vector("dot", ["[1,2,3]", "[4,5,6]"]) == 32.0

    def test_cross(self) -> None:
        assert vector_ops.vector("cross", ["[1,0,0]", "[0,1,0]"]) == [0.0, 0.0, 1.0]

    def test_norm(self) -> None:
        assert vector_ops.vector("norm", ["[3,4]"]) == 5.0

    def test_add(self) -> None:
        assert vector_ops.vector("add", ["[1,2]", "[3,4]"]) == [4.0, 6.0]

    def test_subtract(self) -> None:
        assert vector_ops.vector("subtract", ["[1,2]", "[3,4]"]) == [-2.0, -2.0]

    def test_dimension_mismatch(self) -> None:
        with pytest.raises(MathError):
            vector_ops.vector("dot", ["[1,2]", "[1,2,3]"])

    def test_cross_non_3d(self) -> None:
        with pytest.raises(MathError):
            vector_ops.vector("cross", ["[1,2]", "[3,4]"])

    def test_invalid_json(self) -> None:
        with pytest.raises(SyntaxError_):
            vector_ops.vector("dot", ["not-json", "[1,2]"])

    def test_wrong_arity(self) -> None:
        with pytest.raises(ArgumentError):
            vector_ops.vector("dot", ["[1,2]"])

    def test_unknown_op(self) -> None:
        with pytest.raises(ArgumentError):
            vector_ops.vector("frobnicate", ["[1]"])
