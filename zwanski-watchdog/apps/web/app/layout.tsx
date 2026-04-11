import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Zwanski Watchdog",
  description: "Ethical internet-wide leak detection & responsible disclosure",
};

/**
 * Root layout for the Watchdog web app.
 */
export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body className="min-h-screen">{children}</body>
    </html>
  );
}
