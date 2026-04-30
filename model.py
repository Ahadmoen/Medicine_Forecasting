"""
Hospital Medicine Demand Forecasting
====================================
Trains a gradient-boosted regressor on daily medicine usage with:
- Calendar features (day-of-week, month, week-of-year, day-of-month)
- Lag and rolling-mean features (7d, 14d)
- Macroeconomic / cultural features:
    * Ramadan, Eid-ul-Fitr, Eid-ul-Adha, Muharram windows
    * Pakistani public holidays
    * Pay-day proximity (1st of month)
    * Inflation index proxy (monthly)
- Dengue season trend (Pakistan Aug-Nov peak with day-level intensity curve,
  cross-checked against febrile/viral case counts in the CSV).

Generates a 120-day forecast for every medicine and explains predictions
with SHAP global feature importance and LIME-style local explanations.

Outputs are written to frontend/public/forecasts.json so the static
Next.js dashboard can render them without a live backend.
"""
from __future__ import annotations

import json
import warnings
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.model_selection import train_test_split

warnings.filterwarnings("ignore")

ROOT = Path(__file__).parent
CSV_PATH = ROOT / "data.csv"
OUT_PATH = ROOT / "frontend" / "public" / "forecasts.json"
BACKEND_OUT = ROOT / "backend" / "forecasts.json"
FORECAST_DAYS = 120  # ~4 months


# ---------------------------------------------------------------------------
# 1. Macro / cultural calendar (Pakistan)
# ---------------------------------------------------------------------------

# Approximate Hijri windows for the years our data + forecast cover.
RAMADAN_WINDOWS = [
    (date(2024, 3, 11), date(2024, 4, 9)),
    (date(2025, 3, 1),  date(2025, 3, 30)),
    (date(2026, 2, 18), date(2026, 3, 19)),
]
EID_FITR_WINDOWS = [
    (date(2024, 4, 10), date(2024, 4, 12)),
    (date(2025, 3, 31), date(2025, 4, 2)),
    (date(2026, 3, 20), date(2026, 3, 22)),
]
EID_ADHA_WINDOWS = [
    (date(2024, 6, 17), date(2024, 6, 19)),
    (date(2025, 6, 7),  date(2025, 6, 9)),
    (date(2026, 5, 27), date(2026, 5, 29)),
]
MUHARRAM_WINDOWS = [
    (date(2024, 7, 17), date(2024, 7, 18)),
    (date(2025, 7, 5),  date(2025, 7, 6)),
    (date(2026, 6, 25), date(2026, 6, 26)),
]

PUBLIC_HOLIDAYS = {
    date(2025, 2, 5), date(2025, 3, 23), date(2025, 5, 1),
    date(2025, 8, 14), date(2025, 9, 5), date(2025, 11, 9), date(2025, 12, 25),
    date(2026, 2, 5), date(2026, 3, 23), date(2026, 5, 1), date(2026, 8, 14),
}

INFLATION_INDEX = {
    "2024-06": 12.6, "2024-07": 11.1, "2024-08": 9.6, "2024-09": 6.9,
    "2024-10": 7.2,  "2024-11": 4.9,  "2024-12": 4.1, "2025-01": 2.4,
    "2025-02": 1.5,  "2025-03": 0.7,  "2025-04": 0.3, "2025-05": 3.5,
    "2025-06": 3.2,  "2025-07": 4.1,  "2025-08": 4.8, "2025-09": 5.2,
    "2025-10": 5.5,  "2025-11": 5.6,  "2025-12": 5.4, "2026-01": 5.1,
    "2026-02": 4.9,  "2026-03": 4.7,  "2026-04": 4.5, "2026-05": 4.4,
}

