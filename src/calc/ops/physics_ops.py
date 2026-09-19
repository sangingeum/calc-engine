"""Physics: scipy.constants lookups + sympy equation solving.

Equation registry (ratified for v1 - the registry, not sympy heuristics,
decides solvability):

- kinematics:
    d = v0*t + a*t^2/2
    v = v0 + a*t
    v^2 = v0^2 + 2*a*d
- force:
    F = m*a
- energy:
    KE = m*v^2/2
    W  = F*d
    PE = m*g*h   (g optional, defaults to 9.80665)
"""

from __future__ import annotations

import sympy
from scipy import constants

from calc.errors import ArgumentError, MathError, UnitError

_G_DEFAULT = 9.80665
_SYMBOL_NAMES = ("d", "v0", "v", "a", "t", "F", "m", "KE", "W", "PE", "g", "h")


def _registry() -> dict[str, list[tuple[sympy.Eq, frozenset[str]]]]:
    d, v0, v, a, t, F, m, KE, W, PE, g, h = sympy.symbols(" ".join(_SYMBOL_NAMES))
    return {
        "kinematics": [
            (sympy.Eq(d, v0 * t + a * t**2 / 2), frozenset(("d", "v0", "t", "a"))),
            (sympy.Eq(v, v0 + a * t), frozenset(("v", "v0", "t", "a"))),
            (sympy.Eq(v**2, v0**2 + 2 * a * d), frozenset(("v", "v0", "a", "d"))),
        ],
        "force": [
            (sympy.Eq(F, m * a), frozenset(("F", "m", "a"))),
        ],
        "energy": [
            (sympy.Eq(KE, m * v**2 / 2), frozenset(("KE", "m", "v"))),
            (sympy.Eq(W, F * d), frozenset(("W", "F", "d"))),
            (sympy.Eq(PE, m * g * h), frozenset(("PE", "m", "g", "h"))),
        ],
    }


def constant(symbol: str) -> float:
    """Look up a physical constant by attribute name in scipy.constants."""
    try:
        value = getattr(constants, symbol)
    except AttributeError:
        raise UnitError(f"unknown physical constant: {symbol}") from None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise MathError(f"constant {symbol!r} is not a numeric scalar")
    return float(value)


def solve(domain: str, target: str, kwargs: dict[str, float]) -> float:
    """Solve a registered domain equation for ``target``.

    Candidate equations are those containing the target where every other
    symbol is provided in ``kwargs`` (``g`` defaults to 9.80665 when absent).
    Ambiguity (multiple candidate equations) is an ArgumentError; multiple
    solutions resolve to the first positive real solution, else the first.
    """
    registry = _registry()
    if domain not in registry:
        raise ArgumentError(
            f"unknown physics domain: {domain} (expected one of {', '.join(registry)})"
        )
    unknown = set(kwargs) - set(_SYMBOL_NAMES)
    if unknown:
        raise ArgumentError(f"unknown symbol(s) for domain {domain}: {sorted(unknown)}")

    all_targets: set[str] = set()
    for _, symbols in registry[domain]:
        all_targets |= symbols
    if target not in all_targets:
        raise ArgumentError(f"solve target {target!r} is not a symbol in domain {domain!r}")

    effective_kwargs = dict(kwargs)
    if target != "g" and "g" in all_targets:
        effective_kwargs.setdefault("g", _G_DEFAULT)

    candidates = [
        (equation, symbols)
        for equation, symbols in registry[domain]
        if target in symbols and (symbols - {target}) <= effective_kwargs.keys()
    ]
    if not candidates:
        raise ArgumentError(
            f"insufficient knowns to solve {target!r} in {domain!r}; "
            f"provide all other symbols of one equation"
        )
    if len(candidates) > 1:
        raise ArgumentError(f"ambiguous target {target!r}: multiple equations can solve it")

    equation, _ = candidates[0]
    substitution = {
        sympy.Symbol(name): value
        for name, value in effective_kwargs.items()
        if name != target
    }
    solutions = sympy.solve(equation.subs(substitution), sympy.Symbol(target))
    return _pick(solutions, target)


def _pick(solutions: list[sympy.Expr], target: str) -> float:
    numeric = [s for s in solutions if s.is_number]
    if not numeric:
        raise MathError(f"no numeric solution for {target!r}")
    reals = [s for s in numeric if s.is_real]
    pool = reals or numeric
    if len(pool) > 1:
        positive = [s for s in pool if s > 0]
        if positive:
            pool = positive
    return float(pool[0])
