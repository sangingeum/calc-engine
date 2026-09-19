"""Calculus operations via sympy: derive, integrate, limit."""

from __future__ import annotations

import sympy

from calc.errors import ArgumentError
from calc.ops.sympy_real import parse_expression, to_real


def calculus(
    op: str,
    expr: str,
    var: str,
    *,
    lower: float | None = None,
    upper: float | None = None,
    approach: float | None = None,
) -> float | str:
    """Apply a calculus operation; numeric results as float, symbolic as str."""
    if op not in ("derive", "integrate", "limit"):
        raise ArgumentError(
            f"unknown calculus operation: {op} (expected derive|integrate|limit)"
        )
    if approach is not None and op != "limit":
        raise ArgumentError("--approach is only valid for limit")
    if op == "integrate" and (lower is None) != (upper is None):
        raise ArgumentError("integrate requires both --lower and --upper, or neither")

    expression = parse_expression(expr)
    variable = sympy.Symbol(var)

    if op == "derive":
        return str(sympy.diff(expression, variable))
    if op == "integrate":
        if lower is None:
            return str(sympy.integrate(expression, variable))
        return to_real(sympy.integrate(expression, (variable, lower, upper)))
    # limit
    if approach is None:
        raise ArgumentError("limit requires --approach")
    result = sympy.limit(expression, variable, approach)
    if result.is_number:
        return to_real(result)
    return str(result)
