import type { Metadata } from "next";
import { Merriweather, Source_Sans_3 } from "next/font/google";
import "./globals.css";

const titleFont = Merriweather({
  subsets: ["latin"],
  weight: ["400", "700", "900"],
  variable: "--font-title",
});

const bodyFont = Source_Sans_3({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  variable: "--font-body",
});

export const metadata: Metadata = {
  title: "DataSim Lab",
  description: "Synthetic dataset generation platform",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body
        className={`${titleFont.variable} ${bodyFont.variable} font-[var(--font-body)]`}
      >
        <main className="mx-auto min-h-screen max-w-7xl p-4 md:p-8">
          <div className="sk-shell">{children}</div>
        </main>
      </body>
    </html>
  );
}
