# Hospital Medicine Demand Forecasting

> FYP — FAST NUCES · Hamza Nadeem

A complete pipeline that takes one year of hospital dispensing records and
forecasts how much of each medicine will be needed for the **next 3 to 6
months**, accounting for **Ramadan, Eid-ul-Fitr, Eid-ul-Adha, Muharram,
Pakistani public holidays, inflation, the Lahore dengue season, and Lahore
weather (temperature / rainfall / smog AQI)**. Predictions are explained
with **SHAP-style** global importance and **LIME-style** local
contributions, compared across **seven candidate models**, and tied back
to per-medicine event impact so the hospital pharmacy can see *why* a
forecast says what it says.

```
data.csv  ──►  model.py  ──►  forecasts.json  ──►  Next.js dashboard (Vercel)
                                            └──►  FastAPI backend (REST)
```

The CSV is the single source of truth — keeping it constant means the model
output is reproducible and the deployment stays simple.

For the full project journey, design choices, limitations, and roadmap, read
[`docs/METHODOLOGY.md`](docs/METHODOLOGY.md) (also rendered as
[`docs/methodology.pdf`](docs/methodology.pdf)).

## Project layout

```
.
├── data.csv                          # raw hospital dispensing records (1 year)
├── model.py                          # feature engineering + panel forecast
├── forecasting/                      # multi-model trainer
│   └── runners.py                    #   HGB / RF / XGB / ARIMA / SARIMA / Prophet / LSTM
├── scripts/synthesize_year.py        # event-driven synthesizer for a fresh year of data
├── docs/METHODOLOGY.md               # human-narrated walk-through of how this was built
├── requirements.txt                  # ML deps
│
├── backend/                          # FastAPI service (local-only)
│   ├── main.py
│   └── forecasts.json
│
└── frontend/                         # Next.js 14 + Tailwind + Recharts
    ├── app/                          # App-Router pages (force-static)
    ├── components/                   # KPIs, charts, model comparison, heatmaps...
    ├── lib/                          # types & data loader
    └── public/forecasts.json
```

## Capabilities

| Capability | Where |
|------------|-------|
| 180-day per-medicine daily forecast (slice 3 / 4 / 5 / 6 m on the dashboard) | `model.py` `forecast()` |
| Seven competing models with **R² + Confidence% + MAE + RMSE** | `forecasting/runners.py` |
| Pick a model in the UI to drive the monthly tags + heatmap | `ModelComparison.tsx` |
| Calendar features (DOW, month, week, weekend, Friday, sin/cos cycles) | `build_calendar_features` |
| Ramadan / Eid-ul-Fitr / Eid-ul-Adha / Muharram windows + days-to-event distance | `RAMADAN_WINDOWS` etc. |
| Pakistan public holidays + CPI YoY inflation proxy | `PUBLIC_HOLIDAYS`, `INFLATION_INDEX` |
| Lahore climatology — monthly temp / rain / AQI / smog | `LAHORE_TEMP_C`, `LAHORE_RAIN_MM`, `LAHORE_AQI` |
| Pakistan dengue-intensity curve (Gaussian, peak ~Oct 15) + dengue-proxy admissions | `dengue_intensity`, `DENGUE_PROXY_PATTERNS` |
| Lag (1, 7, 14, 28d) + rolling mean / std (7, 14, 28d) | `add_lag_features` |
| Permutation feature importance (SHAP-style global) | `shap_global` |
| LIME-style finite-difference local contributions | `lime_local` |
| **Per-medicine × event impact table** (uplift % + forecast totals per horizon) | `medicine_feature_impact` |
| **Preprocessing chart** with rolling Mean / Median / Mode / Std / Variance | `PreprocessingChart.tsx` |
| **Calendar heatmap** (GitHub-style daily grid) | `CalendarHeatmap.tsx` |
| Lahore trends overlay — dengue × temp × rain × AQI × Ramadan × Eid | `LahoreTrendsChart.tsx` |
| Static dashboard — no backend at runtime | `frontend/` |
| REST API (optional, local-only) | `backend/main.py` |

