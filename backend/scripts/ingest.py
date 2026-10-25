"""Fetch Elexon FUELHH and WINDFOR and rebuild data/wind.db.

Run locally. The deployed app never calls Elexon.
"""

from __future__ import annotations

import json
import sqlite3
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta
from pathlib import Path

from backend.app.config import (
    ACTUALS_FROM,
    ACTUALS_MAX,
    ACTUALS_MIN,
    ACTUALS_TO,
    DB_PATH,
    ELEXON_BASE,
    EXPECTED_ACTUALS,
    FORECAST_PUBLISH_FROM,
    FORECAST_PUBLISH_TO,
    FUEL_TYPE,
    RAW_DIR,
)
from backend.app.times import UTC, format_utc, parse_utc

USER_AGENT = "wind-forecast-monitor/1.0"


def _daterange_chunks(start: date, end: date, days: int):
    cursor = start
    while cursor <= end:
        chunk_end = min(cursor + timedelta(days=days - 1), end)
        yield cursor, chunk_end
        cursor = chunk_end + timedelta(days=1)


def _each_day(start: date, end: date):
    cursor = start
    while cursor <= end:
        yield cursor
        cursor += timedelta(days=1)


def fetch_json(url: str) -> list[dict]:
    """GET JSON. 429/500 back off; a 400 prints the body and stops."""
    delay = 1.0
    last_error: Exception | None = None
    for _attempt in range(7):
        request = urllib.request.Request(
            url,
            headers={"Accept": "application/json", "User-Agent": USER_AGENT},
        )
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                payload = json.loads(response.read().decode("utf-8"))
            if isinstance(payload, dict) and "data" in payload:
                payload = payload["data"]
            if not isinstance(payload, list):
                raise RuntimeError(f"Unexpected payload from {url}")
            return payload
        except urllib.error.HTTPError as error:
            body = error.read().decode("utf-8", errors="replace")
            if error.code == 400:
                print(body)
                raise SystemExit(1) from error
            if error.code in (429, 500, 502, 503, 504):
                print(f"HTTP {error.code} from {url}; retrying in {delay:.0f}s")
                time.sleep(delay)
                delay *= 2
                last_error = error
                continue
            raise
        except urllib.error.URLError as error:
            print(f"Network error for {url}; retrying in {delay:.0f}s ({error})")
            time.sleep(delay)
            delay *= 2
            last_error = error
    raise SystemExit(f"Gave up fetching {url}: {last_error}")


def _save_raw(name: str, rows: list[dict]) -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    path = RAW_DIR / name
    path.write_text(json.dumps(rows), encoding="utf-8")
    print(f"saved {path.name} ({len(rows)} rows)")


def fetch_actuals() -> list[dict]:
    start = date.fromisoformat(ACTUALS_FROM)
    end = date.fromisoformat(ACTUALS_TO)
    collected: list[dict] = []
    for chunk_start, chunk_end in _daterange_chunks(start, end, 7):
        params = urllib.parse.urlencode(
            {
                "settlementDateFrom": chunk_start.isoformat(),
                "settlementDateTo": chunk_end.isoformat(),
                "fuelType": FUEL_TYPE,
            }
        )
        url = f"{ELEXON_BASE}/FUELHH/stream?{params}"
        rows = fetch_json(url)
        _save_raw(f"fuelhh_{chunk_start.isoformat()}_{chunk_end.isoformat()}.json", rows)
        collected.extend(rows)
        time.sleep(0.15)
    return collected


def fetch_forecasts() -> list[dict]:
    start = date.fromisoformat(FORECAST_PUBLISH_FROM)
    end = date.fromisoformat(FORECAST_PUBLISH_TO)
    collected: list[dict] = []
    for day in _each_day(start, end):
        nxt = day + timedelta(days=1)
        params = urllib.parse.urlencode(
            {
                "publishDateTimeFrom": f"{day.isoformat()}T00:00:00Z",
                "publishDateTimeTo": f"{nxt.isoformat()}T00:00:00Z",
            }
        )
        url = f"{ELEXON_BASE}/WINDFOR/stream?{params}"
        rows = fetch_json(url)
        _save_raw(f"windfor_{day.isoformat()}.json", rows)
        collected.extend(rows)
        time.sleep(0.15)
    return collected


def normalise_actuals(rows: list[dict]) -> list[tuple[str, float]]:
    """Keep WIND rows. One row per start_time: the latest publishTime."""
    best: dict[str, tuple[datetime, float]] = {}
    for row in rows:
        if row.get("fuelType") != FUEL_TYPE:
            continue
        generation = row.get("generation")
        if generation is None:
            continue
        start = format_utc(parse_utc(row["startTime"]))
        published = parse_utc(row["publishTime"])
        current = best.get(start)
        if current is None or published >= current[0]:
            best[start] = (published, float(generation))
    return [(start, value) for start, (_published, value) in sorted(best.items())]


