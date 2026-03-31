import Link from "next/link";
import { ArrowRight, Layout, Sparkles } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

export function HeroSection() {
  return (
    <section className="relative flex flex-col items-center justify-center pt-8 text-center">
      <div className="absolute -top-24 left-1/2 -z-10 h-[500px] w-[500px] -translate-x-1/2 animate-pulse bg-glow-primary opacity-50 blur-3xl" />

      <Badge
        variant="outline"
        className="animate-fade-in gap-2 border-primary/20 bg-primary/5 px-4 py-1.5 text-xs tracking-wide text-primary backdrop-blur-sm"
      >
        <Sparkles className="h-3.5 w-3.5" />
        <span>REALISM ENGINE LIVE</span>
      </Badge>

      <h1 className="mt-8 font-display text-5xl font-extrabold tracking-tight md:text-7xl lg:text-8xl">
        Generate Data
        <br />
        <span className="bg-gradient-to-r from-primary via-secondary to-accent bg-clip-text text-transparent drop-shadow-sm">
          That Behaves Like Production.
        </span>
      </h1>

      <p className="mx-auto mt-8 max-w-2xl text-lg leading-relaxed text-muted-foreground md:text-xl">
        Build realistic synthetic datasets with rule-aware generation, instant
        previews, and export-ready outputs for analytics, experimentation, and
        model development.
      </p>

      <div className="mt-10 flex flex-wrap items-center justify-center gap-4">
        <Button
          asChild
          className="h-12 px-8 text-base shadow-lg shadow-primary/20"
        >
          <Link href="/register">
            <span>Launch Dataset Builder</span>
            <ArrowRight className="ml-2 h-5 w-5" />
          </Link>
        </Button>
        <Button
          asChild
          variant="secondary"
          className="group h-12 px-8 transition-all hover:bg-muted/70"
        >
          <Link href="/studio">
            <span>Open Interactive Studio</span>
            <ArrowRight className="ml-2 h-4 w-4 transition-transform group-hover:translate-x-1" />
          </Link>
        </Button>
      </div>

      <div className="mt-20 w-full max-w-5xl overflow-hidden rounded-2xl border border-border/70 bg-card/70 p-2 shadow-2xl backdrop-blur-sm">
        <div className="rounded-xl border border-border/50 bg-background/50 p-1">
          <div className="flex items-center gap-2 border-b border-border/50 px-4 py-3">
            <div className="flex gap-1.5">
              <div className="h-3 w-3 rounded-full bg-red-500/50" />
              <div className="h-3 w-3 rounded-full bg-yellow-500/50" />
              <div className="h-3 w-3 rounded-full bg-green-500/50" />
            </div>
            <div className="ml-4 flex h-5 items-center rounded-md bg-card/70 px-3">
              <span className="whitespace-nowrap font-mono text-[10px] text-muted-foreground">
                datasim-lab.com/studio/research-dataset-v1
              </span>
            </div>
          </div>
          <div className="relative aspect-[16/9] overflow-hidden bg-grid-white bg-[size:20px_20px] p-6 md:aspect-[21/9]">
            <div className="pointer-events-none grid select-none grid-cols-4 gap-4 opacity-50">
              {[...Array(12)].map((_, i) => (
                <div
                  key={i}
                  className="h-24 animate-pulse rounded-lg border border-border/70 bg-card/70"
                  style={{ animationDelay: `${i * 100}ms` }}
                />
              ))}
            </div>
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="max-w-sm rounded-xl border border-primary/30 bg-background/80 p-6 shadow-2xl backdrop-blur-xl">
                <div className="flex items-center gap-4">
                  <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-primary/20 text-primary">
                    <Layout className="h-6 w-6" />
                  </div>
                  <div>
                    <h4 className="font-bold">Real-time Preview</h4>
                    <p className="text-xs text-muted-foreground">
                      Change constraints and validate output instantly.
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
