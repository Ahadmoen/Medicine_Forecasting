"use client";
import { Forecasts } from "@/lib/types";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  Cell,
} from "recharts";

export default function ShapChart({ data }: { data: Forecasts }) {
  const items = data.explainability.global_shap.slice(0, 12).map((r) => ({
    feature: r.feature,
    importance: Number(r.importance.toFixed(4)),
    desc: data.explainability.feature_descriptions[r.feature] ?? "",
  }));
  const colors = items.map((r, i) =>
    r.feature.startsWith("is_") || r.feature.startsWith("days_") || r.feature === "inflation_idx"
      ? "#9b8cff"
      : i < 3
      ? "#0e9f6e"
      : "#34d399"
  );

  return (
    <div className="card">
      <div className="section-h mb-1">SHAP — what drives the forecast</div>
      <div className="section-sub mb-4">
        Mean absolute SHAP value across a 500-row sample. Bigger bar = stronger
        influence. Purple bars are macro / cultural features.
      </div>
      <ResponsiveContainer width="100%" height={340}>
        <BarChart data={items} layout="vertical" margin={{ left: 16, right: 24, top: 8, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#eceef2" horizontal={false} />
          <XAxis type="number" tick={{ fontSize: 11, fill: "#7e8493" }} />
          <YAxis
            type="category"
            dataKey="feature"
            tick={{ fontSize: 11, fill: "#1d2230" }}
            width={130}
          />
          <Tooltip
            contentStyle={{ borderRadius: 12, border: "1px solid #eceef2" }}
            formatter={(v: number) => [v.toFixed(4), "SHAP"]}
            labelFormatter={(l) => {
              const it = items.find((x) => x.feature === l);
              return it?.desc ? `${l} — ${it.desc}` : l;
            }}
          />
          <Bar dataKey="importance" radius={[0, 6, 6, 0]}>
            {items.map((_, i) => (
              <Cell key={i} fill={colors[i]} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
