"""GitHub issue 9: `--input hex` combined with @file is rejected (fix b).

Silent precedence (file bytes hashed raw, hex flag ignored) is the worst
option for an agent recording evidence: the combination is now an
ArgumentError. `hash`/`crc` share the same data path.
"""

from __future__ import annotations

import hashlib

from conftest import run_calc


def test_hash_input_hex_with_file_rejected(tmp_path) -> None:
    data = tmp_path / "hx.txt"
    data.write_text("68656c6c6f")  # ASCII text, not the bytes 'hello'
    proc = run_calc("hash", "sha256", f"@{data}", "--input", "hex")
    assert proc.returncode == 1
    assert proc.stdout == ""
    assert proc.stderr == (
        "ArgumentError: --input hex cannot be combined with @file (file bytes "
        "are hashed raw); use --input hex only with inline hex\n"
    )


def test_crc_input_hex_with_file_rejected(tmp_path) -> None:
    data = tmp_path / "hx.txt"
    data.write_text("68656c6c6f")
    proc = run_calc("crc", "crc32", f"@{data}", "--input", "hex")
    assert proc.returncode == 1
    assert proc.stdout == ""
    assert proc.stderr.startswith("ArgumentError: --input hex cannot be combined with @file")


def test_hash_input_hex_with_stdin_rejected() -> None:
    import subprocess

    proc = subprocess.run(
        ["uv", "run", "calc", "hash", "sha256", "@-", "--input", "hex"],
        input=b"68656c6c6f",
        capture_output=True,
        check=False,
    )
    assert proc.returncode == 1
    assert proc.stdout == b""
    assert proc.stderr.startswith(
        b"ArgumentError: --input hex cannot be combined with @file"
    )


def test_hash_file_without_input_flag_unchanged(tmp_path) -> None:
    data = tmp_path / "hello.bin"
    data.write_bytes(b"hello")
    proc = run_calc("hash", "sha256", f"@{data}")
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout == hashlib.sha256(b"hello").hexdigest() + "\n"


def test_hash_input_hex_inline_unchanged() -> None:
    proc = run_calc("hash", "sha256", "68656c6c6f", "--input", "hex")
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout == hashlib.sha256(b"hello").hexdigest() + "\n"


def test_hash_escape_unchanged() -> None:
    # R1: @@escape without flags is the literal text '@hello'.
    proc = run_calc("hash", "sha256", "@@hello")
    assert proc.returncode == 0, proc.stderr
    import hashlib

    assert proc.stdout == hashlib.sha256(b"@hello").hexdigest() + "\n"


def test_hash_escape_with_input_hex_rejected() -> None:
    # Issue 9: no silent precedence — the flag is never ignored, even on the
    # @@ escape (which would otherwise hash '@hello' as text, not hex).
    proc = run_calc("hash", "sha256", "@@hello", "--input", "hex")
    assert proc.returncode == 1
    assert proc.stdout == ""
    assert proc.stderr.startswith("ArgumentError: --input hex cannot be combined with @file")
