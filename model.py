"""
Hospital Medicine Demand Forecasting
====================================
Trains a HistGradientBoosting regressor on daily medicine usage with:
- Calendar features (day-of-week, month, week-of-year, day-of-year)
- Cyclical encodings (sin/cos of DOW, month, DOY)
- Lag features (1, 7, 14, 28 days) and rolling means/stds (7, 14, 28 days)
- Macroeconomic / cultural features:
    * Ramadan, Eid-ul-Fitr, Eid-ul-Adha, Muharram windows
    * Pakistani public holidays
    * Pay-day proximity (1st of month)
    * Inflation index proxy (monthly)
- Lahore weather climatology (temperature, rainfall, AQI/smog).
- Dengue season trend (Pakistan Aug-Nov peak with day-level intensity curve,
  cross-checked against febrile/viral case counts in the CSV).

Generates a 120-day forecast for every medicine and explains predictions
with SHAP global feature importance, LIME-style local explanations, and
a per-medicine "feature elasticity" table that quantifies how much each
medicine's daily usage rises during dengue, Eid, Ramadan, smog season etc.

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
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error

warnings.filterwarnings("ignore")

ROOT = Path(__file__).parent
CSV_PATH = ROOT / "data.csv"
OUT_PATH = ROOT / "frontend" / "public" / "forecasts.json"
BACKEND_OUT = ROOT / "backend" / "forecasts.json"
FORECAST_DAYS = 180  # ~6 months — frontend horizon filter offers 3/4/5/6m
HORIZON_BUCKETS = {"3m": 90, "4m": 120, "5m": 150, "6m": 180}


# ---------------------------------------------------------------------------
# 1. Macro / cultural calendar (Pakistan)
# ---------------------------------------------------------------------------

RAMADAN_WINDOWS = [
    (date(2024, 3, 11), date(2024, 4, 9)),
    (date(2025, 3, 1),  date(2025, 3, 30)),
    (date(2026, 2, 18), date(2026, 3, 19)),
    (date(2027, 2, 8),  date(2027, 3, 9)),
]
EID_FITR_WINDOWS = [
    (date(2024, 4, 10), date(2024, 4, 12)),
    (date(2025, 3, 31), date(2025, 4, 2)),
    (date(2026, 3, 20), date(2026, 3, 22)),
    (date(2027, 3, 10), date(2027, 3, 12)),
]
EID_ADHA_WINDOWS = [
    (date(2024, 6, 17), date(2024, 6, 19)),
    (date(2025, 6, 7),  date(2025, 6, 9)),
    (date(2026, 5, 27), date(2026, 5, 29)),
    (date(2027, 5, 17), date(2027, 5, 19)),
]
MUHARRAM_WINDOWS = [
    (date(2024, 7, 17), date(2024, 7, 18)),
    (date(2025, 7, 5),  date(2025, 7, 6)),
    (date(2026, 6, 25), date(2026, 6, 26)),
    (date(2027, 6, 14), date(2027, 6, 15)),
]

PUBLIC_HOLIDAYS = {
    date(2025, 2, 5), date(2025, 3, 23), date(2025, 5, 1),
    date(2025, 8, 14), date(2025, 9, 5), date(2025, 11, 9), date(2025, 12, 25),
    date(2026, 2, 5), date(2026, 3, 23), date(2026, 5, 1), date(2026, 8, 14),
    date(2026, 9, 5), date(2026, 11, 9), date(2026, 12, 25),
}

INFLATION_INDEX = {
    "2024-06": 12.6, "2024-07": 11.1, "2024-08": 9.6, "2024-09": 6.9,
    "2024-10": 7.2,  "2024-11": 4.9,  "2024-12": 4.1, "2025-01": 2.4,
    "2025-02": 1.5,  "2025-03": 0.7,  "2025-04": 0.3, "2025-05": 3.5,
    "2025-06": 3.2,  "2025-07": 4.1,  "2025-08": 4.8, "2025-09": 5.2,
    "2025-10": 5.5,  "2025-11": 5.6,  "2025-12": 5.4, "2026-01": 5.1,
    "2026-02": 4.9,  "2026-03": 4.7,  "2026-04": 4.5, "2026-05": 4.4,
    "2026-06": 4.3,  "2026-07": 4.2,  "2026-08": 4.1, "2026-09": 4.0,
}

# Lahore weather climatology
LAHORE_TEMP_C = {
    1: 12.8,  2: 15.6,  3: 21.0,  4: 27.1,  5: 31.7,  6: 33.5,
    7: 31.6,  8: 30.7,  9: 29.4, 10: 25.0, 11: 18.8, 12: 13.7,
}
LAHORE_RAIN_MM = {
    1: 23.2,  2: 31.4,  3: 36.5,  4: 19.6,  5: 22.3,  6: 36.5,
    7: 202.4, 8: 163.6, 9: 60.5, 10: 11.3, 11: 4.2,  12: 14.0,
}
LAHORE_AQI = {
    1: 240, 2: 200, 3: 150, 4: 130, 5: 110, 6: 100,
    7: 95,  8: 110, 9: 150, 10: 220, 11: 320, 12: 290,
}

DENGUE_PEAK_DOY = 288   # ~ October 15
DENGUE_SIGMA = 28.0     # days

DENGUE_PROXY_PATTERNS = (
    "DENGUE", "DHF", "DSS",
    "FEBRILE ILLNESS", "VIRAL ILLNESS", "VIRAL FEVER",
    "PYREXIA", "PUO",
)


def dengue_intensity(d: date) -> float:
    doy = d.timetuple().tm_yday
    diff = min(abs(doy - DENGUE_PEAK_DOY), 365 - abs(doy - DENGUE_PEAK_DOY))
    return float(np.exp(-(diff ** 2) / (2 * DENGUE_SIGMA ** 2)))


def is_dengue_season(d: date) -> int:
    return int(8 <= d.month <= 11)


def lahore_weather(d: date) -> tuple[float, float, float]:
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
    df["dayofyear"] = dates.dayofyear
    df["is_weekend"] = (dates.dayofweek >= 5).astype(int)
    df["is_friday"] = (dates.dayofweek == 4).astype(int)
    df["is_monthstart"] = (dates.day <= 3).astype(int)
    df["is_monthend"] = (dates.day >= 27).astype(int)

    # Cyclical encodings — let the tree pick up smooth seasonality.
    df["dow_sin"] = np.sin(2 * np.pi * df["dayofweek"] / 7)
    df["dow_cos"] = np.cos(2 * np.pi * df["dayofweek"] / 7)
    df["month_sin"] = np.sin(2 * np.pi * df["month"] / 12)
    df["month_cos"] = np.cos(2 * np.pi * df["month"] / 12)
    df["doy_sin"] = np.sin(2 * np.pi * df["dayofyear"] / 365)
    df["doy_cos"] = np.cos(2 * np.pi * df["dayofyear"] / 365)

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
    return daily, medicines, dengue_daily, df


# ---------------------------------------------------------------------------
# 3. Feature engineering
# ---------------------------------------------------------------------------

def add_lag_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.sort_values(["GenericName", "date"]).copy()
    g = df.groupby("GenericName")["qty"]
    df["lag_1"]  = g.shift(1)
    df["lag_7"]  = g.shift(7)
    df["lag_14"] = g.shift(14)
    df["lag_28"] = g.shift(28)
    shifted = g.shift(1)
    df["roll7_mean"]   = shifted.rolling(7,  min_periods=1).mean().reset_index(0, drop=True)
    df["roll14_mean"]  = shifted.rolling(14, min_periods=1).mean().reset_index(0, drop=True)
    df["roll28_mean"]  = shifted.rolling(28, min_periods=1).mean().reset_index(0, drop=True)
    df["roll7_std"]    = shifted.rolling(7,  min_periods=1).std().reset_index(0, drop=True)
    df["roll28_std"]   = shifted.rolling(28, min_periods=1).std().reset_index(0, drop=True)
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
    "dayofweek", "month", "day", "weekofyear", "dayofyear",
    "dow_sin", "dow_cos", "month_sin", "month_cos", "doy_sin", "doy_cos",
    "is_weekend", "is_friday", "is_monthstart", "is_monthend",
    "is_ramadan", "is_eid_fitr", "is_eid_adha", "is_muharram", "is_public_holiday",
    "days_to_eid_fitr", "days_to_eid_adha", "days_to_ramadan",
    "inflation_idx",
    "lahore_temp_c", "lahore_rain_mm", "lahore_aqi",
    "is_dengue_season", "dengue_intensity",
    "lag_1", "lag_7", "lag_14", "lag_28",
    "roll7_mean", "roll14_mean", "roll28_mean", "roll7_std", "roll28_std",
]


# ---------------------------------------------------------------------------
# 4. Train + recursive forecast
# ---------------------------------------------------------------------------

def train_model(df: pd.DataFrame):
    df = df.sort_values("date").reset_index(drop=True)

    # Time-based split: last 20% of dates form the test window. This is
    # what production demand-forecasting evaluations actually look like —
    # a random shuffle leaks future info and overstates the score.
    cutoff_date = df["date"].quantile(0.8)
    train = df[df["date"] <= cutoff_date]
    test  = df[df["date"] >  cutoff_date]

    Xtr, ytr = train[FEATURE_COLS], train["qty"]
    Xte, yte = test[FEATURE_COLS],  test["qty"]

    model = HistGradientBoostingRegressor(
        max_iter=600,
        max_depth=8,
        learning_rate=0.05,
        l2_regularization=0.5,
        min_samples_leaf=20,
        early_stopping=True,
        validation_fraction=0.15,
        random_state=42,
    )
    model.fit(Xtr, ytr)

    pred = np.clip(model.predict(Xte), 0, None)
    metrics = {
        "mae":  float(mean_absolute_error(yte, pred)),
        "rmse": float(np.sqrt(mean_squared_error(yte, pred))),
        "n_train": int(len(Xtr)),
        "n_test":  int(len(Xte)),
        "split":   "time-based (last 20% of dates held out)",
    }
    return model, metrics


def forecast(model, df, medicines, horizon=FORECAST_DAYS):
    """Vectorised recursive forecast — one batch per future date."""
    last_date = df["date"].max()
    history = df.copy()
    avg_demand = history.groupby("GenericName")["qty"].mean().to_dict()
    med_to_id = {m: i for i, m in enumerate(medicines)}

    # Pre-build a quick lookup of the most recent history rows per medicine.
    hist_by_med = {m: history[history["GenericName"] == m].sort_values("date") for m in medicines}

    out_rows = []
    for h in range(1, horizon + 1):
        target_date = last_date + pd.Timedelta(days=h)
        cal_row = build_calendar_features(pd.DatetimeIndex([target_date])).iloc[0].to_dict()

        rows = []
        for med in medicines:
            qty_series = hist_by_med[med]["qty"]
            n = len(qty_series)
            lag_1  = float(qty_series.iloc[-1])  if n >= 1  else 0.0
            lag_7  = float(qty_series.iloc[-7])  if n >= 7  else lag_1
            lag_14 = float(qty_series.iloc[-14]) if n >= 14 else lag_1
            lag_28 = float(qty_series.iloc[-28]) if n >= 28 else lag_14
            roll7   = float(qty_series.tail(7).mean())   if n else 0.0
            roll14  = float(qty_series.tail(14).mean())  if n else 0.0
            roll28  = float(qty_series.tail(28).mean())  if n else 0.0
            roll7s  = float(qty_series.tail(7).std() or 0.0)
            roll28s = float(qty_series.tail(28).std() or 0.0)

            rows.append({
                "date": target_date,
                "GenericName": med,
                "medicine_id": med_to_id[med],
                "medicine_avg": avg_demand.get(med, 0.0),
                **cal_row,
                "lag_1": lag_1, "lag_7": lag_7, "lag_14": lag_14, "lag_28": lag_28,
                "roll7_mean": roll7, "roll14_mean": roll14, "roll28_mean": roll28,
                "roll7_std": roll7s, "roll28_std": roll28s,
            })

        batch = pd.DataFrame(rows)
        batch["qty"] = np.clip(model.predict(batch[FEATURE_COLS]), 0, None)
        out_rows.append(batch[["date", "GenericName", "qty"]])

        # Append the new predictions back to per-medicine history so the
        # next iteration's lag features see them.
        for med in medicines:
            new_row = batch.loc[batch["GenericName"] == med, ["date", "GenericName", "qty"]]
            hist_by_med[med] = pd.concat([hist_by_med[med], new_row], ignore_index=True)

    return pd.concat(out_rows, ignore_index=True)


# ---------------------------------------------------------------------------
# 5. Explainability
# ---------------------------------------------------------------------------

def shap_global(model, df):
    """Permutation-based feature importance (HistGradientBoosting + sklearn)."""
    from sklearn.inspection import permutation_importance
    sample = df.sample(min(2000, len(df)), random_state=42)
    X = sample[FEATURE_COLS]
    y = sample["qty"]
    pi = permutation_importance(model, X, y, n_repeats=3, random_state=42, n_jobs=-1)
    pairs = sorted(zip(FEATURE_COLS, pi.importances_mean), key=lambda x: -x[1])
    return [{"feature": f, "importance": float(max(v, 0.0))} for f, v in pairs]


def lime_local(model, df, top_meds):
    """Per-medicine local contributions via finite-difference around the latest row."""
    out = {}
    for med in top_meds:
        sub = df[df["GenericName"] == med].tail(1)
        if sub.empty:
            continue
        x = sub[FEATURE_COLS].iloc[0].to_dict()
        base_pred = float(model.predict(pd.DataFrame([x]))[0])
        contributions = []
        for f in FEATURE_COLS:
            x_minus = dict(x)
            # nudge feature toward zero (or toward its column mean for numeric features)
            ref = float(df[f].mean()) if f not in ("medicine_id",) else x[f]
            x_minus[f] = ref
            pred_minus = float(model.predict(pd.DataFrame([x_minus]))[0])
            contributions.append({"feature": f, "contribution": float(base_pred - pred_minus)})
        contributions.sort(key=lambda d: -abs(d["contribution"]))
        out[med] = contributions[:8]
    return out


# ---------------------------------------------------------------------------
# 5b. Per-medicine seasonal/event impact (the table the dashboard renders)
# ---------------------------------------------------------------------------

def _avg_in_mask(daily: pd.DataFrame, mask: pd.Series, med: str) -> float:
    sub = daily[(daily["GenericName"] == med) & mask]
    if sub.empty:
        return 0.0
    return float(sub["qty"].mean())


def medicine_feature_impact(daily: pd.DataFrame, fc: pd.DataFrame, medicines):
    """For each medicine, compute average *historical* daily consumption in
    each event window and the *forecast* total during the next instance of
    that event. This is what the user wants to see: medicine x feature
    columns, plus a 'next-month' projection."""

    daily = daily.copy()
    daily["d"] = daily["date"].dt.date
    py_dates = daily["d"]

    masks = {
        "dengue_peak":   daily["d"].apply(lambda d: dengue_intensity(d) >= 0.5),
        "dengue_season": daily["d"].apply(lambda d: bool(is_dengue_season(d))),
        "ramadan":       daily["d"].apply(lambda d: _in_window(d, RAMADAN_WINDOWS) == 1),
        "eid_fitr":      daily["d"].apply(lambda d: _in_window(d, EID_FITR_WINDOWS) == 1),
        "eid_adha":      daily["d"].apply(lambda d: _in_window(d, EID_ADHA_WINDOWS) == 1),
        "muharram":      daily["d"].apply(lambda d: _in_window(d, MUHARRAM_WINDOWS) == 1),
        "smog_season":   daily["d"].apply(lambda d: d.month in (11, 12, 1, 2)),
        "monsoon":       daily["d"].apply(lambda d: d.month in (7, 8, 9)),
        "summer_heat":   daily["d"].apply(lambda d: d.month in (5, 6, 7)),
        "weekend":       daily["d"].apply(lambda d: d.weekday() >= 5),
    }

    fc = fc.copy()
    fc["d"] = fc["date"].dt.date
    fc_min_date = fc["d"].min()
    event_conds = {
        "dengue_peak":   lambda d: dengue_intensity(d) >= 0.5,
        "dengue_season": lambda d: bool(is_dengue_season(d)),
        "ramadan":       lambda d: _in_window(d, RAMADAN_WINDOWS) == 1,
        "eid_fitr":      lambda d: _in_window(d, EID_FITR_WINDOWS) == 1,
        "eid_adha":      lambda d: _in_window(d, EID_ADHA_WINDOWS) == 1,
        "muharram":      lambda d: _in_window(d, MUHARRAM_WINDOWS) == 1,
        "smog_season":   lambda d: d.month in (11, 12, 1, 2),
        "monsoon":       lambda d: d.month in (7, 8, 9),
        "summer_heat":   lambda d: d.month in (5, 6, 7),
        "weekend":       lambda d: d.weekday() >= 5,
    }
    # Pre-compute, per (horizon, event), the set of forecast dates inside
    # that event window — and the row mask we'll use to sum forecast units.
    horizon_date_event = {}    # horizon_label -> ev -> set[date]
    horizon_fc_masks   = {}    # horizon_label -> ev -> bool Series
    for label, days in HORIZON_BUCKETS.items():
        cutoff = fc_min_date + pd.Timedelta(days=days - 1).to_pytimedelta()
        h_dates = sorted([d for d in fc["d"].unique() if d <= cutoff])
        horizon_date_event[label] = {
            ev: {dt for dt in h_dates if cond(dt)} for ev, cond in event_conds.items()
        }
        horizon_fc_masks[label] = {
            ev: fc["d"].isin(horizon_date_event[label][ev]) for ev in event_conds
        }

    rows = []
    overall_avg = daily.groupby("GenericName")["qty"].mean().to_dict()

    for med in medicines:
        med_daily = daily[daily["GenericName"] == med]
        if med_daily.empty or overall_avg.get(med, 0.0) == 0.0:
            continue
        baseline = overall_avg[med]
        record = {
            "medicine": med,
            "baseline_per_day": round(baseline, 2),
            "events": {},
        }
        med_fc = fc[fc["GenericName"] == med]
        for ev, m in masks.items():
            avg = _avg_in_mask(daily, m, med)
            uplift = (avg / baseline - 1.0) if baseline else 0.0
            per_horizon = {}
            for label in HORIZON_BUCKETS:
                fc_mask = horizon_fc_masks[label][ev]
                # restrict to this medicine's rows inside the horizon-event window
                med_mask = (fc["GenericName"] == med) & fc_mask
                forecast_total = float(fc.loc[med_mask, "qty"].sum())
                per_horizon[label] = {
                    "total_units": round(forecast_total, 1),
                    "days_in_window": len(horizon_date_event[label][ev]),
                }
            record["events"][ev] = {
                "historical_avg_per_day": round(avg, 2),
                "uplift_vs_baseline_pct": round(uplift * 100, 1),
                "forecast": per_horizon,
            }
        rows.append(record)

    # Sort by total historical volume so the most important rows appear first.
    rows.sort(key=lambda r: -r["baseline_per_day"])
    return rows


# ---------------------------------------------------------------------------
# 6. Orchestrate + dump JSON
# ---------------------------------------------------------------------------

def build_trends_timeline(start: pd.Timestamp, end: pd.Timestamp) -> list[dict]:
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
    daily, medicines, dengue_daily, raw = load_daily_demand()
    print(f"  {len(daily):,} daily rows, {len(medicines)} medicines")
    print(f"  range: {daily['date'].min().date()} → {daily['date'].max().date()}")

    print("Engineering features...")
    df = build_training_frame(daily, medicines)

    print("Training HistGradientBoosting model (time-based split)...")
    model, metrics = train_model(df)
    print(f"  MAE={metrics['mae']:.3f}  RMSE={metrics['rmse']:.3f}  n_train={metrics['n_train']:,}  n_test={metrics['n_test']:,}")

    print(f"Forecasting next {FORECAST_DAYS} days...")
    fc = forecast(model, df, medicines)

    print("Computing global feature importance (permutation)...")
    importance = shap_global(model, df)

    top_meds = (
        df.groupby("GenericName")["qty"].sum().sort_values(ascending=False).head(15).index.tolist()
    )
    print(f"Computing local explanations for top {len(top_meds)} medicines...")
    local = lime_local(model, df, top_meds)

    print("Computing per-medicine event impact (dengue / Eid / Ramadan / smog / ...)...")
    impact = medicine_feature_impact(daily, fc, medicines)

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
            "horizon_buckets": HORIZON_BUCKETS,
            "daily": [
                {
                    "date": r["date"].date().isoformat(),
                    "medicine": r["GenericName"],
                    "qty": float(round(r["qty"], 2)),
                }
                for _, r in fc.iterrows()
            ],
            "monthly_by_medicine": monthly.to_dict(orient="records"),
            "weekly_by_medicine":  weekly_agg.to_dict(orient="records"),
        },
        "medicine_feature_impact": impact,
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
                "lag_28":          "Demand same weekday four weeks ago (monthly cycle).",
                "roll7_mean":      "7-day rolling average demand.",
                "roll14_mean":     "14-day rolling average demand.",
                "roll28_mean":     "28-day rolling average demand.",
                "roll7_std":       "7-day rolling std (demand volatility).",
                "roll28_std":      "28-day rolling std (demand volatility).",
                "medicine_avg":    "Historical mean demand for this medicine.",
                "doy_sin":         "Sine of day-of-year — captures smooth annual seasonality.",
                "doy_cos":         "Cosine of day-of-year — captures smooth annual seasonality.",
                "month_sin":       "Sine of month — captures smooth monthly seasonality.",
                "month_cos":       "Cosine of month — captures smooth monthly seasonality.",
                "dow_sin":         "Sine of day-of-week — captures smooth weekly cycle.",
                "dow_cos":         "Cosine of day-of-week — captures smooth weekly cycle.",
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