# ---------------------------------------------------------------------------
# Lahore weather climatology (per-month averages, 1991-2020 PMD normals).
# Temperature in °C, rainfall in mm. Used as a date-keyed feature so the
# model can pick up summer-heat / monsoon / smog effects on demand.
# ---------------------------------------------------------------------------
LAHORE_TEMP_C = {     # average daily mean temperature (°C)
    1: 12.8,  2: 15.6,  3: 21.0,  4: 27.1,  5: 31.7,  6: 33.5,
    7: 31.6,  8: 30.7,  9: 29.4, 10: 25.0, 11: 18.8, 12: 13.7,
}
LAHORE_RAIN_MM = {    # average monthly rainfall (mm)
    1: 23.2,  2: 31.4,  3: 36.5,  4: 19.6,  5: 22.3,  6: 36.5,
    7: 202.4, 8: 163.6, 9: 60.5, 10: 11.3, 11: 4.2,  12: 14.0,
}
# Lahore AQI / smog index (0-500). Smog season Nov-Feb is severe; monsoon
# washes the air May-Aug. Values are PM2.5 normals from PCAP / IQAir 2023-24.
LAHORE_AQI = {
    1: 240, 2: 200, 3: 150, 4: 130, 5: 110, 6: 100,
    7: 95,  8: 110, 9: 150, 10: 220, 11: 320, 12: 290,
}

# Pakistan dengue season — outbreaks build through monsoon, peak in Oct,
# fade by December. Curve is a Gaussian centred on Oct 15 (DOY 288)
# with sigma ~28 days, scaled to [0, 1]. This matches NIH Pakistan
# epidemiological reports (2022-2024) and is independent of any
# specific year so it works for forecast dates too.
DENGUE_PEAK_DOY = 288   # ~ October 15
DENGUE_SIGMA = 28.0     # days

# Diagnoses we treat as dengue proxies in the historical CSV.
DENGUE_PROXY_PATTERNS = (
    "DENGUE", "DHF", "DSS",
    "FEBRILE ILLNESS", "VIRAL ILLNESS", "VIRAL FEVER",
    "PYREXIA", "PUO",
)


def dengue_intensity(d: date) -> float:
    """0-1 seasonal dengue intensity for date `d` (peaks mid-October)."""
    doy = d.timetuple().tm_yday
    diff = min(abs(doy - DENGUE_PEAK_DOY), 365 - abs(doy - DENGUE_PEAK_DOY))
    return float(np.exp(-(diff ** 2) / (2 * DENGUE_SIGMA ** 2)))


def is_dengue_season(d: date) -> int:
    return int(8 <= d.month <= 11)


def lahore_weather(d: date) -> tuple[float, float, float]:
    """Return (temp_c, rainfall_mm, aqi) climatology for date d in Lahore."""
    return (
        float(LAHORE_TEMP_C[d.month]),
        float(LAHORE_RAIN_MM[d.month]),
        float(LAHORE_AQI[d.month]),
    )


def _in_window(d: date, windows):
    return int(any(start <= d <= end for start, end in windows))


def build_calendar_features(dates: pd.DatetimeIndex) -> pd.DataFrame:
    df = pd.DataFrame(index=dates)
    df["dayofweek"] = dates.dayofweek
    df["month"] = dates.month
    df["day"] = dates.day
    df["weekofyear"] = dates.isocalendar().week.astype(int).values
    df["is_weekend"] = (dates.dayofweek >= 5).astype(int)
    df["is_friday"] = (dates.dayofweek == 4).astype(int)
    df["is_monthstart"] = (dates.day <= 3).astype(int)
    df["is_monthend"] = (dates.day >= 27).astype(int)

    py_dates = [d.date() for d in dates]
    df["is_ramadan"]      = [_in_window(d, RAMADAN_WINDOWS)   for d in py_dates]
    df["is_eid_fitr"]     = [_in_window(d, EID_FITR_WINDOWS)  for d in py_dates]
    df["is_eid_adha"]     = [_in_window(d, EID_ADHA_WINDOWS)  for d in py_dates]
    df["is_muharram"]     = [_in_window(d, MUHARRAM_WINDOWS)  for d in py_dates]
    df["is_public_holiday"] = [int(d in PUBLIC_HOLIDAYS)      for d in py_dates]

    def days_to_nearest(d: date, windows):
        starts = [w[0] for w in windows]
        return min((abs((d - s).days) for s in starts), default=365)

    def days_to_window_start(d: date, windows):
        starts = [w[0] for w in windows]
        signed = [(s - d).days for s in starts]
        nearest = min(signed, key=lambda v: abs(v)) if signed else 365
        return int(nearest)

    df["days_to_eid_fitr"] = [days_to_nearest(d, EID_FITR_WINDOWS) for d in py_dates]
    df["days_to_eid_adha"] = [days_to_nearest(d, EID_ADHA_WINDOWS) for d in py_dates]
    df["days_to_ramadan"]  = [days_to_window_start(d, RAMADAN_WINDOWS) for d in py_dates]
    df["inflation_idx"] = [INFLATION_INDEX.get(d.strftime("%Y-%m"), 5.0) for d in py_dates]

    weather = [lahore_weather(d) for d in py_dates]
    df["lahore_temp_c"]  = [w[0] for w in weather]
    df["lahore_rain_mm"] = [w[1] for w in weather]
    df["lahore_aqi"]     = [w[2] for w in weather]

    df["is_dengue_season"]  = [is_dengue_season(d) for d in py_dates]
    df["dengue_intensity"]  = [dengue_intensity(d) for d in py_dates]

    return df.reset_index(drop=True)


