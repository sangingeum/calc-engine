"""``check`` command: expression-evaluating assertion (QA-gate one-call).

Difference from ``assert``: operands are full eval expressions, not numeric
literals. Prints ``true`` or ``false``; a negative answer is a VALID result
(exit 0) unless ``--strict`` is given, in which case a false check is a
domain failure (stderr ``CheckFailed: ...``, exit 1).
"""

from __future__ import annotations

from calc.errors import ArgumentError
from calc.ops.eval_ops import evaluate


class CheckFailedError_(ArgumentError):
    """Failed strict check: stderr prefix ``CheckFailed``."""

    prefix = "CheckFailed"


def check(
    actual_expr: str,
    expected_expr: str,
    *,
    atol: float = 1e-9,
    rtol: float = 1e-9,
    strict: bool = False,
) -> str:
    """Compare two evaluated expressions; returns the literal true/false."""
    actual = _as_number(evaluate(actual_expr), "--actual")
    expected = _as_number(evaluate(expected_expr), "--expected")
    ok = abs(actual - expected) <= atol + rtol * abs(expected)
    if ok:
        return "true"
    if strict:
        raise CheckFailedError_(f"actual={actual!r} expected={expected!r}")
    return "false"


def _as_number(value: object, flag: str) -> float:
    if isinstance(value, bool):
        return float(value)
    if isinstance(value, (int, float)):
        return float(value)
    raise ArgumentError(f"{flag} must evaluate to a number")
