import type { Metadata } from "next";
import { Inter, JetBrains_Mono, Sora } from "next/font/google";
import "./globals.css";
import { Navbar } from "@/components/layout/navbar";
import { Footer } from "@/components/layout/footer";
import { FeedbackProvider } from "@/components/ui/feedback-provider";
import { ThemeProvider } from "@/components/ui/theme-provider";
import { AnimatedBackground } from "@/components/layout/animated-background";
import { ScrollReveal } from "@/components/layout/scroll-reveal";

const sansFont = Inter({
  subsets: ["latin"],
  variable: "--font-sans",
});

const monoFont = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-mono",
});

const displayFont = Sora({
  subsets: ["latin"],
  variable: "--font-display",
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
    <html lang="en" className="scroll-smooth">
      <body
        className={`${sansFont.variable} ${monoFont.variable} ${displayFont.variable} font-sans antialiased`}
      >
        <ThemeProvider>
          <FeedbackProvider>
            <AnimatedBackground />
            <ScrollReveal />
            <Navbar />
            <main className="mx-auto min-h-screen max-w-7xl px-4 pb-20 pt-28 md:px-8">
              {children}
            </main>
            <Footer />
          </FeedbackProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
