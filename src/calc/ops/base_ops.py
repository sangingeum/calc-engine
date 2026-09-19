"""Integer base conversion.

Ratified semantics (6.1): integer-only, bare digit strings, case-insensitive
input, lowercase output, negatives via leading sign, fractional input ->
MathError. Bases: bin/oct/dec/hex names or any integer 2..36.
"""

from __future__ import annotations

from calc.errors import ArgumentError, MathError, SyntaxError_

_DIGITS = "0123456789abcdefghijklmnopqrstuvwxyz"
_BASE_NAMES = {"bin": 2, "oct": 8, "dec": 10, "hex": 16}


def _resolve_base(spec: str) -> int:
    if spec in _BASE_NAMES:
        return _BASE_NAMES[spec]
    try:
        base = int(spec)
    except ValueError:
        raise ArgumentError(
            f"invalid base: {spec!r} (expected bin|oct|dec|hex or 2..36)"
        ) from None
    if not 2 <= base <= 36:
        raise ArgumentError(f"base out of range: {base} (expected 2..36)")
    return base


def _to_base(number: int, base: int) -> str:
    if number == 0:
        return "0"
    sign = "-" if number < 0 else ""
    number = abs(number)
    digits = []
    while number:
        digits.append(_DIGITS[number % base])
        number //= base
    return sign + "".join(reversed(digits))


def convert(value: str, from_base: str, to_base: str) -> str:
    """Convert an integer between bases; returns the lowercase digit string."""
    source = _resolve_base(from_base)
    target = _resolve_base(to_base)
    text = value.strip().lower()
    if "." in text:
        raise MathError("fractional values are not supported in base conversion")
    sign = ""
    if text[:1] in "+-":
        sign = "-" if text[0] == "-" else ""
        text = text[1:]
    if not text:
        raise SyntaxError_("empty value")
    valid = _DIGITS[:source]
    for char in text:
        if char not in valid:
            raise SyntaxError_(f"invalid digit {char!r} for base {source}")
    number = int(text, source)
    return _to_base(-number if sign == "-" else number, target)
