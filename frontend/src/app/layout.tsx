import type { Metadata } from "next";
import { Orbitron, Exo_2 } from "next/font/google";
import "./globals.css";

const titleFont = Orbitron({
  subsets: ["latin"],
  weight: ["400", "700", "900"],
  variable: "--font-title",
});

const bodyFont = Exo_2({
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
    <html lang="en" className="dark">
      <body
        className={`${titleFont.variable} ${bodyFont.variable} font-sans`}
      >
        <main className="mx-auto min-h-screen max-w-7xl p-4 md:p-8">
          {children}
        </main>
      </body>
    </html>
  );
}