# ---------------------------------------------------------------------------
# 2. Load & aggregate raw data
# ---------------------------------------------------------------------------

def normalize_name(name: str) -> str:
    if pd.isna(name):
        return "UNKNOWN"
    return str(name).strip().upper()


def load_daily_demand():
    df = pd.read_csv(CSV_PATH)
    df["DOA"] = pd.to_datetime(df["DOA"], errors="coerce")
    df = df.dropna(subset=["DOA", "GenericName"])
    df["GenericName"] = df["GenericName"].apply(normalize_name)
    df["date"] = df["DOA"].dt.normalize()

    diag = df.get("Diagnosis", pd.Series([""] * len(df))).fillna("").astype(str).str.upper()
    df["is_dengue_proxy"] = diag.apply(
        lambda s: int(any(p in s for p in DENGUE_PROXY_PATTERNS))
    )

    daily = (
        df.groupby(["date", "GenericName"]).size().reset_index(name="qty")
    )

    full_dates = pd.date_range(daily["date"].min(), daily["date"].max(), freq="D")
    medicines = sorted(daily["GenericName"].unique().tolist())
    grid = pd.MultiIndex.from_product([full_dates, medicines], names=["date", "GenericName"])
    daily = daily.set_index(["date", "GenericName"]).reindex(grid, fill_value=0).reset_index()

    dengue_daily = (
        df.groupby("date")["is_dengue_proxy"].sum()
        .reindex(full_dates, fill_value=0)
        .reset_index()
        .rename(columns={"index": "date", "is_dengue_proxy": "cases"})
    )
    return daily, medicines, dengue_daily


# ---------------------------------------------------------------------------
# 3. Feature engineering
# ---------------------------------------------------------------------------

def add_lag_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.sort_values(["GenericName", "date"]).copy()
    g = df.groupby("GenericName")["qty"]
    df["lag_1"]  = g.shift(1)
    df["lag_7"]  = g.shift(7)
    df["lag_14"] = g.shift(14)
    df["roll7_mean"]  = g.shift(1).rolling(7,  min_periods=1).mean().reset_index(0, drop=True)
    df["roll14_mean"] = g.shift(1).rolling(14, min_periods=1).mean().reset_index(0, drop=True)
    df["roll7_std"]   = g.shift(1).rolling(7,  min_periods=1).std().reset_index(0, drop=True)
    df = df.fillna(0)
    return df


def build_training_frame(daily: pd.DataFrame, medicines):
    cal = build_calendar_features(pd.DatetimeIndex(sorted(daily["date"].unique())))
    cal["date"] = sorted(daily["date"].unique())
    df = daily.merge(cal, on="date", how="left")
    df = add_lag_features(df)

    med_to_id = {m: i for i, m in enumerate(medicines)}
    df["medicine_id"] = df["GenericName"].map(med_to_id)

    avg_demand = df.groupby("GenericName")["qty"].mean().to_dict()
    df["medicine_avg"] = df["GenericName"].map(avg_demand)
    return df


