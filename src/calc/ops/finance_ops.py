"""Financial operations mirroring numpy-financial signatures (ratified 6.3).

Strict validation: each operation requires exactly its required argument set,
nothing more, nothing less - otherwise ArgumentError. ``pmt`` uses
``--principal`` with ``--pv`` accepted as an alias (both given -> error).

Sign convention (numpy-financial, documented in README/SKILL.md): money you
invest (cash out) is NEGATIVE, money you receive (cash in) is POSITIVE —
e.g. ``fv --rate 0.05 --periods 10 --pv 1000`` is -1628.8946 because the
1000 invested today becomes 1628.89 received later.
"""

from __future__ import annotations

import json
import math

from calc.errors import ArgumentError, MathError, SyntaxError_

_REQUIREMENTS: dict[str, set[str]] = {
    "fv": {"rate", "periods", "pv"},
    "pv": {"rate", "periods", "fv"},
    "pmt": {"rate", "periods", "principal"},
    "npv": {"rate", "cashflows"},
    "irr": {"cashflows"},
    "nper": {"rate", "pmt", "pv"},
}


def _numpy_financial():
    """numpy_financial resolved lazily (cold-start: only finance pays)."""
    import numpy_financial as npf

    return npf


def _parse_cashflows(raw: str) -> list[float]:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SyntaxError_(f"invalid cashflows JSON: {exc}") from None
    if not isinstance(data, list) or len(data) < 2:
        raise SyntaxError_("cashflows must be a JSON array of >= 2 numbers")
    if any(isinstance(x, bool) or not isinstance(x, (int, float)) for x in data):
        raise SyntaxError_("cashflows must contain only numbers")
    return [float(x) for x in data]


def finance(
    op: str,
    *,
    pv: float | None = None,
    fv: float | None = None,
    rate: float | None = None,
    periods: float | None = None,
    principal: float | None = None,
    cashflows: str | None = None,
    pmt: float | None = None,
) -> float:
    """Compute fv, pv, pmt, npv, irr, or nper with exactly-required-set checks."""
    if op not in _REQUIREMENTS:
        raise ArgumentError(
            f"unknown finance operation: {op} "
            "(expected one of fv, pv, pmt, npv, irr, nper)"
        )

    # --principal aliases --pv for pmt; both together is an error.
    if op == "pmt" and principal is None and pv is not None:
        principal, pv = pv, None

    given = {
        "pv": pv,
        "fv": fv,
        "rate": rate,
        "periods": periods,
        "principal": principal,
        "cashflows": cashflows,
        "pmt": pmt,
    }
    provided = {key for key, value in given.items() if value is not None}
    required = _REQUIREMENTS[op]
    if provided != required:
        missing = sorted(required - provided)
        unexpected = sorted(provided - required)
        raise ArgumentError(
            f"finance {op} requires exactly {sorted(required)}; "
            f"missing={missing}, unexpected={unexpected}"
        )

    npf = _numpy_financial()
    if op == "fv":
        return float(npf.fv(rate, periods, pmt=0, pv=pv))
    if op == "pv":
        return float(npf.pv(rate, periods, pmt=0, fv=fv))
    if op == "pmt":
        return float(npf.pmt(rate, periods, principal))
    if op == "npv":
        flows = _parse_cashflows(cashflows or "")
        return float(npf.npv(rate, flows))
    if op == "irr":
        flows = _parse_cashflows(cashflows or "")
        result = npf.irr(flows)
        if result is None or math.isnan(float(result)):
            raise MathError("no real IRR found (cashflows never change sign)")
        return float(result)
    # nper: solve for the number of periods of an annuity (pv required-set)
    if pv is None:  # narrowed by the required-set check; defensive
        raise ArgumentError("finance nper requires --pv")
    payment = pmt if pmt is not None else 0.0
    if rate == 0:
        if payment == 0:
            raise MathError("nper undefined: zero rate requires a nonzero payment")
        return -pv / payment
    result = npf.nper(rate, pmt, pv)
    if math.isnan(float(result)) or math.isinf(float(result)):
        raise MathError("nper undefined for these parameters")
    return float(result)
