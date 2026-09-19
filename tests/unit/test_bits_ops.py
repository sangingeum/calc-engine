"""Unit tests: fixed-width integer ops (bits) and byte-order ops (endian)."""

from __future__ import annotations

import math

import pytest

from calc.errors import ArgumentError, MathError, SyntaxError_
from calc.ops import bits_ops


class TestParseIntLiteral:
    def test_decimal(self) -> None:
        assert bits_ops.parse_int_literal("42") == 42

    def test_hex(self) -> None:
        assert bits_ops.parse_int_literal("0xF0") == 240

    def test_binary(self) -> None:
        assert bits_ops.parse_int_literal("0b1010") == 10

    def test_negative(self) -> None:
        assert bits_ops.parse_int_literal("-128") == -128

    def test_negative_hex(self) -> None:
        assert bits_ops.parse_int_literal("-0x10") == -16

    def test_invalid(self) -> None:
        with pytest.raises(SyntaxError_):
            bits_ops.parse_int_literal("nope")


class TestWidthRequired:
    def test_missing_width(self) -> None:
        with pytest.raises(ArgumentError, match="--width is required"):
            bits_ops.bits("and", ["0xF0", "0x3C"])

    def test_bad_width(self) -> None:
        with pytest.raises(ArgumentError, match="unsupported width"):
            bits_ops.bits("and", ["1", "2"], width=12)

    def test_endian_missing_width(self) -> None:
        with pytest.raises(ArgumentError):
            bits_ops.endian("swap", "0x12")


class TestBinaryOps:
    def test_and(self) -> None:
        assert bits_ops.bits("and", ["0xF0", "0x3C"], width=8) == 48

    def test_or(self) -> None:
        assert bits_ops.bits("or", ["0xF0", "0x0F"], width=8) == 255

    def test_xor(self) -> None:
        assert bits_ops.bits("xor", ["0xFF", "0x0F"], width=8) == 240

    def test_shl_wraps(self) -> None:
        assert bits_ops.bits("shl", ["1", "7"], width=8) == 128

    def test_shl_overflow_wraps_mod_2w(self) -> None:
        assert bits_ops.bits("shl", ["1", "9"], width=8) == 0

    def test_shr(self) -> None:
        assert bits_ops.bits("shr", ["128", "4"], width=8) == 8

    def test_sar_sign_extension(self) -> None:
        assert bits_ops.bits("sar", ["-128", "1"], width=8, signed=True) == -64

    def test_rol(self) -> None:
        assert bits_ops.bits("rol", ["0x81", "1"], width=8) == 3

    def test_ror(self) -> None:
        # 0x81 = 1b10000001 rotated right 1 -> 1b11000000 = 0xC0
        assert bits_ops.bits("ror", ["0x81", "1"], width=8) == 0xC0

    def test_rol_by_width_is_identity(self) -> None:
        assert bits_ops.bits("rol", ["0x81", "8"], width=8) == 0x81


class TestUnaryOps:
    def test_not(self) -> None:
        assert bits_ops.bits("not", ["0x0F"], width=8) == 240

    def test_popcount(self) -> None:
        assert bits_ops.bits("popcount", ["255"], width=8) == 8

    def test_clz(self) -> None:
        assert bits_ops.bits("clz", ["1"], width=32) == 31

    def test_ctz(self) -> None:
        assert bits_ops.bits("ctz", ["8"], width=32) == 3

    def test_ctz_zero_is_width(self) -> None:
        assert bits_ops.bits("ctz", ["0"], width=32) == 32

    def test_to_signed(self) -> None:
        assert bits_ops.bits("to-signed", ["0xFF"], width=8) == -1

    def test_to_unsigned(self) -> None:
        assert bits_ops.bits("to-unsigned", ["-1"], width=8) == 255


