"""Fixed-width integer operations (bits) and byte-order conversions (endian).

--width is required for every value->value operation (8|16|32|64); omitting it
or passing an unsupported width is an ArgumentError (plan: "A silently applied
default would make it easy for the agent to assume 32 bits"). Integers accept
0x/0b/decimal with an optional sign; a value that does not fit the width is a
MathError. Default output is decimal; --format hex|bin renders lowercase,
zero-padded, no prefix (like convert-base).
"""

from __future__ import annotations

import struct
from typing import Literal, cast

from calc.errors import ArgumentError, MathError, SyntaxError_
from calc.ops.parse_utils import parse_hex_bytes

_WIDTHS: tuple[int, ...] = (8, 16, 32, 64)

_UNARY_OPS = frozenset({"not", "popcount", "clz", "ctz", "to-signed", "to-unsigned"})
_BINARY_OPS = frozenset({"and", "or", "xor", "shl", "shr", "sar", "rol", "ror"})
_OPS = _UNARY_OPS | _BINARY_OPS | {"float-to-bits", "bits-to-float"}


def parse_int_literal(text: str) -> int:
    """Parse an integer literal: 0x/0b prefixed or decimal, optional sign."""
    t = text.strip()
    sign = 1
    if t[:1] in "+-":
        sign = -1 if t[0] == "-" else 1
        t = t[1:].lower()
    else:
        t = t.lower()
    try:
        if t.startswith("0x"):
            return sign * int(t[2:], 16)
        if t.startswith("0b"):
            return sign * int(t[2:], 2)
        return sign * int(t, 10)
    except ValueError:
        raise SyntaxError_(f"invalid integer literal: {text!r}") from None


def _parse_float_literal(text: str) -> int | float:
    """Parse a float literal, falling back to integer forms (0x/0b/dec)."""
    try:
        return float(text)
    except ValueError:
        return parse_int_literal(text)


def _resolve_width(width: int | None) -> int:
    if width is None:
        raise ArgumentError("--width is required (expected 8, 16, 32, or 64)")
    if width not in _WIDTHS:
        raise ArgumentError(f"unsupported width: {width} (expected one of 8, 16, 32, 64)")
    return width


def _checked_mask(value: int, width: int) -> int:
    """Range-check against the width (signed range accepted for negatives)."""
    if value < -(1 << (width - 1)) or value >= (1 << width):
        raise MathError(f"value {value} does not fit a {width}-bit integer")
    return value & ((1 << width) - 1)


def _to_signed(value: int, width: int) -> int:
    if value >= (1 << (width - 1)):
        return value - (1 << width)
    return value


def _format_int(value: int, width: int, fmt: str | None, signed: bool) -> int | str:
    """Render per --format; decimal is the default (signed interpretation if asked)."""
    if signed:
        value = _to_signed(value, width)
    if fmt is None:
        return value
    if fmt == "hex":
        return f"{value & ((1 << width) - 1):0{width // 4}x}"
    return f"{value & ((1 << width) - 1):0{width}b}"


def _resolve_format(fmt: str | None) -> str | None:
    if fmt not in (None, "hex", "bin"):
        raise ArgumentError(f"unknown format: {fmt!r} (expected hex or bin)")
    return fmt


def _shift_amount(value: int) -> int:
    if value < 0:
        raise MathError(f"negative shift amount: {value}")
    return value


