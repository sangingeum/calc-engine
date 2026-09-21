"""Contract tests for the v2 verification-backend extension (R1-R12)."""

from __future__ import annotations

import subprocess

import pytest
from conftest import run_calc


def assert_failure(*args: str, prefix: str, code: int = 1) -> None:
    proc = run_calc(*args)
    assert proc.returncode == code
    assert proc.stdout == "", repr(proc.stdout)
    assert proc.stderr.startswith(f"{prefix}: "), proc.stderr
    assert proc.stderr.count("\n") == 1  # exactly one stderr line


# ---------------------------------------------------------------------------
# R1: hash/crc/base64 with @file (raw bytes) and @@ escape
# ---------------------------------------------------------------------------


def test_r1_hash_file_bytes(tmp_path):
    f = tmp_path / "f.bin"
    f.write_bytes(b"hello")
    expected = run_calc("hash", "sha256", "hello").stdout
    proc = run_calc("hash", "sha256", f"@{f}")
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout == expected


def test_r1_hash_escape(tmp_path):
    import hashlib

    proc = run_calc("hash", "sha256", "@@hello")
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip() == hashlib.sha256(b"@hello").hexdigest()


def test_r1_hash_missing_file_is_typed_failure():
    proc = run_calc("hash", "sha256", "@does-not-exist-v2")
    assert proc.returncode == 1
    assert proc.stdout == ""
    assert proc.stderr.startswith("ArgumentError: cannot read file ")
    assert proc.stderr.count("\n") == 1


def test_r1_crc_and_base64_file_bytes(tmp_path):
    f = tmp_path / "f.bin"
    f.write_bytes(b"hello")
    assert run_calc("crc", "crc32", f"@{f}").stdout == run_calc("crc", "crc32", "hello").stdout
    assert (
        run_calc("base64", "encode", f"@{f}").stdout
        == run_calc("base64", "encode", "hello").stdout
    )
    # decode from a file of base64 text
    b64file = tmp_path / "f.b64"
    b64file.write_text("aGVsbG8=")
    proc = run_calc("base64", "decode", f"@{b64file}")
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout == "hello\n"


def test_r1_regression_no_silent_literal_hash(tmp_path):
    """Regression for Appendix B1: '@path' is never hashed as literal text."""
    f = tmp_path / "data.json"
    f.write_bytes(b"{}")
    proc = run_calc("hash", "sha256", f"@{f}")
    assert proc.returncode == 0, proc.stderr
    import hashlib

    literal_digest = hashlib.sha256(f"@{f}".encode()).hexdigest()
    assert proc.stdout.strip() != literal_digest
    assert proc.stdout.strip() == hashlib.sha256(b"{}").hexdigest()


# ---------------------------------------------------------------------------
# R2: arguments beginning with '-'
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "args,expected",
    [
        (["eval", "-2+5"], "3"),
        (["eval", "-0.35*(1+0.5*(0.5-0.25)*2)", "--precision", "6"], "-0.437500"),
        (["eval", "--", "-2+5"], "3"),
        (["assert", "sign", "-0.5", "negative"], "true"),
        (["assert", "between", "-0.5", "-1", "0"], "true"),
        (["regex", "test", "-x", "-x"], "true"),
    ],
)
def test_r2_leading_dash_positionals(args: list[str], expected: str) -> None:
    proc = run_calc(*args)
    assert proc.returncode == 0, (args, proc.stderr)
    assert proc.stdout == expected + "\n", (args, proc.stdout)


def test_r2_glued_option_form_regression():
    """Fix round: --opt=value must still parse (baseline 5206a52 did)."""
    proc = run_calc("eval", "2+2", "--precision=6")
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout == "4\n"  # int renders bare regardless of precision
    proc = run_calc("eval", "1/3", "--precision=6")
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout == "0.333333\n"
    proc = run_calc("eval", "-0.5-1.5", "--precision=1")
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout == "-2.0\n"


def test_inv2_huge_exact_result_one_typed_line():
    """Fix round: render failures must stay inside the INV-2 handler."""
    proc = run_calc("eval", "2**10000000", "--exact")
    assert proc.returncode == 1
    assert proc.stdout == ""
    assert proc.stderr.count("\n") == 1, proc.stderr
    assert proc.stderr.startswith("MathError: "), proc.stderr


def test_r11_exact_plus_precision_always_rejected():
    """F1 gate: --exact + --precision is an ArgumentError regardless of value.

    The original guard only rejected precision != 4, so the *default* value
    slipped through: `eval "1/2" --exact --precision 4` printed 1/2. Spec R11:
    any --precision together with --exact is an ArgumentError.
    """
    proc = run_calc("eval", "1/2", "--exact", "--precision", "4")
    assert proc.returncode == 1
    assert proc.stdout == ""
    assert proc.stderr.startswith("ArgumentError: --exact cannot be combined"), proc.stderr
    assert proc.stderr.count("\n") == 1
    # non-default values were already rejected; keep both pinned
    proc = run_calc("eval", "1/2", "--exact", "--precision", "6")
    assert proc.returncode == 1
    assert proc.stderr.startswith("ArgumentError: --exact cannot be combined")
    # glued form too
    proc = run_calc("eval", "1/2", "--exact", "--precision=4")
    assert proc.returncode == 1
    assert proc.stderr.startswith("ArgumentError: --exact cannot be combined")
    # and --exact alone still works
    proc = run_calc("eval", "1/2", "--exact")
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout == "1/2\n"