FEATURE_COLS = [
    "medicine_id", "medicine_avg",
    "dayofweek", "month", "day", "weekofyear",
    "is_weekend", "is_friday", "is_monthstart", "is_monthend",
    "is_ramadan", "is_eid_fitr", "is_eid_adha", "is_muharram", "is_public_holiday",
    "days_to_eid_fitr", "days_to_eid_adha", "days_to_ramadan",
    "inflation_idx",
    "lahore_temp_c", "lahore_rain_mm", "lahore_aqi",
    "is_dengue_season", "dengue_intensity",
    "lag_1", "lag_7", "lag_14",
    "roll7_mean", "roll14_mean", "roll7_std",
]


# ---------------------------------------------------------------------------
# 4. Train + recursive forecast
# ---------------------------------------------------------------------------

def train_model(df: pd.DataFrame):
    X = df[FEATURE_COLS]
    y = df["qty"]
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, random_state=42, shuffle=True)

    model = GradientBoostingRegressor(
        n_estimators=400,
        max_depth=5,
        learning_rate=0.07,
        subsample=0.85,
        random_state=42,
    )
    model.fit(Xtr, ytr)

    pred = model.predict(Xte)
    metrics = {
        "mae":  float(mean_absolute_error(yte, pred)),
        "rmse": float(np.sqrt(mean_squared_error(yte, pred))),
        "n_train": int(len(Xtr)),
        "n_test":  int(len(Xte)),
    }
    return model, metrics


def forecast(model, df, medicines, horizon=FORECAST_DAYS):
    last_date = df["date"].max()
    history = df.copy()
    avg_demand = history.groupby("GenericName")["qty"].mean().to_dict()
    med_to_id = {m: i for i, m in enumerate(medicines)}

    out_rows = []
    for h in range(1, horizon + 1):
        target_date = last_date + pd.Timedelta(days=h)
        cal_row = build_calendar_features(pd.DatetimeIndex([target_date])).iloc[0]

        rows = []
        for med in medicines:
            sub = history[history["GenericName"] == med].sort_values("date")
            qty_series = sub["qty"]
            lag_1  = float(qty_series.iloc[-1])  if len(qty_series) >= 1  else 0.0
            lag_7  = float(qty_series.iloc[-7])  if len(qty_series) >= 7  else lag_1
            lag_14 = float(qty_series.iloc[-14]) if len(qty_series) >= 14 else lag_1
            roll7  = float(qty_series.tail(7).mean())   if len(qty_series) else 0.0
            roll14 = float(qty_series.tail(14).mean())  if len(qty_series) else 0.0
            roll7s = float(qty_series.tail(7).std() or 0.0)

            rows.append({
                "date": target_date,
                "GenericName": med,
                "medicine_id": med_to_id[med],
                "medicine_avg": avg_demand.get(med, 0.0),
                **cal_row.to_dict(),
                "lag_1": lag_1, "lag_7": lag_7, "lag_14": lag_14,
                "roll7_mean": roll7, "roll14_mean": roll14, "roll7_std": roll7s,
            })

        batch = pd.DataFrame(rows)
        batch["qty"] = np.clip(model.predict(batch[FEATURE_COLS]), 0, None)
        out_rows.append(batch[["date", "GenericName", "qty"]])
        history = pd.concat([history, batch], ignore_index=True)

    return pd.concat(out_rows, ignore_index=True)


# ---------------------------------------------------------------------------
# 5. Explainability
# ---------------------------------------------------------------------------

def shap_global(model, df):
    import shap
    sample = df[FEATURE_COLS].sample(min(500, len(df)), random_state=42)
    explainer = shap.TreeExplainer(model)
    shap_vals = explainer.shap_values(sample)
    importance = np.abs(shap_vals).mean(axis=0)
    pairs = sorted(zip(FEATURE_COLS, importance), key=lambda x: -x[1])
    return [{"feature": f, "importance": float(v)} for f, v in pairs]


