"use client";

import { useState } from "react";
import { Forecasts, HorizonLabel } from "@/lib/types";
import ForecastChart from "./ForecastChart";
import MonthlyHeatmap from "./MonthlyHeatmap";
import MedicineFeatureImpact from "./MedicineFeatureImpact";

const HORIZON_OPTIONS: { label: HorizonLabel; days: number; text: string }[] = [
  { label: "3m", days: 90,  text: "3 months" },
  { label: "4m", days: 120, text: "4 months" },
  { label: "5m", days: 150, text: "5 months" },
  { label: "6m", days: 180, text: "6 months" },
];

export default function ForecastSection({ data }: { data: Forecasts }) {
  const [horizon, setHorizon] = useState<HorizonLabel>("4m");
  const horizonDays =
    HORIZON_OPTIONS.find((o) => o.label === horizon)?.days ?? 120;

  return (
    <div className="space-y-6">
      <div className="card flex flex-col md:flex-row md:items-center md:justify-between gap-3">
        <div>
          <div className="section-h">Forecast horizon</div>
          <div className="section-sub mt-1">
            Pick how far ahead the forecast charts and event-impact totals
            should look. The model is trained once and you slice the same
            prediction window — no re-training needed.
          </div>
        </div>
        <div className="inline-flex rounded-md border border-ink-200 overflow-hidden text-sm font-medium self-start md:self-auto">
          {HORIZON_OPTIONS.map((opt) => (
            <button
              key={opt.label}
              onClick={() => setHorizon(opt.label)}
              className={`px-4 py-2 ${
                horizon === opt.label
                  ? "bg-emerald-600 text-white"
                  : "bg-white text-ink-600 hover:bg-ink-50"
              }`}
            >
              {opt.text}
            </button>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <ForecastChart data={data} horizonDays={horizonDays} />
        <MonthlyHeatmap data={data} horizonDays={horizonDays} />
      </div>
      <MedicineFeatureImpact data={data} horizon={horizon} horizonDays={horizonDays} />
    </div>
  );
}
