"""stat extension contract: multimode/mad/range/percentile/zscore."""

from __future__ import annotations

from conftest import run_calc


def test_multimode_all_modes_sorted() -> None:
    proc = run_calc("stat", "multimode", "[1,1,2,2,3]")
    assert proc.returncode == 0
    assert proc.stdout.strip() == "[1,2]"


def test_multimode_single_mode() -> None:
    proc = run_calc("stat", "multimode", "[1,1,2]")
    assert proc.stdout.strip() == "[1]"


def test_mad_median_absolute_deviation() -> None:
    # data [1,2,3,4]: median 2.5, abs devs [1.5,0.5,0.5,1.5] -> median 1.0
    proc = run_calc("stat", "mad", "[1,2,3,4]")
    assert proc.stdout.strip() == "1.0000"


def test_range() -> None:
    assert run_calc("stat", "range", "[1,7]").stdout.strip() == "6"


def test_percentile_90() -> None:
    proc = run_calc("stat", "percentile", "[1,2,3,4,5]", "90")
    assert proc.stdout.strip() == "4.6000"  # identical to quantile q=0.9


def test_percentile_50_equals_median() -> None:
    proc = run_calc("stat", "percentile", "[1,2,3,4,5]", "50")
    assert proc.stdout.strip() == "3.0000"


def test_percentile_out_of_range() -> None:
    proc = run_calc("stat", "percentile", "[1,2,3]", "101")
    assert proc.returncode == 1
    assert proc.stderr.startswith("MathError: stat percentile P must be in [0, 100]")


def test_zscore_reference() -> None:
    # data [1,2,3,4]: mean 2.5, sample stdev ~1.2910; (2-2.5)/1.2910 = -0.3873
    proc = run_calc("stat", "zscore", "[1,2,3,4]", "2")
    assert proc.stdout.strip() == "-0.3873"


def test_zscore_zero_stdev() -> None:
    proc = run_calc("stat", "zscore", "[5,5,5]", "5")
    assert proc.returncode == 1
    assert proc.stderr.startswith("MathError: stat zscore undefined")


def test_zscore_missing_x() -> None:
    proc = run_calc("stat", "zscore", "[1,2,3]")
    assert proc.returncode == 1
    assert proc.stderr.startswith("ArgumentError: stat zscore takes exactly")


def test_legacy_ops_byte_identical() -> None:
    assert run_calc("stat", "mean", "[1,2,3,4]").stdout == "2.5000\n"
    assert run_calc("stat", "mode", "[1,2,2,3]").stdout == "2\n"
    assert run_calc("stat", "quantile", "[1,2,3,4,5]", "0.5").stdout == "3.0000\n"
