import { Forecasts } from "./types";

export async function loadForecasts(): Promise<Forecasts> {
  // Loaded from /public/forecasts.json - shipped at build time so the
  // dashboard renders identically on Vercel without a live backend.
  const fs = await import("fs");
  const path = await import("path");
  const file = path.join(process.cwd(), "public", "forecasts.json");
  const raw = fs.readFileSync(file, "utf-8");
  return JSON.parse(raw) as Forecasts;
}
