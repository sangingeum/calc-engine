"""Error taxonomy for calc-engine.

Every failure path in the domain modules raises one of these; cli.py maps the
class to its stderr prefix via the class-level ``prefix`` attribute so raise
sites never build error strings by hand. Class names deliberately differ from
the built-ins so we never shadow SyntaxError/ValueError.
"""

from __future__ import annotations


class CalcError(Exception):
    """Base class for all calc-engine domain errors; never raised directly."""

    prefix = "MathError"

    def __init__(self, message: str) -> None:
        super().__init__(message)


class MathError(CalcError):
    """Invalid math: division by zero, bad matrix dimensions, singular inverse."""

    prefix = "MathError"


class SyntaxError_(CalcError):
    """Bad input formatting: unparseable expression, invalid JSON, bad digits."""

    prefix = "SyntaxError"


class UnitError(CalcError):
    """Unsupported unit or unknown physical constant (stderr prefix: ValueError)."""

    prefix = "ValueError"


class ArgumentError(CalcError):
    """Missing/extra arguments or an unknown operation choice."""

    prefix = "ArgumentError"
