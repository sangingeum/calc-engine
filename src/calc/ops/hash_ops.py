"""Hashing (hash), CRC variants (crc), and base64 coding (base64).

hash input defaults to UTF-8 text; --input hex takes raw bytes (invalid hex is
a SyntaxError). CRC variants are fixed by name (registry style) with the
"123456789" check values as the correctness contract. base64 encode/decode
uses the standard or URL-safe alphabet; --output hex renders non-UTF-8 bytes.
"""

from __future__ import annotations

import base64 as b64
import binascii
import hashlib

from calc.errors import ArgumentError, SyntaxError_
from calc.ops.parse_utils import parse_hex_bytes

_HASHES: dict[str, str] = {
    "md5": "md5",
    "sha1": "sha1",
    "sha256": "sha256",
    "sha512": "sha512",
    "sha3_256": "sha3_256",
    "blake2b": "blake2b",
}

_TEXT = "text"
_HEX = "hex"


def _resolve_input(mode: str | None) -> str:
    if mode is None:
        return _TEXT
    if mode not in (_TEXT, _HEX):
        raise ArgumentError(f"unknown input format: {mode!r} (expected text or hex)")
    return mode


def _input_bytes(data: str, mode: str | None) -> bytes:
    fmt = _resolve_input(mode)
    if fmt == _TEXT:
        return data.encode("utf-8")
    return parse_hex_bytes(data)


def hash_digest(algorithm: str, data: str, *, input_format: str | None = None) -> str:
    """Digest of the input as lowercase hex."""
    if algorithm not in _HASHES:
        raise ArgumentError(
            f"unknown hash algorithm: {algorithm!r} (expected one of "
            f"{', '.join(sorted(_HASHES))})"
        )
    return hashlib.new(_HASHES[algorithm], _input_bytes(data, input_format)).hexdigest()


def _bit_reverse(value: int, width: int) -> int:
    return int(f"{value:0{width}b}"[::-1], 2)


class _CrcVariant:
    """A named CRC variant: params fixed at registration, no runtime config."""

    __slots__ = ("name", "width", "poly", "init", "refin", "refout", "xorout")

    def __init__(
        self,
        name: str,
        width: int,
        poly: int,
        init: int,
        refin: bool,
        refout: bool,
        xorout: int,
    ) -> None:
        self.name = name
        self.width = width
        self.poly = poly
        self.init = init
        self.refin = refin
        self.refout = refout
        self.xorout = xorout

    def compute(self, data: bytes) -> int:
        mask = (1 << self.width) - 1
        if self.refin:
            # Reflected (LSB-first) algorithm: use the reflected polynomial.
            # init/xorout are already in the reflected domain; the reflected
            # output needs no final reversal (refin == refout for all variants).
            poly_r = _bit_reverse(self.poly, self.width)
            crc = self.init
            for byte in data:
                crc ^= byte
                for _ in range(8):
                    crc = (crc >> 1) ^ poly_r if crc & 1 else crc >> 1
            return crc ^ self.xorout
        crc = self.init
        top_bit = 1 << (self.width - 1)
        for byte in data:
            crc ^= byte << (self.width - 8)
            for _ in range(8):
                crc = ((crc << 1) ^ self.poly if crc & top_bit else crc << 1) & mask
        if self.refout:
            crc = _bit_reverse(crc, self.width)
        return crc ^ self.xorout


_VARIANTS: dict[str, _CrcVariant] = {
    variant.name: variant
    for variant in (
        _CrcVariant("crc32", 32, 0x04C11DB7, 0xFFFFFFFF, True, True, 0xFFFFFFFF),
        _CrcVariant("crc32c", 32, 0x1EDC6F41, 0xFFFFFFFF, True, True, 0xFFFFFFFF),
        _CrcVariant("crc16-ccitt-false", 16, 0x1021, 0xFFFF, False, False, 0x0000),
        _CrcVariant("crc16-xmodem", 16, 0x1021, 0x0000, False, False, 0x0000),
        _CrcVariant("crc16-modbus", 16, 0x8005, 0xFFFF, True, True, 0x0000),
        _CrcVariant("crc8", 8, 0x07, 0x00, False, False, 0x0000),
    )
}


def crc_digest(variant: str, data: str, *, input_format: str | None = None) -> str:
    """CRC of the input as lowercase hex, zero-padded to the variant's width."""
    if variant not in _VARIANTS:
        raise ArgumentError(
            f"unknown CRC variant: {variant!r} (expected one of {', '.join(sorted(_VARIANTS))})"
        )
    crc = _VARIANTS[variant].compute(_input_bytes(data, input_format))
    width = _VARIANTS[variant].width
    return f"{crc:0{width // 4}x}"


def base64_code(
    op: str,
    data: str,
    *,
    urlsafe: bool = False,
    output_format: str | None = None,
) -> str:
    """Base64 encode/decode; decode output is UTF-8 text or hex with --output hex."""
    if op not in ("encode", "decode"):
        raise ArgumentError(f"unknown base64 operation: {op!r} (expected encode|decode)")
    if op == "encode":
        raw = data.encode("utf-8")
        return (
            b64.urlsafe_b64encode(raw).decode("ascii")
            if urlsafe
            else b64.b64encode(raw).decode("ascii")
        )
    if output_format not in (None, _HEX):
        raise ArgumentError(f"unknown output format: {output_format!r} (expected hex)")
    # Strict validation for both alphabets: stdlib decoders silently ignore
    # invalid characters by default, which would break the SyntaxError contract.
    if urlsafe:
        decoder = lambda data: b64.b64decode(  # noqa: E731 — trivial adapter
            data, altchars=b"-_", validate=True
        )
    else:
        decoder = lambda data: b64.b64decode(data, validate=True)  # noqa: E731
    try:
        raw = decoder(data.strip())
    except (binascii.Error, ValueError):
        raise SyntaxError_(f"invalid base64 input: {data!r}") from None
    if output_format == _HEX:
        return raw.hex()
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        raise SyntaxError_(
            "decoded bytes are not valid UTF-8; retry with --output hex"
        ) from None
