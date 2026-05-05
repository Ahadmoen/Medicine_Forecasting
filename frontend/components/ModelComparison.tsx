"use client";

import { useMemo, useState } from "react";
import { Forecasts, ModelResult } from "@/lib/types";

const COL_DEFS: { key: keyof ModelResult["metrics"]; label: string; fmt: (n: number) => string; help: string }[] = [
  { key: "r2",             label: "R²",          fmt: (n) => n.toFixed(3),       help: "Coefficient of determination on the held-out window. 1.0 is perfect, 0 means no better than predicting the mean." },
  { key: "confidence_pct", label: "Confidence",  fmt: (n) => `${n.toFixed(0)}%`, help: "Share of test days whose prediction lands within ±25% (or ±2 units) of actual demand." },
  { key: "mae",            label: "MAE",         fmt: (n) => n.toFixed(2),       help: "Mean absolute error — average miss in raw units per day." },
  { key: "rmse",           label: "RMSE",        fmt: (n) => n.toFixed(2),       help: "Root-mean-squared error — penalises large misses more heavily." },
  { key: "n_test",         label: "Test rows",   fmt: (n) => n.toLocaleString(), help: "Number of held-out points used to score the model." },
];

function rankCellClass(values: number[], v: number, higherIsBetter: boolean): string {
  if (values.length === 0) return "";
  const sorted = [...values].sort((a, b) => (higherIsBetter ? b - a : a - b));
  if (v === sorted[0]) return "bg-emerald-100 text-emerald-800 font-semibold";
  if (v === sorted[1]) return "bg-emerald-50 text-emerald-700";
  if (v === sorted[sorted.length - 1]) return "bg-rose-50 text-rose-600";
  return "";
}

export default function ModelComparison({
  data,
  onPick,
  selected,
}: {
  data: Forecasts;
  onPick?: (name: string) => void;
  selected?: string;
}) {
  const models = data.models ?? [];
  const [sortKey, setSortKey] = useState<keyof ModelResult["metrics"]>("r2");

  const sorted = useMemo(() => {
    const higherBetter = sortKey === "r2" || sortKey === "confidence_pct";
    return [...models].sort((a, b) => {
      const av = a.metrics[sortKey] as number;
      const bv = b.metrics[sortKey] as number;
      return higherBetter ? bv - av : av - bv;
    });
  }, [models, sortKey]);

  if (models.length === 0) {
    return (
      <div className="card">
        <div className="section-h">Model comparison</div>
        <div className="section-sub mt-2">
          No <code>models</code> block in <code>forecasts.json</code> — re-run
          <code className="mx-1">python model.py</code> after this change.
        </div>
      </div>
    );
  }

  return (
    <div className="card">
      <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-3 mb-4">
        <div>
          <div className="section-h">Model selection</div>
          <div className="section-sub mt-1">
            Each candidate is trained on the same held-out window so the
            scores compare apples to apples. Click a row to drive the
            forecast charts above with that model&apos;s monthly projection.
          </div>
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-ink-500">
              <th className="text-left py-2 pr-3 font-medium">Model</th>
              <th className="text-left py-2 pr-3 font-medium">Type</th>
              {COL_DEFS.map((c) => {
                const active = sortKey === c.key;
                return (
                  <th
                    key={c.key}
                    className="py-2 px-2 font-medium text-right"
                    title={c.help}
                  >
                    <button
                      onClick={() => setSortKey(c.key)}
                      className={`inline-flex items-center gap-1 ${
                        active ? "text-emerald-700" : "hover:text-ink-700"
                      }`}
                    >
                      {c.label}
                      {active && <span>↓</span>}
                    </button>
                  </th>
                );
              })}
            </tr>
          </thead>
          <tbody>
            {sorted.map((m) => {
              const isSelected = selected === m.name;
              return (
                <tr
                  key={m.name}
                  onClick={() => onPick?.(m.name)}
                  className={`cursor-pointer ${
                    isSelected ? "bg-emerald-50" : "hover:bg-ink-50/40"
                  }`}
                >
                  <td className="py-2 pr-3 font-medium text-ink-800 whitespace-nowrap">
                    <span className="inline-flex items-center gap-2">
                      <input
                        type="radio"
                        checked={isSelected}
                        readOnly
                        className="accent-emerald-600"
                      />
                      {m.name}
                    </span>
                  </td>
                  <td className="py-2 pr-3 text-ink-500 text-xs">{m.metrics.type}</td>
                  {COL_DEFS.map((c) => {
                    const v = m.metrics[c.key] as number;
                    const allValues = models.map(
                      (mm) => mm.metrics[c.key] as number,
                    );
                    const higherBetter = c.key === "r2" || c.key === "confidence_pct";
                    const cls = rankCellClass(allValues, v, higherBetter);
                    return (
                      <td
                        key={c.key}
                        className={`py-2 px-2 text-right tabular-nums rounded ${cls}`}
                      >
                        {c.fmt(v)}
                      </td>
                    );
                  })}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <div className="mt-3 text-xs text-ink-400">
        <span className="font-medium text-ink-600">Reading the table:</span>{" "}
        Higher R² and Confidence is better; lower MAE / RMSE is better. Best in
        column is highlighted green, worst is red. Tabular models (HGB / RF / XGBoost)
        use the same engineered features; ARIMA / SARIMA / Prophet / LSTM are
        univariate per-medicine baselines.
      </div>
    </div>
  );
}
