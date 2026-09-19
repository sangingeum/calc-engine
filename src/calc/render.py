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


def render(result: object, precision: int = 4) -> str:
    """Render a computed result to its exact stdout string."""
    precision = max(0, int(precision))
    if isinstance(result, str):
        return result
    if isinstance(result, bool):  # defensive; booleans never reach stdout
        return str(int(result))
    if isinstance(result, int):
        return str(result)
    if isinstance(result, float):
        return _format_float(result, precision)
    if isinstance(result, Sequence):
        return "[" + ",".join(render(item, precision) for item in result) + "]"
    return str(result)


def _format_float(value: float, precision: int) -> str:
    if math.isnan(value):
        return "nan"
    if math.isinf(value):
        return "inf" if value > 0 else "-inf"
    return f"{value:.{precision}f}"
