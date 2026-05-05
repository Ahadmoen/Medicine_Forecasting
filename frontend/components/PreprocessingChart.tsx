"use client";

import { useMemo, useState } from "react";
import { Forecasts, DailyByMedicineRow } from "@/lib/types";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  Legend,
} from "recharts";

type Stat = "mean" | "median" | "mode" | "std" | "var";

const STAT_LABELS: Record<Stat, string> = {
  mean:   "Rolling mean",
  median: "Rolling median",
  mode:   "Rolling mode",
  std:    "Rolling std-dev",
  var:    "Rolling variance",
};

const WINDOW_OPTIONS = [7, 14, 28];

function rollingApply(values: number[], window: number, stat: Stat): (number | null)[] {
  const out: (number | null)[] = [];
  for (let i = 0; i < values.length; i++) {
    const start = Math.max(0, i - window + 1);
    const slice = values.slice(start, i + 1);
    if (slice.length < Math.min(window, 3)) {
      out.push(null);
      continue;
    }
    if (stat === "mean") {
      out.push(slice.reduce((a, b) => a + b, 0) / slice.length);
    } else if (stat === "median") {
      const s = [...slice].sort((a, b) => a - b);
      const mid = Math.floor(s.length / 2);
      out.push(s.length % 2 === 1 ? s[mid] : (s[mid - 1] + s[mid]) / 2);
    } else if (stat === "mode") {
      const counts = new Map<number, number>();
      for (const v of slice) counts.set(v, (counts.get(v) ?? 0) + 1);
      let best = slice[0];
      let bestC = 0;
      counts.forEach((c, v) => {
        if (c > bestC) {
          best = v;
          bestC = c;
        }
      });
      out.push(best);
    } else {
      const m = slice.reduce((a, b) => a + b, 0) / slice.length;
      const v = slice.reduce((a, b) => a + (b - m) ** 2, 0) / slice.length;
      out.push(stat === "var" ? v : Math.sqrt(v));
    }
  }
  return out;
}

