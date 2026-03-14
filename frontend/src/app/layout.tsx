import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "DataSim Lab",
  description: "Synthetic dataset generation platform",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>
        <main className="mx-auto min-h-screen max-w-7xl p-6 md:p-10">
          {children}
        </main>
      </body>
    </html>
  );
}
