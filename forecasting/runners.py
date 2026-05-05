"""
Train and score a small zoo of forecasting models on the per-medicine
daily-demand series so the dashboard can let users compare them.

Why per-medicine univariate models? ARIMA / SARIMA / Prophet / LSTM are
naturally univariate, and Random Forest / XGBoost / HistGradientBoosting
benefit from the same feature set used by the panel-level model. Forecasts
are aggregated and stored alongside the panel model in `forecasts.json`,
keyed by model name so the frontend can let users pick a model.

Each runner returns a dict:
    {
      "name": "...",
      "metrics": {"mae": float, "rmse": float, "r2": float,
                  "confidence_pct": float, "n_test": int, "type": "..."},
      "monthly_by_medicine": [{"GenericName": str, "month": "YYYY-MM", "qty": float}, ...],
      "daily_by_medicine":   [{"GenericName": str, "date":  "YYYY-MM-DD", "qty": float}, ...],
    }
"""
from __future__ import annotations

import warnings
from datetime import date, timedelta
from typing import Callable

import numpy as np
import pandas as pd
from sklearn.ensemble import (
    HistGradientBoostingRegressor,
    RandomForestRegressor,
)
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

warnings.filterwarnings("ignore")


# ---------------------------------------------------------------------------
# Shared utilities
# ---------------------------------------------------------------------------