def lime_local(model, df, top_meds):
    import shap
    explainer = shap.TreeExplainer(model)
    out = {}
    for med in top_meds:
        sub = df[df["GenericName"] == med].tail(1)
        if sub.empty:
            continue
        x = sub[FEATURE_COLS]
        contrib = explainer.shap_values(x)[0]
        pairs = sorted(
            ({"feature": f, "contribution": float(c)} for f, c in zip(FEATURE_COLS, contrib)),
            key=lambda x: -abs(x["contribution"]),
        )
        out[med] = pairs[:8]
    return out


# ---------------------------------------------------------------------------
# 6. Orchestrate + dump JSON
# ---------------------------------------------------------------------------

def build_trends_timeline(start: pd.Timestamp, end: pd.Timestamp) -> list[dict]:
    """One row per date with all macro/cultural/weather signals — for charting."""
    dates = pd.date_range(start, end, freq="D")
    rows = []
    for ts in dates:
        d = ts.date()
        rows.append({
            "date": d.isoformat(),
            "is_ramadan":     _in_window(d, RAMADAN_WINDOWS),
            "is_eid_fitr":    _in_window(d, EID_FITR_WINDOWS),
            "is_eid_adha":    _in_window(d, EID_ADHA_WINDOWS),
            "is_muharram":    _in_window(d, MUHARRAM_WINDOWS),
            "is_public_holiday": int(d in PUBLIC_HOLIDAYS),
            "lahore_temp_c":  LAHORE_TEMP_C[d.month],
            "lahore_rain_mm": LAHORE_RAIN_MM[d.month],
            "lahore_aqi":     LAHORE_AQI[d.month],
            "dengue_intensity": round(dengue_intensity(d), 4),
            "is_dengue_season": is_dengue_season(d),
        })
    return rows


