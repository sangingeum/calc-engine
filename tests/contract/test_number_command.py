"""``number`` contract: number-theory operations."""

from __future__ import annotations

from conftest import run_calc


def test_factorize() -> None:
    proc = run_calc("number", "factorize", "360")
    assert proc.returncode == 0
    assert proc.stdout.strip() == "2^3*3^2*5"


def test_factorize_prime() -> None:
    proc = run_calc("number", "factorize", "97")
    assert proc.stdout.strip() == "97"


def test_isprime_true_and_false() -> None:
    assert run_calc("number", "isprime", "97").stdout.strip() == "true"
    assert run_calc("number", "isprime", "96").stdout.strip() == "false"


def test_nextprime() -> None:
    proc = run_calc("number", "nextprime", "100")
    assert proc.stdout.strip() == "101"


def test_modinv() -> None:
    proc = run_calc("number", "modinv", "3", "11")
    assert proc.stdout.strip() == "4"


def test_modinv_non_invertible() -> None:
    proc = run_calc("number", "modinv", "3", "6")
    assert proc.returncode == 1
    assert proc.stdout == ""
    assert proc.stderr.startswith("MathError: ")
    assert proc.stderr.count("\n") == 1


def test_gcd_lcm_multiarg() -> None:
    assert run_calc("number", "gcd", "12", "18", "24").stdout.strip() == "6"
    assert run_calc("number", "lcm", "4", "6").stdout.strip() == "12"


def test_factorize_rejects_small() -> None:
    for n in ("1", "0", "-5"):
        proc = run_calc("number", "factorize", n)
        assert proc.returncode == 1
        assert proc.stderr.startswith("MathError: factorize requires N >= 2")


def test_non_integer_operand() -> None:
    proc = run_calc("number", "isprime", "12.5")
    assert proc.returncode == 1
    assert proc.stderr.startswith("ArgumentError: ")


def test_unknown_op() -> None:
    proc = run_calc("number", "frobnicate", "3")
    assert proc.returncode == 1
    assert proc.stderr.startswith("ArgumentError: unknown number operation")


def test_oversized_guard() -> None:
    proc = run_calc("number", "factorize", str(10**18))
    assert proc.returncode == 1
    assert proc.stderr.startswith("MathError: ")
    assert "exceeds the guard" in proc.stderr
