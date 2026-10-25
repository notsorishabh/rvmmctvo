# Wind Forecast Monitor

National GB wind output is hard to buy against on D-1 because the forecast keeps moving and its error is large. This app is for a utility's day-ahead buying desk. It shows the latest Elexon WINDFOR forecast that existed at a chosen D-1 cutoff, compares it with FUELHH wind actuals for 2 January–1 February 2026, and shows a historically calibrated range for where the actual is likely to land.

## Live app

https://rvmmctvo.vercel.app/

## Key findings (January 2026, cutoff 09:00 UTC)

- **Accuracy:** the decision-time forecast has a mean absolute error of about 2,039 MW (18.1% of mean wind output) over 744 delivery hours.
- **Bias:** the forecast ran high. Mean error is about +1,748 MW, positive on 27 of 31 days, and positive at every horizon. No cause is claimed; see "Method and assumptions".
- **Planning range:** the P10–P90 range for the actual, built only from earlier days, contained the actual in 78.3% of hours (526 of 672) against a nominal 80%.
- **Horizon:** error grows with lead time, from roughly 1,700 MW MAE at 0–12 h to roughly 2,300 MW beyond 48 h.

## What the app does

| Tab | Purpose |
|---|---|
| **Overview** | Actual vs decision forecast over the chosen range, with MAE, NMAE, RMSE, bias and P95 error. |
| **Decision** | Pick one delivery day: the run used, its horizon, the forecast, the actual, and the likely range of the actual. |
| **Error analysis** | Error by hour of day, by forecast horizon (all runs), and a histogram of errors. |
| **Revisions** | Every forecast run covering a delivery day, with the decision run highlighted and runs after the cutoff greyed. |

The decision cutoff (time on D-1) is configurable, with presets for 09:00, 09:20 (EPEX GB) and 09:50 (N2EX). All times are UTC.

## Files and directories

```
.
├── README.md                  # this file
├── CURSOR_SPEC.md             # build spec used with Cursor
├── Dockerfile                 # multi-stage: Node 20 build, Python 3.12 serve
├── docker-compose.yml         # one service, port 8000
├── .dockerignore
├── .gitignore
├── .python-version            # 3.12 for Vercel
├── vercel.json                # static output + /api rewrite to the Python function
├── requirements.txt           # pinned API runtime dependencies only
├── pyproject.toml             # Python metadata and Vercel entrypoint
├── uv.lock                    # locked API dependencies (Python >=3.12)
├── pytest.ini
├── api/
│   └── index.py               # Vercel function: imports backend.app.main:app
├── backend/
│   ├── app/
│   │   ├── main.py            # FastAPI routes under /api; serves frontend/dist
│   │   ├── config.py          # dates, default cutoff, DB path, assumptions text
│   │   ├── db.py              # read-only SQLite connection (mode=ro)
│   │   ├── schemas.py         # Pydantic response models
│   │   ├── times.py           # UTC parsing and formatting
│   │   └── services/
│   │       ├── decision.py    # latest WINDFOR run at or before the cutoff
│   │       ├── align.py       # hourly actual = mean of H:00 and H:30
│   │       ├── metrics.py     # MAE, RMSE, bias, percentiles, breakdowns
│   │       ├── band.py        # likely range of actual from P10/P90 of error
│   │       ├── coverage.py    # expanding-window band coverage backtest
│   │       └── report.py      # loads SQLite and calls the pure functions
│   ├── scripts/
│   │   ├── ingest.py          # fetches Elexon JSON and rebuilds wind.db
│   │   └── diagnose_bias.py   # read-only bias breakdown (applies no correction)
│   ├── data/
│   │   ├── raw/               # committed Elexon JSON responses
│   │   └── wind.db            # committed SQLite database, opened read-only
│   └── tests/                 # unit tests: hand-made cases and known rows in wind.db
└── frontend/
    ├── package.json
    ├── vite.config.ts         # proxies /api to port 8000 in dev
    └── src/                   # React + TypeScript: Overview, Decision, Error analysis, Revisions
```

## How to start

**(a) With Docker**

```bash
docker compose up --build
```

Open http://localhost:8000. The image contains `wind.db` and the built UI, has no volumes, does not call Elexon and does not write to disk.

**(b) Without Docker** (Python 3.12+ and Node 20+)