export default function PreprocessingChart({ data }: { data: Forecasts }) {
  const dailyByMed: DailyByMedicineRow[] = data.history.daily_by_medicine ?? [];
  const medicines = useMemo(() => {
    if (dailyByMed.length === 0) return data.medicines;
    return Array.from(new Set(dailyByMed.map((r) => r.medicine))).sort();
  }, [dailyByMed, data]);

  const [medicine, setMedicine] = useState<string>(
    data.top_medicines[0] ?? medicines[0] ?? "",
  );
  const [stat, setStat] = useState<Stat>("mean");
  const [window, setWindow] = useState<number>(7);

  const series = useMemo(() => {
    const rows = dailyByMed
      .filter((r) => r.medicine === medicine)
      .sort((a, b) => a.date.localeCompare(b.date));
    if (rows.length === 0) return [];
    const qty = rows.map((r) => r.qty);
    const rolled = rollingApply(qty, window, stat);
    return rows.map((r, i) => ({
      date: r.date,
      qty: r.qty,
      stat: rolled[i],
    }));
  }, [dailyByMed, medicine, stat, window]);

  if (dailyByMed.length === 0) {
    return (
      <div className="card">
        <div className="section-h">Preprocessing — daily usage with rolling stats</div>
        <div className="section-sub mt-2">
          No <code>history.daily_by_medicine</code> in <code>forecasts.json</code> —
          re-run <code className="mx-1">python model.py</code>.
        </div>
      </div>
    );
  }

  // Whole-series statistics shown as KPIs.
  const summary = useMemo(() => {
    const qty = series.map((r) => r.qty);
    if (qty.length === 0) return null;
    const sorted = [...qty].sort((a, b) => a - b);
    const mean = qty.reduce((a, b) => a + b, 0) / qty.length;
    const median =
      sorted.length % 2 === 1
        ? sorted[(sorted.length - 1) / 2]
        : (sorted[sorted.length / 2 - 1] + sorted[sorted.length / 2]) / 2;
    const counts = new Map<number, number>();
    for (const v of qty) counts.set(v, (counts.get(v) ?? 0) + 1);
    let mode = qty[0];
    let bestC = 0;
    counts.forEach((c, v) => {
      if (c > bestC) {
        mode = v;
        bestC = c;
      }
    });
    const variance = qty.reduce((a, b) => a + (b - mean) ** 2, 0) / qty.length;
    const std = Math.sqrt(variance);
    return { mean, median, mode, std, variance, n: qty.length };
  }, [series]);

  return (
    <div className="card">
      <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-3 mb-3">
        <div>
          <div className="section-h">Preprocessing — daily usage</div>
          <div className="section-sub mt-1">
            Per-medicine time series with the rolling statistic of your choice
            overlaid. Use this to spot regime shifts before feeding the model:
            sudden volatility, missing weeks, or quiet vs. surge phases.
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          <select
            value={medicine}
            onChange={(e) => setMedicine(e.target.value)}
            className="border border-ink-200 rounded-md px-3 py-1.5 text-sm bg-white"
          >
            {medicines.map((m) => (
              <option key={m} value={m}>
                {m}
              </option>
            ))}
          </select>
          <div className="inline-flex rounded-md border border-ink-200 overflow-hidden text-xs font-medium">
            {(Object.keys(STAT_LABELS) as Stat[]).map((s) => (
              <button
                key={s}
                onClick={() => setStat(s)}
                className={`px-3 py-1.5 ${
                  stat === s
                    ? "bg-emerald-600 text-white"
                    : "bg-white text-ink-600 hover:bg-ink-50"
                }`}
              >
                {s.charAt(0).toUpperCase() + s.slice(1)}
              </button>
            ))}
          </div>
          <div className="inline-flex rounded-md border border-ink-200 overflow-hidden text-xs font-medium">
            {WINDOW_OPTIONS.map((w) => (
              <button
                key={w}
                onClick={() => setWindow(w)}
                className={`px-3 py-1.5 ${
                  window === w
                    ? "bg-ink-800 text-white"
                    : "bg-white text-ink-600 hover:bg-ink-50"
                }`}
              >
                {w}d
              </button>
            ))}
          </div>
        </div>
      </div>

      {summary && (
        <div className="grid grid-cols-3 md:grid-cols-6 gap-2 mb-3 text-xs">
          {[
            { k: "Days",     v: summary.n.toLocaleString() },
            { k: "Mean",     v: summary.mean.toFixed(2) },
            { k: "Median",   v: summary.median.toFixed(2) },
            { k: "Mode",     v: summary.mode.toFixed(0) },
            { k: "Std",      v: summary.std.toFixed(2) },
            { k: "Variance", v: summary.variance.toFixed(2) },
          ].map((x) => (
            <div key={x.k} className="rounded-md border border-ink-200 px-2 py-1.5 bg-ink-50/40">
              <div className="text-[10px] uppercase tracking-wide text-ink-400">
                {x.k}
              </div>
              <div className="font-semibold text-ink-800 tabular-nums">{x.v}</div>
            </div>
          ))}
        </div>
      )}

      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={series} margin={{ left: 0, right: 16, top: 8, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#eceef2" vertical={false} />
          <XAxis dataKey="date" tick={{ fontSize: 11, fill: "#7e8493" }} minTickGap={40} />
          <YAxis tick={{ fontSize: 11, fill: "#7e8493" }} width={36} />
          <Tooltip
            contentStyle={{ borderRadius: 12, border: "1px solid #eceef2" }}
            labelStyle={{ color: "#1d2230", fontWeight: 600 }}
          />
          <Legend />
          <Line
            type="monotone"
            dataKey="qty"
            stroke="#94a3b8"
            strokeWidth={1.2}
            dot={false}
            name="Daily units"
          />
          <Line
            type="monotone"
            dataKey="stat"
            stroke="#0b8a5e"
            strokeWidth={2}
            dot={false}
            name={`${STAT_LABELS[stat]} (${window}d)`}
            connectNulls
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
