const events = [
  {
    label: "Independence Day",
    date: "2025-08-14",
    note: "Single-day public holiday — OPD volume drops, emergency only.",
    impact: "lower elective demand",
    type: "holiday",
  },
  {
    label: "Eid Milad-un-Nabi",
    date: "2025-09-04 — 2025-09-05",
    note: "Public processions. Trauma / first-aid demand may rise.",
    impact: "moderate spike for analgesics",
    type: "religious",
  },
  {
    label: "Iqbal Day",
    date: "2025-11-09",
    note: "Public holiday.",
    impact: "lower routine OPD",
    type: "holiday",
  },
  {
    label: "Quaid-e-Azam Day",
    date: "2025-12-25",
    note: "Public holiday.",
    impact: "lower routine OPD",
    type: "holiday",
  },
  {
    label: "Ramadan 2026",
    date: "2026-02-18 — 2026-03-19",
    note: "Fasting month — GI / dehydration / hypoglycaemia cases surge in evenings.",
    impact: "↑ ESOMEPRAZOLE, ondansetron, IV fluids",
    type: "religious",
  },
  {
    label: "Eid-ul-Fitr 2026",
    date: "2026-03-20 — 2026-03-22",
    note: "End of Ramadan. Pre-Eid stocking peaks 5–7 days earlier.",
    impact: "stock pre-emptively",
    type: "religious",
  },
  {
    label: "CPI inflation proxy",
    date: "Monthly",
    note: "Pakistan YoY inflation feeds the model — affects affordability and brand-switching.",
    impact: "captured via inflation_idx feature",
    type: "macro",
  },
  {
    label: "Dengue season (Lahore)",
    date: "Aug — Nov · peak ~Oct 15",
    note: "Mosquito-borne outbreak window after monsoon. Expect spikes in IV fluids, paracetamol, ondansetron, platelet support.",
    impact: "captured via dengue_intensity feature",
    type: "macro",
  },
  {
    label: "Lahore monsoon",
    date: "Jul — Aug (~365 mm)",
    note: "Heavy rainfall + standing water — drives waterborne GI and respiratory cases.",
    impact: "feeds lahore_rain_mm + leads dengue intensity by ~6 weeks",
    type: "macro",
  },
  {
    label: "Lahore smog season",
    date: "Nov — Feb · peak Nov-Dec",
    note: "PM2.5 frequently >300. Surge in inhalers, salbutamol, prednisolone, steroidal sprays.",
    impact: "captured via lahore_aqi feature",
    type: "macro",
  },
];

export default function MacroPanel() {
  return (
    <div className="card">
      <div className="section-h mb-1">Macro &amp; cultural calendar</div>
      <div className="section-sub mb-4">
        These events are encoded as features so the model can adjust forecasts
        around them.
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {events.map((e) => (
          <div
            key={e.label}
            className="border border-ink-100 rounded-xl p-3 hover:border-brand-500 transition"
          >
            <div className="flex items-center justify-between mb-1">
              <span className="font-semibold text-ink-800">{e.label}</span>
              <span
                className={
                  e.type === "religious"
                    ? "tag"
                    : e.type === "holiday"
                    ? "tag-warn"
                    : "tag"
                }
              >
                {e.type}
              </span>
            </div>
            <div className="text-xs text-ink-400 mb-1">{e.date}</div>
            <div className="text-sm text-ink-600">{e.note}</div>
            <div className="text-xs text-brand-700 font-medium mt-1">→ {e.impact}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
