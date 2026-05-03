"use client";

import { useMemo, useState } from "react";
import { Forecasts, HorizonLabel, MedicineImpact } from "@/lib/types";

const EVENT_LABELS: Record<string, { label: string; sub: string }> = {
  dengue_peak:   { label: "Dengue peak",      sub: "intensity ≥ 0.5 (≈ Sep-Nov)" },
  dengue_season: { label: "Dengue season",    sub: "Aug-Nov outbreak window"     },
  monsoon:       { label: "Monsoon",          sub: "Jul-Sep — waterborne GI"     },
  summer_heat:   { label: "Summer heat",      sub: "May-Jul — heatstroke / dehydration" },
  smog_season:   { label: "Smog season",      sub: "Nov-Feb — Lahore PM2.5 peak" },
  ramadan:       { label: "Ramadan",          sub: "fasting window"              },
  eid_fitr:      { label: "Eid-ul-Fitr",      sub: "post-Ramadan festive days"   },
  eid_adha:      { label: "Eid-ul-Adha",      sub: "zoonotic / meat GI cases"    },
  muharram:      { label: "Muharram",         sub: "processions, trauma"         },
  weekend:       { label: "Weekend",          sub: "Sat/Sun — emergency-only"    },
};

const EVENT_ORDER = [
  "dengue_peak",
  "dengue_season",
  "monsoon",
  "summer_heat",
  "smog_season",
  "ramadan",
  "eid_fitr",
  "eid_adha",
  "muharram",
  "weekend",
];

function upliftBg(pct: number): string {
  if (pct >= 50)  return "bg-emerald-200/80 text-emerald-900";
  if (pct >= 20)  return "bg-emerald-100/80 text-emerald-800";
  if (pct >= 5)   return "bg-emerald-50   text-emerald-700";
  if (pct <= -50) return "bg-rose-200/80   text-rose-900";
  if (pct <= -20) return "bg-rose-100/80   text-rose-800";
  if (pct <= -5)  return "bg-rose-50     text-rose-700";
  return "bg-ink-50 text-ink-600";
}

export default function MedicineFeatureImpact({
  data,
  horizon = "4m",
  horizonDays,
}: {
  data: Forecasts;
  horizon?: HorizonLabel;
  horizonDays?: number;
}) {
  const impact: MedicineImpact[] = data.medicine_feature_impact ?? [];
  const [view, setView] = useState<"uplift" | "forecast" | "historical">("uplift");
  const [search, setSearch] = useState("");

  const filtered = useMemo(() => {
    const q = search.trim().toUpperCase();
    if (!q) return impact;
    return impact.filter((r) => r.medicine.includes(q));
  }, [impact, search]);

  if (impact.length === 0) {
    return (
      <div className="card">
        <div className="section-h">Medicine × event impact</div>
        <div className="section-sub mt-2">
          No <code>medicine_feature_impact</code> block in forecasts.json — re-run
          <code className="mx-1">python model.py</code>.
        </div>
      </div>
    );
  }

  function cellValue(row: MedicineImpact, ev: string): string {
    const e = row.events[ev];
    if (!e) return "—";
    if (view === "uplift") {
      const sign = e.uplift_vs_baseline_pct > 0 ? "+" : "";
      return `${sign}${e.uplift_vs_baseline_pct.toFixed(0)}%`;
    }
    if (view === "forecast") {
      const fc = e.forecast?.[horizon];
      if (!fc || fc.days_in_window === 0) return "—";
      return Math.round(fc.total_units).toLocaleString();
    }
    return e.historical_avg_per_day.toFixed(1);
  }

  function cellTitle(row: MedicineImpact, ev: string): string {
    const e = row.events[ev];
    if (!e) return "";
    const fc = e.forecast?.[horizon];
    const days = fc?.days_in_window ?? 0;
    const total = fc?.total_units ?? 0;
    return [
      `${row.medicine} • ${EVENT_LABELS[ev]?.label ?? ev}`,
      `Historical avg / day: ${e.historical_avg_per_day.toFixed(2)}`,
      `Uplift vs baseline:   ${e.uplift_vs_baseline_pct > 0 ? "+" : ""}${e.uplift_vs_baseline_pct.toFixed(1)}%`,
      `Forecast (${horizon}): ${Math.round(total).toLocaleString()} units across ${days} day${days === 1 ? "" : "s"}`,
    ].join("\n");
  }

  return (
    <div className="card">
      <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-3 mb-4">
        <div>
          <div className="section-h">Medicine × event impact</div>
          <div className="section-sub mt-1">
            How each medicine&apos;s consumption shifts during dengue, Eid, Ramadan,
            smog and other windows — plus forecast totals for the next instance of each
            inside the active <span className="font-medium">{horizon.replace("m", " month")}</span> horizon.
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Filter medicine…"
            className="px-3 py-1.5 text-sm border border-ink-200 rounded-md focus:outline-none focus:ring-2 focus:ring-emerald-200"
          />
          <div className="inline-flex rounded-md border border-ink-200 overflow-hidden text-xs font-medium">
            {(["uplift", "forecast", "historical"] as const).map((v) => (
              <button
                key={v}
                onClick={() => setView(v)}
                className={`px-3 py-1.5 ${
                  view === v
                    ? "bg-emerald-600 text-white"
                    : "bg-white text-ink-600 hover:bg-ink-50"
                }`}
              >
                {v === "uplift"
                  ? "Uplift %"
                  : v === "forecast"
                  ? "Forecast units"
                  : "Hist. avg/day"}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-sm border-separate border-spacing-0">
          <thead>
            <tr className="text-ink-500">
              <th className="text-left py-2 pr-3 font-medium sticky left-0 bg-white z-10">
                Medicine
              </th>
              <th className="text-right py-2 px-2 font-medium">Baseline / day</th>
              {EVENT_ORDER.map((ev) => (
                <th
                  key={ev}
                  className="py-2 px-2 font-medium text-center min-w-[110px]"
                  title={EVENT_LABELS[ev]?.sub ?? ev}
                >
                  <div>{EVENT_LABELS[ev]?.label ?? ev}</div>
                  <div className="text-[10px] font-normal text-ink-400">
                    {EVENT_LABELS[ev]?.sub ?? ""}
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {filtered.map((row) => (
              <tr key={row.medicine} className="hover:bg-ink-50/40">
                <td className="py-1.5 pr-3 font-medium text-ink-800 whitespace-nowrap sticky left-0 bg-white">
                  {row.medicine}
                </td>
                <td className="py-1.5 px-2 text-right tabular-nums text-ink-700">
                  {row.baseline_per_day.toFixed(1)}
                </td>
                {EVENT_ORDER.map((ev) => {
                  const e = row.events[ev];
                  const cls =
                    view === "uplift" && e
                      ? upliftBg(e.uplift_vs_baseline_pct)
                      : "bg-ink-50 text-ink-700";
                  return (
                    <td key={ev} className="py-1 px-1 text-center" title={cellTitle(row, ev)}>
                      <div className={`rounded px-2 py-1.5 tabular-nums text-xs ${cls}`}>
                        {cellValue(row, ev)}
                      </div>
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="mt-3 text-xs text-ink-400">
        <span className="font-medium text-ink-600">Reading the table:</span>{" "}
        <em>Uplift %</em> compares the medicine&apos;s avg daily use during the event
        to its overall baseline — green = surge, red = drop.{" "}
        <em>Forecast units</em> sums the model&apos;s next-{horizonDays ?? 120}-day prediction
        inside the event window. Hover any cell for the full breakdown.
      </div>
    </div>
  );
}
