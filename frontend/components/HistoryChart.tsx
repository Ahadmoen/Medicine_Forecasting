"use client";
import { Forecasts } from "@/lib/types";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

export default function HistoryChart({ data }: { data: Forecasts }) {
  const series = data.history.daily_total.map((r) => ({
    date: r.date,
    qty: r.qty,
  }));
  return (
    <div className="card">
      <div className="flex items-center justify-between mb-3">
        <div>
          <div className="section-h">Historical daily medicine dispensing</div>
          <div className="section-sub">
            Total units issued per day across all medicines.
          </div>
        </div>
        <span className="tag">{series.length} days</span>
      </div>
      <ResponsiveContainer width="100%" height={260}>
        <AreaChart data={series} margin={{ left: 0, right: 16, top: 8, bottom: 0 }}>
          <defs>
            <linearGradient id="hist" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#0e9f6e" stopOpacity={0.5} />
              <stop offset="95%" stopColor="#0e9f6e" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#eceef2" vertical={false} />
          <XAxis dataKey="date" tick={{ fontSize: 11, fill: "#7e8493" }} minTickGap={28} />
          <YAxis tick={{ fontSize: 11, fill: "#7e8493" }} width={36} />
          <Tooltip
            contentStyle={{ borderRadius: 12, border: "1px solid #eceef2" }}
            labelStyle={{ color: "#1d2230", fontWeight: 600 }}
          />
          <Area
            type="monotone"
            dataKey="qty"
            stroke="#0e9f6e"
            fill="url(#hist)"
            strokeWidth={2}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
