# Wind Forecast Monitor — Cursor Spec

Paste this into the repo root (or into `.cursor/rules/project.mdc`) and tell Cursor to follow it.
Build in the order of section 9. Do not invent behaviour that is not in this file.

## 1. Goal

Web app for a UK utility's day-ahead buying team. It must:
1. Show the **latest wind forecast available at decision time** (the cutoff on D-1) for any delivery day in scope.
2. **Quantify forecast error** (actual vs forecast) so buyers can plan a safety margin.

Scope: national wind only, Elexon BMRS data only (FUELHH actuals, WINDFOR forecasts).
Decisions made in **January 2026** → decision days Jan 1–31, **delivery days Jan 2 – Feb 1, 2026**.

Priorities: correct functionality first, moderate clean design second. Time cap: 16 hours.

## 2. Stack and decisions (fixed)

- Backend: Python 3.11, FastAPI, pandas, SQLite (stdlib `sqlite3`), pytest.
- Frontend: React + Vite + TypeScript, Recharts, plain CSS or Tailwind. Keep it simple.
- Docker: one multi-stage Dockerfile + `docker-compose.yml` for local runs.
- Live deployment: **Vercel** (static frontend + FastAPI serverless function). The SQLite file is **prebuilt and committed**, opened **read-only** at runtime. Never write to disk at runtime.
- Default cutoff: **09:00 UTC on D-1**, configurable by the user in the UI.
  January UK time == UTC, so treat all times as UTC internally and say so in the UI.

## 3. Data facts (verified from real responses)

**FUELHH (actuals)**
- Endpoint: `GET https://bmrs.elexon.co.uk/api/v1/datasets/FUELHH/stream`
- Params used: `settlementDateFrom=2026-01-02`, `settlementDateTo=2026-02-01`, `fuelType=WIND`.
  **Do NOT send `settlementPeriod`** (it filters rows).
- Send header `Accept: application/json`. Handle 429/500 with exponential backoff; print the body on 400.
- Fields: `startTime` (UTC, half-hourly), `generation` (MW), `publishTime`, `settlementDate`, `settlementPeriod`.
- Verified: exactly 1,488 rows (31 days × 48), no gaps, no duplicates.

**WINDFOR (forecasts)**
- Endpoint: `GET https://bmrs.elexon.co.uk/api/v1/datasets/WINDFOR/stream`
- Params: `publishDateTimeFrom`, `publishDateTimeTo`. Pull `2026-01-01T00:00Z` → `2026-02-01T00:00Z`, **one day per request**.
- Fields: `publishTime`, `startTime` (UTC, **hourly**), `generation` (MW).
- Each `publishTime` is one forecast **run** of ~73 hourly rows.
- About 8 runs per day, irregular times (e.g. 02:30, 04:30, 07:30, 09:30, 12:25, 15:30, 18:30, 22:30). Never assume a schedule; use real `publishTime` values.
- **Rows with `startTime <= publishTime` are not forecasts** (they repeat the same values across runs). Drop them.
- Forecasts are revised between runs; the revisions view depends on this.

## 4. Directory structure

```
.
├── README.md
├── CURSOR_SPEC.md
├── Dockerfile
├── docker-compose.yml
├── vercel.json
├── requirements.txt
├── backend/
│   ├── app/
│   │   ├── main.py            # FastAPI app, routes under /api
│   │   ├── config.py          # DB path, default cutoff, constants
│   │   ├── db.py              # read-only sqlite connection helper
│   │   ├── schemas.py         # Pydantic response models
│   │   ├── services/
│   │   │   ├── decision.py    # select decision-time forecast
│   │   │   ├── align.py       # actuals -> hourly alignment
│   │   │   └── metrics.py     # pure metric functions
│   ├── scripts/
│   │   └── ingest.py          # fetch + build data/wind.db
│   ├── data/
│   │   ├── raw/               # raw JSON (committed)
│   │   └── wind.db            # prebuilt SQLite (committed)
│   └── tests/
│       ├── test_decision.py
│       ├── test_align.py
│       └── test_metrics.py
├── api/
│   └── index.py               # Vercel entry: exposes the FastAPI app
└── frontend/
    ├── package.json
    ├── vite.config.ts
    └── src/
        ├── main.tsx
        ├── App.tsx
        ├── api.ts             # typed fetch helpers
        ├── components/        # ControlBar, MetricCards, charts, tabs
        └── pages/             # Overview, Decision, ErrorAnalysis, Revisions
```

