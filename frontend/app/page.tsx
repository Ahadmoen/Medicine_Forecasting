import Header from "@/components/Header";
import KpiCards from "@/components/KpiCards";
import HistoryChart from "@/components/HistoryChart";
import ForecastChart from "@/components/ForecastChart";
import LahoreTrendsChart from "@/components/LahoreTrendsChart";
import TopMedicinesTable from "@/components/TopMedicinesTable";
import ShapChart from "@/components/ShapChart";
import LimePanel from "@/components/LimePanel";
import MacroPanel from "@/components/MacroPanel";
import MonthlyHeatmap from "@/components/MonthlyHeatmap";
import Footer from "@/components/Footer";
import { loadForecasts } from "@/lib/data";

export const dynamic = "force-static";

export default async function Home() {
  const data = await loadForecasts();
  return (
    <div className="min-h-screen">
      <Header generatedAt={data.generated_at} />
      <main className="max-w-7xl mx-auto px-6 py-8 space-y-6">
        <KpiCards data={data} />
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <HistoryChart data={data} />
          <ForecastChart data={data} />
        </div>
        <LahoreTrendsChart data={data} />
        <TopMedicinesTable data={data} />
        <MonthlyHeatmap data={data} />
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <ShapChart data={data} />
          <LimePanel data={data} />
        </div>
        <MacroPanel />
      </main>
      <Footer data={data} />
    </div>
  );
}
