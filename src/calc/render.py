"""Result rendering: value -> exact stdout string (cli.py is the sole writer).

Rules (DESIGN.md 3.2):
- floats render with fixed ``precision`` decimal places; no locale dependence;
- inf/-inf/nan pass through as literal inf / -inf / nan (ratified 6.8);
- integers render bare; booleans never appear on stdout;
- lists (vectors/matrices) render as nested JSON-like brackets, no spaces;
- strings (convert-base, symbolic sympy output) render as-is.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from fractions import Fraction

from calc.errors import LimitError
from calc.limits import max_result_digits


def render(result: object, precision: int = 4) -> str:
    """Render a computed result to its exact stdout string."""
    precision = max(0, int(precision))
    if isinstance(result, str):
        return result
    if isinstance(result, bool):  # defensive; booleans never reach stdout
        return str(int(result))
    if isinstance(result, Fraction):  # R11 --exact: integer or p/q in lowest terms
        return _render_exact(result)
    if isinstance(result, int):
        return _render_int(result)
    if isinstance(result, float):
        return _format_float(result, precision)
    if isinstance(result, Sequence):
        return "[" + ",".join(render(item, precision) for item in result) + "]"
    return str(result)


def _render_exact(value: Fraction) -> str:
    """Render an exact Fraction; huge numerators map to LimitError (not raw)."""
    return _render_int_str(value.numerator) + (
        "/" + _render_int_str(value.denominator) if value.denominator != 1 else ""
    )


def _render_int(value: int) -> str:
    return _render_int_str(value)


def _render_int_str(value: int) -> str:
    """str() with the digit-limit guard: overflow is a LimitError, never raw."""
    try:
        return str(value)
    except ValueError:
        raise LimitError(
            f"result exceeds {max_result_digits()} digits"
        ) from None


def _format_float(value: float, precision: int) -> str:
    if math.isnan(value):
        return "nan"
    if math.isinf(value):
        return "inf" if value > 0 else "-inf"
    # Fixed-point only where precision decimal places are meaningful; general
    # format elsewhere keeps --precision as significant digits instead of
    # collapsing small/large magnitudes to 0.0000.
    # Band: exact 0, or |x| in [1e-4, 1e16). Nonzero values below 1e-4 would
    # zero out at precision 4; above 1e16 fixed-point would render a 17-digit
    # integer string.
    if value == 0 or 1e-4 <= abs(value) < 1e16:
        return f"{value:.{precision}f}"
    return f"{value:.{precision}g}"
