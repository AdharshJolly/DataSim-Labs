import { ExportSection } from "@/components/home/export-section";
import { FeatureGridSection } from "@/components/home/feature-grid-section";
import { FinalCtaSection } from "@/components/home/final-cta-section";
import { HeroSection } from "@/components/home/hero-section";
import { ProcessSection } from "@/components/home/process-section";
import { StatsSection } from "@/components/home/stats-section";

export default function HomePage() {
  return (
    <div className="space-y-32">
      <HeroSection />
      <StatsSection />
      <ProcessSection />
      <FeatureGridSection />
      <ExportSection />
      <FinalCtaSection />
    </div>
  );
}
