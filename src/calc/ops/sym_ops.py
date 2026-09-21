"""Symbolic equivalence / simplify / expand (R10): the ``sym`` subcommand.

Real domain only, via the shared restricted sympy parsing path
(``sympy_real.parse_expression`` — never ``sympify`` on unrestricted input).

- Symbols must be declared with ``--var``; undeclared symbols => SyntaxError.
- Decimal literals are parsed as EXACT RATIONALS (0.35 -> 7/20) so decimal
  identities hold exactly instead of leaving float residues.
- equiv prints ``true`` iff simplify(E1 - E2) == 0; ``false`` iff provably
  non-zero (non-zero constant, or differs by > 1e-9 at any point of the
  fixed rational test-point grid below); otherwise MathError: undecided.
  Fixed grid, no randomness (INV-5).
"""

from __future__ import annotations

import types
from fractions import Fraction

import sympy

from calc.errors import ArgumentError, MathError, SyntaxError_
from calc.ops.sympy_real import parse_expression

# Fixed, documented rational test points for the numeric equiv fallback
# (ratified in DESIGN.md; no randomness — INV-5).
_EQUIV_TEST_POINTS = (
    Fraction(1, 2),
    Fraction(-1, 3),
    Fraction(7, 5),
    Fraction(3),
    Fraction(-2),
    Fraction(11, 13),
    Fraction(1, 100),
)

_EQUIV_TOLERANCE = 1e-9


def _declared_vars(args: types.SimpleNamespace) -> dict[str, sympy.Symbol]:
    """Build {name: Symbol} from the repeatable --var flags."""
    names = args.var or []
    seen: dict[str, sympy.Symbol] = {}
    for name in names:
        if not name.isidentifier():
            raise SyntaxError_(f"invalid --var name: {name!r}")
        if name in seen:
            raise SyntaxError_(f"duplicate --var: {name!r}")
        seen[name] = sympy.Symbol(name, real=True)
    return seen


def _parse_with_rationals(
    expr: str, vars_: dict[str, sympy.Symbol]
) -> sympy.Expr:
    """Parse with declared symbols; decimal literals become exact rationals.

    Implemented by rewriting decimal literals to exact rational Ratios before
    the standard parse path: sympy's ``rationalize`` parse step is not in our
    restricted transformation set, so we pre-convert tokens ourselves.
    """
    import re

    def _sub(match: re.Match[str]) -> str:
        text = match.group(0)
        if text.startswith("."):
            text = "0" + text
        # exact rational, e.g. 0.35 -> Rational(35,100) via Fraction
        frac = Fraction(text)
        return f"Rational({frac.numerator},{frac.denominator})"

    rewritten = re.sub(r"(?<![\w.])(\d+\.\d*|\.\d+)(?![\w.])", _sub, expr)
    parsed = parse_expression(rewritten)
    # The shared parse path creates assumptions-free symbols; substitute the
    # declared (real) symbols for them so the caller's declarations apply.
    rename = {
        sym: vars_[name]
        for name, sym in (
            (name, sympy.Symbol(name)) for name in vars_
        )
        if sym in parsed.free_symbols
    }
    if rename:
        parsed = parsed.xreplace(rename)
    free = {str(s) for s in parsed.free_symbols}
    undeclared = free - set(vars_)
    if undeclared:
        raise SyntaxError_(
            f"undeclared symbol(s): {', '.join(sorted(undeclared))} (declare with --var)"
        )
    return parsed


def sym_command(args: types.SimpleNamespace) -> str:
    """Dispatch the ``sym`` subcommand."""
    op = args.op
    vars_ = _declared_vars(args)
    if op == "equiv":
        if len(args.exprs) != 2:
            raise ArgumentError("sym equiv takes exactly 2 expressions")
        return _equiv(args.exprs[0], args.exprs[1], vars_)
    if op == "simplify":
        if len(args.exprs) != 1:
            raise ArgumentError("sym simplify takes exactly 1 expression")
        return _stringify(sympy.simplify(_parse_with_rationals(args.exprs[0], vars_)))
    if op == "expand":
        if len(args.exprs) != 1:
            raise ArgumentError("sym expand takes exactly 1 expression")
        return _stringify(sympy.expand(_parse_with_rationals(args.exprs[0], vars_)))
    raise ArgumentError(f"unknown sym operation: {op} (expected equiv|simplify|expand)")


def _stringify(expr: sympy.Expr) -> str:
    """sympy-style string like ``calculus`` prints (str of the expression)."""
    return str(expr)


def _equiv(expr1: str, expr2: str, vars_: dict[str, sympy.Symbol]) -> str:
    diff = sympy.simplify(
        _parse_with_rationals(expr1, vars_) - _parse_with_rationals(expr2, vars_)
    )
    if diff == 0:
        return "true"
    if diff.is_number and diff.is_real:
        # provably non-zero constant
        return "false"
    if not vars_:
        # fully numeric and simplified to non-zero — covered above
        return "false"
    # Numeric probe on the fixed rational grid (deterministic).
    import math

    for point in _EQUIV_TEST_POINTS:
        try:
            value = float(
                diff.subs(
                    {
                        sym: sympy.Rational(point.numerator, point.denominator)
                        for sym in vars_.values()
                    }
                )
            )
        except (TypeError, ValueError):
            continue
        if math.isnan(value):
            continue
        if abs(value) > _EQUIV_TOLERANCE:
            return "false"
    # Every grid point agrees within tolerance; ask sympy for a proof.
    zero_proof = diff.is_zero
    if zero_proof is True:
        return "true"
    if zero_proof is False:
        return "false"
    raise MathError("undecided: difference is neither provably zero nor non-zero")
