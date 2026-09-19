"""Financial operations mirroring numpy-financial signatures (ratified 6.3).

Strict validation: each operation requires exactly its required argument set,
nothing more, nothing less - otherwise ArgumentError. ``pmt`` uses
``--principal`` with ``--pv`` accepted as an alias (both given -> error).
"""

from __future__ import annotations

import numpy_financial as npf

from calc.errors import ArgumentError

_REQUIREMENTS: dict[str, set[str]] = {
    "fv": {"rate", "periods", "pv"},
    "pv": {"rate", "periods", "fv"},
    "pmt": {"rate", "periods", "principal"},
}


def finance(
    op: str,
    *,
    pv: float | None = None,
    fv: float | None = None,
    rate: float | None = None,
    periods: float | None = None,
    principal: float | None = None,
) -> float:
    """Compute fv, pv, or pmt with exactly-required-set validation."""
    if op not in _REQUIREMENTS:
        raise ArgumentError(f"unknown finance operation: {op} (expected one of fv, pv, pmt)")

    # --principal aliases --pv for pmt; both together is an error.
    if op == "pmt" and principal is None and pv is not None:
        principal, pv = pv, None

    given = {"pv": pv, "fv": fv, "rate": rate, "periods": periods, "principal": principal}
    provided = {key for key, value in given.items() if value is not None}
    required = _REQUIREMENTS[op]
    if provided != required:
        missing = sorted(required - provided)
        unexpected = sorted(provided - required)
        raise ArgumentError(
            f"finance {op} requires exactly {sorted(required)}; "
            f"missing={missing}, unexpected={unexpected}"
        )

    if op == "fv":
        return float(npf.fv(rate, periods, pmt=0, pv=pv))
    if op == "pv":
        return float(npf.pv(rate, periods, pmt=0, fv=fv))
    return float(npf.pmt(rate, periods, principal))
