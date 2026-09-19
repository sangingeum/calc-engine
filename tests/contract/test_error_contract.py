"""Error-contract edge cases: prefixes, security guarantees, exit codes."""

from __future__ import annotations

from conftest import run_calc


def test_error_prefixes_map_to_taxonomy() -> None:
    cases = [
        (["eval", "1/0"], "MathError"),
        (["eval", "open(1)"], "SyntaxError"),
        (["convert-unit", "1", "zzz", "m"], "ValueError"),
        (["calculus", "frobnicate", "x", "--var", "x"], "ArgumentError"),
    ]
    for args, prefix in cases:
        proc = run_calc(*args)
        assert proc.returncode == 1
        assert proc.stdout == ""
        assert proc.stderr.strip().startswith(f"{prefix}: "), proc.stderr


def test_eval_dunder_attribute_access_blocked() -> None:
    proc = run_calc("eval", "().__class__")
    assert proc.returncode == 1
    assert proc.stdout == ""
    assert proc.stderr.startswith("SyntaxError: "), proc.stderr


def test_error_line_has_description_after_prefix() -> None:
    proc = run_calc("eval", "1/0")
    assert proc.stderr.startswith("MathError: ")
    assert len(proc.stderr.strip().split(":", 1)[1].strip()) > 0


def test_success_exit_code_zero() -> None:
    proc = run_calc("eval", "2+2")
    assert proc.returncode == 0


def test_precision_flag_global() -> None:
    two = run_calc("eval", "1/3", "--precision", "2")
    assert two.stdout.strip() == "0.33"
    six = run_calc("eval", "1/3", "--precision", "6")
    assert six.stdout.strip() == "0.333333"


def test_physics_constant_small_magnitude_rendering() -> None:
    # GitHub issue #1: G (6.6743e-11) must not collapse to 0.0000.
    r = run_calc("physics-constant", "G")
    assert r.returncode == 0, r.stderr
    val = float(r.stdout)
    assert 6.674e-11 <= val <= 6.675e-11  # 4 sig digits: 6.674e-11 exactly
    assert "e" in r.stdout  # scientific rendering, per README


def test_large_magnitude_not_truncated() -> None:
    r = run_calc("physics-constant", "c")
    assert r.stdout.strip() == "299792458.0000"  # inside the band: fixed-point


def test_small_magnitude_precision_controls_significant_digits() -> None:
    two = run_calc("physics-constant", "G", "--precision", "2")
    assert two.stdout.strip() == "6.7e-11"
    six = run_calc("physics-constant", "G", "--precision", "6")
    assert six.stdout.strip() == "6.6743e-11"