## 5. Database schema (SQLite)

```sql
CREATE TABLE actuals (
  start_time TEXT PRIMARY KEY,   -- ISO UTC, half-hourly
  generation REAL NOT NULL       -- MW
);
CREATE TABLE forecasts (
  publish_time TEXT NOT NULL,    -- ISO UTC
  start_time   TEXT NOT NULL,    -- ISO UTC, hourly
  generation   REAL NOT NULL,    -- MW
  horizon_h    REAL NOT NULL,    -- (start_time - publish_time) in hours, always > 0
  PRIMARY KEY (publish_time, start_time)
);
CREATE INDEX idx_fc_start ON forecasts(start_time);
CREATE INDEX idx_fc_pub   ON forecasts(publish_time);
```

## 6. Ingestion (`backend/scripts/ingest.py`)

1. Fetch actuals in 7-day chunks; save raw JSON to `data/raw/fuelhh_*.json`.
2. Fetch forecasts one day per request; save raw JSON to `data/raw/windfor_*.json`.
3. Normalise: parse times to UTC, filter `fuelType == "WIND"`, dedupe actuals by `start_time` keeping latest `publishTime`.
4. Forecasts: compute `horizon_h`, **drop rows with `horizon_h <= 0`**, dedupe on `(publish_time, start_time)`.
5. Write `data/wind.db` (recreate from scratch each run).
6. Assertions after load (fail loudly): actuals count == 1488; min `start_time` == `2026-01-02T00:00:00Z`; max == `2026-02-01T23:30:00Z`; all actual gaps == 30 min; at least one forecast run for every day from Dec 31 to Jan 31.
7. Print a summary: row counts, number of distinct runs, runs per day.
8. Ingestion runs locally only. The deployed app never calls Elexon.

## 7. Core logic

### 7.1 Decision-time forecast (`services/decision.py`)
For delivery day D (UTC date) and cutoff time `c` (default 09:00):
- `cutoff_ts = (D - 1 day) at c UTC`
- Candidates: forecasts where `publish_time <= cutoff_ts` and `start_time` in `[D 00:00, D+1 00:00)`.
- For each `start_time`, keep the row with the **latest `publish_time`** (groupby + tail(1)).
- Also return the chosen `publish_time` (the run used) and `horizon_h` per hour.
- If no run qualifies for a day, return empty and let the API report "no forecast available".

### 7.2 Aligning actuals to the hourly forecast (`services/align.py`)
- Forecast hour `H:00` represents the hour starting at H:00.
- Hourly actual = **mean of the actual at `H:00` and `H:30`**. If either half-hour is missing, drop that hour.
- Document this assumption in README and in a UI tooltip.

### 7.3 Metrics (`services/metrics.py`, pure functions, no DB access)
Error definition: `error = forecast - actual` (positive = over-forecast).
Return, for a set of aligned (forecast, actual) pairs:
- `n`, `mae`, `rmse`, `bias` (mean error), `mape` (skip rows with actual == 0), `p95_abs_error`, `max_abs_error`
- `nmae` = MAE / mean(actual), as a percentage

Breakdowns:
- **By hour of day** (0–23): MAE and bias for the decision forecast.
- **By horizon bucket** using **all runs** (not only decision forecasts): `0–12h`, `12–24h`, `24–36h`, `36–48h`, `48h+` → MAE, RMSE, bias, n.
- **Error band for planning**: P10 and P90 of the error, usable as "expected range" around a forecast.

## 8. API (all under `/api`, JSON)

Common query params: `from` and `to` (delivery dates, `YYYY-MM-DD`, default full range), `cutoff` (`HH:MM`, default `09:00`).

| Endpoint | Returns |
|---|---|
| `GET /api/meta` | date range, default cutoff, assumptions text, list of runs per day |
| `GET /api/series` | hourly rows: `time`, `actual`, `forecast`, `error`, `run_publish_time`, `horizon_h` |
| `GET /api/metrics` | summary metrics (7.3) for the range |
| `GET /api/error-by-hour` | list of `{hour, mae, bias, n}` |
| `GET /api/error-by-horizon` | list of `{bucket, mae, rmse, bias, n}` (all runs) |
| `GET /api/decision?date=YYYY-MM-DD` | decision forecast for one delivery day + the run used + error band from history |
| `GET /api/revisions?date=YYYY-MM-DD` | all runs covering that delivery day: `publish_time`, hourly values |

