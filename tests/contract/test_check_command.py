"""``check`` contract: expression assertion, tolerance, strict mode."""

from __future__ import annotations

import pytest
from conftest import run_calc

from calc.ops.check_ops import check


def test_unit_true_within_default_tolerance() -> None:
    assert check("0.1+0.2", "0.3") == "true"


def test_unit_false_beyond_tolerance() -> None:
    assert check("1/3", "0.333") == "false"


def test_unit_strict_raises_checkfailed() -> None:
    from calc.errors import CalcError

    with pytest.raises(CalcError) as excinfo:
        check("1/3", "0.333", strict=True)
    assert type(excinfo.value).prefix == "CheckFailed"


def test_unit_non_numeric_operand_rejected() -> None:
    from calc.errors import ArgumentError

    with pytest.raises(ArgumentError):
        check("sqrt(2)", "'text'")


def test_cli_true_exit0() -> None:
    proc = run_calc("check", "--actual", "0.1+0.2", "--expected", "0.3")
    assert proc.returncode == 0
    assert proc.stdout.strip() == "true"
    assert proc.stderr == ""


def test_cli_false_exit0() -> None:
    proc = run_calc("check", "--actual", "1/3", "--expected", "0.333")
    assert proc.returncode == 0
    assert proc.stdout.strip() == "false"
    assert proc.stderr == ""


def test_cli_strict_false_is_checkfailed() -> None:
    proc = run_calc(
        "check", "--actual", "1/3", "--expected", "0.333", "--strict"
    )
    assert proc.returncode == 1
    assert proc.stdout == ""
    assert proc.stderr.startswith("CheckFailed: ")
    assert proc.stderr.count("\n") == 1


def test_cli_tolerance_flags() -> None:
    proc = run_calc(
        "check", "--actual", "1/3", "--expected", "0.333", "--atol", "0.001"
    )
    assert proc.returncode == 0
    assert proc.stdout.strip() == "true"


def test_cli_relative_tolerance() -> None:
    proc = run_calc(
        "check",
        "--actual",
        "1000.0001",
        "--expected",
        "1000",
        "--rtol",
        "1e-6",
        "--atol",
        "0",
    )
    assert proc.stdout.strip() == "true"


def test_cli_expression_functions() -> None:
    proc = run_calc("check", "--actual", "sqrt(2)*sqrt(2)", "--expected", "2")
    assert proc.stdout.strip() == "true"


def test_cli_invalid_expression_is_typed_failure() -> None:
    proc = run_calc("check", "--actual", "sqrt(", "--expected", "1")
    assert proc.returncode == 1
    assert proc.stdout == ""
    assert proc.stderr.startswith("SyntaxError: ")
