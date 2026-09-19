"""Unit tests: hash digests, CRC variants (check values), and base64 coding."""

from __future__ import annotations

import pytest

from calc.errors import ArgumentError, SyntaxError_
from calc.ops import hash_ops


class TestHash:
    def test_sha256_text(self) -> None:
        assert (
            hash_ops.hash_digest("sha256", "hello")
            == "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"
        )

    def test_md5_text(self) -> None:
        assert hash_ops.hash_digest("md5", "hello") == "5d41402abc4b2a76b9719d911017c592"

    def test_hex_input_equals_text(self) -> None:
        # 68656c6c6f == b"hello"
        assert hash_ops.hash_digest(
            "sha256", "68656c6c6f", input_format="hex"
        ) == hash_ops.hash_digest("sha256", "hello")

    def test_all_algorithms_accepted(self) -> None:
        for algorithm in ("md5", "sha1", "sha256", "sha512", "sha3_256", "blake2b"):
            assert len(hash_ops.hash_digest(algorithm, "")) > 0

    def test_unknown_algorithm(self) -> None:
        with pytest.raises(ArgumentError, match="unknown hash algorithm"):
            hash_ops.hash_digest("sh999", "x")

    def test_bad_hex_input(self) -> None:
        with pytest.raises(SyntaxError_, match="invalid hex input"):
            hash_ops.hash_digest("md5", "zz", input_format="hex")

    def test_bad_input_format(self) -> None:
        with pytest.raises(ArgumentError, match="unknown input format"):
            hash_ops.hash_digest("md5", "x", input_format="base64")


class TestCrc:
    # The "123456789" check values are the acceptance contract.
    CHECK_CASES = [
        ("crc32", "cbf43926"),
        ("crc32c", "e3069283"),
        ("crc16-ccitt-false", "29b1"),
        ("crc16-xmodem", "31c3"),
        ("crc16-modbus", "4b37"),
        ("crc8", "f4"),
    ]

    @pytest.mark.parametrize(("variant", "expected"), CHECK_CASES)
    def test_check_values(self, variant: str, expected: str) -> None:
        assert hash_ops.crc_digest(variant, "123456789") == expected

    def test_hex_input(self) -> None:
        assert hash_ops.crc_digest("crc32", "68656c6c6f", input_format="hex") == "3610a686"

    def test_hex_equals_text(self) -> None:
        assert hash_ops.crc_digest(
            "crc32", "68656c6c6f", input_format="hex"
        ) == hash_ops.crc_digest("crc32", "hello")

    def test_unknown_variant(self) -> None:
        with pytest.raises(ArgumentError, match="unknown CRC variant"):
            hash_ops.crc_digest("crc33", "123456789")

    def test_bad_hex_input(self) -> None:
        with pytest.raises(SyntaxError_, match="invalid hex input"):
            hash_ops.crc_digest("crc32", "nothex", input_format="hex")

    def test_width_zero_padding(self) -> None:
        # crc8 is 8 bits: one hex byte wide
        assert len(hash_ops.crc_digest("crc8", "123456789")) == 2


class TestBase64:
    def test_encode(self) -> None:
        assert hash_ops.base64_code("encode", "hello") == "aGVsbG8="

    def test_decode(self) -> None:
        assert hash_ops.base64_code("decode", "aGVsbG8=") == "hello"

    def test_decode_output_hex(self) -> None:
        assert hash_ops.base64_code("decode", "aGVsbG8=", output_format="hex") == "68656c6c6f"

    def test_encode_urlsafe(self) -> None:
        assert hash_ops.base64_code("encode", "hello?>", urlsafe=True) == "aGVsbG8_Pg=="

    def test_decode_urlsafe(self) -> None:
        assert hash_ops.base64_code("decode", "aGVsbG8_Pg==", urlsafe=True) == "hello?>"

    def test_decode_non_utf8_output_hex(self) -> None:
        # single 0xFF byte: valid base64, not valid UTF-8
        encoded = hash_ops.base64_code("decode", "/w==", output_format="hex")
        assert encoded == "ff"

    def test_decode_non_utf8_without_hex_is_syntax_error(self) -> None:
        with pytest.raises(SyntaxError_, match="not valid UTF-8"):
            hash_ops.base64_code("decode", "/w==")

    def test_decode_invalid(self) -> None:
        with pytest.raises(SyntaxError_, match="invalid base64 input"):
            hash_ops.base64_code("decode", "!!!")

    def test_unknown_op(self) -> None:
        with pytest.raises(ArgumentError, match="unknown base64 operation"):
            hash_ops.base64_code("frobnicate", "hello")

    def test_bad_output_format(self) -> None:
        with pytest.raises(ArgumentError, match="unknown output format"):
            hash_ops.base64_code("decode", "aGVsbG8=", output_format="bin")
