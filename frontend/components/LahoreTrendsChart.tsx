"use client";
import { useMemo, useState } from "react";
import { Forecasts } from "@/lib/types";
import {
  Area,
  AreaChart,
  CartesianGrid,
  Line,
  LineChart,
  ReferenceArea,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

type SignalKey = "dengue" | "weather" | "smog" | "rain";

const SIGNALS: Record<SignalKey, { label: string; sub: string; color: string; key: keyof Pick<TimelineRow, "dengue_intensity" | "lahore_temp_c" | "lahore_aqi" | "lahore_rain_mm">; unit: string }> = {
  dengue:  { label: "Dengue intensity",   sub: "0-1 seasonal curve, peaks mid-Oct",          color: "#dc2626", key: "dengue_intensity", unit: "" },
  weather: { label: "Temperature (°C)",   sub: "Lahore monthly mean (PMD normals)",          color: "#f97316", key: "lahore_temp_c",    unit: "°C" },
  smog:    { label: "AQI / smog",         sub: "PM2.5 index, peaks Nov-Dec",                 color: "#7c3aed", key: "lahore_aqi",       unit: "" },
  rain:    { label: "Rainfall (mm)",      sub: "Monsoon Jul-Aug",                            color: "#0ea5e9", key: "lahore_rain_mm",   unit: "mm" },
};

type TimelineRow = NonNullable<Forecasts["trends"]>["timeline"][number];

export default function LahoreTrendsChart({ data }: { data: Forecasts }) {
  const trends = data.trends;
  const [signal, setSignal] = useState<SignalKey>("dengue");

  const series = useMemo(() => {
    if (!trends) return [];
    const cfg = SIGNALS[signal];
    return trends.timeline.map((r) => ({
      date: r.date,
      value: r[cfg.key] as number,
      ramadan: r.is_ramadan ? 1 : 0,
      eid: r.is_eid_fitr || r.is_eid_adha ? 1 : 0,
    }));
  }, [trends, signal]);

  const dataEnd = data.data_range.end;

  if (!trends) {
    return (
      <div className="card">
        <div className="section-h mb-1">Lahore signals against time</div>
        <div className="section-sub">
          Re-run <code>python model.py</code> to regenerate forecasts with the new
          Lahore weather, dengue and Eid/Ramadan trend data.
        </div>
      </div>
    );
  }

  const cfg = SIGNALS[signal];

  return (
    <div className="card">
      <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-3 mb-3">
        <div>
          <div className="section-h">{trends.city} — {cfg.label} over time</div>
          <div className="section-sub">
            {cfg.sub}. Green band = Ramadan, amber = Eid. The vertical
            dashed line marks the boundary between historical data and forecast.
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          {(Object.keys(SIGNALS) as SignalKey[]).map((k) => (
            <button
              key={k}
              onClick={() => setSignal(k)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition ${
                signal === k
                  ? "bg-brand-500 text-white border-brand-500"
                  : "bg-white text-ink-600 border-ink-200 hover:border-brand-500"
              }`}
            >
              {SIGNALS[k].label}
            </button>
          ))}
        </div>
      </div>

      <ResponsiveContainer width="100%" height={300}>
        <AreaChart data={series} margin={{ left: 0, right: 16, top: 8, bottom: 0 }}>
          <defs>
            <linearGradient id="trend-fill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor={cfg.color} stopOpacity={0.45} />
              <stop offset="95%" stopColor={cfg.color} stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#eceef2" vertical={false} />
          <XAxis dataKey="date" tick={{ fontSize: 11, fill: "#7e8493" }} minTickGap={36} />
          <YAxis tick={{ fontSize: 11, fill: "#7e8493" }} width={42} />
          <Tooltip
            contentStyle={{ borderRadius: 12, border: "1px solid #eceef2" }}
            labelStyle={{ color: "#1d2230", fontWeight: 600 }}
            formatter={(v: number) => [
              cfg.unit ? `${v.toFixed(2)} ${cfg.unit}` : v.toFixed(3),
              cfg.label,
            ]}
          />
          {trends.ramadan_windows.map(([s, e], i) => (
            <ReferenceArea
              key={`r${i}`}
              x1={s}
              x2={e}
              y1={0}
              fill="#0e9f6e"
              fillOpacity={0.1}
              stroke="#0e9f6e"
              strokeOpacity={0.3}
              label={{ value: "Ramadan", position: "insideTop", fontSize: 10, fill: "#0e9f6e" }}
            />
          ))}
          {trends.eid_fitr_windows.map(([s, e], i) => (
            <ReferenceArea
              key={`ef${i}`}
              x1={s}
              x2={e}
              y1={0}
              fill="#f59e0b"
              fillOpacity={0.18}
              stroke="#f59e0b"
              strokeOpacity={0.4}
              label={{ value: "Eid Fitr", position: "insideTop", fontSize: 10, fill: "#b45309" }}
            />
          ))}
          {trends.eid_adha_windows.map(([s, e], i) => (
            <ReferenceArea
              key={`ea${i}`}
              x1={s}
              x2={e}
              y1={0}
              fill="#fb923c"
              fillOpacity={0.18}
              stroke="#fb923c"
              strokeOpacity={0.4}
              label={{ value: "Eid Adha", position: "insideTop", fontSize: 10, fill: "#9a3412" }}
            />
          ))}
          <ReferenceArea
            x1={dataEnd}
            x2={dataEnd}
            stroke="#1d2230"
            strokeDasharray="4 4"
            strokeOpacity={0.45}
            label={{ value: "forecast →", position: "insideTopRight", fontSize: 10, fill: "#1d2230" }}
          />
          <Area
            type="monotone"
            dataKey="value"
            stroke={cfg.color}
            fill="url(#trend-fill)"
            strokeWidth={2}
            name={cfg.label}
          />
        </AreaChart>
      </ResponsiveContainer>

      <DengueProxyMini data={data} />
    </div>
  );
}

function DengueProxyMini({ data }: { data: Forecasts }) {
  const proxy = data.history.dengue_proxy_daily ?? [];
  if (!proxy.length) return null;
  const series = proxy.map((r) => ({ date: r.date, cases: r.cases }));
  const total = proxy.reduce((s, r) => s + r.cases, 0);
  return (
    <div className="mt-6 border-t border-ink-100 pt-4">
      <div className="flex items-center justify-between mb-2">
        <div>
          <div className="text-sm font-semibold text-ink-800">
            Historical dengue-proxy admissions
          </div>
          <div className="text-xs text-ink-400">
            Diagnoses tagged as DENGUE / DHF / Acute Febrile Illness / Viral Illness in the CSV.
          </div>
        </div>
        <span className="tag">{total} cases</span>
      </div>
      <ResponsiveContainer width="100%" height={120}>
        <LineChart data={series} margin={{ left: 0, right: 16, top: 4, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#eceef2" vertical={false} />
          <XAxis dataKey="date" tick={{ fontSize: 10, fill: "#7e8493" }} minTickGap={36} />
          <YAxis tick={{ fontSize: 10, fill: "#7e8493" }} width={28} />
          <Tooltip
            contentStyle={{ borderRadius: 12, border: "1px solid #eceef2" }}
            formatter={(v: number) => [v, "cases"]}
          />
          <Line type="monotone" dataKey="cases" stroke="#dc2626" strokeWidth={2} dot={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
