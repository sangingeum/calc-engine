"""``number`` command: number-theory operations (sympy-backed).

Deterministic integer number theory: primality, factorization, next prime,
modular inverse, multi-argument gcd/lcm. sympy.isprime is deterministic for
n < 2^64 (BPSW + Miller-Rabin with known-good bases); larger inputs are
probable-prime results (documented). factorize is subject to the compute
timeout like every sympy path — factoring a >64-bit semiprime can legitimately
time out rather than hang.
"""

from __future__ import annotations

import math

import sympy

from calc.errors import ArgumentError, MathError
from calc.limits import max_comb_n


def _parse_int(text: str, what: str) -> int:
    try:
        return int(text)
    except ValueError:
        raise ArgumentError(f"{what} must be an integer (got {text!r})") from None


def number(op: str, operands: list[str]) -> object:
    """Dispatch a number-theory operation."""
    if op == "isprime":
        if len(operands) != 1:
            raise ArgumentError("number isprime takes exactly N")
        return "true" if sympy.isprime(_parse_int(operands[0], "N")) else "false"
    if op == "nextprime":
        if len(operands) != 1:
            raise ArgumentError("number nextprime takes exactly N")
        n = _parse_int(operands[0], "N")
        if n > max_comb_n():
            raise MathError(f"N {n} exceeds the guard {max_comb_n()}")
        return int(sympy.nextprime(n))
    if op == "factorize":
        if len(operands) != 1:
            raise ArgumentError("number factorize takes exactly N")
        n = _parse_int(operands[0], "N")
        if n < 2:
            raise MathError(f"factorize requires N >= 2 (got {n})")
        if n > max_comb_n():
            raise MathError(f"N {n} exceeds the guard {max_comb_n()}")
        return _format_factorization(sympy.factorint(n))
    if op == "modinv":
        if len(operands) != 2:
            raise ArgumentError("number modinv takes exactly A and M")
        a = _parse_int(operands[0], "A")
        m = _parse_int(operands[1], "M")
        if m <= 0:
            raise MathError("modulus M must be positive")
        try:
            return pow(a, -1, m)
        except ValueError:
            raise MathError(f"{a} has no inverse modulo {m}") from None
    if op in ("gcd", "lcm"):
        if len(operands) < 2:
            raise ArgumentError(f"number {op} takes at least two integers")
        values = [_parse_int(text, "operand") for text in operands]
        if any(v < 0 for v in values):
            raise MathError(f"{op} operands must be non-negative")
        return math.gcd(*values) if op == "gcd" else math.lcm(*values)
    raise ArgumentError(
        f"unknown number operation: {op} "
        "(expected one of isprime|nextprime|factorize|modinv|gcd|lcm)"
    )


def _format_factorization(factors: dict[int, int]) -> str:
    """Render sympy.factorint output as ``2^3*3^2*5`` (ascending bases)."""
    return "*".join(
        f"{base}^{exp}" if exp != 1 else str(base)
        for base, exp in sorted(factors.items())
    )