Rules: validate params with Pydantic, return 400 with a clear message for bad input, 404-style empty responses for no data, CORS allowed for local dev, no writes anywhere.

## 9. Frontend

Layout: header + control bar + 4 tabs. Moderate design: clean cards, one accent colour, consistent spacing, light theme, readable charts, responsive down to tablet.

Control bar: date range picker (limited to Jan 2 – Feb 1, 2026), cutoff time input with presets (`09:00` default, `09:20 EPEX GB`, `09:50 N2EX`), small "times are UTC" label.

Tabs:
1. **Overview**: metric cards (MAE, NMAE %, RMSE, bias, P95) + line chart actual vs decision forecast over the range.
2. **Decision view**: pick one delivery day. Show forecast vs actual for the day, the run used (publish time), horizon range, and the P10–P90 error band as a shaded area. Sentence: "Buying on this forecast, plan for roughly ±X MW of error."
3. **Error analysis**: bar chart error by hour of day; line or bar chart error by horizon bucket; optional histogram of errors.
4. **Revisions**: for a chosen delivery day, overlay all forecast runs (colour by publish time) and the actual.

Handle loading, empty and error states on every chart. Tooltips explain error sign (positive = over-forecast).

## 10. Docker

- Multi-stage `Dockerfile`: stage 1 builds the frontend (`npm ci && npm run build`); stage 2 is `python:3.11-slim`, installs requirements, copies backend + `frontend/dist`, serves static files and `/api` with uvicorn on port 8000.
- `docker-compose.yml`: one service, port `8000:8000`, mounts nothing (DB is baked in).
- Run: `docker compose up --build`, then open `http://localhost:8000`.

## 11. Vercel deployment

- `vercel.json`: build the frontend to `frontend/dist`; rewrite `/api/(.*)` to the Python function; everything else to the SPA.
- `api/index.py` imports and exposes the FastAPI `app`.
- Ensure `backend/data/wind.db` is included in the function bundle (`includeFiles` in `vercel.json` if needed).
- Open SQLite with `file:...?mode=ro` (uri=True). No runtime writes.
- Verify the current Vercel FastAPI/Python setup in its docs before configuring; if it fights back, fall back to Heroku Eco with the Dockerfile.
- Test the live URL in an incognito window.

## 12. Testing (write these, they matter most)

- `test_decision.py`: with a hand-made 3-run fixture, cutoff before/after a run picks the right run; a run published after the cutoff is never used; day with no eligible run returns empty.
- `test_align.py`: half-hour pairs average correctly; missing half-hour drops the hour.
- `test_metrics.py`: known small arrays give hand-computed MAE, RMSE, bias, P95; actual == 0 is skipped in MAPE; horizon bucket edges (12.0h goes to the correct bucket).
- Ingest sanity assertions from section 6.

## 13. README must contain

- Files and directories explained (use section 4).
- How to start: with Docker, and without (backend + frontend dev commands), and how to re-run ingestion.
- Link to the Vercel app.
- **AI usage statement**: built with Cursor and Claude assistance; state what was AI-assisted and that logic was reviewed and tested by the author.
- Assumptions: cutoff default and why configurable, hourly alignment by averaging, UTC == UK time in January, rows with `startTime <= publishTime` excluded, error sign convention.

## 14. Coding practices

- Type hints everywhere in Python; Pydantic models for responses.
- Pure functions for logic; keep I/O at the edges.
- No hard-coded dates outside `config.py`.
- Small commits with meaningful messages.
- No secrets needed (Elexon BMRS endpoints used here are open); do not add any.
- Keep the code readable enough to walk through in the 5-minute tech-lead video.

## 15. Build order for Cursor

1. Scaffold repo, `config.py`, `db.py`.
2. `ingest.py` + run it, check assertions, commit `wind.db`.
3. `decision.py`, `align.py`, `metrics.py` with tests (tests passing before any API).
4. FastAPI routes + schemas.
5. React app: Overview → Decision → Error analysis → Revisions.
6. Dockerfile + compose, test locally.
7. Vercel deploy, incognito check.
8. README, then record the video.