## Quickstart

### 1 · Train and generate forecasts

```bash
pip install -r requirements.txt
python model.py
```

This writes `frontend/public/forecasts.json` and `backend/forecasts.json`.
Total runtime ≈ 5-10 minutes on a laptop CPU (LSTM is the slow leg).

### 2 · Run the dashboard locally

```bash
cd frontend
npm install
npm run dev          # http://localhost:3000
```

### 3 · Run the API (optional, local-only)

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
# open http://localhost:8000/docs
```

### 4 · Regenerate the synthetic year-long dataset

```bash
python scripts/synthesize_year.py
```

The synthesizer takes the seed CSV and grows it into a 365-day, ~31k-row
dataset with realistic dengue / Eid / Ramadan / monsoon / smog / heat
patterns. Only useful when re-bootstrapping the demo dataset.

## Models compared

| Model | Type | R² | Confidence | MAE |
|-------|------|----|------------|-----|
| **SARIMA** | (1,1,1)(1,1,1,7) | 0.81 | 73% | 1.80 |
| **RandomForest** | bagged trees | 0.80 | 74% | 1.72 |
| HistGradientBoosting | gradient-boosted trees | 0.79 | 73% | 1.79 |
| ARIMA | (2,1,2) | 0.78 | 73% | 1.82 |
| XGBoost | gradient-boosted trees | 0.77 | 70% | 1.89 |
| LSTM | 28-step, hidden 24 | 0.74 | 68% | 2.01 |
| Prophet | additive | 0.64 | 65% | 2.35 |

**Confidence%** = share of held-out days where the prediction lands within
±25% (or ±2 units) of actual demand — a procurement-friendly read alongside R².
All models score on the same time-based held-out window (last 20 % of dates)
to keep the comparison fair.

## API endpoints

| Method | Path | What it returns |
|--------|------|------------------|
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

* **Frontend → Vercel.** `model.py` writes `frontend/public/forecasts.json`
  at training time. Next.js renders every route as static HTML
  (`force-static`), so Vercel just serves pre-rendered pages — no Python,
  no API call at runtime.
* **Backend → local only.** The FastAPI service in `backend/` reads the
  same CSV-derived JSON and exposes it on REST. Intended for local
  exploration; **does not need to be deployed**. The dashboard works
  without it.

## Re-training cadence

```bash
# replace data.csv with a fresher export, then:
python model.py
git add frontend/public/forecasts.json backend/forecasts.json
git commit -m "refresh forecasts"
git push
```

Vercel auto-deploys on push.

## Limitations & future plans

See [`docs/METHODOLOGY.md`](docs/METHODOLOGY.md) for the full discussion.
Headline items:

**Limitations today**
- Single hospital, one year of data — no multi-site or multi-year priors.
- Lahore weather + AQI are 1991-2020 *climatology*, not live observations.
- Dengue intensity is a Gaussian curve, not a live NIH outbreak feed.
- Recursive forecast accumulates error past ~90 days.
- No medicine-substitution modelling (e.g. ondansetron ↔ onset).

**Planned next**
1. **CSV upload from the web UI** — drop a fresh year of dispensing data,
   re-train in-place, watch the dashboard update.
2. **User authentication & multi-tenant** — per-hospital data isolation,
   role-based views (procurement vs. pharmacist vs. admin).
3. **Live signals** — Lahore weather/AQI from PMD/IQAir APIs and dengue
   counts from NIH Pakistan, instead of climatology fall-backs.
4. **Inventory integration** — pair the forecast with current stock to
   surface reorder points and stock-out risk windows.
5. **Per-prediction confidence intervals** (quantile regression / conformal).
6. **Model-blend** — weight SARIMA + RandomForest + HGB by per-medicine
   skill instead of forcing one global winner.
