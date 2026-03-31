import { Database, ShieldCheck, Sparkles, Zap } from "lucide-react";

const STATS = [
  { label: "Realism Confidence", value: "99.5%", icon: Sparkles },
  { label: "Preview Latency", value: "< 2s", icon: Zap },
  { label: "Field Templates", value: "50+", icon: Database },
  { label: "PII Exposure", value: "0%", icon: ShieldCheck },
] as const;

export function StatsSection() {
  return (
    <section className="grid grid-cols-2 gap-8 border-y border-border/50 py-12 md:grid-cols-4">
      {STATS.map((stat) => (
        <div key={stat.label} className="space-y-2 text-center">
          <div className="flex justify-center">
            <stat.icon className="h-5 w-5 text-primary/60" />
          </div>
          <p className="text-3xl font-bold tracking-tight">{stat.value}</p>
          <p className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">
            {stat.label}
          </p>
        </div>
      ))}
    </section>
  );
}
