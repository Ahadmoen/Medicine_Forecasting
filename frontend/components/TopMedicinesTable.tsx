import { Forecasts } from "@/lib/types";

export default function TopMedicinesTable({ data }: { data: Forecasts }) {
  const totals: Record<string, number> = {};
  for (const r of data.forecast.daily) {
    totals[r.medicine] = (totals[r.medicine] ?? 0) + r.qty;
  }
  const rows = data.history.total_by_medicine.slice(0, 15).map((h) => ({
    name: h.GenericName,
    history: h.qty,
    forecast: Math.round(totals[h.GenericName] ?? 0),
    daily: ((totals[h.GenericName] ?? 0) / data.forecast.horizon_days).toFixed(2),
  }));

  return (
    <div className="card">
      <div className="section-h mb-1">Stock-up plan — top 15 medicines</div>
      <div className="section-sub mb-4">
        Predicted total units across the {data.forecast.horizon_days}-day horizon, with
        average daily issuance.
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-ink-400 border-b border-ink-100">
              <th className="py-2 pr-4 font-medium">Medicine</th>
              <th className="py-2 pr-4 font-medium text-right">Used (history)</th>
              <th className="py-2 pr-4 font-medium text-right">Predicted (next {data.forecast.horizon_days} d)</th>
              <th className="py-2 pr-4 font-medium text-right">Avg / day</th>
              <th className="py-2 pr-4 font-medium text-right">Δ vs history</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => {
              const delta =
                r.history > 0 ? ((r.forecast - r.history) / r.history) * 100 : 0;
              return (
                <tr key={r.name} className="border-b border-ink-100 hover:bg-ink-50">
                  <td className="py-2 pr-4 font-medium text-ink-800">{r.name}</td>
                  <td className="py-2 pr-4 text-right tabular-nums">{r.history}</td>
                  <td className="py-2 pr-4 text-right tabular-nums font-semibold text-brand-700">
                    {r.forecast.toLocaleString()}
                  </td>
                  <td className="py-2 pr-4 text-right tabular-nums">{r.daily}</td>
                  <td className="py-2 pr-4 text-right tabular-nums">
                    <span
                      className={
                        delta >= 0 ? "text-brand-700" : "text-rose-600"
                      }
                    >
                      {delta >= 0 ? "+" : ""}
                      {delta.toFixed(0)}%
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
