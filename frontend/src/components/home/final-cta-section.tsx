import Link from "next/link";

import { Button } from "@/components/ui/button";

export function FinalCtaSection() {
  return (
    <section className="relative overflow-hidden rounded-3xl border border-primary/30 bg-primary/5 px-4 py-24 text-center">
      <div className="absolute left-1/2 top-0 -z-10 h-full w-full -translate-x-1/2 bg-glow-primary opacity-30" />
      <div className="relative z-10 mx-auto max-w-2xl space-y-8">
        <h2 className="font-display text-4xl font-bold leading-tight tracking-tight md:text-6xl">
          Launch faster with{" "}
          <span className="text-primary">trustworthy synthetic data.</span>
        </h2>
        <p className="text-lg text-muted-foreground">
          Join teams using DataSim Lab to reduce data bottlenecks across
          testing, analytics, and model iteration.
        </p>
        <div className="flex flex-col items-center justify-center gap-4 sm:flex-row">
          <Button asChild className="h-14 w-full px-10 text-lg sm:w-auto">
            <Link href="/register">
              <span>Create a Dataset Now</span>
            </Link>
          </Button>
          <p className="text-sm text-muted-foreground">
            No credit card required. Get started in minutes.
          </p>
        </div>
      </div>
    </section>
  );
}
