export default function Header({ generatedAt }: { generatedAt: string }) {
  return (
    <header className="bg-white border-b border-ink-100">
      <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-brand-500 flex items-center justify-center text-white font-bold text-lg">
            Rx
          </div>
          <div>
            <h1 className="text-lg font-bold text-ink-900">
              Hospital Medicine Forecasting
            </h1>
            <p className="text-xs text-ink-400">
              4-month demand forecast • macro &amp; cultural signals • SHAP / LIME explained
            </p>
          </div>
        </div>
        <div className="text-xs text-ink-400 text-right">
          <div>Model retrained</div>
          <div className="font-medium text-ink-600">
            {new Date(generatedAt).toLocaleString()}
          </div>
        </div>
      </div>
    </header>
  );
}