def _confidence_pct(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """A simple coverage-style confidence:

    100 * fraction of test points whose predicted value lies within
    ±25% (or ±2 units, whichever is larger — to handle near-zero series)
    of the true value. Maps R² intuition to something procurement teams
    can read directly: "85% confidence" means 85% of days landed within
    a quarter of the actual demand.
    """
    if len(y_true) == 0:
        return 0.0
    tol = np.maximum(0.25 * np.abs(y_true), 2.0)
    hits = np.abs(y_true - y_pred) <= tol
    return float(100.0 * np.mean(hits))


def _summary_metrics(y_true, y_pred, kind: str) -> dict:
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    return {
        "mae":  float(mean_absolute_error(y_true, y_pred)),
        "rmse": float(np.sqrt(mean_squared_error(y_true, y_pred))),
        "r2":   float(r2_score(y_true, y_pred)) if len(y_true) > 1 else 0.0,
        "confidence_pct": _confidence_pct(y_true, y_pred),
        "n_test": int(len(y_true)),
        "type":   kind,
    }


def _aggregate_monthly(daily_rows: list[dict]) -> list[dict]:
    if not daily_rows:
        return []
    df = pd.DataFrame(daily_rows)
    df["date"] = pd.to_datetime(df["date"])
    df["month"] = df["date"].dt.to_period("M").astype(str)
    out = (
        df.groupby(["GenericName", "month"])["qty"]
          .sum().round().reset_index()
    )
    return out.to_dict(orient="records")


def _split_time(df: pd.DataFrame):
    cutoff = df["date"].quantile(0.8)
    train = df[df["date"] <= cutoff].copy()
    test  = df[df["date"] >  cutoff].copy()
    return train, test


# ---------------------------------------------------------------------------
# Tabular runners (HGB / RF / XGBoost) — share the same feature matrix
# ---------------------------------------------------------------------------

def _tabular_run(
    df_full: pd.DataFrame,
    feature_cols: list[str],
    medicines: list[str],
    horizon_days: int,
    cal_builder: Callable[[pd.DatetimeIndex], pd.DataFrame],
    model_factory: Callable[[], object],
    name: str,
    kind: str,
) -> dict:
    train, test = _split_time(df_full)
    Xtr, ytr = train[feature_cols], train["qty"]
    Xte, yte = test[feature_cols],  test["qty"]
    model = model_factory()
    model.fit(Xtr, ytr)
    pred = np.clip(model.predict(Xte), 0, None)
    metrics = _summary_metrics(yte, pred, kind)

    # Recursive forecast — same shape as the panel model.
    last_date = df_full["date"].max()
    avg_demand = df_full.groupby("GenericName")["qty"].mean().to_dict()
    med_to_id  = {m: i for i, m in enumerate(medicines)}
    hist_by_med = {m: df_full[df_full["GenericName"] == m].sort_values("date") for m in medicines}

    out_rows = []
    for h in range(1, horizon_days + 1):
        target_date = last_date + pd.Timedelta(days=h)
        cal_row = cal_builder(pd.DatetimeIndex([target_date])).iloc[0].to_dict()
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
        batch["qty"] = np.clip(model.predict(batch[feature_cols]), 0, None)
        for med in medicines:
            new_row = batch.loc[batch["GenericName"] == med, ["date", "GenericName", "qty"]]
            hist_by_med[med] = pd.concat([hist_by_med[med], new_row], ignore_index=True)
            out_rows.append({
                "date": new_row["date"].iloc[0].date().isoformat(),
                "GenericName": med,
                "qty": float(round(new_row["qty"].iloc[0], 2)),
            })

    return {
        "name": name,
        "metrics": metrics,
        "daily_by_medicine":   out_rows,
        "monthly_by_medicine": _aggregate_monthly(out_rows),
    }


def _hgb_factory():
    return HistGradientBoostingRegressor(
        max_iter=600, max_depth=8, learning_rate=0.05,
        l2_regularization=0.5, min_samples_leaf=20,
        early_stopping=True, validation_fraction=0.15, random_state=42,
    )


def _rf_factory():
    return RandomForestRegressor(
        n_estimators=300, max_depth=14, min_samples_leaf=4,
        n_jobs=-1, random_state=42,
    )


def _xgb_factory():
    import xgboost as xgb
    return xgb.XGBRegressor(
        n_estimators=600, max_depth=7, learning_rate=0.05,
        subsample=0.85, colsample_bytree=0.85, reg_lambda=1.0,
        tree_method="hist", random_state=42, n_jobs=-1, verbosity=0,
    )


# ---------------------------------------------------------------------------
# Univariate runners (ARIMA / SARIMA / Prophet / LSTM)
# ---------------------------------------------------------------------------

def _per_medicine_test_eval(daily: pd.DataFrame, predict_fn) -> tuple[list, list]:
    """Walk every medicine, fit on train half, evaluate on test half."""
    yt_all, yp_all = [], []
    for med, sub in daily.groupby("GenericName"):
        sub = sub.sort_values("date")
        if len(sub) < 30:
            continue
        cutoff = int(len(sub) * 0.8)
        train = sub.iloc[:cutoff]
        test  = sub.iloc[cutoff:]
        if test.empty:
            continue
        try:
            preds = predict_fn(train, len(test))
        except Exception:
            continue
        preds = np.clip(np.asarray(preds, dtype=float), 0, None)
        if len(preds) != len(test):
            continue
        yt_all.extend(test["qty"].tolist())
        yp_all.extend(preds.tolist())
    return yt_all, yp_all


def _arima_run(daily: pd.DataFrame, medicines: list[str], horizon_days: int) -> dict:
    from statsmodels.tsa.arima.model import ARIMA

    def predict(train, steps):
        y = train["qty"].astype(float).values
        m = ARIMA(y, order=(2, 1, 2)).fit()
        return m.forecast(steps=steps)

    yt, yp = _per_medicine_test_eval(daily, predict)
    metrics = _summary_metrics(yt, yp, "ARIMA(2,1,2)")

    # Forecast: train on the full per-medicine history and project horizon_days.
    out_rows = []
    last_date = daily["date"].max()
    for med, sub in daily.groupby("GenericName"):
        sub = sub.sort_values("date")
        try:
            m = ARIMA(sub["qty"].astype(float).values, order=(2, 1, 2)).fit()
            preds = np.clip(np.asarray(m.forecast(steps=horizon_days), dtype=float), 0, None)
        except Exception:
            preds = np.full(horizon_days, float(sub["qty"].mean()))
        for h, q in enumerate(preds, start=1):
            out_rows.append({
                "date": (last_date + pd.Timedelta(days=h)).date().isoformat(),
                "GenericName": med,
                "qty": float(round(q, 2)),
            })

    return {
        "name": "ARIMA",
        "metrics": metrics,
        "daily_by_medicine":   out_rows,
        "monthly_by_medicine": _aggregate_monthly(out_rows),
    }


def _sarima_run(daily: pd.DataFrame, medicines: list[str], horizon_days: int) -> dict:
    from statsmodels.tsa.statespace.sarimax import SARIMAX

    def predict(train, steps):
        y = train["qty"].astype(float).values
        m = SARIMAX(
            y, order=(1, 1, 1), seasonal_order=(1, 1, 1, 7),
            enforce_stationarity=False, enforce_invertibility=False,
        ).fit(disp=False)
        return m.forecast(steps=steps)

    yt, yp = _per_medicine_test_eval(daily, predict)
    metrics = _summary_metrics(yt, yp, "SARIMA(1,1,1)(1,1,1,7)")

    out_rows = []
    last_date = daily["date"].max()
    for med, sub in daily.groupby("GenericName"):
        sub = sub.sort_values("date")
        try:
            m = SARIMAX(
                sub["qty"].astype(float).values,
                order=(1, 1, 1), seasonal_order=(1, 1, 1, 7),
                enforce_stationarity=False, enforce_invertibility=False,
            ).fit(disp=False)
            preds = np.clip(np.asarray(m.forecast(steps=horizon_days), dtype=float), 0, None)
        except Exception:
            preds = np.full(horizon_days, float(sub["qty"].mean()))
        for h, q in enumerate(preds, start=1):
            out_rows.append({
                "date": (last_date + pd.Timedelta(days=h)).date().isoformat(),
                "GenericName": med,
                "qty": float(round(q, 2)),
            })

    return {
        "name": "SARIMA",
        "metrics": metrics,
        "daily_by_medicine":   out_rows,
        "monthly_by_medicine": _aggregate_monthly(out_rows),
    }


def _prophet_run(daily: pd.DataFrame, medicines: list[str], horizon_days: int) -> dict:
    import logging
    logging.getLogger("prophet").setLevel(logging.ERROR)
    logging.getLogger("cmdstanpy").setLevel(logging.ERROR)
    from prophet import Prophet

    def fit_predict(train_df, steps):
        prep = train_df[["date", "qty"]].rename(columns={"date": "ds", "qty": "y"})
        m = Prophet(
            weekly_seasonality=True, yearly_seasonality=True,
            daily_seasonality=False, seasonality_mode="additive",
            uncertainty_samples=0,
        )
        m.fit(prep)
        future = m.make_future_dataframe(periods=steps, freq="D")
        fc = m.predict(future).tail(steps)["yhat"].values
        return fc

    yt, yp = _per_medicine_test_eval(daily, fit_predict)
    metrics = _summary_metrics(yt, yp, "Prophet (additive)")

    out_rows = []
    last_date = daily["date"].max()
    for med, sub in daily.groupby("GenericName"):
        sub = sub.sort_values("date")
        try:
            preds = np.clip(fit_predict(sub, horizon_days), 0, None)
        except Exception:
            preds = np.full(horizon_days, float(sub["qty"].mean()))
        for h, q in enumerate(preds, start=1):
            out_rows.append({
                "date": (last_date + pd.Timedelta(days=h)).date().isoformat(),
                "GenericName": med,
                "qty": float(round(q, 2)),
            })

    return {
        "name": "Prophet",
        "metrics": metrics,
        "daily_by_medicine":   out_rows,
        "monthly_by_medicine": _aggregate_monthly(out_rows),
    }


def _lstm_run(daily: pd.DataFrame, medicines: list[str], horizon_days: int) -> dict:
    """Tiny per-medicine LSTM. Sequence length 28, hidden 24, 20 epochs.
    Trained per medicine (CPU-only, single-threaded to avoid contention with
    any leftover joblib workers). Designed to be cheap and a fair structural
    baseline for a recurrent model — not an SOTA tuned model."""
    import torch
    from torch import nn

    # Pin to a single thread; torch's default OpenMP pool fights with
    # joblib's loky workers and on macOS fork() can deadlock the pair.
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)

    SEQ = 28
    HIDDEN = 24
    EPOCHS = 20
    LR = 0.01

    class LSTMReg(nn.Module):
        def __init__(self):
            super().__init__()
            self.lstm = nn.LSTM(input_size=1, hidden_size=HIDDEN, batch_first=True)
            self.head = nn.Linear(HIDDEN, 1)

        def forward(self, x):
            out, _ = self.lstm(x)
            return self.head(out[:, -1, :]).squeeze(-1)

    def _scale(arr):
        mu = float(arr.mean()) if len(arr) else 0.0
        sd = float(arr.std() or 1.0)
        return (arr - mu) / sd, mu, sd

    def _windows(y_scaled):
        xs, ys = [], []
        for i in range(SEQ, len(y_scaled)):
            xs.append(y_scaled[i - SEQ:i])
            ys.append(y_scaled[i])
        if not xs:
            return None, None
        return (torch.tensor(np.array(xs), dtype=torch.float32).unsqueeze(-1),
                torch.tensor(np.array(ys), dtype=torch.float32))

    def _train_predict(train_y, steps):
        scaled, mu, sd = _scale(np.asarray(train_y, dtype=float))
        Xt, yt = _windows(scaled)
        if Xt is None:
            return np.full(steps, mu)
        net = LSTMReg()
        opt = torch.optim.Adam(net.parameters(), lr=LR)
        for _ in range(EPOCHS):
            opt.zero_grad()
            pred = net(Xt)
            loss = ((pred - yt) ** 2).mean()
            loss.backward()
            opt.step()
        # iterative forecast
        with torch.no_grad():
            window = list(scaled[-SEQ:])
            preds = []
            for _ in range(steps):
                x = torch.tensor(window[-SEQ:], dtype=torch.float32).view(1, SEQ, 1)
                p = float(net(x).item())
                preds.append(p)
                window.append(p)
        return np.asarray(preds) * sd + mu

    # Test eval
    yt_all, yp_all = [], []
    med_groups = list(daily.groupby("GenericName"))
    for i, (med, sub) in enumerate(med_groups, start=1):
        sub = sub.sort_values("date")
        print(f"      LSTM [{i}/{len(med_groups)}] eval: {med}", flush=True)
        if len(sub) < SEQ + 10:
            continue
        cutoff = int(len(sub) * 0.8)
        train = sub.iloc[:cutoff]
        test  = sub.iloc[cutoff:]
        if test.empty:
            continue
        try:
            preds = _train_predict(train["qty"].values, len(test))
        except Exception:
            continue
        preds = np.clip(np.asarray(preds), 0, None)
        yt_all.extend(test["qty"].tolist())
        yp_all.extend(preds.tolist())
    metrics = _summary_metrics(yt_all, yp_all, "LSTM (28-step, hidden 24)")

    # Forecast on full series
    out_rows = []
    last_date = daily["date"].max()
    for i, (med, sub) in enumerate(med_groups, start=1):
        sub = sub.sort_values("date")
        print(f"      LSTM [{i}/{len(med_groups)}] forecast: {med}", flush=True)
        try:
            preds = np.clip(_train_predict(sub["qty"].values, horizon_days), 0, None)
        except Exception:
            preds = np.full(horizon_days, float(sub["qty"].mean()))
        for h, q in enumerate(preds, start=1):
            out_rows.append({
                "date": (last_date + pd.Timedelta(days=h)).date().isoformat(),
                "GenericName": med,
                "qty": float(round(q, 2)),
            })

    return {
        "name": "LSTM",
        "metrics": metrics,
        "daily_by_medicine":   out_rows,
        "monthly_by_medicine": _aggregate_monthly(out_rows),
    }


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

