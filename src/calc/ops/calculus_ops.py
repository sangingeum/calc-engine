"""Calculus operations via sympy: derive, integrate, limit."""

from __future__ import annotations

import sympy

from calc.errors import ArgumentError, MathError
from calc.ops.sympy_real import parse_expression, to_real


def calculus(
    op: str,
    expr: str,
    var: str,
    *,
    lower: float | None = None,
    upper: float | None = None,
    approach: float | None = None,
    direction: str = "both",
) -> float | str:
    """Apply a calculus operation; numeric results as float, symbolic as str."""
    if op not in ("derive", "integrate", "limit"):
        raise ArgumentError(
            f"unknown calculus operation: {op} (expected derive|integrate|limit)"
        )
    if approach is not None and op != "limit":
        raise ArgumentError("--approach is only valid for limit")
    if direction != "both" and op != "limit":
        raise ArgumentError("--dir is only valid for limit")
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
    if direction == "both":
        # sympy's limit() defaults to dir='+', silently presenting a one-sided
        # limit as the answer. A two-sided limit exists only when both sides
        # agree (MathError otherwise).
        left = sympy.limit(expression, variable, approach, dir="-")
        right = sympy.limit(expression, variable, approach, dir="+")
        if left == right:
            result = left
        else:
            raise MathError(
                "limit does not exist (left="
                f"{_limit_text(left)}, right={_limit_text(right)})"
            )
    else:
        result = sympy.limit(
            expression, variable, approach, dir="+" if direction == "+" else "-"
        )
    if result.is_number:
        return to_real(result)
    return str(result)


def _limit_text(value: sympy.Expr) -> str:
    """Human-readable side value for the limit-does-not-exist message."""
    if value == sympy.oo:
        return "oo"
    if value == -sympy.oo:
        return "-oo"
    return str(value)
