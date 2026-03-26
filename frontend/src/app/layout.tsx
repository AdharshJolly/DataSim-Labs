import type { Metadata } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import "./globals.css";
import { Navbar } from "@/components/layout/navbar";
import { Footer } from "@/components/layout/footer";
import { FeedbackProvider } from "@/components/ui/feedback-provider";

const sansFont = Inter({
  subsets: ["latin"],
  variable: "--font-sans",
});

const monoFont = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-mono",
});

export const metadata: Metadata = {
  title: "DataSim Lab | Professional Synthetic Data Generation",
  description:
    "Design, preview, and generate high-quality synthetic datasets for research and development.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className="dark scroll-smooth">
      <body
        className={`${sansFont.variable} ${monoFont.variable} font-sans antialiased`}
      >
        <FeedbackProvider>
          <div className="fixed inset-0 bg-grid-white opacity-25 pointer-events-none -z-10" />
          <Navbar />
          <main className="mx-auto min-h-screen max-w-7xl px-4 pb-20 pt-28 md:px-8">
            {children}
          </main>
          <Footer />
        </FeedbackProvider>
      </body>
    </html>
  );
}
