"""Unit tests: regex ops — spec examples, error taxonomy, and the timeout guard."""

from __future__ import annotations

import time

import pytest

from calc.errors import ArgumentError, MathError, SyntaxError_
from calc.ops import regex_ops


class TestSpecExamples:
    def test_test_true(self) -> None:
        assert regex_ops.regex("test", r"^\d+$", "12345") == "true"

    def test_test_false(self) -> None:
        assert regex_ops.regex("test", r"^\d+$", "12x45") == "false"

    def test_findall(self) -> None:
        assert regex_ops.regex("findall", r"\d+", "a1b22c333") == ["1", "22", "333"]

    def test_groups(self) -> None:
        assert regex_ops.regex(r"groups", r"(\w+)@(\w+)\.com", "x bob@example.com y") == [
            "bob",
            "example",
        ]

    def test_sub(self) -> None:
        assert regex_ops.regex("sub", r"\s+", "a   b \t c", replacement=" ") == "a b c"

    def test_test_case_insensitive(self) -> None:
        assert regex_ops.regex("test", "hello", "HELLO", flags="i") == "true"

    def test_groups_no_match(self) -> None:
        assert regex_ops.regex("groups", r"(\w+)x", "abc") == []

    def test_test_no_match_is_not_an_error(self) -> None:
        # false is a normal result, not a failure (exit 0 at the CLI layer)
        assert regex_ops.regex("test", "zzz", "hello") == "false"


class TestFlags:
    def test_multiline(self) -> None:
        assert regex_ops.regex("test", r"^b$", "a\nb", flags="m") == "true"

    def test_dotall(self) -> None:
        assert regex_ops.regex("test", "a.b", "a\nb", flags="s") == "true"

    def test_combined(self) -> None:
        assert regex_ops.regex("test", "HELLO", "hello", flags="i") == "true"

    def test_unknown_flag(self) -> None:
        with pytest.raises(ArgumentError, match="unknown regex flag"):
            regex_ops.regex("test", "x", "x", flags="q")

    def test_unknown_flavor(self) -> None:
        with pytest.raises(ArgumentError, match="unknown regex flavor"):
            regex_ops.regex("test", "x", "x", flavor="ecma")


class TestErrors:
    def test_invalid_pattern_is_syntax_error(self) -> None:
        with pytest.raises(SyntaxError_, match="invalid regex pattern"):
            regex_ops.regex("test", "[", "x")

    def test_bad_quantifier(self) -> None:
        with pytest.raises(SyntaxError_):
            regex_ops.regex("test", "*", "x")

    def test_unknown_op(self) -> None:
        with pytest.raises(ArgumentError, match="unknown regex operation"):
            regex_ops.regex("grep", "x", "x")

    def test_sub_requires_replacement(self) -> None:
        with pytest.raises(ArgumentError, match="requires --replacement"):
            regex_ops.regex("sub", "a", "abc")

    def test_sub_backreferences_rejected(self) -> None:
        with pytest.raises(ArgumentError, match="backreferences"):
            regex_ops.regex("sub", r"(\w)", "abc", replacement=r"\1\1")


class TestTimeout:
    def test_catastrophic_backtracking_times_out(self) -> None:
        # (a+)+b against many a's hangs re without a timeout guard
        start = time.monotonic()
        with pytest.raises(MathError, match="execution budget"):
            regex_ops.regex("test", "(a+)+b", "a" * 40)
        elapsed = time.monotonic() - start
        assert elapsed < 5.0  # would hang indefinitely without the guard
