"""GitHub issue 10 contract: the ``two-point`` step-CDF family over stdout.

Byte-exact stdout on success, exactly one typed stderr line on failure, and the
``@file`` resolver still applies to the DATA positional (ops stay pure; the CLI
layer resolves inputs).
"""

from __future__ import annotations

from conftest import run_calc

PERFECT_50_50 = "[" + ",".join(["0.25"] * 120 + ["0.75"] * 120) + "]"


def _two_point_args(data: str, *extra: str) -> list[str]:
    return [
        "gof", "ks", data, "two-point",
        "--low", "0.25", "--high", "0.75",
        "--weight-low", "0.5", "--weight-high", "0.5",
        *extra,
    ]


def test_two_point_perfect_match_prints_zero() -> None:
    proc = run_calc(*_two_point_args(PERFECT_50_50, "--field", "statistic"))
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout == "0.0000\n"
    assert proc.stderr == ""


def test_two_point_mismatch_prints_pinned_statistic() -> None:
    data = "[" + ",".join(["0.25"] * 140 + ["0.75"] * 100) + "]"
    proc = run_calc(*_two_point_args(data, "--field", "statistic"))
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout == "0.0833\n"
    # precision applies at render time only
    proc12 = run_calc(*_two_point_args(data, "--field", "statistic", "--precision", "12"))
    assert proc12.returncode == 0, proc12.stderr
    assert proc12.stdout == "0.083333333333\n"


def test_two_point_weighted_match_prints_zero() -> None:
    data = "[" + ",".join(["0.25"] * 60 + ["0.75"] * 180) + "]"
    proc = run_calc(
        "gof", "ks", data, "two-point",
        "--low", "0.25", "--high", "0.75",
        "--weight-low", "0.25", "--weight-high", "0.75",
        "--field", "statistic",
    )
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout == "0.0000\n"


def test_two_point_data_positional_accepts_file(tmp_path) -> None:
    data = tmp_path / "bimodal.json"
    data.write_text("[" + ",".join(["0.25"] * 120 + ["0.75"] * 120) + "]")
    proc = run_calc(*_two_point_args(f"@{data}", "--field", "statistic"))
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout == "0.0000\n"


def test_two_point_p_field_refused() -> None:
    proc = run_calc(*_two_point_args(PERFECT_50_50, "--field", "p"))
    assert proc.returncode == 1
    assert proc.stdout == ""
    assert proc.stderr == (
        "ArgumentError: two-point is a step CDF: --field p has no pinned convention "
        "(the continuous asymptotic p is conservative under ties); use --field "
        "statistic\n"
    )


def test_two_point_rejected_by_chi2_bins() -> None:
    proc = run_calc(
        "gof", "chi2-bins", PERFECT_50_50, "two-point",
        "--low", "0.25", "--high", "0.75",
        "--weight-low", "0.5", "--weight-high", "0.5",
        "--bins", "2", "--field", "statistic",
    )
    assert proc.returncode == 1
    assert proc.stdout == ""
    assert proc.stderr == (
        "ArgumentError: two-point is a step CDF (point masses, no PPF); only gof ks "
        "--field statistic supports it\n"
    )


def test_two_point_weights_must_sum_to_one() -> None:
    proc = run_calc(
        "gof", "ks", "[0.25,0.75]", "two-point",
        "--low", "0.25", "--high", "0.75",
        "--weight-low", "0.4", "--weight-high", "0.4",
        "--field", "statistic",
    )
    assert proc.returncode == 1
    assert proc.stdout == ""
    assert proc.stderr == "MathError: two-point requires weight-low + weight-high = 1\n"


def test_two_point_support_must_be_ordered() -> None:
    proc = run_calc(
        "gof", "ks", "[0.25,0.75]", "two-point",
        "--low", "0.75", "--high", "0.25",
        "--weight-low", "0.5", "--weight-high", "0.5",
        "--field", "statistic",
    )
    assert proc.returncode == 1
    assert proc.stdout == ""
    assert proc.stderr == "MathError: two-point requires low < high\n"


def test_two_point_requires_authored_locations() -> None:
    proc = run_calc(
        "gof", "ks", "[0.25,0.75]", "two-point",
        "--weight-low", "0.5", "--weight-high", "0.5",
        "--field", "statistic",
    )
    assert proc.returncode == 1
    assert proc.stdout == ""
    assert proc.stderr == (
        "ArgumentError: two-point requires --low and --high (the mass locations)\n"
    )
