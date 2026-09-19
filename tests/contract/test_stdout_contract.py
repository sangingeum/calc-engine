"""Contract tests: stdout-only success, stderr+exit-1 failure, no stream mixing."""

from __future__ import annotations

import re

import pytest
from conftest import run_calc

ERROR_LINE = re.compile(r"^(MathError|SyntaxError|ValueError|ArgumentError): .+")

SUCCESS_CASES = [
    (["eval", "2+2"], "4"),
    (["eval", "sqrt(2)", "--precision", "6"], "1.414214"),
    (["stat", "mean", "[1,2,3,4]"], "2.5000"),
    (["stat", "mode", "[1,2,2,3]"], "2"),
    (["stat", "sum", "[1,2,3]"], "6"),
    (
        ["finance", "pmt", "--rate", "0.05", "--periods", "10", "--principal", "1000"],
        "-129.5046",
    ),
    (["matrix", "multiply", "[[1,2],[3,4]]", "[[1],[2]]"], "[[5],[11]]"),
    (["matrix", "transpose", "[[1,2],[3,4]]"], "[[1,3],[2,4]]"),
    (["convert-base", "255", "--from", "dec", "--to", "hex"], "ff"),
    (["convert-base", "FF", "--from", "hex", "--to", "bin"], "11111111"),
    (["convert-unit", "1", "miles", "km"], "1.6093"),
    (["convert-unit", "100", "degC", "degF"], "212.0000"),
    (["calculus", "derive", "x**2", "--var", "x"], "2*x"),
    (
        ["calculus", "integrate", "x**2", "--var", "x", "--lower", "0", "--upper", "1"],
        "0.3333",
    ),
    (["physics-constant", "c"], "299792458.0000"),
    (
        ["physics", "kinematics", "--solve", "d", "--v0", "10", "--t", "2", "--a", "3"],
        "26.0000",
    ),
    (["physics", "force", "--solve", "F", "--m", "5", "--a", "2"], "10.0000"),
    (["physics", "energy", "--solve", "PE", "--m", "2", "--h", "5"], "98.0665"),
    (["vector", "dot", "[1,2,3]", "[4,5,6]"], "32.0000"),
    (["vector", "cross", "[1,0,0]", "[0,1,0]"], "[0.0000,0.0000,1.0000]"),
]

FAILURE_CASES = [
    (["eval", "1/0"], "MathError"),
    (["eval", "(2+3"], "SyntaxError"),
    (["eval", "__import__('os')"], "SyntaxError"),
    (["matrix", "multiply", "[[1,2]]", "[[1,2]]"], "MathError"),
    (["matrix", "multiply", "not-json", "[[1]]"], "SyntaxError"),
    (["convert-unit", "1", "blorp", "km"], "ValueError"),
    (["physics-constant", "notathing"], "ValueError"),
    (["physics", "kinematics", "--solve", "d"], "ArgumentError"),
    (["physics", "nope", "--solve", "d", "--v0", "1", "--t", "1"], "ArgumentError"),
    (
        [
            "finance",
            "pmt",
            "--rate",
            "0.05",
            "--periods",
            "10",
            "--pv",
            "1000",
            "--principal",
            "1000",
        ],
        "ArgumentError",
    ),
    (["finance", "pmt", "--rate", "0.05", "--periods", "10"], "ArgumentError"),
    (["vector", "dot", "[1,2]", "[1,2,3]"], "MathError"),
    (["stat", "mean", "[]"], "MathError"),
    (["stat", "bogus", "[1,2]"], "ArgumentError"),
    (["convert-base", "1.5", "--from", "dec", "--to", "hex"], "MathError"),
    (["convert-base", "ff", "--from", "dec", "--to", "hex"], "SyntaxError"),
]


@pytest.mark.parametrize(
    ("args", "expected"), SUCCESS_CASES, ids=[f"{a[0]}-{a[1]}" for a in SUCCESS_CASES]
)
def test_success_stdout_only(args: list[str], expected: str) -> None:
    proc = run_calc(*args)
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip() == expected
    assert proc.stderr == ""


@pytest.mark.parametrize(
    ("args", "prefix"), FAILURE_CASES, ids=[f"{a[0]}-{a[1]}" for a in FAILURE_CASES]
)
def test_failure_single_stderr_line(args: list[str], prefix: str) -> None:
    proc = run_calc(*args)
    assert proc.returncode == 1
    assert proc.stdout == ""
    lines = proc.stderr.strip().splitlines()
    assert len(lines) == 1
    assert ERROR_LINE.match(lines[0]), lines[0]
    assert lines[0].startswith(f"{prefix}: ")


def test_bad_usage_exits_nonzero_with_stderr() -> None:
    proc = run_calc()
    assert proc.returncode != 0
    assert proc.stderr.strip() != ""
    assert proc.stdout == ""