def test_r3_base64_decode_non_utf8_file_typed_error(tmp_path):
    """Fix round: non-UTF-8 @file on decode -> typed ArgumentError."""
    f = tmp_path / "bad.b64"
    f.write_bytes(b"\xff\xfe\x00")
    proc = run_calc("base64", "decode", f"@{f}")
    assert proc.returncode == 1
    assert proc.stdout == ""
    assert proc.stderr.startswith(f"ArgumentError: cannot read file '{f}'"), proc.stderr
    assert proc.stderr.count("\n") == 1


def test_r2_hash_leading_dash():
    proc = run_calc("hash", "sha256", "-abc")
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout != ""


# ---------------------------------------------------------------------------
# R3: uniform file/stdin resolver
# ---------------------------------------------------------------------------


def _run_stdin(args: list[str], data: bytes) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        ["uv", "run", "calc", *args],
        input=data,
        capture_output=True,
        check=False,
    )


def test_r3_stat_file_equals_inline(tmp_path):
    x = tmp_path / "x.json"
    y = tmp_path / "y.json"
    x.write_text("[1,2,3]")
    y.write_text("[2,4,6]")
    inline = run_calc("stat", "covariance", "[1,2,3]", "[2,4,6]").stdout
    proc = run_calc("stat", "covariance", f"@{x}", f"@{y}")
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout == inline


def test_r3_stat_stdin():
    proc = _run_stdin(["stat", "mean", "@-"], b"[1,2,3,4]")
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout == b"2.5000\n"


def test_r3_escape_is_literal_not_json():
    proc = run_calc("stat", "mean", "@@[1,2]")
    assert proc.returncode == 1
    assert proc.stderr.startswith("SyntaxError: ")


def test_r3_missing_file(tmp_path):
    proc = run_calc("stat", "mean", f"@{tmp_path}/nope.json")
    assert proc.returncode == 1
    assert proc.stderr.startswith("ArgumentError: cannot read file ")
    assert proc.stderr.count("\n") == 1


def test_r3_directory_rejected(tmp_path):
    proc = run_calc("stat", "mean", f"@{tmp_path}")
    assert proc.returncode == 1
    assert proc.stderr.startswith("ArgumentError: cannot read file ")


def test_r3_size_cap(tmp_path):
    f = tmp_path / "big.json"
    f.write_bytes(b"[" + b"1," * 10 + b"1]")
    proc = run_calc("stat", "mean", f"@{f}", "--max-input-bytes", "4")
    assert proc.returncode == 1
    assert "ArgumentError: cannot read file" in proc.stderr
    assert "4" in proc.stderr  # cap named in the message


def test_r3_two_stdin_refs_rejected():
    proc = _run_stdin(["stat", "covariance", "@-", "@-"], b"[1,2,3]")
    assert proc.returncode == 1
    assert proc.stderr.decode().startswith("ArgumentError:")


def test_r3_matrix_vector_regex_gof_files(tmp_path):
    m = tmp_path / "m.json"
    m.write_text("[[1,2],[3,4]]")
    assert run_calc("matrix", "determinant", f"@{m}").stdout == "-2.0000\n"
    v = tmp_path / "v.json"
    v.write_text("[3,4]")
    assert run_calc("vector", "norm", f"@{v}").stdout == "5.0000\n"
    d = tmp_path / "d.json"
    d.write_text("[0.05,0.2,0.35,0.5,0.65,0.8,0.95]")
    assert (
        run_calc("gof", "ks", f"@{d}", "uniform", "--low", "0", "--high", "1",
                 "--field", "statistic").stdout
        == "0.0929\n"
    )


def test_r3_inv7_no_fs_access_in_ops():
    """Static guard: no module under src/calc/ops imports open/pathlib/sys.stdin."""
    from pathlib import Path

    ops_dir = Path(__file__).resolve().parents[2] / "src" / "calc" / "ops"
    assert ops_dir.is_dir()
    banned = ("from pathlib", "import pathlib", "open(")
    for py in ops_dir.rglob("*.py"):  # recursive: nested packages stay guarded
        text = py.read_text(encoding="utf-8")
        for needle in banned:
            assert needle not in text, f"{py.name} contains {needle!r}"
        # sys.stdin must never appear OUTSIDE the regex worker payload string
        # (the worker runs in a short-lived subprocess guarded for backtracking;
        # the sandboxed worker receives JSON over its own stdin by design).
        if "sys.stdin" in text:
            for lineno, line in enumerate(text.splitlines(), 1):
                if "sys.stdin" in line:
                    assert (
                        "payload = json.loads(sys.stdin.read())" in line
                        or line.strip().startswith("#")
                    ), f"{py.name}:{lineno} touches sys.stdin directly"
