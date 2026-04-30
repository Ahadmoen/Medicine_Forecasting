export type DataRange = {
  start: string;
  end: string;
  days: number;
  rows: number;
};

export type Metrics = {
  mae: number;
  rmse: number;
  n_train: number;
  n_test: number;
};

export type ForecastDailyRow = {
  date: string;
  medicine: string;
  qty: number;
};

export type ForecastAggRow = {
  GenericName: string;
  qty: number;
  month?: string;
  week?: string;
};

export type ShapImportance = { feature: string; importance: number };
export type LimeContribution = { feature: string; contribution: number };

export type TrendRow = {
  date: string;
  is_ramadan: number;
  is_eid_fitr: number;
  is_eid_adha: number;
  is_muharram: number;
  is_public_holiday: number;
  lahore_temp_c: number;
  lahore_rain_mm: number;
  lahore_aqi: number;
  dengue_intensity: number;
  is_dengue_season: number;
};

export type WeatherClimatology = {
  month: number;
  temp_c: number;
  rain_mm: number;
  aqi: number;
};

export type Forecasts = {
  generated_at: string;
  data_range: DataRange;
  metrics: Metrics;
  medicines: string[];
  top_medicines: string[];
  history: {
    daily_total: { date: string; qty: number }[];
    total_by_medicine: { GenericName: string; qty: number }[];
    dengue_proxy_daily?: { date: string; cases: number }[];
  };
  forecast: {
    horizon_days: number;
    daily: ForecastDailyRow[];
    monthly_by_medicine: ForecastAggRow[];
    weekly_by_medicine: ForecastAggRow[];
  };
  trends?: {
    city: string;
    timeline: TrendRow[];
    ramadan_windows: [string, string][];
    eid_fitr_windows: [string, string][];
    eid_adha_windows: [string, string][];
    muharram_windows: [string, string][];
    weather_climatology: WeatherClimatology[];
  };
  explainability: {
    global_shap: ShapImportance[];
    local_lime: Record<string, LimeContribution[]>;
    feature_descriptions: Record<string, string>;
  };
};
