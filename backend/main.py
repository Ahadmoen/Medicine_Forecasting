"""
FastAPI backend for the Hospital Medicine Forecasting dashboard.

The CSV at the repo root is the single source of truth. On startup the
backend will (re)build forecasts.json by running model.main() if the
JSON is missing or older than the CSV — so adding rows to data.csv and
restarting the API is enough to refresh predictions. No deployment is
required: the dashboard ships forecasts.json statically on Vercel and
this API is for local exploration only.

Run locally:
    uvicorn main:app --reload --port 8000
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

ROOT = Path(__file__).parent
REPO_ROOT = ROOT.parent
DATA_PATH = ROOT / "forecasts.json"
CSV_PATH = REPO_ROOT / "data.csv"

# Make the top-level model.py importable so we can rebuild forecasts.json
# directly from the CSV without an external pre-step.
sys.path.insert(0, str(REPO_ROOT))


def _csv_newer_than_json() -> bool:
    if not DATA_PATH.exists():
        return True
    if not CSV_PATH.exists():
        return False
    return CSV_PATH.stat().st_mtime > DATA_PATH.stat().st_mtime


def _ensure_forecasts():
    """Re-run model.py if forecasts.json is missing or older than data.csv."""
    if not _csv_newer_than_json():
        return
    try:
        import model  # noqa: F401  — top-level model.py
        print("[backend] data.csv is newer than forecasts.json — re-training...")
        model.main()
    except Exception as exc:  # pragma: no cover - surfaced via /health
        print(f"[backend] WARNING: could not auto-train ({exc!r}); "
              "falling back to whatever forecasts.json is on disk.")


app = FastAPI(
    title="Hospital Medicine Forecasting API",
    description=(
        "3-4 month medicine demand forecasts with Lahore weather, dengue, "
        "Eid / Ramadan and inflation features. CSV-backed, local-only."
    ),
    version="1.1.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_cache: Optional[dict] = None


@app.on_event("startup")
def _on_startup():
    _ensure_forecasts()


def load_data() -> dict:
    global _cache
    if _cache is None:
        if not DATA_PATH.exists():
            raise HTTPException(
                500,
                "forecasts.json missing — run `python model.py` from the repo root.",
            )
        _cache = json.loads(DATA_PATH.read_text())
    return _cache


@app.get("/")
def root():
    return {
        "service": "Hospital Medicine Forecasting API",
        "source": str(CSV_PATH),
        "endpoints": [
            "/health",
            "/summary",
            "/medicines",
            "/forecast/{medicine}",
            "/forecast/{medicine}/monthly",
            "/explain/global",
            "/explain/{medicine}",
            "/history",
            "/dengue",
            "/trends",
            "/refresh",
        ],
    }


@app.get("/health")
def health():
    return {
        "status": "ok",
        "csv_present": CSV_PATH.exists(),
        "forecasts_present": DATA_PATH.exists(),
    }


@app.post("/refresh")
def refresh():
    """Force a re-train from data.csv and clear the in-memory cache."""
    global _cache
    import model  # noqa: WPS433
    model.main()
    _cache = None
    return {"refreshed": True}


@app.get("/summary")
def summary():
    d = load_data()
    return {
        "generated_at": d["generated_at"],
        "data_range":   d["data_range"],
        "metrics":      d["metrics"],
        "horizon_days": d["forecast"]["horizon_days"],
        "n_medicines":  len(d["medicines"]),
        "top_medicines": d["top_medicines"],
    }


@app.get("/medicines")
def medicines():
    d = load_data()
    return {"medicines": d["medicines"], "top_medicines": d["top_medicines"]}


@app.get("/forecast/{medicine}")
def forecast_for(medicine: str, granularity: str = Query("daily", pattern="^(daily|weekly|monthly)$")):
    d = load_data()
    med = medicine.upper().strip()
    if med not in d["medicines"]:
        raise HTTPException(404, f"Unknown medicine: {medicine}")

    if granularity == "daily":
        rows = [r for r in d["forecast"]["daily"] if r["medicine"] == med]
    elif granularity == "weekly":
        rows = [r for r in d["forecast"]["weekly_by_medicine"] if r["GenericName"] == med]
    else:
        rows = [r for r in d["forecast"]["monthly_by_medicine"] if r["GenericName"] == med]
    return {"medicine": med, "granularity": granularity, "rows": rows}


@app.get("/forecast/{medicine}/monthly")
def forecast_monthly(medicine: str):
    return forecast_for(medicine, "monthly")


@app.get("/explain/global")
def explain_global():
    d = load_data()
    return {
        "global_shap": d["explainability"]["global_shap"],
        "feature_descriptions": d["explainability"]["feature_descriptions"],
    }


@app.get("/explain/{medicine}")
def explain_medicine(medicine: str):
    d = load_data()
    med = medicine.upper().strip()
    local = d["explainability"]["local_lime"]
    if med not in local:
        raise HTTPException(404, f"No local explanation for: {medicine}")
    return {"medicine": med, "contributions": local[med]}


@app.get("/history")
def history():
    d = load_data()
    return d["history"]


@app.get("/dengue")
def dengue():
    """Historical dengue-proxy admissions + future seasonal intensity curve."""
    d = load_data()
    timeline = d.get("trends", {}).get("timeline", [])
    return {
        "history_proxy_daily": d["history"].get("dengue_proxy_daily", []),
        "intensity_curve": [
            {"date": r["date"], "intensity": r["dengue_intensity"], "in_season": r["is_dengue_season"]}
            for r in timeline
        ],
    }


@app.get("/trends")
def trends(signal: Optional[str] = Query(None, pattern="^(dengue|temp|rain|aqi|ramadan|eid)$")):
    """Lahore time-series for any tracked signal."""
    d = load_data()
    t = d.get("trends")
    if not t:
        raise HTTPException(500, "Trends payload missing — re-run model.py.")
    if signal is None:
        return t

    key_map = {
        "dengue":  "dengue_intensity",
        "temp":    "lahore_temp_c",
        "rain":    "lahore_rain_mm",
        "aqi":     "lahore_aqi",
        "ramadan": "is_ramadan",
        "eid":     "is_eid_fitr",
    }
    field = key_map[signal]
    return {
        "city": t.get("city", "Lahore"),
        "signal": signal,
        "rows": [{"date": r["date"], "value": r[field]} for r in t["timeline"]],
    }
