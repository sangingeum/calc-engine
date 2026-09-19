"""Date/time operations (ratified plan).

The reference time is always passed in as an argument (no ``now``). Output is
ISO-8601 with explicit offset. Naive timestamps are an ArgumentError unless a
timezone is supplied (--tz on from-epoch/add/weekday, --from on convert-tz) —
this is the most common source of time-calculation bugs. Unknown timezones are
a ValueError (UnitError). ``add`` deliberately supports only calendar-safe
units: days, hours, minutes, seconds, weeks — no month arithmetic.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from calc.errors import ArgumentError, UnitError

_ADD_UNITS: dict[str, timedelta] = {}


def _load_zone(name: str) -> ZoneInfo:
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError, KeyError) as exc:
        raise UnitError(f"unknown timezone: {name!r}") from exc


def _parse_timestamp(text: str, *, tz_name: str | None = None) -> datetime:
    """Parse ISO-8601; naive input requires tz_name (ArgumentError otherwise)."""
    try:
        parsed = datetime.fromisoformat(text.strip())
    except ValueError:
        raise ArgumentError(f"invalid ISO-8601 timestamp: {text!r}") from None
    if parsed.tzinfo is None:
        if tz_name is None:
            raise ArgumentError(f"naive timestamp {text!r} without offset: pass --tz or --from")
        return parsed.replace(tzinfo=_load_zone(tz_name))
    return parsed


def _iso(value: datetime) -> str:
    return value.isoformat()


def from_epoch(epoch: str, *, tz: str | None = None) -> str:
    """Unix epoch seconds -> ISO-8601 (UTC by default, --tz for display zone)."""
    try:
        seconds = float(epoch)
    except ValueError:
        raise ArgumentError(f"invalid epoch seconds: {epoch!r}") from None
    instant = datetime.fromtimestamp(seconds, tz=UTC)
    if tz is not None:
        instant = instant.astimezone(_load_zone(tz))
    return _iso(instant)


def to_epoch(timestamp: str) -> int:
    """ISO-8601 (offset required) -> Unix epoch seconds as an integer."""
    parsed = _parse_timestamp(timestamp)
    return int(parsed.timestamp())


def diff(left: str, right: str, *, unit: str = "seconds") -> float:
    """Elapsed time from left to right (right - left) in the given unit."""
    factors = {"seconds": 1.0, "minutes": 60.0, "hours": 3600.0, "days": 86400.0}
    if unit not in factors:
        raise ArgumentError(
            f"unknown diff unit: {unit!r} (expected one of {', '.join(factors)})"
        )
    a = _parse_timestamp(left)
    b = _parse_timestamp(right)
    return (b - a).total_seconds() / factors[unit]


def add(
    timestamp: str,
    *,
    days: float = 0.0,
    hours: float = 0.0,
    minutes: float = 0.0,
    seconds: float = 0.0,
    weeks: float = 0.0,
    tz: str | None = None,
) -> str:
    """Shift a timestamp by calendar-safe units only (no month arithmetic)."""
    delta = timedelta(days=days, hours=hours, minutes=minutes, seconds=seconds, weeks=weeks)
    parsed = _parse_timestamp(timestamp, tz_name=tz)
    return _iso(parsed + delta)


_WEEKDAYS = (
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
)


def weekday(date_text: str, *, tz: str | None = None) -> str:
    """Weekday name of a date or timestamp."""
    text = date_text.strip()
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        raise ArgumentError(f"invalid date: {date_text!r}") from None
    if parsed.tzinfo is None and tz is not None:
        parsed = parsed.replace(tzinfo=_load_zone(tz))
    # date-only input without --tz needs no timezone semantics
    return _WEEKDAYS[parsed.isoweekday() - 1]


def convert_tz(timestamp: str, *, from_tz: str | None = None, to_tz: str = "UTC") -> str:
    """Re-express a timestamp in another timezone; naive input requires --from."""
    parsed = _parse_timestamp(timestamp, tz_name=from_tz)
    return _iso(parsed.astimezone(_load_zone(to_tz)))