```bash
pip install -r requirements.txt
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

In a second terminal:

```bash
cd frontend
npm ci
npm run dev
```

Vite proxies `/api` to port 8000. To serve the UI from FastAPI instead, run `npm run build` in `frontend/` and restart uvicorn; `frontend/dist` is mounted when it exists.

**(c) Rebuilding the data** (optional; the committed database is already built)

```bash
python backend/scripts/ingest.py
```

This refetches FUELHH (7-day chunks) and WINDFOR (one publish day per request), writes `backend/data/raw/*.json`, rebuilds `backend/data/wind.db`, and checks load assertions (for example, 1,488 half-hourly actuals). The deployed app never calls Elexon.

Note: the assignment links `https://bmrs.elexon.co.uk/api/v1/datasets`, which now returns the BMRS website. Ingestion uses `https://data.elexon.co.uk/bmrs/api/v1/datasets`, which serves the same dataset paths as JSON.

## Method and assumptions

**Data**
- Actuals: FUELHH, fuel type `WIND`, half-hourly. Forecasts: WINDFOR, hourly, many runs per day (each `publishTime` is one run).
- Scope: purchase decisions made in January 2026, so delivery days are 2 January–1 February 2026.

**Decision-time forecast**
- For delivery day D and cutoff time c, the decision forecast for each hour is the latest run published at or before D-1 at c (UTC).
- Default cutoff is **09:00 UTC on D-1**. It is configurable because GB auctions do not all close at the same time: EPEX GB closes at about 09:20 UK time and N2EX at about 09:50. These come from the exchanges' published auction schedules and may change.
- January UK civil time equals UTC, so every timestamp is stored and shown as UTC.
- WINDFOR rows with `startTime` at or before `publishTime` are not forecasts and are excluded.

**Comparing forecast and actual**
- A forecast hour starting at H:00 is compared with the **mean of the FUELHH actuals at H:00 and H:30**. If either half-hour is missing, that hour is dropped.
- **Error = forecast − actual.** Positive means an over-forecast; the actual equals the forecast minus the error.
- Metrics: MAE, NMAE (MAE divided by mean actual), RMSE, bias (mean error), P95 absolute error, plus breakdowns by hour of day and by horizon bucket (0–12, 12–24, 24–36, 36–48, 48+ hours, using all runs).

**Likely range of the actual**
- `band_low = max(0, forecast − P90(error))` and `band_high = forecast − P10(error)`.
- P10 and P90 use an **expanding window** of delivery days strictly before the selected day, at the same cutoff, so the band never uses information a buyer would not have had. With fewer than 3 prior days, no band is shown.
- Coverage backtest at cutoff 09:00 over 2 January–1 February 2026: **78.3% of actual hours landed inside the band (526 of 672 hours, 28 days)**. The first three delivery days have no band. The band was not tuned to raise this figure.

**Bias observations** (cutoff 09:00; no correction applied)
- Mean error about +1,748 MW; 27 of 31 days positive; every horizon bucket positive (about +1,400 to +1,900 MW), including a 0–3 h lead of about +1,479 MW; sum(forecast)/sum(actual) is about 1.15.
- Diagnostics found no evidence of a selector or alignment bug (known cases match hand calculations). The cause is not established from this data alone.

## Testing

```bash
pip install pytest
python -m pytest
```

Tests cover forecast selection, half-hour averaging, error metrics, band sign and expanding-window leakage, known cases on `wind.db` (delivery day 16 January at 09:00 uses run `2026-01-15T07:30:00Z`; the 01:00 forecast is 7,008 MW, the actual 7,084 MW, the error −76 MW), ingest assertions, and a small coverage fixture (4 hours, 3 inside, 75%).

## Deployment

The live app runs on Vercel as one project: `frontend/dist` is served as static output and `/api/*` is rewritten to the FastAPI function in `api/index.py`. `backend/data/wind.db` is bundled with the function and opened read-only (`mode=ro`), so nothing is written at runtime and no environment variables are needed. The first request after idle time can be slower because of cold start and the pandas import.

## AI usage

Built with Cursor and Claude assistance (planning, code generation, review). Assistance covered scaffolding, the Elexon ingest, FastAPI routes, the React UI, Docker and Vercel configuration, and the coverage backtest. Forecast selection, hourly alignment, error signs, the band formula and the expanding-window rule were reviewed against the spec and tested on hand-computed cases and known rows in `wind.db`. A sign error in the first version of the band was found in review and fixed with tests. Bias was diagnosed, not "fixed".

## Limitations and next steps

- One month of data and one forecast source (WINDFOR); no demand data, so the app shows wind error, not the buyer's full shortfall.
- The band needs three prior days, so early January has none. A longer history would tighten it.
- Coverage of 78.3% against a nominal 80% comes from a single month and should not be generalised.
- Bias correction is a possible next step and is not implemented; day-to-day bias varies widely, so a single offset would not remove the error.
- Cold starts on Vercel can add a few seconds to the first request.
