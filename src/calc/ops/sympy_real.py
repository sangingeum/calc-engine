"""Shared sympy helpers: expression parsing and real-number extraction.

Ratified (6.8): inf/-inf/nan pass through as floats; zoo/complex results
raise MathError (not representable as a real number).
"""

from __future__ import annotations

import math
import tokenize

import sympy
from sympy.parsing.sympy_parser import (
    convert_xor,
    implicit_multiplication_application,
    parse_expr,
    standard_transformations,
)

from calc.errors import MathError, SyntaxError_

_TRANSFORMATIONS = standard_transformations + (
    implicit_multiplication_application,
    convert_xor,
)


def parse_expression(expr: str) -> sympy.Expr:
    """Parse a math expression string into a sympy expression."""
    try:
        return parse_expr(expr, transformations=_TRANSFORMATIONS, evaluate=True)
    except (SyntaxError, TypeError, ValueError, AttributeError, tokenize.TokenError) as exc:
        raise SyntaxError_(f"invalid expression: {exc}") from None


def to_real(expr: sympy.Expr) -> float:
    """Convert a sympy result to a float, enforcing the real-number policy."""
    if expr is sympy.nan:
        return math.nan
    if expr == sympy.oo:
        return math.inf
    if expr == -sympy.oo:
        return -math.inf
    if not expr.is_number:
        raise MathError(f"result is symbolic, not a number: {expr}")
    if not expr.is_real:
        raise MathError("result is not a real number")
    return float(expr)
