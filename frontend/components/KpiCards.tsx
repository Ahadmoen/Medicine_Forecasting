import { Forecasts } from "@/lib/types";

export default function KpiCards({ data }: { data: Forecasts }) {
  const totalForecast = data.forecast.daily.reduce((s, r) => s + r.qty, 0);
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
      <div className="card">
        <div className="card-title">Training window</div>
        <div className="kpi">{data.data_range.days} days</div>
        <div className="kpi-sub">
          {data.data_range.start} → {data.data_range.end}
        </div>
      </div>
      <div className="card">
        <div className="card-title">Medicines tracked</div>
        <div className="kpi">{data.medicines.length}</div>
        <div className="kpi-sub">{data.data_range.rows.toLocaleString()} historical units</div>
      </div>
      <div className="card">
        <div className="card-title">Forecast horizon</div>
        <div className="kpi">{data.forecast.horizon_days} d</div>
        <div className="kpi-sub">~{Math.round(data.forecast.horizon_days / 30)} months ahead</div>
      </div>
      <div className="card">
        <div className="card-title">Predicted units</div>
        <div className="kpi">{Math.round(totalForecast).toLocaleString()}</div>
        <div className="kpi-sub">
          MAE {data.metrics.mae.toFixed(2)} • RMSE {data.metrics.rmse.toFixed(2)}
        </div>
      </div>
    </div>
  );
}
