"""Expression evaluation via simpleeval - never Python eval/exec (DESIGN.md 5).

Extensions (v2 spec): special functions (erf/erfc/gamma/lgamma/comb/perm plus
abs/min/max/round), optional ``--let NAME=NUMBER`` variable binding, and
``--exact`` rational arithmetic via ``fractions.Fraction`` (R8/R11).
"""

from __future__ import annotations

import math
import operator
import re
from fractions import Fraction

from simpleeval import simple_eval

from calc.errors import ArgumentError, MathError, SyntaxError_

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
    # v2 (R8): special functions + conveniences
    "erf",
    "erfc",
    "gamma",
    "lgamma",
    "comb",
    "perm",
    "abs",
    "min",
    "max",
    "round",
)
_FUNCTIONS = {
    name: getattr(math, name)
    for name in _FUNCTION_NAMES
    if name not in ("abs", "min", "max", "round")
}
_FUNCTIONS.update(
    {
        "abs": abs,
        "min": min,
        "max": max,
        "round": round,  # banker's rounding, documented
        # gamma/lgamma: surface integral results as ints (24, not 24.0) to
        # preserve the bare-integer stdout convention for exact values.
        "gamma": lambda x: _int_if_exact(math.gamma(x)),
        "lgamma": lambda x: _int_if_exact(math.lgamma(x)),
    }
)


def _int_if_exact(value: float) -> float:
    """Return an int when the float is integral (render.py prints ints bare)."""
    if isinstance(value, float) and value.is_integer() and abs(value) < 1e15:
        return int(value)
    return value


_LET_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z_0-9]*$")
_IDENT_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z_0-9]*$")


def _parse_let_bindings(bindings: list[str] | None) -> dict[str, float]:
    """Parse ``NAME=NUMBER`` pairs; numeric literals only (safe-eval model)."""
    names: dict[str, float] = {}
    if not bindings:
        return names
    for binding in bindings:
        name, sep, value = binding.partition("=")
        if not sep:
            raise ArgumentError(
                f"invalid --let binding: {binding!r} (expected NAME=NUMBER)"
            )
        name = name.strip()
        if not _LET_PATTERN.match(name):
            raise ArgumentError(f"invalid --let name: {name!r}")
        if name in _FUNCTIONS or name in _NAMES:
            raise ArgumentError(f"--let name shadows a function/constant: {name!r}")
        try:
            parsed = float(value)
        except ValueError:
            raise ArgumentError(
                f"--let value must be a numeric literal: {value!r}"
            ) from None
        if math.isnan(parsed) or math.isinf(parsed):
            raise ArgumentError(f"--let value must be finite: {value!r}")
        if name in names:
            raise ArgumentError(f"duplicate --let name: {name!r}")
        names[name] = parsed
    return names


def evaluate(
    expr: str,
    *,
    let_bindings: list[str] | None = None,
    exact: bool = False,
) -> int | float | str | Fraction:
    """Evaluate an arithmetic expression safely; returns int or float."""
    if exact:
        return _evaluate_exact(expr)
    names = dict(_NAMES)
    names.update(_parse_let_bindings(let_bindings))
    try:
        return simple_eval(expr, functions=_FUNCTIONS, names=names)
    except ZeroDivisionError as exc:
        raise MathError(str(exc)) from None
    except (ValueError, OverflowError) as exc:
        raise MathError(str(exc)) from None
    except Exception as exc:  # noqa: BLE001 — simpleeval raises many types; all mean SyntaxError
        raise SyntaxError_(f"invalid expression: {exc}") from None


# ---------------------------------------------------------------------------
# R11: --exact (exact rational arithmetic)
# ---------------------------------------------------------------------------

_EXACT_BINOPS = {
    "+": operator.add,
    "-": operator.sub,
    "*": operator.mul,
    "/": operator.truediv,
    "//": operator.floordiv,
    "%": operator.mod,
}

