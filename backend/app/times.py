"""UTC timestamp parsing. Every stored time uses the same ISO form."""

from datetime import date, datetime, time, timedelta, timezone

UTC = timezone.utc


def parse_utc(value: str) -> datetime:
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def format_utc(value: datetime) -> str:
    stamped = value.astimezone(UTC).replace(microsecond=0)
    return stamped.strftime("%Y-%m-%dT%H:%M:%SZ")


def day_bounds(delivery_day: date) -> tuple[datetime, datetime]:
    start = datetime.combine(delivery_day, time(0), tzinfo=UTC)
    return start, start + timedelta(days=1)


def parse_hhmm(value: str) -> time:
    parts = value.split(":")
    if len(parts) != 2 or not all(part.isdigit() for part in parts):
        raise ValueError("cutoff must be HH:MM")
    hour, minute = int(parts[0]), int(parts[1])
    if hour > 23 or minute > 59 or len(parts[0]) != 2 or len(parts[1]) != 2:
        raise ValueError("cutoff must be HH:MM")
    return time(hour, minute)
