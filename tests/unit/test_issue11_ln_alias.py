"""GitHub issue 11: `eval` gains `ln` as a natural-log alias of `log`.

The `calculus` and `sym` surfaces already accept `ln` (via sympy); `eval`
(simpleeval) exposed only `log`. Both now resolve to the natural logarithm,
so all expression surfaces agree.
"""

from __future__ import annotations

import math

import pytest

from calc.errors import ArgumentError, MathError
from calc.ops import eval_ops


def test_ln_value() -> None:
    assert eval_ops.evaluate("ln(2)") == pytest.approx(math.log(2))
    assert eval_ops.evaluate("ln(e)") == pytest.approx(1.0)


def test_ln_is_alias_of_log() -> None:
    for value in (0.5, 1, 2, 10, 1234.5):
        assert eval_ops.evaluate(f"ln({value})") == pytest.approx(
            eval_ops.evaluate(f"log({value})")
        )


def test_ln_and_log_share_implementation() -> None:
    assert eval_ops._FUNCTIONS["ln"] is eval_ops._FUNCTIONS["log"]
    assert "ln" in eval_ops._FUNCTION_NAMES


@pytest.mark.parametrize("expr", ["ln(0)", "ln(-1)"])
def test_ln_invalid_domain_is_math_error(expr: str) -> None:
    with pytest.raises(MathError):
        eval_ops.evaluate(expr)


def test_ln_cannot_be_shadowed_by_let() -> None:
    with pytest.raises(ArgumentError):
        eval_ops.evaluate("ln(2)", let_bindings=["ln=1"])
