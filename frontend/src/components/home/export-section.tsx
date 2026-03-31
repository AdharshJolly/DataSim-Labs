import Link from "next/link";
import { ArrowRight, Database, Sparkles } from "lucide-react";

import { Badge } from "@/components/ui/badge";

const FORMAT_TAGS = ["CSV", "JSON", "JSONL", "Excel", "API Ready"] as const;
const THROUGHPUT_BARS = [40, 60, 45, 80, 50, 95, 70, 90, 85] as const;

export function ExportSection() {
  return (
    <section className="space-y-10">
      <div className="space-y-3 text-center">
        <h2 className="font-display text-4xl font-bold md:text-5xl">
          Export and Integrate Anywhere
        </h2>
        <p className="mx-auto max-w-2xl text-muted-foreground">
          One generation run can power analytics notebooks, staging databases,
          test pipelines, and benchmarking suites across your stack.
        </p>
      </div>

      <div className="grid items-center gap-8 lg:grid-cols-2">
        <div className="relative w-full rounded-2xl border border-border/70 bg-card/70 p-4 shadow-2xl backdrop-blur-xl">
          <div className="absolute -inset-0.5 -z-10 rounded-2xl bg-gradient-to-tr from-primary/20 via-transparent to-secondary/20 blur-xl" />

          <div className="mb-4 flex items-center justify-between border-b border-border/50 pb-4">
            <div className="flex items-center gap-3">
              <div className="flex h-8 w-8 items-center justify-center rounded bg-primary/20">
                <Database className="h-4 w-4 text-primary" />
              </div>
              <div className="font-mono text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Dataset Generation
              </div>
            </div>
            <div className="flex gap-2">
              <span className="rounded-full bg-blue-500/20 px-2 py-0.5 text-[10px] font-bold text-blue-400">
                JSON
              </span>
              <span className="rounded-full bg-green-500/20 px-2 py-0.5 text-[10px] font-bold text-green-400">
                CSV
              </span>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="relative flex h-40 flex-col justify-end overflow-hidden rounded-xl border border-border/50 bg-background/50 p-4">
              <div className="absolute left-4 top-4 text-xs font-medium text-muted-foreground">
                Throughput (Rows/s)
              </div>
              <div className="mt-6 flex h-full items-end justify-between gap-1 opacity-60">
                {THROUGHPUT_BARS.map((height, index) => (
                  <div
                    key={index}
                    className="w-full rounded-t-sm bg-primary/80 transition-all hover:bg-primary"
                    style={{ height: `${height}%` }}
                  />
                ))}
              </div>
            </div>

            <div className="h-40 overflow-hidden rounded-xl border border-border/50 bg-background/50 p-4 font-mono text-[10px] text-muted-foreground">
              <div className="text-secondary/80">{"{"}</div>
              <div className="ml-2 text-primary">
                "id":{" "}
                <span className="text-muted-foreground">"usr_9f82...",</span>
              </div>
              <div className="ml-2 text-primary">
                "record": <span className="text-secondary/80">{"{"}</span>
              </div>
              <div className="ml-4 text-primary">
                "name":{" "}
                <span className="text-green-400/80">"Alex Morgan",</span>
              </div>
              <div className="ml-4 text-primary">
                "status": <span className="text-orange-400/80">"VERIFIED"</span>
              </div>
              <div className="ml-2 text-secondary/80">{"},"}</div>
              <div className="ml-2 text-primary">
                "created_at":{" "}
                <span className="text-green-400/80">"2026-03-18..."</span>
              </div>
              <div className="text-secondary/80">{"}"}</div>
              <div className="mt-2 h-2 w-16 animate-pulse rounded bg-muted/70" />
            </div>
          </div>
        </div>

        <div className="space-y-6 lg:pl-8">
          <Badge
            variant="outline"
            className="gap-2 border-border/70 bg-card/70 px-3 py-1 text-xs font-medium text-muted-foreground"
          >
            <Sparkles className="h-3.5 w-3.5 text-primary" /> Multi-Format
            Support
          </Badge>
          <h3 className="font-display text-3xl font-bold">
            Built for real engineering workflows
          </h3>
          <p className="leading-relaxed text-muted-foreground">
            Export consistent datasets to JSON, CSV, JSONL, and Excel in a
            single run, then plug them directly into testing, BI analysis, and
            ML experimentation.
          </p>
          <div className="flex flex-wrap gap-3 pt-2">
            {FORMAT_TAGS.map((fmt) => (
              <div
                key={fmt}
                className="cursor-default rounded-md border border-border/50 bg-card/65 px-4 py-2 font-mono text-sm font-semibold transition-colors hover:border-primary/30"
              >
                {fmt}
              </div>
            ))}
          </div>
          <div className="pt-4">
            <Link
              href="/register"
              className="inline-flex items-center gap-2 font-medium text-primary underline-offset-4 hover:underline"
            >
              Start Exporting Datasets <ArrowRight className="h-4 w-4" />
            </Link>
          </div>
        </div>
      </div>
    </section>
  );
}