_EXACT_TOKEN_PATTERN = re.compile(
    r"""\s*(?:
        (?P<ws>\s+)
      | (?P<number>\d+\.\d*|\.\d+|\d+)
      | (?P<name>[A-Za-z_][A-Za-z_0-9]*)
      | (?P<op>\*\*|//|[+\-*/%()])
    )""",
    re.VERBOSE,
)


def _tokenize_exact(expr: str) -> list[str]:
    tokens: list[str] = []
    pos = 0
    while pos < len(expr):
        match = _EXACT_TOKEN_PATTERN.match(expr, pos)
        if match is None:
            raise SyntaxError_(f"invalid expression: {expr!r}")
        pos = match.end()
        if match.lastgroup == "ws":
            continue
        tokens.append(match.group(match.lastgroup))  # type: ignore[arg-type]
    return tokens


def _parse_exact_tokens(tokens: list[str]) -> list[str]:
    """Tokenize to a postfix-ready prefix list, validating the grammar."""
    # Grammar-only validation happens in the recursive descent below.
    return tokens


class _ExactParser:
    """Recursive-descent parser for exact rational arithmetic.

    Grammar (no functions, no names — the --exact model is arithmetic only):
        expr   := term (('+'|'-') term)*
        term   := unary (('*'|'/'|'//'|'%') unary)*
        unary  := ('+'|'-') unary | power
        power  := atom ('**' unary)?
        atom   := NUMBER | '(' expr ')'
    """

    def __init__(self, tokens: list[str]) -> None:
        self.tokens = tokens
        self.pos = 0

    def peek(self) -> str | None:
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None

    def next(self) -> str:
        token = self.peek()
        if token is None:
            raise SyntaxError_("invalid expression: unexpected end of input")
        self.pos += 1
        return token

    def parse(self) -> Fraction:
        value = self.expr()
        if self.peek() is not None:
            raise SyntaxError_(f"invalid expression: unexpected {self.peek()!r}")
        return value

    def expr(self) -> Fraction:
        value = self.term()
        while self.peek() in ("+", "-"):
            op = self.next()
            rhs = self.term()
            if op == "+":
                value += rhs
            else:
                value -= rhs
        return value

    def term(self) -> Fraction:
        value = self.unary()
        while self.peek() in ("*", "/", "//", "%"):
            op = self.next()
            rhs = self.unary()
            if op == "*":
                value *= rhs
            elif op == "/":
                if rhs == 0:
                    raise MathError("division by zero")
                value /= rhs
            elif op == "//":
                if rhs == 0:
                    raise MathError("division by zero")
                floored = value // rhs
                value = Fraction(floored)
            else:
                if rhs == 0:
                    raise MathError("division by zero")
                value %= rhs
        return value

    def unary(self) -> Fraction:
        if self.peek() in ("+", "-"):
            op = self.next()
            value = self.unary()
            return value if op == "+" else -value
        return self.power()

    def power(self) -> Fraction:
        base = self.atom()
        if self.peek() == "**":
            self.next()
            exponent = self.unary()  # right-associative
            return self._pow(base, exponent)
        return base

    @staticmethod
    def _pow(base: Fraction, exponent: Fraction) -> Fraction:
        if exponent.denominator != 1:
            raise MathError("result not exactly representable: non-integer exponent")
        exp = int(exponent)
        try:
            result = base**exp
        except (ZeroDivisionError, OverflowError) as exc:
            raise MathError(str(exc)) from None
        return result

    def atom(self) -> Fraction:
        token = self.next()
        if token == "(":
            value = self.expr()
            if self.next() != ")":
                raise SyntaxError_("invalid expression: expected ')'")
            return value
        if re.fullmatch(r"\d+\.\d*|\.\d+|\d+", token):
            return Fraction(token)
        raise SyntaxError_(f"invalid expression: unexpected {token!r}")


def _evaluate_exact(expr: str) -> Fraction:
    """Exact rational evaluation; rendered by render.py via Fraction.__str__."""
    for token in _tokenize_exact(expr):
        if _IDENT_PATTERN.fullmatch(token):
            raise MathError(
                "result not exactly representable: names ineligible in --exact mode"
            )
    return _ExactParser(_tokenize_exact(expr)).parse()
