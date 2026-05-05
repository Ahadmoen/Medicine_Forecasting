"use client";

import { useMemo, useState } from "react";
import { Forecasts } from "@/lib/types";

const DAY_LABELS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

type Bucket = { date: string; qty: number };

function buildGrid(rows: Bucket[]) {
  if (rows.length === 0) return { weeks: [] as string[], grid: {} as Record<string, Record<number, number>> };
  const sorted = [...rows].sort((a, b) => a.date.localeCompare(b.date));
  const startDate = new Date(sorted[0].date);
  const endDate   = new Date(sorted[sorted.length - 1].date);

  // Slide back to Monday so each column is a full ISO week.
  const startWeekDay = (startDate.getUTCDay() + 6) % 7; // 0 == Mon
  const startMonday = new Date(startDate);
  startMonday.setUTCDate(startMonday.getUTCDate() - startWeekDay);

  const lookup: Record<string, number> = {};
  for (const r of sorted) lookup[r.date] = r.qty;

  const grid: Record<string, Record<number, number | null>> = {};
  const weeks: string[] = [];
  const cursor = new Date(startMonday);
  while (cursor <= endDate) {
    const weekKey = cursor.toISOString().slice(0, 10);
    weeks.push(weekKey);
    grid[weekKey] = {};
    for (let dow = 0; dow < 7; dow++) {
      const d = new Date(cursor);
      d.setUTCDate(d.getUTCDate() + dow);
      const k = d.toISOString().slice(0, 10);
      const v = lookup[k];
      grid[weekKey][dow] = v === undefined ? null : v;
    }
    cursor.setUTCDate(cursor.getUTCDate() + 7);
  }
  return { weeks, grid };
}

function intensityColor(v: number, max: number): string {
  if (max <= 0) return "#f1f5f4";
  const t = Math.min(1, v / max);
  // green ramp
  const stops = [
    [241, 245, 244],   // 0
    [185, 234, 211],   // 0.25
    [117, 213, 173],   // 0.5
    [38,  173, 119],   // 0.75
    [11,  124, 78],    // 1
  ];
  const seg = Math.min(stops.length - 2, Math.floor(t * (stops.length - 1)));
  const lo = stops[seg];
  const hi = stops[seg + 1];
  const localT = t * (stops.length - 1) - seg;
  const ch = (i: number) => Math.round(lo[i] + (hi[i] - lo[i]) * localT);
  return `rgb(${ch(0)}, ${ch(1)}, ${ch(2)})`;
}

export default function CalendarHeatmap({ data }: { data: Forecasts }) {
  const dailyByMed = data.history.daily_by_medicine ?? [];
  const medicines = useMemo(() => {
    const set = new Set<string>();
    set.add("__ALL__");
    if (dailyByMed.length > 0) {
      for (const r of dailyByMed) set.add(r.medicine);
    } else {
      for (const m of data.medicines) set.add(m);
    }
    return Array.from(set);
  }, [dailyByMed, data]);
  const [medicine, setMedicine] = useState<string>("__ALL__");

  const rows: Bucket[] = useMemo(() => {
    if (medicine === "__ALL__") {
      return data.history.daily_total ?? [];
    }
    return dailyByMed
      .filter((r) => r.medicine === medicine)
      .map((r) => ({ date: r.date, qty: r.qty }));
  }, [data, dailyByMed, medicine]);

  const { weeks, grid } = useMemo(() => buildGrid(rows), [rows]);

  const max = useMemo(
    () => Math.max(1, ...Object.values(grid).flatMap((w) => Object.values(w).filter((x): x is number => x !== null))),
    [grid],
  );

  // Month labels above the grid — show one tick per change.
  const monthLabels = useMemo(() => {
    const result: { weekIdx: number; label: string }[] = [];
    let lastMonth = "";
    weeks.forEach((wk, i) => {
      const m = wk.slice(0, 7);
      if (m !== lastMonth) {
        result.push({ weekIdx: i, label: new Date(wk).toLocaleString("en", { month: "short" }) });
        lastMonth = m;
      }
    });
    return result;
  }, [weeks]);

  return (
    <div className="card">
      <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-3 mb-3">
        <div>
          <div className="section-h">Daily demand heatmap</div>
          <div className="section-sub mt-1">
            One square per day, coloured by units dispensed — quickly spot
            seasonal surges, weekend dips and the dengue-peak ramp through
            October.
          </div>
        </div>
        <select
          value={medicine}
          onChange={(e) => setMedicine(e.target.value)}
          className="border border-ink-200 rounded-md px-3 py-1.5 text-sm bg-white"
        >
          <option value="__ALL__">All medicines (total)</option>
          {medicines.filter((m) => m !== "__ALL__").map((m) => (
            <option key={m} value={m}>
              {m}
            </option>
          ))}
        </select>
      </div>

      <div className="overflow-x-auto">
        <div style={{ minWidth: weeks.length * 14 + 60 }}>
          {/* Month axis */}
          <div className="flex pl-10 text-[10px] text-ink-400" style={{ height: 14 }}>
            {weeks.map((_, i) => {
              const tick = monthLabels.find((t) => t.weekIdx === i);
              return (
                <div key={i} style={{ width: 14 }} className="shrink-0">
                  {tick?.label ?? ""}
                </div>
              );
            })}
          </div>

          {/* Day rows */}
          {DAY_LABELS.map((dayName, dow) => (
            <div key={dayName} className="flex items-center" style={{ height: 14 }}>
              <div className="w-10 shrink-0 text-[10px] text-ink-400 pr-1 text-right">
                {dow % 2 === 0 ? dayName : ""}
              </div>
              {weeks.map((wk) => {
                const v = grid[wk]?.[dow];
                const bg = v === null || v === undefined ? "#f1f5f4" : intensityColor(v, max);
                const date = (() => {
                  const d = new Date(wk);
                  d.setUTCDate(d.getUTCDate() + dow);
                  return d.toISOString().slice(0, 10);
                })();
                return (
                  <div
                    key={wk + "-" + dow}
                    title={
                      v === null || v === undefined
                        ? `${date}: no data`
                        : `${date}: ${Math.round(v)} units`
                    }
                    style={{
                      width: 12,
                      height: 12,
                      background: bg,
                      borderRadius: 2,
                      margin: "1px",
                    }}
                  />
                );
              })}
            </div>
          ))}

          {/* Legend */}
          <div className="flex items-center gap-1 mt-3 pl-10 text-[10px] text-ink-500">
            <span>Less</span>
            {[0, 0.25, 0.5, 0.75, 1].map((t) => (
              <div
                key={t}
                style={{
                  width: 12,
                  height: 12,
                  background: intensityColor(t * max, max),
                  borderRadius: 2,
                }}
              />
            ))}
            <span>More</span>
            <span className="ml-3">(max {Math.round(max)} units / day)</span>
          </div>
        </div>
      </div>
    </div>
  );
}
