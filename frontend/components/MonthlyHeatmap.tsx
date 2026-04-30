import { Forecasts } from "@/lib/types";

export default function MonthlyHeatmap({ data }: { data: Forecasts }) {
  const meds = data.top_medicines.slice(0, 12);
  const months = Array.from(
    new Set(data.forecast.monthly_by_medicine.map((r) => r.month!))
  ).sort();

  const lookup: Record<string, Record<string, number>> = {};
  for (const r of data.forecast.monthly_by_medicine) {
    lookup[r.GenericName] ??= {};
    lookup[r.GenericName][r.month!] = r.qty;
  }

  const allValues = meds.flatMap((m) => months.map((mo) => lookup[m]?.[mo] ?? 0));
  const max = Math.max(1, ...allValues);

  return (
    <div className="card">
      <div className="section-h mb-1">Monthly demand heatmap</div>
      <div className="section-sub mb-4">
        Predicted units per medicine, per calendar month — quick glance at where
        consumption peaks.
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr>
              <th className="text-left py-2 pr-3 font-medium text-ink-400">Medicine</th>
              {months.map((m) => (
                <th key={m} className="py-2 px-2 font-medium text-ink-400 text-center">
                  {m}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {meds.map((med) => (
              <tr key={med}>
                <td className="py-2 pr-3 font-medium text-ink-800 whitespace-nowrap">
                  {med}
                </td>
                {months.map((mo) => {
                  const v = lookup[med]?.[mo] ?? 0;
                  const intensity = v / max;
                  const bg = `rgba(14,159,110,${0.05 + intensity * 0.85})`;
                  return (
                    <td key={mo} className="py-1 px-1 text-center">
                      <div
                        style={{ background: bg }}
                        className="rounded-md py-2 text-xs font-medium text-ink-800 tabular-nums"
                      >
                        {Math.round(v)}
                      </div>
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
