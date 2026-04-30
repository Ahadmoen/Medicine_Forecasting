"use client";
import { useState } from "react";
import { Forecasts } from "@/lib/types";

export default function LimePanel({ data }: { data: Forecasts }) {
  const meds = Object.keys(data.explainability.local_lime);
  const [med, setMed] = useState(meds[0] ?? "");
  const rows = data.explainability.local_lime[med] ?? [];
  const max = Math.max(1, ...rows.map((r) => Math.abs(r.contribution)));

  return (
    <div className="card">
      <div className="flex items-center justify-between mb-3">
        <div>
          <div className="section-h">LIME-style local explanation</div>
          <div className="section-sub">
            Why the model predicted what it did for the most-recent observation of this
            medicine. Green = pushed prediction up, red = pushed it down.
          </div>
        </div>
        <select
          value={med}
          onChange={(e) => setMed(e.target.value)}
          className="border border-ink-200 rounded-lg px-3 py-2 text-sm bg-white text-ink-800"
        >
          {meds.map((m) => (
            <option key={m} value={m}>
              {m}
            </option>
          ))}
        </select>
      </div>

      <div className="space-y-2">
        {rows.map((r) => {
          const positive = r.contribution >= 0;
          const widthPct = (Math.abs(r.contribution) / max) * 100;
          const desc = data.explainability.feature_descriptions[r.feature] ?? "";
          return (
            <div key={r.feature} className="">
              <div className="flex justify-between items-baseline text-xs">
                <span className="font-medium text-ink-800">{r.feature}</span>
                <span
                  className={`tabular-nums ${
                    positive ? "text-brand-700" : "text-rose-600"
                  }`}
                >
                  {positive ? "+" : ""}
                  {r.contribution.toFixed(3)}
                </span>
              </div>
              <div className="h-2 bg-ink-100 rounded-full overflow-hidden mt-1">
                <div
                  className={`h-full ${positive ? "bg-brand-500" : "bg-rose-500"}`}
                  style={{ width: `${widthPct}%` }}
                />
              </div>
              {desc && <div className="text-xs text-ink-400 mt-0.5">{desc}</div>}
            </div>
          );
        })}
      </div>
    </div>
  );
}
