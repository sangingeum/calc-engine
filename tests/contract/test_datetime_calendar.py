"""datetime calendar extensions: month/year add with clamping, business-days."""

from __future__ import annotations

from conftest import run_calc


def test_add_months_clamps_end_of_month() -> None:
    proc = run_calc("datetime", "add", "2026-01-31T00:00:00+00:00", "--months", "1")
    assert proc.returncode == 0
    assert proc.stdout.strip() == "2026-02-28T00:00:00+00:00"


def test_add_months_leap_year_clamp() -> None:
    proc = run_calc("datetime", "add", "2024-01-31T00:00:00+00:00", "--months", "1")
    assert proc.stdout.strip() == "2024-02-29T00:00:00+00:00"


def test_add_years_clamps_feb29() -> None:
    proc = run_calc("datetime", "add", "2024-02-29T00:00:00+00:00", "--years", "1")
    assert proc.stdout.strip() == "2025-02-28T00:00:00+00:00"


def test_add_negative_and_wrapping_months() -> None:
    proc = run_calc("datetime", "add", "2026-01-31T00:00:00+00:00", "--months", "-1")
    assert proc.stdout.strip() == "2025-12-31T00:00:00+00:00"
    proc = run_calc("datetime", "add", "2026-01-31T00:00:00+00:00", "--months", "13")
    assert proc.stdout.strip() == "2027-02-28T00:00:00+00:00"


def test_add_fractional_months_rejected() -> None:
    proc = run_calc("datetime", "add", "2026-01-31T00:00:00+00:00", "--months", "1.5")
    assert proc.returncode == 1
    assert proc.stderr.startswith("ArgumentError: --months/--years take whole numbers")


def test_add_months_naive_requires_tz() -> None:
    proc = run_calc("datetime", "add", "2026-01-31", "--months", "1")
    assert proc.returncode == 1
    assert proc.stderr.startswith("ArgumentError: naive timestamp")


def test_add_months_with_tz_naive_input() -> None:
    proc = run_calc("datetime", "add", "2026-01-31", "--months", "1", "--tz", "UTC")
    assert proc.returncode == 0
    assert proc.stdout.strip() == "2026-02-28T00:00:00+00:00"


def test_business_days_basic() -> None:
    # 2026-10-05 (Mon) .. 2026-10-15 (Thu): 9 weekdays; the 16th excluded
    proc = run_calc("datetime", "business-days", "2026-10-05", "2026-10-16")
    assert proc.returncode == 0
    assert proc.stdout.strip() == "9"


def test_business_days_holidays() -> None:
    proc = run_calc(
        "datetime",
        "business-days",
        "2026-10-05",
        "2026-10-16",
        "--holidays",
        '["2026-10-09"]',
    )
    assert proc.stdout.strip() == "8"


def test_business_days_weekend_excluded() -> None:
    # Sat 2026-10-10 + Sun 2026-10-11 are not counted
    proc = run_calc("datetime", "business-days", "2026-10-10", "2026-10-12")
    assert proc.stdout.strip() == "0"


def test_business_days_half_open() -> None:
    # a Sunday-only range [Sat, Sun) counts 0; end date never counts
    proc = run_calc("datetime", "business-days", "2026-10-16", "2026-10-16")
    assert proc.stdout.strip() == "0"


def test_business_days_invalid_holidays_json() -> None:
    proc = run_calc(
        "datetime", "business-days", "2026-10-05", "2026-10-16", "--holidays", "nope"
    )
    assert proc.returncode == 1
    assert proc.stderr.startswith("SyntaxError: ")
