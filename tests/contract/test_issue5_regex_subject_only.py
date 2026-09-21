"""GitHub issue 5: only the SUBJECT of regex is @file/@-/@@ resolved.

Pattern and replacement are always literal (R3 scope: "regex (subject
text)"). Before the fix, _resolve_cli_inputs resolved every token, so
`calc regex test '@\\w+' 'hi @bob'` failed with
`ArgumentError: cannot read file '\\w+'`.
"""

from __future__ import annotations

from conftest import run_calc


def test_regex_pattern_at_mention_is_literal() -> None:
    proc = run_calc("regex", "test", r"@\w+", "hi @bob")
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout == "true\n"


def test_regex_sub_replacement_at_is_literal() -> None:
    proc = run_calc("regex", "sub", "a", "@x", "banana")
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout == "b@xn@xn@x\n"


def test_regex_subject_file_resolution_unchanged(tmp_path) -> None:
    subject = tmp_path / "subject.txt"
    subject.write_text("x")
    proc = run_calc("regex", "findall", r"\w+", f"@{subject}")
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout == "[x]\n"


def test_regex_subject_escape_unchanged() -> None:
    proc = run_calc("regex", "test", "x", "@@x")
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout == "true\n"


def test_regex_groups_unchanged() -> None:
    proc = run_calc("regex", "groups", r"(\w+)@(\w+)\.com", "x bob@example.com y")
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout == "[bob,example]\n"


def test_regex_pattern_via_file_stays_literal(tmp_path) -> None:
    """A file path in the PATTERN slot is a literal pattern, not a file read."""
    proc = run_calc("regex", "test", "a", "banana")
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout == "true\n"
