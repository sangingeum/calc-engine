"""Contract tests: stdout-only success, stderr+exit-1 failure, no stream mixing."""

from __future__ import annotations

import re

import pytest
from conftest import run_calc

ERROR_LINE = re.compile(r"^(MathError|SyntaxError|ValueError|ArgumentError): .+")

SUCCESS_CASES = [
    (["eval", "2+2"], "4"),
    (["eval", "sqrt(2)", "--precision", "6"], "1.414214"),
    (["stat", "mean", "[1,2,3,4]"], "2.5000"),
    (["stat", "mode", "[1,2,2,3]"], "2"),
    (["stat", "sum", "[1,2,3]"], "6"),
    (
        ["finance", "pmt", "--rate", "0.05", "--periods", "10", "--principal", "1000"],
        "-129.5046",
    ),
    (["matrix", "multiply", "[[1,2],[3,4]]", "[[1],[2]]"], "[[5],[11]]"),
    (["matrix", "transpose", "[[1,2],[3,4]]"], "[[1,3],[2,4]]"),
    (["convert-base", "255", "--from", "dec", "--to", "hex"], "ff"),
    (["convert-base", "FF", "--from", "hex", "--to", "bin"], "11111111"),
    (["convert-unit", "1", "miles", "km"], "1.6093"),
    (["convert-unit", "100", "degC", "degF"], "212.0000"),
    (["calculus", "derive", "x**2", "--var", "x"], "2*x"),
    (
        ["calculus", "integrate", "x**2", "--var", "x", "--lower", "0", "--upper", "1"],
        "0.3333",
    ),
    (["physics-constant", "c"], "299792458.0000"),
    (
        ["physics", "kinematics", "--solve", "d", "--v0", "10", "--t", "2", "--a", "3"],
        "26.0000",
    ),
    (["physics", "force", "--solve", "F", "--m", "5", "--a", "2"], "10.0000"),
    (["physics", "energy", "--solve", "PE", "--m", "2", "--h", "5"], "98.0665"),
    (["vector", "dot", "[1,2,3]", "[4,5,6]"], "32.0000"),
    (["vector", "cross", "[1,0,0]", "[0,1,0]"], "[0.0000,0.0000,1.0000]"),
    # hash / crc / base64
    (
        ["hash", "sha256", "hello"],
        "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824",
    ),
    (["hash", "md5", "hello"], "5d41402abc4b2a76b9719d911017c592"),
    (["crc", "crc32", "123456789"], "cbf43926"),
    (["crc", "crc32c", "123456789"], "e3069283"),
    (["crc", "crc16-ccitt-false", "123456789"], "29b1"),
    (["crc", "crc16-xmodem", "123456789"], "31c3"),
    (["crc", "crc16-modbus", "123456789"], "4b37"),
    (["crc", "crc8", "123456789"], "f4"),
    (["crc", "crc32", "68656c6c6f", "--input", "hex"], "3610a686"),
    (["base64", "encode", "hello"], "aGVsbG8="),
    (["base64", "decode", "aGVsbG8="], "hello"),
    (["base64", "decode", "aGVsbG8=", "--output", "hex"], "68656c6c6f"),
    # datetime (spec acceptance examples)
    (["datetime", "from-epoch", "1700000000"], "2023-11-14T22:13:20+00:00"),
    (
        ["datetime", "from-epoch", "1700000000", "--tz", "Asia/Seoul"],
        "2023-11-15T07:13:20+09:00",
    ),
    (["datetime", "to-epoch", "2023-11-14T22:13:20+00:00"], "1700000000"),
    (
        [
            "datetime",
            "diff",
            "2024-01-01T00:00:00+00:00",
            "2024-03-01T00:00:00+00:00",
            "--unit",
            "days",
        ],
        "60.0000",
    ),
    (
        ["datetime", "add", "2024-02-28T12:00:00+00:00", "--days", "2"],
        "2024-03-01T12:00:00+00:00",
    ),
    (["datetime", "weekday", "2024-02-29"], "Thursday"),
    (
        [
            "datetime",
            "convert-tz",
            "2024-03-10T12:00:00",
            "--from",
            "America/New_York",
            "--to",
            "Asia/Seoul",
        ],
        "2024-03-11T01:00:00+09:00",
    ),
    # regex (test=false is a SUCCESS case — exit 0)
    (["regex", "test", r"^\d+$", "12345"], "true"),
    (["regex", "test", r"^\d+$", "12x45"], "false"),
    (["regex", "findall", r"\d+", "a1b22c333"], "[1,22,333]"),
    (["regex", "groups", r"(\w+)@(\w+)\.com", "x bob@example.com y"], "[bob,example]"),
    (["regex", "sub", r"\s+", " ", "a   b \t c"], "a b c"),
    (["regex", "test", "hello", "HELLO", "--flags", "i"], "true"),
    # bits / endian (spec acceptance examples)
    (["bits", "and", "0xF0", "0x3C", "--width", "8"], "48"),
    (["bits", "not", "0x0F", "--width", "8"], "240"),
    (["bits", "shl", "1", "7", "--width", "8"], "128"),
    (["bits", "sar", "-128", "1", "--width", "8", "--signed"], "-64"),
    (["bits", "rol", "0x81", "1", "--width", "8"], "3"),
    (["bits", "popcount", "255", "--width", "8"], "8"),
    (["bits", "clz", "1", "--width", "32"], "31"),
    (["bits", "ctz", "8", "--width", "32"], "3"),
    (["bits", "to-signed", "0xFF", "--width", "8"], "-1"),
    (["bits", "to-unsigned", "-1", "--width", "8"], "255"),
    (["bits", "and", "0xF0", "0x3C", "--width", "8", "--format", "hex"], "30"),
    (["bits", "float-to-bits", "1.0", "--width", "32"], "3f800000"),
    (["bits", "bits-to-float", "0x3fc00000", "--width", "32"], "1.5000"),
    (["endian", "swap", "0x12345678", "--width", "32"], "78563412"),
    (["endian", "to-bytes", "0x12345678", "--width", "32", "--order", "little"], "78563412"),
    (["endian", "to-bytes", "0x12345678", "--width", "32", "--order", "big"], "12345678"),
    (["endian", "from-bytes", "78563412", "--order", "little"], "305419896"),
]