def normalise_forecasts(rows: list[dict]) -> list[tuple[str, str, float, float]]:
    """Drop non-forecast rows (horizon <= 0) and duplicate keys."""
    best: dict[tuple[str, str], tuple[float, float]] = {}
    for row in rows:
        generation = row.get("generation")
        if generation is None:
            continue
        published = parse_utc(row["publishTime"])
        start = parse_utc(row["startTime"])
        horizon_h = (start - published).total_seconds() / 3600.0
        if horizon_h <= 0:
            continue
        key = (format_utc(published), format_utc(start))
        best[key] = (float(generation), horizon_h)
    return [
        (publish, start, generation, horizon)
        for (publish, start), (generation, horizon) in sorted(best.items())
    ]


def write_database(
    actuals: list[tuple[str, float]],
    forecasts: list[tuple[str, str, float, float]],
    path: Path = DB_PATH,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.unlink()
    connection = sqlite3.connect(path)
    try:
        connection.executescript(
            """
            CREATE TABLE actuals (
              start_time TEXT PRIMARY KEY,
              generation REAL NOT NULL
            );
            CREATE TABLE forecasts (
              publish_time TEXT NOT NULL,
              start_time   TEXT NOT NULL,
              generation   REAL NOT NULL,
              horizon_h    REAL NOT NULL,
              PRIMARY KEY (publish_time, start_time)
            );
            CREATE INDEX idx_fc_start ON forecasts(start_time);
            CREATE INDEX idx_fc_pub   ON forecasts(publish_time);
            """
        )
        connection.executemany(
            "INSERT INTO actuals (start_time, generation) VALUES (?, ?)",
            actuals,
        )
        connection.executemany(
            """
            INSERT INTO forecasts (publish_time, start_time, generation, horizon_h)
            VALUES (?, ?, ?, ?)
            """,
            forecasts,
        )
        connection.commit()
    finally:
        connection.close()


def assert_database(path: Path = DB_PATH) -> dict:
    """Fail loudly when the built database does not match the spec."""
    connection = sqlite3.connect(path)
    try:
        actual_times = [
            row[0]
            for row in connection.execute("SELECT start_time FROM actuals ORDER BY start_time")
        ]
        count = len(actual_times)
        if count != EXPECTED_ACTUALS:
            raise AssertionError(f"actuals count {count} != {EXPECTED_ACTUALS}")
        if not actual_times:
            raise AssertionError("actuals table is empty")
        if actual_times[0] != ACTUALS_MIN:
            raise AssertionError(f"min start_time {actual_times[0]} != {ACTUALS_MIN}")
        if actual_times[-1] != ACTUALS_MAX:
            raise AssertionError(f"max start_time {actual_times[-1]} != {ACTUALS_MAX}")
        parsed = [parse_utc(value) for value in actual_times]
        for previous, current in zip(parsed, parsed[1:]):
            gap = current - previous
            if gap != timedelta(minutes=30):
                raise AssertionError(f"actual gap {previous} -> {current} is {gap}, expected 30 min")

        publish_times = [
            row[0]
            for row in connection.execute("SELECT DISTINCT publish_time FROM forecasts ORDER BY 1")
        ]
        run_days = {value[:10] for value in publish_times}
        required_start = date.fromisoformat(FORECAST_PUBLISH_FROM)
        required_end = date.fromisoformat(FORECAST_PUBLISH_TO)
        missing = [
            day.isoformat()
            for day in _each_day(required_start, required_end)
            if day.isoformat() not in run_days
        ]
        if missing:
            raise AssertionError(f"days with no forecast run: {', '.join(missing)}")

        non_positive = connection.execute(
            "SELECT COUNT(*) FROM forecasts WHERE horizon_h <= 0"
        ).fetchone()[0]
        if non_positive:
            raise AssertionError(f"{non_positive} forecast rows have horizon_h <= 0")

        forecast_rows = connection.execute("SELECT COUNT(*) FROM forecasts").fetchone()[0]
        per_day: dict[str, int] = {}
        for published in publish_times:
            per_day[published[:10]] = per_day.get(published[:10], 0) + 1
        return {
            "actuals": count,
            "forecast_rows": forecast_rows,
            "runs": len(publish_times),
            "runs_per_day": per_day,
        }
    finally:
        connection.close()


def print_summary(summary: dict) -> None:
    print(f"actuals: {summary['actuals']}")
    print(f"forecast rows: {summary['forecast_rows']}")
    print(f"distinct runs: {summary['runs']}")
    print("runs per day:")
    for day, count in summary["runs_per_day"].items():
        print(f"  {day}  {count}")


def main() -> None:
    print(f"Elexon base: {ELEXON_BASE}")
    actual_raw = fetch_actuals()
    forecast_raw = fetch_forecasts()
    actuals = normalise_actuals(actual_raw)
    forecasts = normalise_forecasts(forecast_raw)
    write_database(actuals, forecasts)
    summary = assert_database()
    print_summary(summary)


if __name__ == "__main__":
    main()
