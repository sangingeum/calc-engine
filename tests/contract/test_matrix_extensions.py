"""matrix extension contract: solve/rank/trace/power/scale/identity + shapes."""

from __future__ import annotations

from conftest import run_calc


def test_solve_planar_system() -> None:
    proc = run_calc("matrix", "solve", "[[2,1],[1,3]]", "[3,5]")
    assert proc.returncode == 0
    assert proc.stdout.strip() == "[0.8000,1.4000]"


def test_solve_singular_is_matherror() -> None:
    proc = run_calc("matrix", "solve", "[[1,1],[1,1]]", "[1,2]")
    assert proc.returncode == 1
    assert proc.stdout == ""
    assert proc.stderr.startswith("MathError: singular system")
    assert proc.stderr.count("\n") == 1


def test_solve_shape_mismatch_named() -> None:
    proc = run_calc("matrix", "solve", "[[1,0],[0,1]]", "[1,2,3]")
    assert proc.returncode == 1
    assert "shape mismatch" in proc.stderr
    assert "2x2" in proc.stderr


def test_solve_requires_square() -> None:
    proc = run_calc("matrix", "solve", "[[1,2,3],[4,5,6]]", "[1,2]")
    assert proc.returncode == 1
    assert proc.stderr.startswith("MathError: solve requires a square matrix (got 2x3)")


def test_rank_and_trace() -> None:
    assert run_calc("matrix", "rank", "[[1,2],[2,4]]").stdout.strip() == "1"
    assert run_calc("matrix", "trace", "[[1,2],[3,4]]").stdout.strip() == "5.0000"


def test_power_matrix() -> None:
    proc = run_calc("matrix", "power", "[[1,1],[0,1]]", "3")
    assert proc.stdout.strip() == "[[1,3],[0,1]]"


def test_power_negative_exponent_on_singular() -> None:
    proc = run_calc("matrix", "power", "[[1,0],[0,0]]", "-1")
    assert proc.returncode == 1
    assert proc.stderr.startswith("MathError: ")


def test_scale() -> None:
    proc = run_calc("matrix", "scale", "[[1,2],[3,4]]", "2")
    assert proc.stdout.strip() == "[[2.0000,4.0000],[6.0000,8.0000]]"


def test_identity() -> None:
    proc = run_calc("matrix", "identity", "2")
    assert proc.stdout.strip() == "[[1.0000,0.0000],[0.0000,1.0000]]"


def test_multiply_shape_named_in_error() -> None:
    proc = run_calc("matrix", "multiply", "[[1,2],[3,4]]", "[[1,2,3]]")
    assert proc.returncode == 1
    assert proc.stderr == "MathError: cannot multiply 2x2 by 1x3\n"


def test_add_shape_named_in_error() -> None:
    proc = run_calc("matrix", "add", "[[1,2]]", "[[1],[2]]")
    assert proc.returncode == 1
    assert proc.stderr.startswith("MathError: cannot add 1x2 with 2x1")


def test_legacy_examples_byte_identical() -> None:
    proc = run_calc("matrix", "multiply", "[[1,2],[3,4]]", "[[1],[2]]")
    assert proc.stdout == "[[5],[11]]\n"
    proc = run_calc("matrix", "determinant", "[[1,2],[3,4]]")
    assert proc.stdout == "-2.0000\n"
    proc = run_calc("matrix", "transpose", "[[1,2],[3,4]]")
    assert proc.stdout == "[[1,3],[2,4]]\n"
