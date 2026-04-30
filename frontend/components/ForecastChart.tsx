"use client";
import { useMemo, useState } from "react";
import { Forecasts } from "@/lib/types";
import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceArea,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  Legend,
} from "recharts";

// Highlight cultural / macro bands the model uses as features.
const BANDS: { start: string; end: string; label: string; color: string }[] = [
  { start: "2025-08-14", end: "2025-08-14", label: "Independence Day", color: "#0e9f6e" },
  { start: "2025-09-04", end: "2025-09-05", label: "Eid Milad-un-Nabi",  color: "#9b8cff" },
  { start: "2025-11-09", end: "2025-11-09", label: "Iqbal Day",          color: "#fbbf24" },
  { start: "2025-12-25", end: "2025-12-25", label: "Quaid Day",          color: "#fb7185" },
  { start: "2026-02-18", end: "2026-03-19", label: "Ramadan 2026",       color: "#34d399" },
];

export default function ForecastChart({ data }: { data: Forecasts }) {
  const [medicine, setMedicine] = useState<string>(data.top_medicines[0] ?? data.medicines[0]);

  const series = useMemo(() => {
    const hist = data.history.daily_total
      .filter(() => false)
      .map((r) => ({ date: r.date, history: 0, forecast: undefined as number | undefined }));
    const histPerMed: Record<string, Record<string, number>> = {};
    return histPerMed;
  }, [data]);

  const merged = useMemo(() => {
    // Reconstruct historical per-medicine series from forecast.daily not enough,
    // so use forecast daily for the chosen medicine + history total scaled.
    const fc = data.forecast.daily.filter((r) => r.medicine === medicine);
    return fc.map((r) => ({
      date: r.date,
      forecast: r.qty,
    }));
  }, [data, medicine]);

  const monthlyAgg = useMemo(() => {
    const rows = data.forecast.monthly_by_medicine.filter((r) => r.GenericName === medicine);
    return rows;
  }, [data, medicine]);

  return (
    <div className="card">
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-3 mb-3">
        <div>
          <div className="section-h">Forecast for next {data.forecast.horizon_days} days</div>
          <div className="section-sub">
            Choose a medicine to inspect daily projected demand. Shaded bands mark Eid /
            Ramadan / public-holiday windows the model accounts for.
          </div>
        </div>
        <select
          value={medicine}
          onChange={(e) => setMedicine(e.target.value)}
          className="border border-ink-200 rounded-lg px-3 py-2 text-sm bg-white text-ink-800 max-w-xs"
        >
          {data.medicines.map((m) => (
            <option key={m} value={m}>
              {m}
            </option>
          ))}
        </select>
      </div>

      <div className="flex gap-2 flex-wrap mb-3">
        {monthlyAgg.map((r) => (
          <span key={r.month} className="tag">
            {r.month}: <b className="ml-1">{Math.round(r.qty)}</b> units
          </span>
        ))}
      </div>

      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={merged} margin={{ left: 0, right: 16, top: 8, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#eceef2" vertical={false} />
          <XAxis dataKey="date" tick={{ fontSize: 11, fill: "#7e8493" }} minTickGap={36} />
          <YAxis tick={{ fontSize: 11, fill: "#7e8493" }} width={36} />
          <Tooltip
            contentStyle={{ borderRadius: 12, border: "1px solid #eceef2" }}
            labelStyle={{ color: "#1d2230", fontWeight: 600 }}
          />
          <Legend />
          {BANDS.map((b) => (
            <ReferenceArea
              key={b.label}
              x1={b.start}
              x2={b.end}
              y1={0}
              fill={b.color}
              fillOpacity={0.08}
              stroke={b.color}
              strokeOpacity={0.25}
              label={{ value: b.label, position: "insideTop", fontSize: 10, fill: b.color }}
            />
          ))}
          <Line
            type="monotone"
            dataKey="forecast"
            stroke="#0b8a5e"
            strokeWidth={2}
            dot={false}
            name="Forecast"
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