def train_all_models(
    df_full: pd.DataFrame,
    daily: pd.DataFrame,
    feature_cols: list[str],
    medicines: list[str],
    horizon_days: int,
    cal_builder: Callable[[pd.DatetimeIndex], pd.DataFrame],
    skip_lstm: bool = False,
) -> list[dict]:
    """Run every available model. Each runner is wrapped in try/except so a
    missing dependency or a noisy series doesn't kill the whole pipeline."""
    results: list[dict] = []

    runners: list[tuple[str, Callable[[], dict]]] = [
        ("HistGradientBoosting", lambda: _tabular_run(
            df_full, feature_cols, medicines, horizon_days,
            cal_builder, _hgb_factory, "HistGradientBoosting", "Gradient-boosted trees (sklearn)",
        )),
        ("RandomForest", lambda: _tabular_run(
            df_full, feature_cols, medicines, horizon_days,
            cal_builder, _rf_factory, "RandomForest", "Bagged decision trees",
        )),
        ("XGBoost", lambda: _tabular_run(
            df_full, feature_cols, medicines, horizon_days,
            cal_builder, _xgb_factory, "XGBoost", "Gradient-boosted trees (xgboost)",
        )),
        ("ARIMA",   lambda: _arima_run(daily,   medicines, horizon_days)),
        ("SARIMA",  lambda: _sarima_run(daily,  medicines, horizon_days)),
        ("Prophet", lambda: _prophet_run(daily, medicines, horizon_days)),
    ]
    if not skip_lstm:
        runners.append(("LSTM", lambda: _lstm_run(daily, medicines, horizon_days)))

    for name, fn in runners:
        try:
            print(f"  · training {name}...")
            res = fn()
            print(f"      MAE={res['metrics']['mae']:.2f}  R²={res['metrics']['r2']:.2f}  "
                  f"conf={res['metrics']['confidence_pct']:.0f}%")
            results.append(res)
        except Exception as exc:
            print(f"      WARNING: {name} failed ({exc!r}); skipping")

    return results
