import { Forecasts } from "@/lib/types";

export default function Footer({ data }: { data: Forecasts }) {
  return (
    <footer className="max-w-7xl mx-auto px-6 py-8 text-xs text-ink-400 flex flex-col md:flex-row justify-between gap-2">
      <div>
        FYP — Hospital Medicine Demand Forecasting · FAST NUCES · {" "}
        Trained on {data.data_range.rows.toLocaleString()} dispensing rows from {" "}
        {data.data_range.start} to {data.data_range.end}.
      </div>
      <div>
        Model: gradient-boosted regression · Test MAE {data.metrics.mae.toFixed(3)} · {" "}
        Test RMSE {data.metrics.rmse.toFixed(3)}.
      </div>
    </footer>
  );
}
