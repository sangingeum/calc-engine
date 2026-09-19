"""Shared input-parsing helpers for the op modules (no I/O, pure)."""

from __future__ import annotations

from calc.errors import SyntaxError_


def parse_hex_bytes(text: str) -> bytes:
    """Parse a hex byte string (case-insensitive); odd length/invalid digits
    are a SyntaxError."""
    try:
        return bytes.fromhex(text.strip())
    except ValueError:
        raise SyntaxError_(f"invalid hex byte string: {text!r}") from None
