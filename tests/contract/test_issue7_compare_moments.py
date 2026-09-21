"""GitHub issue 7: compare-moments must work on every supported interpreter.

The documented interleaved form (`... beta --alpha 2 --beta 2 uniform --low
0 --high 1 --moment mean`) relied on argparse routing a post-option
positional into the nargs="?" slot `value`, which is version-specific
(3.12.3 leaves the token unmatched → "unrecognized arguments: uniform").
Fix: `_normalize_positionals` now rebuilds argv as `<cmd> <options> --
<positionals>` for interleaved positionals too (single-dash hazard is no
longer the trigger), so `family2` receives the second family token on
every interpreter, and `--family2` is a registered option (preferred form).
"""

from __future__ import annotations

import re

from conftest import run_calc

_INTERLEAVED = [
    "distribution",
    "compare-moments",
    "beta",
    "--alpha",
    "2",
    "--beta",
    "2",
]


def test_compare_moments_documented_interleaved_form() -> None:
    proc = run_calc(*_INTERLEAVED, "uniform", "--low", "0", "--high", "1", "--moment", "mean")
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout == "true\n"


def test_compare_moments_explicit_family2_form() -> None:
    proc = run_calc(
        *_INTERLEAVED, "--family2", "uniform", "--low2", "0", "--high2", "1", "--moment", "mean"
    )
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout == "true\n"


def test_compare_moments_post_option_positional_form() -> None:
    proc = run_calc(
        *_INTERLEAVED, "--moment", "mean", "uniform", "--low2", "0", "--high2", "1"
    )
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout == "true\n"


def test_compare_moments_variance_false_all_forms() -> None:
    for args in (
        [*_INTERLEAVED, "uniform", "--low", "0", "--high", "1", "--moment", "variance"],
        [
            *_INTERLEAVED,
            "--family2",
            "uniform",
            "--low2",
            "0",
            "--high2",
            "1",
            "--moment",
            "variance",
        ],
        [*_INTERLEAVED, "--moment", "variance", "uniform", "--low2", "0", "--high2", "1"],
    ):
        proc = run_calc(*args)
        assert proc.returncode == 0, proc.stderr
        assert proc.stdout == "false\n", (args, proc.stdout)


def test_compare_moments_familyX_rejected() -> None:
    """After --family2 became a real option, --familyX must be unrecognized."""
    proc = run_calc(
        *_INTERLEAVED, "--familyX", "uniform", "--low", "0", "--high", "1", "--moment", "mean"
    )
    assert proc.returncode == 1
    assert proc.stdout == ""
    assert proc.stderr.startswith("ArgumentError: unrecognized arguments: --familyX")
    assert proc.stderr.count("\n") == 1


def test_skill_and_readme_compare_moments_examples_run() -> None:
    """Doc-example test (spirit of the doc-drift guard): every
    `calc distribution compare-moments ...` example in SKILL.md/README.md
    executes and produces the comment it claims."""
    repo = __import__("pathlib").Path(__file__).resolve().parents[2]
    for doc in (repo / "SKILL.md", repo / "README.md"):
        text = doc.read_text(encoding="utf-8")
        for line in text.splitlines():
            match = re.match(r"calc distribution compare-moments (.+?)\s+# (.+)$", line)
            if not match:
                continue
            args, expected = match.group(1), match.group(2).split()[0]
            proc = run_calc(*["distribution", "compare-moments", *args.split()])
            assert proc.returncode == 0, (doc.name, line, proc.stderr)
            assert proc.stdout.strip() == expected, (doc.name, line, proc.stdout)