def bits(
    op: str,
    values: list[str],
    *,
    width: int | None = None,
    fmt: str | None = None,
    signed: bool = False,
) -> int | float | str:
    """Fixed-width integer operation; decimal int (or float for bits-to-float)."""
    if op not in _OPS:
        raise ArgumentError(f"unknown bits operation: {op!r}")
    w = _resolve_width(width)
    out_fmt = _resolve_format(fmt)
    if op in _UNARY_OPS or op in ("float-to-bits", "bits-to-float"):
        if len(values) != 1:
            raise ArgumentError(f"bits {op} takes exactly 1 value, got {len(values)}")
    elif op in _BINARY_OPS and len(values) != 2:
        raise ArgumentError(f"bits {op} takes exactly 2 values, got {len(values)}")

    if op == "float-to-bits":
        return _float_to_bits(_parse_float_literal(values[0]), w)
    if op == "bits-to-float":
        return _bits_to_float(parse_int_literal(values[0]), w)

    parsed = [parse_int_literal(v) for v in values]
    v = _checked_mask(parsed[0], w)
    if op == "not":
        result = v ^ ((1 << w) - 1)
    elif op == "and":
        result = v & _checked_mask(parsed[1], w)
    elif op == "or":
        result = v | _checked_mask(parsed[1], w)
    elif op == "xor":
        result = v ^ _checked_mask(parsed[1], w)
    elif op == "shl":
        result = (v << min(_shift_amount(parsed[1]), w)) & ((1 << w) - 1)
    elif op == "shr":
        result = v >> min(_shift_amount(parsed[1]), w)
    elif op == "sar":
        result = _to_signed(v, w) >> min(_shift_amount(parsed[1]), w)
        result &= (1 << w) - 1
    elif op == "rol":
        n = _shift_amount(parsed[1]) % w
        result = ((v << n) | (v >> (w - n))) & ((1 << w) - 1) if n else v
    elif op == "ror":
        n = _shift_amount(parsed[1]) % w
        result = ((v >> n) | (v << (w - n))) & ((1 << w) - 1) if n else v
    elif op == "popcount":
        result = v.bit_count()
    elif op == "clz":
        result = w - v.bit_length()
    elif op == "ctz":
        result = w if v == 0 else (v & -v).bit_length() - 1
    elif op == "to-signed":
        return _format_int(_to_signed(v, w), w, out_fmt, signed)
    else:  # to-unsigned
        return _format_int(v, w, out_fmt, signed)
    return _format_int(result, w, out_fmt, signed)


def _float_to_bits(value: int | float, width: int) -> str:
    """Reinterpret a float's IEEE-754 representation as bits (hex string)."""
    try:
        packed = struct.pack(">d" if width == 64 else ">f", float(value))
    except (OverflowError, struct.error) as exc:
        raise MathError(f"cannot represent {value} in {width}-bit float") from exc
    return packed.hex()


def _bits_to_float(value: int, width: int) -> float:
    """Reinterpret bits (given as an integer) as an IEEE-754 float."""
    # Same width-overflow contract as the integer ops: the literal must fit
    # (signed range accepted), else MathError — not a generic OverflowError.
    _checked_mask(value, width)
    code = ">d" if width == 64 else ">f"
    raw = value.to_bytes(width // 8, "big", signed=value < 0)
    return struct.unpack(code, raw)[0]


_ORDERS = frozenset({"little", "big"})
_ByteOrder = Literal["little", "big"]
_ENDIAN_OPS = frozenset({"swap", "to-bytes", "from-bytes"})


def _resolve_order(order: str | None) -> _ByteOrder:
    if order is None:
        raise ArgumentError("--order is required (expected little or big)")
    if order not in _ORDERS:
        raise ArgumentError(f"unknown byte order: {order!r} (expected little or big)")
    return cast(_ByteOrder, order)


def _parse_hex_bytes(text: str) -> bytes:
    return parse_hex_bytes(text)


def endian(
    op: str,
    value: str,
    *,
    width: int | None = None,
    order: str | None = None,
) -> int | str:
    """Byte-order conversions; swap/to-bytes yield hex, from-bytes yields decimal."""
    if op not in _ENDIAN_OPS:
        raise ArgumentError(f"unknown endian operation: {op!r}")

    if op == "from-bytes":
        raw = _parse_hex_bytes(value)
        return int.from_bytes(raw, _resolve_order(order))

    w = _resolve_width(width)
    v = _checked_mask(parse_int_literal(value), w)
    raw = v.to_bytes(w // 8, "big")
    if op == "swap":
        return raw[::-1].hex()
    return v.to_bytes(w // 8, _resolve_order(order)).hex()
