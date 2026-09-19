"""Expression evaluation via simpleeval - never Python eval/exec (DESIGN.md 5)."""

from __future__ import annotations

import math

from simpleeval import simple_eval

from calc.errors import MathError, SyntaxError_

_NAMES = {"pi": math.pi, "tau": math.tau, "e": math.e}

_FUNCTION_NAMES = (
    "sqrt",
    "sin",
    "cos",
    "tan",
    "asin",
    "acos",
    "atan",
    "atan2",
    "sinh",
    "cosh",
    "tanh",
    "log",
    "log2",
    "log10",
    "log1p",
    "exp",
    "expm1",
    "pow",
    "fabs",
    "floor",
    "ceil",
    "trunc",
    "factorial",
    "gcd",
    "lcm",
    "hypot",
    "degrees",
    "radians",
    "isqrt",
    "cbrt",
)
_FUNCTIONS = {name: getattr(math, name) for name in _FUNCTION_NAMES}


def evaluate(expr: str) -> int | float:
    """Evaluate an arithmetic expression safely; returns int or float."""
    try:
        return simple_eval(expr, functions=_FUNCTIONS, names=_NAMES)
    except ZeroDivisionError as exc:
        raise MathError(str(exc)) from None
    except (ValueError, OverflowError) as exc:
        raise MathError(str(exc)) from None
    except Exception as exc:  # noqa: BLE001 — simpleeval raises many types; all mean SyntaxError
        raise SyntaxError_(f"invalid expression: {exc}") from None
