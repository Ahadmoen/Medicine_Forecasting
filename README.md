# Hospital Medicine Demand Forecasting

> FYP — FAST NUCES · Hamza Nadeem

A complete pipeline that takes one year of hospital dispensing records and
forecasts how much of each medicine will be needed for the **next 3-4
months**, accounting for **Ramadan, Eid-ul-Fitr, Eid-ul-Adha, Muharram,
Pakistani public holidays, inflation, the Lahore dengue season, and Lahore
weather (temperature / rainfall / smog AQI)**. Predictions are explained
with **SHAP** (global) and **LIME-style local contributions** so the
hospital pharmacy can see *why* a forecast says what it says.

```
data.csv  ──►  model.py  ──►  forecasts.json  ──►  Next.js dashboard (Vercel)
                                            └──►  FastAPI backend (REST)
```

The CSV is the single source of truth — keeping it constant means the model
output is reproducible and the deployment stays simple.

## Project layout

```
.
├── data.csv                          # raw hospital dispensing records
├── model.py                          # train + forecast + SHAP/LIME → JSON
├── requirements.txt                  # ML deps
│
├── backend/                          # FastAPI service
│   ├── main.py
│   ├── forecasts.json
│   └── requirements.txt
│
└── frontend/                         # Next.js 14 + Tailwind + Recharts
    ├── app/                          # App-Router pages
    ├── components/                   # KpiCards, charts, SHAP, LIME, ...
    ├── lib/                          # types & data loader
    ├── public/forecasts.json
    └── vercel.json
```

## Features

| Capability | Where |
|------------|-------|
| Daily forecast for every medicine, 120 days ahead | `model.py` `forecast()` |
| Weekly + monthly aggregations | `model.py` |
| Calendar features (DOW, month, week, weekend, Friday) | `build_calendar_features` |
| Ramadan / Eid-ul-Fitr / Eid-ul-Adha / Muharram windows | `RAMADAN_WINDOWS` etc. |
| Days-to-Eid distance (captures pre-Eid stocking) | `days_to_eid_*` |
| Pakistan public holidays | `PUBLIC_HOLIDAYS` |
| Pakistan CPI YoY inflation proxy | `INFLATION_INDEX` |
| Lahore dengue intensity curve (Aug-Nov, peak ~Oct 15) | `dengue_intensity` |
| Lahore weather climatology (temp °C, rain mm) | `LAHORE_TEMP_C`, `LAHORE_RAIN_MM` |
| Lahore PM2.5 / smog index (Nov-Dec peak) | `LAHORE_AQI` |
| Dengue-proxy admissions extracted from `Diagnosis` column | `DENGUE_PROXY_PATTERNS` |
| Lag (1d, 7d, 14d) + rolling-mean (7d, 14d) demand | `add_lag_features` |
| SHAP global feature importance | `shap_global` |
| LIME-style local contributions per medicine | `lime_local` |
| Static dashboard (no backend at runtime) | `frontend/` |
| REST API (optional) | `backend/main.py` |

## Quickstart

### 1 · Train and generate forecasts

```bash
pip install -r requirements.txt
python model.py
```

This writes `frontend/public/forecasts.json` and `backend/forecasts.json`.

### 2 · Run the dashboard locally

```bash
cd frontend
npm install
npm run dev          # http://localhost:3000
```

### 3 · Run the API (optional)

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
# open http://localhost:8000/docs
```

## API endpoints

| Method | Path                         | What it returns                          |
|--------|------------------------------|------------------------------------------|
| GET    | `/summary`                   | training window, metrics, top medicines  |
| GET    | `/medicines`                 | full list of medicines                   |
| GET    | `/forecast/{medicine}`       | daily forecast (default), `?granularity=weekly|monthly` |
| GET    | `/explain/global`            | SHAP global importance + descriptions    |
| GET    | `/explain/{medicine}`        | LIME-style per-medicine contributions    |
| GET    | `/history`                   | historical totals + dengue-proxy daily   |
| GET    | `/dengue`                    | dengue intensity curve + history proxy   |
| GET    | `/trends?signal=dengue\|temp\|rain\|aqi\|ramadan\|eid` | one Lahore signal as a date series |
| POST   | `/refresh`                   | re-train from `data.csv` and clear cache |

## Deployment topology

* **Frontend → Vercel.** `data.csv` and `model.py` produce
  `frontend/public/forecasts.json` at training time. Next.js renders
  every route as static HTML (`force-static`), so Vercel just serves
  pre-rendered pages — no Python, no API call at runtime.
* **Backend → local only.** The FastAPI service in `backend/` reads
  the same CSV-derived JSON and exposes it on REST. It is intended
  for local exploration / report generation; **it does not need to
  be deployed**. The dashboard works without it.

### Deploying the frontend on Vercel

1. Push this repository to GitHub.
2. In Vercel → "Add New Project" → import the repo.
3. **Set "Root Directory" to `frontend`**.
4. Build command: `npm run build` · Install: `npm install` · Output: `.next`.
5. Deploy. The build refuses to start if `public/forecasts.json` is
   missing, so you cannot accidentally ship a dashboard with stale data.

### Running the backend locally (CSV-backed, no deploy)

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

On startup the backend checks if `data.csv` is newer than
`forecasts.json` and silently re-runs `model.main()` if so —
the CSV stays the single source of truth, no separate training
step is required. `POST /refresh` forces a re-train on demand.

## Re-training

```bash
# replace data.csv with a fresher year-long export, then:
python model.py
git add frontend/public/forecasts.json backend/forecasts.json
git commit -m "refresh forecasts"
git push
```

Vercel auto-deploys on push.

## Model details

- **Algorithm**: gradient-boosted regression trees (sklearn
  `GradientBoostingRegressor`, 400 trees, depth 5, lr 0.07).
- **Target**: daily units of a given medicine.
- **Validation**: 80 / 20 random split, MAE & RMSE reported in the dashboard.
- **Forecast strategy**: recursive — each predicted day feeds the lag/rolling
  features for the next day.
- **Macro / cultural / Lahore features**: pre-encoded windows + days-to-event
  distance (Eid-Fitr, Eid-Adha, Ramadan), monthly CPI proxy, Lahore
  monthly mean temperature, monthly rainfall, PM2.5 / smog index, plus a
  Gaussian dengue-intensity curve centred on October 15 (Pakistan NIH
  epidemiology).
- **Explainability**: TreeSHAP for global importance and per-row attribution.
