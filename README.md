# Wind Forecast Monitor

National GB wind generation is hard to buy against on D-1 because the forecast keeps moving and the error is large. This app is for a utility day-ahead buying desk: it shows the latest Elexon WINDFOR run that existed at a chosen D-1 cutoff, compares it with FUELHH wind actuals for 2 January–1 February 2026, and puts a historically calibrated band around the actual.

## Live app

Not deployed yet. Vercel CLI is not logged in on this machine. Use the click path under “Vercel” below once the GitHub repo exists.

## Files and directories

```
.
├── README.md                  # this file
├── CURSOR_SPEC.md             # assignment spec
├── Dockerfile                 # multi-stage: Node 20 build, Python 3.12 serve
├── docker-compose.yml         # one service, port 8000
├── .dockerignore
├── .gitignore
├── .python-version            # 3.12 for Vercel
├── vercel.json                # SPA output + /api rewrite to the Python function
├── requirements.txt           # pinned API runtime deps only
├── pyproject.toml             # Python metadata and Vercel entrypoint
├── uv.lock                    # locked API deps for Python >=3.12
├── pytest.ini
├── api/
│   └── index.py               # Vercel function: imports backend.app.main:app
├── backend/
│   ├── app/
│   │   ├── main.py            # FastAPI routes under /api; serves frontend/dist
│   │   ├── config.py          # dates, cutoff, DB path, assumptions
│   │   ├── db.py              # read-only SQLite (mode=ro)
│   │   ├── schemas.py         # Pydantic response models
│   │   ├── times.py           # UTC parse/format
│   │   └── services/
│   │       ├── decision.py    # latest WINDFOR run at or before cutoff
│   │       ├── align.py       # hourly actual = mean of H:00 and H:30
│   │       ├── metrics.py     # MAE, RMSE, bias, percentiles
│   │       ├── band.py        # actual band from P10/P90 of error
│   │       ├── coverage.py    # expanding-window band coverage backtest
│   │       └── report.py      # load SQLite and call the pure functions
│   ├── scripts/
│   │   ├── ingest.py          # fetch Elexon JSON and rebuild wind.db
│   │   └── diagnose_bias.py   # read-only bias breakdown (no correction)
│   ├── data/
│   │   ├── raw/               # committed Elexon JSON
│   │   └── wind.db            # committed read-only SQLite
│   └── tests/                 # unit tests against hand-made cases and wind.db
└── frontend/
    ├── package.json
    ├── vite.config.ts         # /api proxy to port 8000 in dev
    └── src/                   # Overview, Decision, Error analysis, Revisions
```

## How to start

**(a) Docker**

```bash
docker compose up --build
```

Open http://localhost:8000. The image contains `wind.db` and the built UI. There are no volumes. The process does not call Elexon and does not write.

**(b) Without Docker**

Python 3.12+ and Node 20+.

```bash
pip install -r requirements.txt
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

In another terminal:

```bash
cd frontend
npm ci
npm run dev
```

Vite proxies `/api` to port 8000. To serve the UI from FastAPI instead, run `npm run build` in `frontend/` and restart uvicorn (`frontend/dist` is mounted when it exists).

**(c) Rebuilding the data**

```bash
python backend/scripts/ingest.py
```

That refetches FUELHH (7-day chunks) and WINDFOR (one publish day per request), writes `backend/data/raw/*.json`, rebuilds `backend/data/wind.db`, and checks the load assertions (1488 half-hourly actuals). The deployed app never calls Elexon; it only reads the committed database.

The spec lists `https://bmrs.elexon.co.uk/api/v1/datasets`. That host now returns the BMRS website. Ingestion uses `https://data.elexon.co.uk/bmrs/api/v1/datasets`, which serves the same dataset paths as JSON.

## Method and assumptions

- Runtime is **Python 3.12** (`.python-version`, Docker `python:3.12-slim`, Vercel).
- Default decision cutoff is **09:00 UTC on D-1**. It is configurable because GB auctions do not all close at 09:00: EPEX GB around 09:20, N2EX around 09:50. Presets for those three times sit in the control bar.
- January UK civil time equals UTC, so every timestamp is stored and shown as UTC.
- A forecast hour starting at H:00 is compared with the **mean of the FUELHH actuals at H:00 and H:30**. If either half-hour is missing, that hour is dropped.
- WINDFOR rows with `startTime` at or before `publishTime` are not forecasts and are excluded.
- **Error = forecast − actual**. Positive means an over-forecast; the actual equals the forecast minus the error.
- The shaded band is the likely range of the actual: `band_low = max(0, forecast − P90(error))`, `band_high = forecast − P10(error)`.
- P10 and P90 use an **expanding window** of delivery days strictly before the selected day, at the same cutoff. The selected day and later days are excluded. Fewer than 3 prior days shows no band.
- Coverage backtest at cutoff 09:00 over 2 Jan–1 Feb 2026: **78.3% of actual hours landed inside the band (526 of 672 hours, 28 days)**. The first three delivery days have no band. The band was not tuned to raise this figure.
- Bias observations (cutoff 09:00, no causal claim and no correction): mean error about +1,748 MW; 27 of 31 days positive; every horizon bucket positive (about +1,400 to +1,900 MW), including a 0–3 h lead of about +1,479 MW; sum(forecast)/sum(actual) ≈ 1.15. This is treated as a property of the series, not a bug in the selector.

## Testing

```bash
pip install pytest
python -m pytest
```

Tests cover forecast selection, half-hour averaging, error metrics, band sign and expanding-window leakage, known cases on `wind.db` (16 Jan 09:00 run `2026-01-15T07:30:00Z`, 01:00 forecast 7008 MW, actual 7084 MW, error −76 MW), ingest assertions, and a 4-hour / 3-inside coverage fixture (75%).

## AI usage

Built with Cursor and Claude assistance (planning, code generation, review). Assistance covered scaffolding, Elexon ingest, FastAPI routes, the React UI, Docker/Vercel config, and the coverage backtest. Forecast selection, hourly alignment, error signs, the band formula, and the expanding-window rule were reviewed against the spec and tested on hand-computed cases and known rows in `wind.db`. Bias was diagnosed, not “fixed”.

## Limitations and next steps

One month of data and one forecast source (WINDFOR). No demand data. Bias correction is a possible next step and is not implemented. A longer history would tighten the early-January band, which currently needs three prior days.

## Vercel

Current Vercel docs (2026): FastAPI becomes one Python Function ([Deploy a FastAPI app](https://vercel.com/docs/frameworks/backend/fastapi)). `tool.vercel.entrypoint` in `pyproject.toml` points at `api.index:app`. A Vite frontend can also be a Vercel Service; this repo keeps one project with `frontend/dist` as static output and `/api/(.*)` rewritten to `api/index.py`, because the Python package imports `backend.app` from the repo root. `includeFiles` bundles `backend/data/wind.db`. The DB path is resolved from `config.py`, not the working directory. SQLite opens `file:...?mode=ro`. Python’s standard uncompressed bundle limit is 500 MB (Large Functions up to 5 GB). pandas 3.1.0 is ~12 MB on Linux manylinux plus numpy ~17 MB and a 2.7 MB database, so pandas is kept.

No environment variables are required.
