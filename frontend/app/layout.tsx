import "./globals.css";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Hospital Medicine Forecasting",
  description:
    "Forecast medicine demand for the next 3-4 months using historical hospital data plus Ramadan, Eid, public-holiday and inflation signals. Built for FAST FYP.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen">{children}</body>
    </html>
  );
}