class TestSignednessAndFormat:
    def test_signed_decimal_output(self) -> None:
        assert bits_ops.bits("and", ["0xF0", "0x3C"], width=8, signed=True) == 48

    def test_signed_negative_result(self) -> None:
        assert bits_ops.bits("xor", ["0xFF", "0x7F"], width=8, signed=True) == -128

    def test_hex_zero_padded(self) -> None:
        assert bits_ops.bits("and", ["0xF0", "0x3C"], width=8, fmt="hex") == "30"

    def test_hex_zero_padding_to_width(self) -> None:
        assert bits_ops.bits("or", ["1", "0"], width=16, fmt="hex") == "0001"

    def test_bin_zero_padded(self) -> None:
        assert bits_ops.bits("and", ["0xF0", "0x3C"], width=8, fmt="bin") == "00110000"

    def test_bad_format(self) -> None:
        with pytest.raises(ArgumentError, match="unknown format"):
            bits_ops.bits("not", ["1"], width=8, fmt="oct")


class TestValueRange:
    def test_value_overflows_width(self) -> None:
        with pytest.raises(MathError, match="does not fit"):
            bits_ops.bits("not", ["256"], width=8)

    def test_negative_shift(self) -> None:
        with pytest.raises(MathError, match="negative shift"):
            bits_ops.bits("shl", ["1", "-1"], width=8)

    def test_wrong_arity_binary(self) -> None:
        with pytest.raises(ArgumentError, match="exactly 2"):
            bits_ops.bits("and", ["1"], width=8)

    def test_wrong_arity_unary(self) -> None:
        with pytest.raises(ArgumentError, match="exactly 1"):
            bits_ops.bits("not", ["1", "2"], width=8)

    def test_unknown_op(self) -> None:
        with pytest.raises(ArgumentError, match="unknown bits operation"):
            bits_ops.bits("bogus", ["1"], width=8)


class TestFloatBits:
    def test_float_to_bits(self) -> None:
        assert bits_ops.bits("float-to-bits", ["1.0"], width=32) == "3f800000"

    def test_float_to_bits_64(self) -> None:
        assert bits_ops.bits("float-to-bits", ["1.0"], width=64) == "3ff0000000000000"

    def test_bits_to_float(self) -> None:
        assert bits_ops.bits("bits-to-float", ["0x3fc00000"], width=32) == pytest.approx(1.5)

    def test_bits_to_float_nan(self) -> None:
        value = bits_ops.bits("bits-to-float", ["0x7fc00000"], width=32)
        assert isinstance(value, float)
        assert math.isnan(value)


class TestEndian:
    def test_swap(self) -> None:
        assert bits_ops.endian("swap", "0x12345678", width=32) == "78563412"

    def test_swap_zero_padded(self) -> None:
        assert bits_ops.endian("swap", "0x1234", width=16) == "3412"

    def test_to_bytes_little(self) -> None:
        assert bits_ops.endian("to-bytes", "0x12345678", width=32, order="little") == "78563412"

    def test_to_bytes_big(self) -> None:
        assert bits_ops.endian("to-bytes", "0x12345678", width=32, order="big") == "12345678"

    def test_from_bytes_little(self) -> None:
        assert bits_ops.endian("from-bytes", "78563412", order="little") == 305419896

    def test_from_bytes_big(self) -> None:
        assert bits_ops.endian("from-bytes", "12345678", order="big") == 305419896

    def test_from_bytes_missing_order(self) -> None:
        with pytest.raises(ArgumentError, match="--order is required"):
            bits_ops.endian("from-bytes", "78563412")

    def test_bad_order(self) -> None:
        with pytest.raises(ArgumentError, match="unknown byte order"):
            bits_ops.endian("to-bytes", "1", width=8, order="middle")

    def test_bad_hex(self) -> None:
        with pytest.raises(SyntaxError_, match="invalid hex byte string"):
            bits_ops.endian("from-bytes", "zz", order="little")

    def test_odd_length_hex(self) -> None:
        with pytest.raises(SyntaxError_):
            bits_ops.endian("from-bytes", "abc", order="little")

    def test_unknown_op(self) -> None:
        with pytest.raises(ArgumentError, match="unknown endian operation"):
            bits_ops.endian("rotate", "1", width=8)
