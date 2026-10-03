"""Resource guards: result/argument/input limits (CalcError taxonomy).

Single source of truth for every compute-side cap; each constant is
overridable by an environment variable (``CALC_MAX_RESULT_DIGITS``,
``CALC_MAX_FACTORIAL_ARG``, ``CALC_MAX_COMB_N``, ``CALC_TIMEOUT_SECONDS``)
so a host with different resources can raise/lower the bars without code
changes. All values are plain ints/floats; the guards are checked BEFORE a
computation starts so a pathological request is rejected in microseconds.
"""

from __future__ import annotations

import os
import signal
import sys
from contextlib import suppress

from calc.errors import LimitError

_DEFAULT_MAX_RESULT_DIGITS = 100_000
_DEFAULT_MAX_FACTORIAL_ARG = 20_000
_DEFAULT_MAX_COMB_N = 100_000
_DEFAULT_TIMEOUT_SECONDS = 10.0
_DEFAULT_MAX_EXPRESSION_CHARS = 10_000


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def max_result_digits() -> int:
    """Largest integer the renderer may stringify."""
    return _env_int("CALC_MAX_RESULT_DIGITS", _DEFAULT_MAX_RESULT_DIGITS)


def max_factorial_arg() -> int:
    """Largest n accepted by factorial(n)/gamma/comb/perm computations."""
    return _env_int("CALC_MAX_FACTORIAL_ARG", _DEFAULT_MAX_FACTORIAL_ARG)


def max_comb_n() -> int:
    """Largest first argument accepted by comb/perm."""
    return _env_int("CALC_MAX_COMB_N", _DEFAULT_MAX_COMB_N)


def timeout_seconds() -> float:
    """Default compute timeout in seconds (0 disables the guard)."""
    return _env_float("CALC_TIMEOUT_SECONDS", _DEFAULT_TIMEOUT_SECONDS)


def max_expression_chars() -> int:
    """Largest single expression/statement accepted by eval/batch."""
    return _env_int("CALC_MAX_EXPRESSION_CHARS", _DEFAULT_MAX_EXPRESSION_CHARS)


def apply_digit_limit() -> None:
    """Raise CPython's int->str cap to our documented result-digit limit.

    The interpreter's 4300-digit default makes `str()` of large exact values
    fail inside rendering; our own cap (100000, env-overridable) is the
    contract instead, and render-time overflow maps to LimitError.
    """
    limit = max_result_digits()
    with suppress(ValueError, AttributeError):  # pre-3.11 / unusual builds
        sys.set_int_max_str_digits(limit)


def check_factorial(n: int) -> None:
    """Reject a factorial-sized argument before computing."""
    if n > max_factorial_arg():
        raise LimitError(f"factorial argument {n} exceeds {max_factorial_arg()}")


def check_comb(n: int, k: int) -> None:
    """Reject comb/perm arguments that would produce huge results."""
    if n > max_comb_n():
        raise LimitError(f"comb/perm n={n} exceeds {max_comb_n()}")
    if n > max_factorial_arg():
        # k near n still factors through n! internally in many backends;
        # cap conservatively the same way.
        raise LimitError(
            f"comb/perm n={n} exceeds the factorial guard {max_factorial_arg()}"
        )


class _TimeoutError_(BaseException):
    """Internal signal raised by the timeout handler (never user-visible)."""


def start_timeout(seconds: float) -> float | None:
    """Arm the wall-clock guard; returns the elapsed-budget (0 disables)."""
    if seconds <= 0:
        return None
    if not hasattr(signal, "setitimer"):  # pragma: no cover - non-POSIX
        return None
    signal.signal(signal.SIGALRM, _timeout_handler)
    signal.setitimer(signal.ITIMER_REAL, seconds)
    return seconds


def stop_timeout() -> None:
    """Disarm the guard (must run on every exit path, success or failure)."""
    if hasattr(signal, "setitimer"):
        signal.setitimer(signal.ITIMER_REAL, 0)


def _timeout_handler(signum: int, frame: object) -> None:  # noqa: ARG001
    raise _TimeoutError_("timeout")


def check_timeout(seconds: float | None, elapsed_label: str = "10s") -> None:
    """Map a fired timeout to the user-facing LimitError."""
    if seconds is not None:
        raise LimitError(f"timed out after {seconds:g}s")
    raise LimitError(f"timed out after {elapsed_label}")