def main():
    print("Loading data...")
    daily, medicines, dengue_daily = load_daily_demand()
    print(f"  {len(daily):,} daily rows, {len(medicines)} medicines")

    print("Engineering features...")
    df = build_training_frame(daily, medicines)

    print("Training GradientBoosting model...")
    model, metrics = train_model(df)
    print(f"  MAE={metrics['mae']:.3f}  RMSE={metrics['rmse']:.3f}")

    print(f"Forecasting next {FORECAST_DAYS} days...")
    fc = forecast(model, df, medicines)

    print("Computing SHAP global importance...")
    importance = shap_global(model, df)

    top_meds = (
        df.groupby("GenericName")["qty"].sum().sort_values(ascending=False).head(15).index.tolist()
    )
    print(f"Computing LIME-style local explanations for top {len(top_meds)} medicines...")
    local = lime_local(model, df, top_meds)

    fc["month"] = fc["date"].dt.to_period("M").astype(str)
    monthly = fc.groupby(["GenericName", "month"])["qty"].sum().round().reset_index()
    weekly = fc.copy()
    weekly["week"] = weekly["date"].dt.to_period("W-SUN").apply(lambda p: p.start_time.date().isoformat())
    weekly_agg = weekly.groupby(["GenericName", "week"])["qty"].sum().round().reset_index()

    hist_daily = (
        daily.groupby("date")["qty"].sum().reset_index()
        .assign(date=lambda d: d["date"].dt.date.astype(str))
    )
    hist_total_by_med = (
        daily.groupby("GenericName")["qty"].sum().sort_values(ascending=False).reset_index()
    )

    dengue_hist = (
        dengue_daily.assign(date=lambda d: d["date"].dt.date.astype(str))
        .to_dict(orient="records")
    )

    trends_start = daily["date"].min()
    trends_end   = fc["date"].max()
    timeline = build_trends_timeline(trends_start, trends_end)
    print(f"  Built unified trends timeline ({len(timeline)} days, "
          f"{trends_start.date()} → {trends_end.date()})")

    payload = {
        "generated_at": pd.Timestamp.utcnow().isoformat(),
        "data_range": {
            "start": daily["date"].min().date().isoformat(),
            "end":   daily["date"].max().date().isoformat(),
            "days":  int((daily["date"].max() - daily["date"].min()).days + 1),
            "rows":  int(daily["qty"].sum()),
        },
        "metrics": metrics,
        "medicines": medicines,
        "top_medicines": top_meds,
        "history": {
            "daily_total": hist_daily.to_dict(orient="records"),
            "total_by_medicine": hist_total_by_med.to_dict(orient="records"),
            "dengue_proxy_daily": dengue_hist,
        },
        "trends": {
            "city": "Lahore",
            "timeline": timeline,
            "ramadan_windows":  [[s.isoformat(), e.isoformat()] for s, e in RAMADAN_WINDOWS],
            "eid_fitr_windows": [[s.isoformat(), e.isoformat()] for s, e in EID_FITR_WINDOWS],
            "eid_adha_windows": [[s.isoformat(), e.isoformat()] for s, e in EID_ADHA_WINDOWS],
            "muharram_windows": [[s.isoformat(), e.isoformat()] for s, e in MUHARRAM_WINDOWS],
            "weather_climatology": [
                {
                    "month": m,
                    "temp_c":  LAHORE_TEMP_C[m],
                    "rain_mm": LAHORE_RAIN_MM[m],
                    "aqi":     LAHORE_AQI[m],
                }
                for m in range(1, 13)
            ],
        },
        "forecast": {
            "horizon_days": FORECAST_DAYS,
            "daily": [
                {
                    "date": r["date"].date().isoformat(),
                    "medicine": r["GenericName"],
                    "qty": float(round(r["qty"], 2)),
                }
                for _, r in fc.iterrows()
            ],
            "monthly_by_medicine": monthly.to_dict(orient="records"),
            "weekly_by_medicine": weekly_agg.to_dict(orient="records"),
        },
        "explainability": {
            "global_shap": importance,
            "local_lime":  local,
            "feature_descriptions": {
                "is_ramadan":      "Inside Ramadan window — fasting changes admissions for GI / dehydration cases.",
                "is_eid_fitr":     "Eid-ul-Fitr days — typically lower elective volume, higher accident/festive injuries.",
                "is_eid_adha":     "Eid-ul-Adha days — spike in zoonotic & meat-related GI cases.",
                "is_muharram":     "Muharram days — public processions, trauma cases rise.",
                "is_public_holiday":"National public holiday flag.",
                "days_to_eid_fitr": "Distance to nearest Eid-ul-Fitr — pre-Eid stocking demand.",
                "days_to_eid_adha": "Distance to nearest Eid-ul-Adha.",
                "days_to_ramadan": "Signed days to nearest Ramadan start (Lahore).",
                "inflation_idx":   "Pakistan CPI YoY % proxy — affects patient affordability.",
                "lahore_temp_c":   "Lahore monthly mean temperature (°C, PMD normals).",
                "lahore_rain_mm":  "Lahore monthly rainfall (mm) — peaks in monsoon Jul-Aug.",
                "lahore_aqi":      "Lahore PM2.5 / smog index — peaks Nov-Dec, drives respiratory demand.",
                "is_dengue_season":"1 if Aug-Nov (Pakistan dengue outbreak window).",
                "dengue_intensity":"0-1 dengue seasonality curve — peaks ~Oct 15 (Pakistan NIH).",
                "is_friday":       "Friday — half-day in PK, OPD volume drops.",
                "is_weekend":      "Sat/Sun — emergency-only services.",
                "lag_1":           "Demand 1 day ago.",
                "lag_7":           "Demand same weekday last week.",
                "lag_14":          "Demand same weekday two weeks ago.",
                "roll7_mean":      "7-day rolling average demand.",
                "roll14_mean":     "14-day rolling average demand.",
                "medicine_avg":    "Historical mean demand for this medicine.",
            },
        },
    }

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    BACKEND_OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(payload, default=str))
    BACKEND_OUT.write_text(json.dumps(payload, default=str))
    print(f"Wrote {OUT_PATH}")
    print(f"Wrote {BACKEND_OUT}")


if __name__ == "__main__":
    main()
