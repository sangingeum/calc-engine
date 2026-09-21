"""GitHub issue 6 (`distribution` silently accepts unknown ``--flags``).

Root cause (issue report, confirmed at 66d6eb5): ``_normalize_positionals``
classifies any unregistered token as a positional; a token shaped like a long
option (``--foo``) therefore lands behind ``--``, where ``distribution``'s two
``nargs=\"?\"`` positionals (``value``, ``family2``) swallow it. Expected:
``ArgumentError: unrecognized arguments: ...`` (exit 1), as at baseline
5206a52. Also pins the owner-ratified family tightening: for every
``distribution`` op except ``compare-moments``, parameters that do not belong
to the chosen family are rejected.
"""

from __future__ import annotations

from conftest import run_calc


def test_distribution_unknown_long_option_rejected() -> None:
    proc = run_calc(
        "distribution", "mean", "normal", "--mu", "0", "--sigma", "1", "--foo", "3"
    )
    assert proc.returncode == 1
    assert proc.stdout == ""
    assert proc.stderr.startswith(
        "ArgumentError: unrecognized arguments: --foo 3"
    ), proc.stderr
    assert proc.stderr.count("\n") == 1


def test_distribution_unknown_long_option_without_value_rejected() -> None:
    proc = run_calc("distribution", "mean", "normal", "--mu", "0", "--sigma", "1", "--foo")
    assert proc.returncode == 1
    assert proc.stdout == ""
    assert proc.stderr.startswith("ArgumentError: unrecognized arguments: --foo")


def test_unknown_long_option_rejected_on_every_subcommand() -> None:
    """Parametrized over representative valid invocations of all subcommands."""
    cases: list[list[str]] = [
        ["eval", "2+2"],
        ["stat", "mean", "[1,2,3]"],
        ["finance", "fv", "--rate", "0.05", "--periods", "10", "--pv", "1000"],
        ["matrix", "transpose", "[[1,2]]"],
        ["convert-base", "255", "--from", "dec", "--to", "hex"],
        ["convert-unit", "1", "m", "km"],
        ["calculus", "derive", "x**2", "--var", "x"],
        ["physics-constant", "c"],
        # physics: dynamic `--symbol value` pairs are extracted upstream by
        # design, so a stray long option does not surface as argparse noise;
        # the domain validator already rejects it by name.
        # ["physics", "kinematics", "--solve", "d", "--u", "1", "--t", "2"],
        ["vector", "norm", "[3,4]"],
        ["bits", "and", "0xF0", "0x3C", "--width", "8"],
        ["endian", "to-bytes", "1", "--width", "16", "--order", "little"],
        ["hash", "sha256", "hello"],
        ["crc", "crc32", "hello"],
        ["base64", "encode", "hello"],
        ["datetime", "from-epoch", "0"],
        ["regex", "test", "a", "a"],
        ["distribution", "mean", "normal", "--mu", "0", "--sigma", "1"],
        ["assert", "equal", "1", "1"],
        ["gof", "chi2", "[18,22,20,20]", "[20,20,20,20]", "--field", "p"],
        ["sym", "simplify", "x+x", "--var", "x"],
    ]
    for args in cases:
        proc = run_calc(*args, "--definitely-unknown", "1")
        assert proc.returncode == 1, (args, proc.stdout, proc.stderr)
        assert proc.stdout == "", (args, proc.stdout)
        assert proc.stderr.startswith(
            "ArgumentError: unrecognized arguments: --definitely-unknown"
        ), (args, proc.stderr)
        assert proc.stderr.count("\n") == 1


def test_r2_leading_dash_behavior_preserved() -> None:
    """Issue 6 fix must not regress the R2 leading-dash positional contract."""
    proc = run_calc("eval", "-2+5")
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout == "3\n"
    proc = run_calc("eval", "--", "-2+5")
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout == "3\n"
    proc = run_calc("hash", "sha256", "-abc")
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout != ""
    proc = run_calc("regex", "test", "-x", "-x")
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout == "true\n"
    proc = run_calc("assert", "between", "-0.5", "-1", "0")
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout == "true\n"


def test_explicit_double_dash_forces_positional() -> None:
    proc = run_calc("hash", "sha256", "--", "--foo")
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout != ""


# Owner-ratified family tightening (issue 6 secondary observation). ----------


def test_irrelevant_parameter_rejected_normal() -> None:
    proc = run_calc(
        "distribution", "mean", "normal", "--mu", "0", "--sigma", "1", "--alpha", "3"
    )
    assert proc.returncode == 1
    assert proc.stdout == ""
    assert proc.stderr == "ArgumentError: --alpha is not a parameter of normal\n"


def test_irrelevant_parameter_rejected_beta() -> None:
    proc = run_calc("distribution", "mean", "beta", "--alpha", "2", "--beta", "2", "--a", "9")
    assert proc.returncode == 1
    assert proc.stdout == ""
    assert proc.stderr == "ArgumentError: --a is not a parameter of beta\n"


def test_irrelevant_suffixed_parameter_rejected() -> None:
    proc = run_calc(
        "distribution", "cdf", "normal", "1", "--mu", "0", "--sigma", "1", "--sigma2", "5"
    )
    assert proc.returncode == 1
    assert proc.stdout == ""
    assert proc.stderr == "ArgumentError: --sigma2 is not a parameter of normal\n"


def test_compare_moments_exempt_from_family_tightening() -> None:
    """compare-moments keeps tolerant parsing (both families' params coexist)."""
    proc = run_calc(
        "distribution", "compare-moments", "beta", "--alpha", "2", "--beta", "2",
        "--family2", "uniform", "--low2", "0", "--high2", "1", "--moment", "mean",
    )
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout == "true\n"


def test_family_params_still_accepted() -> None:
    """The tightening only rejects non-members; correct params are untouched."""
    proc = run_calc("distribution", "mean", "normal", "--mu", "0", "--sigma", "1")
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout == "0.0000\n"
    proc = run_calc("distribution", "validate", "beta", "--alpha", "2", "--beta", "2")
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout == "true\n"
