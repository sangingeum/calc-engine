"""Unit conversion via pint (offset units like degC/degF handled correctly)."""

from __future__ import annotations

import pint

from calc.errors import SyntaxError_, UnitError

_UREG = pint.UnitRegistry()


def convert(value: float, src: str, dst: str) -> float:
    """Convert a value between units; returns the float magnitude."""
    try:
        quantity = _UREG.Quantity(float(value), src)
        result = quantity.to(dst)
    except ValueError as exc:
        raise SyntaxError_(f"invalid numeric value: {exc}") from None
    except (pint.UndefinedUnitError, pint.DimensionalityError) as exc:
        raise UnitError(str(exc)) from None
    return float(result.magnitude)
