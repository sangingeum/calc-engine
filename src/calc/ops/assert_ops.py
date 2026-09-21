"""``assert`` command: lightweight deterministic assertion layer (spec §15).

Success prints ``true`` (bool -> int 1 is suppressed; we return the bool and
render.py maps it to ``true``/``false`` — actually the house render maps bool
to ``0/1``; we therefore return the string "true"/"false" directly so stdout
matches the spec examples byte-exactly).

Conventions:
- approx: |actual - expected| <= atol + rtol * |expected| (NumPy allclose form);
- between: inclusive endpoints;
- sign: positive | negative | zero | nonnegative | nonpositive;
- failure is a domain failure: one ``AssertionError: ...`` line on stderr,
  exit 1, no stdout.
"""

from __future__ import annotations

import math

from calc.errors import ArgumentError, SyntaxError_

_SIGNS = ("positive", "negative", "zero", "nonnegative", "nonpositive")


class AssertionError_(SyntaxError_):
    """Failed assertion: stderr prefix ``AssertionError``."""

    prefix = "AssertionError"


def _parse_float(token: str, what: str) -> float:
    try:
        return float(token)
    except ValueError:
        raise SyntaxError_(f"{what} must be a number (got {token!r})") from None


def assert_command(op: str, values: list[str], atol: float = 1e-6, rtol: float = 1e-6) -> str:
    """Dispatch an assertion; returns the literal string 'true' on success."""
    if op == "approx":
        if len(values) != 2:
            raise ArgumentError("assert approx takes exactly ACTUAL and EXPECTED")
        actual = _parse_float(values[0], "actual")
        expected = _parse_float(values[1], "expected")
        if not math.isfinite(actual) or not math.isfinite(expected):
            raise AssertionError_("approx operands must be finite")
        if abs(actual - expected) <= atol + rtol * abs(expected):
            return "true"
        raise AssertionError_(
            f"{actual!r} not approx {expected!r} within atol={atol}, rtol={rtol}"
        )
    if op == "equal":
        if len(values) != 2:
            raise ArgumentError("assert equal takes exactly 2 values")
        a = _parse_float(values[0], "first")
        b = _parse_float(values[1], "second")
        if a == b:
            return "true"
        raise AssertionError_(f"{a!r} != {b!r}")
    if op == "between":
        if len(values) != 3:
            raise ArgumentError("assert between takes exactly VALUE LOW HIGH")
        value = _parse_float(values[0], "value")
        low = _parse_float(values[1], "low")
        high = _parse_float(values[2], "high")
        if not low <= high:
            raise ArgumentError("between requires low <= high")
        if low <= value <= high:  # inclusive endpoints (documented)
            return "true"
        raise AssertionError_(f"{value!r} not between {low!r} and {high!r} (inclusive)")
    if op == "sign":
        if len(values) != 2:
            raise ArgumentError("assert sign takes exactly VALUE SIGN")
        value = _parse_float(values[0], "value")
        sign = values[1]
        if sign not in _SIGNS:
            raise ArgumentError(f"unknown sign: {sign} (expected one of {', '.join(_SIGNS)})")
        ok = {
            "positive": value > 0,
            "negative": value < 0,
            "zero": value == 0,
            "nonnegative": value >= 0,
            "nonpositive": value <= 0,
        }[sign]
        if ok:
            return "true"
        raise AssertionError_(f"{value!r} is not {sign}")
    if op == "abs-lt":
        if len(values) != 2:
            raise ArgumentError("assert abs-lt takes exactly 2 values")
        a = _parse_float(values[0], "first")
        b = _parse_float(values[1], "threshold")
        if abs(a) < abs(b):
            return "true"
        raise AssertionError_(f"|{a!r}| not < |{b!r}|")
    if op == "abs-gt":
        if len(values) != 2:
            raise ArgumentError("assert abs-gt takes exactly 2 values")
        a = _parse_float(values[0], "first")
        b = _parse_float(values[1], "threshold")
        if abs(a) > abs(b):
            return "true"
        raise AssertionError_(f"|{a!r}| not > |{b!r}|")
    raise ArgumentError(
        f"unknown assert operation: {op} "
        "(expected one of approx|equal|between|sign|abs-lt|abs-gt)"
    )