FAILURE_CASES = [
    (["eval", "1/0"], "MathError"),
    (["eval", "(2+3"], "SyntaxError"),
    (["eval", "__import__('os')"], "SyntaxError"),
    (["matrix", "multiply", "[[1,2]]", "[[1,2]]"], "MathError"),
    (["matrix", "multiply", "not-json", "[[1]]"], "SyntaxError"),
    (["convert-unit", "1", "blorp", "km"], "ValueError"),
    (["physics-constant", "notathing"], "ValueError"),
    (["physics", "kinematics", "--solve", "d"], "ArgumentError"),
    (["physics", "nope", "--solve", "d", "--v0", "1", "--t", "1"], "ArgumentError"),
    (
        [
            "finance",
            "pmt",
            "--rate",
            "0.05",
            "--periods",
            "10",
            "--pv",
            "1000",
            "--principal",
            "1000",
        ],
        "ArgumentError",
    ),
    (["finance", "pmt", "--rate", "0.05", "--periods", "10"], "ArgumentError"),
    (["vector", "dot", "[1,2]", "[1,2,3]"], "MathError"),
    (["stat", "mean", "[]"], "MathError"),
    (["stat", "bogus", "[1,2]"], "ArgumentError"),
    (["convert-base", "1.5", "--from", "dec", "--to", "hex"], "MathError"),
    (["convert-base", "ff", "--from", "dec", "--to", "hex"], "SyntaxError"),
    # bits/endian: --width required, bad values, unknown ops
    (["bits", "and", "0xF0", "0x3C"], "ArgumentError"),
    (["bits", "and", "0xF0", "0x3C", "--width", "12"], "ArgumentError"),
    (["bits", "and", "256", "1", "--width", "8"], "MathError"),
    (["bits", "bogus", "1", "--width", "8"], "ArgumentError"),
    (["bits", "and", "zz", "1", "--width", "8"], "SyntaxError"),
    (["endian", "swap", "0x12345678"], "ArgumentError"),
    (["endian", "from-bytes", "zz", "--order", "little"], "SyntaxError"),
    (["endian", "frobnicate", "1", "--width", "8"], "ArgumentError"),
    # hash/crc/base64: unknown choices, invalid hex/base64
    (["hash", "sh999", "x"], "ArgumentError"),
    (["crc", "crc33", "123456789"], "ArgumentError"),
    (["hash", "md5", "zz", "--input", "hex"], "SyntaxError"),
    (["base64", "decode", "!!!"], "SyntaxError"),
    (["base64", "frobnicate", "hello"], "ArgumentError"),
    # datetime: naive timestamps, unknown timezone/operation
    (["datetime", "to-epoch", "2023-11-14T22:13:20"], "ArgumentError"),
    (["datetime", "add", "2024-03-10T12:00:00", "--days", "1"], "ArgumentError"),
    (["datetime", "from-epoch", "1700000000", "--tz", "Not/AZone"], "ValueError"),
    (["datetime", "frobnicate", "1700000000"], "ArgumentError"),
    (["datetime", "from-epoch", "soon"], "ArgumentError"),
    # regex: invalid pattern is SyntaxError; unknown op/flag/flavor are ArgumentError
    (["regex", "test", "[", "x"], "SyntaxError"),
    (["regex", "grep", "x", "y"], "ArgumentError"),
    (["regex", "test", "x", "y", "--flavor", "ecma"], "ArgumentError"),
    (["regex", "test", "x", "y", "--flags", "q"], "ArgumentError"),
]


@pytest.mark.parametrize(
    ("args", "expected"), SUCCESS_CASES, ids=[f"{a[0]}-{a[1]}" for a in SUCCESS_CASES]
)
def test_success_stdout_only(args: list[str], expected: str) -> None:
    proc = run_calc(*args)
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip() == expected
    assert proc.stderr == ""


@pytest.mark.parametrize(
    ("args", "prefix"), FAILURE_CASES, ids=[f"{a[0]}-{a[1]}" for a in FAILURE_CASES]
)
def test_failure_single_stderr_line(args: list[str], prefix: str) -> None:
    proc = run_calc(*args)
    assert proc.returncode == 1
    assert proc.stdout == ""
    lines = proc.stderr.strip().splitlines()
    assert len(lines) == 1
    assert ERROR_LINE.match(lines[0]), lines[0]
    assert lines[0].startswith(f"{prefix}: ")


def test_bad_usage_exits_nonzero_with_stderr() -> None:
    proc = run_calc()
    assert proc.returncode != 0
    assert proc.stderr.strip() != ""
    assert proc.stdout == ""
