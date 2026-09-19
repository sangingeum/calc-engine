"""Unit tests: datetime operations (spec examples + error taxonomy)."""

from __future__ import annotations

import pytest

from calc.errors import ArgumentError, UnitError
from calc.ops import datetime_ops as dt


class TestFromEpoch:
    def test_utc_default(self) -> None:
        assert dt.from_epoch("1700000000") == "2023-11-14T22:13:20+00:00"

    def test_tz(self) -> None:
        assert dt.from_epoch("1700000000", tz="Asia/Seoul") == "2023-11-15T07:13:20+09:00"

    def test_invalid_epoch(self) -> None:
        with pytest.raises(ArgumentError, match="invalid epoch seconds"):
            dt.from_epoch("soon")

    def test_unknown_tz_is_value_error(self) -> None:
        with pytest.raises(UnitError, match="unknown timezone"):
            dt.from_epoch("1700000000", tz="Mars/Olympus")


class TestToEpoch:
    def test_roundtrip(self) -> None:
        assert dt.to_epoch("2023-11-14T22:13:20+00:00") == 1700000000

    def test_offset_timezone(self) -> None:
        assert dt.to_epoch("2023-11-15T07:13:20+09:00") == 1700000000

    def test_naive_timestamp_rejected(self) -> None:
        with pytest.raises(ArgumentError, match="naive timestamp"):
            dt.to_epoch("2023-11-14T22:13:20")

    def test_garbage(self) -> None:
        with pytest.raises(ArgumentError, match="invalid ISO-8601"):
            dt.to_epoch("not-a-time")


class TestDiff:
    def test_days(self) -> None:
        assert (
            dt.diff("2024-01-01T00:00:00+00:00", "2024-03-01T00:00:00+00:00", unit="days")
            == 60.0
        )

    def test_hours(self) -> None:
        assert (
            dt.diff("2024-01-01T00:00:00+00:00", "2024-01-01T06:00:00+00:00", unit="hours")
            == 6.0
        )

    def test_seconds_default(self) -> None:
        assert dt.diff("2024-01-01T00:00:00+00:00", "2024-01-01T00:01:00+00:00") == 60.0

    def test_negative_when_reversed(self) -> None:
        assert (
            dt.diff("2024-03-01T00:00:00+00:00", "2024-01-01T00:00:00+00:00", unit="days")
            == -60.0
        )

    def test_unknown_unit(self) -> None:
        with pytest.raises(ArgumentError, match="unknown diff unit"):
            dt.diff("2024-01-01T00:00:00+00:00", "2024-01-02T00:00:00+00:00", unit="moons")

    def test_mixed_offsets_normalised(self) -> None:
        # same instant, +09:00 vs +00:00 -> zero
        assert (
            dt.diff("2024-01-01T09:00:00+09:00", "2024-01-01T00:00:00+00:00", unit="seconds")
            == 0.0
        )


class TestAdd:
    def test_days_rollover(self) -> None:
        assert dt.add("2024-02-28T12:00:00+00:00", days=2) == "2024-03-01T12:00:00+00:00"

    def test_weeks(self) -> None:
        assert dt.add("2024-01-01T00:00:00+00:00", weeks=1) == "2024-01-08T00:00:00+00:00"

    def test_hours(self) -> None:
        assert dt.add("2024-01-01T23:00:00+00:00", hours=2) == "2024-01-02T01:00:00+00:00"

    def test_combined_units(self) -> None:
        assert (
            dt.add("2024-01-01T00:00:00+00:00", days=1, hours=1, minutes=1, seconds=1)
            == "2024-01-02T01:01:01+00:00"
        )

    def test_naive_with_tz(self) -> None:
        assert dt.add("2024-03-10T12:00:00", days=1, tz="America/New_York").endswith("-04:00")

    def test_naive_without_tz_rejected(self) -> None:
        with pytest.raises(ArgumentError, match="naive timestamp"):
            dt.add("2024-03-10T12:00:00", days=1)


class TestWeekday:
    def test_leap_day(self) -> None:
        assert dt.weekday("2024-02-29") == "Thursday"

    def test_sunday(self) -> None:
        assert dt.weekday("2024-03-10") == "Sunday"

    def test_invalid_date(self) -> None:
        with pytest.raises(ArgumentError, match="invalid date"):
            dt.weekday("2024-02-30")


class TestConvertTz:
    def test_spec_example(self) -> None:
        # 2024-03-10 is the US DST transition: 12:00 EST = 2024-03-11T01:00+09:00
        assert (
            dt.convert_tz("2024-03-10T12:00:00", from_tz="America/New_York", to_tz="Asia/Seoul")
            == "2024-03-11T01:00:00+09:00"
        )

    def test_naive_without_from_rejected(self) -> None:
        with pytest.raises(ArgumentError, match="naive timestamp"):
            dt.convert_tz("2024-03-10T12:00:00", to_tz="Asia/Seoul")

    def test_unknown_target_tz(self) -> None:
        with pytest.raises(UnitError, match="unknown timezone"):
            dt.convert_tz("2024-03-10T12:00:00+00:00", from_tz="UTC", to_tz="Nowhere/Nothing")

    def test_aware_target_default_utc(self) -> None:
        assert dt.convert_tz("2024-03-10T12:00:00+00:00") == "2024-03-10T12:00:00+00:00"
