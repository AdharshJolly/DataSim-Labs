import Link from "next/link";
import {
  ArrowRight,
  Code,
  Calendar,
  CheckSquare,
  Hash,
  Mail,
  Milestone,
  Palette,
  Type,
  Users,
  Database,
  Eye,
  FileText,
  Download,
  Sparkles,
  Zap,
  ShieldCheck,
  Layout,
} from "lucide-react";

export default function HomePage() {
  return (
    <div className="space-y-32">
      {/* Hero Section */}
      <section className="relative flex flex-col items-center justify-center pt-8 text-center">
        {/* Animated Glow Blobs */}
        <div className="absolute -top-24 left-1/2 -z-10 h-[500px] w-[500px] -translate-x-1/2 bg-glow-primary opacity-50 blur-3xl animate-pulse" />

        <div className="inline-flex animate-fade-in items-center gap-2 rounded-full border border-primary/20 bg-primary/5 px-4 py-1.5 text-xs font-semibold tracking-wide text-primary backdrop-blur-sm">
          <Sparkles className="h-3.5 w-3.5" />
          <span>REALISM ENGINE LIVE</span>
        </div>

        <h1 className="mt-8 font-display text-5xl font-extrabold tracking-tight md:text-7xl lg:text-8xl">
          Generate Data
          <br />
          <span className="bg-gradient-to-r from-primary via-secondary to-accent bg-clip-text text-transparent drop-shadow-sm">
            That Behaves Like Production.
          </span>
        </h1>

        <p className="mt-8 mx-auto max-w-2xl text-lg md:text-xl text-muted-foreground leading-relaxed">
          Build realistic synthetic datasets with rule-aware generation, instant
          previews, and export-ready outputs for analytics, experimentation, and
          model development.
        </p>

        <div className="mt-10 flex flex-wrap items-center justify-center gap-4">
          <Link
            href="/register"
            className="btn-primary h-12 px-8 text-base shadow-lg shadow-primary/20"
          >
            <span>Launch Dataset Builder</span>
            <ArrowRight className="ml-2 h-5 w-5" />
          </Link>
          <Link
            href="/studio"
            className="group inline-flex h-12 items-center justify-center rounded-lg border border-border bg-white/5 px-8 font-medium transition-all hover:bg-white/10"
          >
            <span>Open Interactive Studio</span>
            <ArrowRight className="ml-2 h-4 w-4 transition-transform group-hover:translate-x-1" />
          </Link>
        </div>

        {/* Hero Visual */}
        <div className="mt-20 w-full max-w-5xl overflow-hidden rounded-2xl border border-white/10 bg-black/40 p-2 backdrop-blur-sm shadow-2xl">
          <div className="rounded-xl border border-white/5 bg-background/50 p-1">
            <div className="flex items-center gap-2 px-4 py-3 border-b border-white/5">
              <div className="flex gap-1.5">
                <div className="h-3 w-3 rounded-full bg-red-500/50"></div>
                <div className="h-3 w-3 rounded-full bg-yellow-500/50"></div>
                <div className="h-3 w-3 rounded-full bg-green-500/50"></div>
              </div>
              <div className="ml-4 h-5  rounded-md bg-white/5 flex items-center px-3">
                <span className="text-[10px] text-muted-foreground font-mono whitespace-nowrap">
                  datasim-lab.com/studio/research-dataset-v1
                </span>
              </div>
            </div>
            <div className="aspect-[16/9] md:aspect-[21/9] bg-grid-white bg-[size:20px_20px] p-6 overflow-hidden relative">
              <div className="grid grid-cols-4 gap-4 opacity-50 select-none pointer-events-none">
                {[...Array(12)].map((_, i) => (
                  <div
                    key={i}
                    className="h-24 rounded-lg border border-white/10 bg-white/5 animate-pulse"
                    style={{ animationDelay: `${i * 100}ms` }}
                  />
                ))}
              </div>
              <div className="absolute inset-0 flex items-center justify-center">
                <div className="rounded-xl border border-primary/30 bg-background/80 p-6 shadow-2xl backdrop-blur-xl max-w-sm">
                  <div className="flex items-center gap-4">
                    <div className="h-12 w-12 rounded-lg bg-primary/20 flex items-center justify-center text-primary">
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

      {/* Stats/Social Proof */}
      <section className="grid grid-cols-2 gap-8 md:grid-cols-4 border-y border-white/5 py-12">
        {[
          { label: "Realism Confidence", value: "99.5%", icon: Sparkles },
          { label: "Preview Latency", value: "< 2s", icon: Zap },
          { label: "Field Templates", value: "50+", icon: Database },
          { label: "PII Exposure", value: "0%", icon: ShieldCheck },
        ].map((stat) => (
          <div key={stat.label} className="text-center space-y-2">
            <div className="flex justify-center">
              <stat.icon className="h-5 w-5 text-primary/60" />
            </div>
            <p className="text-3xl font-bold tracking-tight">{stat.value}</p>
            <p className="text-xs uppercase tracking-widest text-muted-foreground font-semibold">
              {stat.label}
            </p>
          </div>
        ))}
      </section>

      {/* Process Section */}
      <section className="space-y-16">
        <div className="text-center space-y-4">
          <h2 className="font-display text-4xl font-bold md:text-5xl">
            From Idea to Dataset in Minutes
          </h2>
          <p className="mx-auto max-w-2xl text-muted-foreground">
            Follow a focused workflow to define schema logic, validate behavior,
            and generate large-scale outputs confidently.
          </p>
        </div>

        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
          {[
            {
              icon: Database,
              step: "01",
              title: "Define",
              desc: "Start with use case, scale, and domain constraints to shape the dataset foundation.",
              color: "text-blue-400",
            },
            {
              icon: Code,
              step: "02",
              title: "Model",
              desc: "Configure attribute types, distributions, and dependency-aware realism rules.",
              color: "text-primary",
            },
            {
              icon: Eye,
              step: "03",
              title: "Validate",
              desc: "Inspect live preview rows and refine logic until outputs look production-credible.",
              color: "text-secondary",
            },
            {
              icon: Download,
              step: "04",
              title: "Generate",
              desc: "Run high-volume generation with consistent multi-format exports and quality signals.",
              color: "text-accent",
            },
          ].map(({ icon: Icon, step, title, desc, color }) => (
            <article
              key={step}
              className="group relative rounded-2xl border border-white/5 bg-white/[0.02] p-8 transition-all hover:border-white/10 hover:bg-white/[0.04]"
            >
              <div className="flex items-center justify-between mb-8">
                <div
                  className={`rounded-xl bg-white/5 p-3 group-hover:scale-110 transition-transform ${color}`}
                >
                  <Icon className="h-6 w-6" />
                </div>
                <span className="font-display text-4xl font-black opacity-10 group-hover:opacity-20 transition-opacity">
                  {step}
                </span>
              </div>
              <h3 className="font-display text-xl font-bold mb-2 group-hover:text-primary transition-colors">
                {title}
              </h3>
              <p className="text-sm text-muted-foreground leading-relaxed">
                {desc}
              </p>
            </article>
          ))}
        </div>
      </section>

      {/* Feature Grid */}
      <section className="space-y-16">
        <div className="flex flex-col md:flex-row md:items-end justify-between gap-6">
          <div className="space-y-4">
            <h2 className="font-display text-4xl font-bold">
              Rich Schema Components
            </h2>
            <p className="max-w-xl text-muted-foreground">
              Combine structured primitives, synthetic identity data, and
              behavioral attributes to mirror real production data surfaces.
            </p>
          </div>
          <Link
            href="/register"
            className="text-primary font-medium flex items-center gap-2 hover:underline underline-offset-4"
          >
            Explore supported schema types <ArrowRight className="h-4 w-4" />
          </Link>
        </div>

        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5">
          {[
            { icon: Hash, label: "Numeric Ranges" },
            { icon: Users, label: "Identity Profiles" },
            { icon: Mail, label: "Company Emails" },
            { icon: Milestone, label: "Geographic Fields" },
            { icon: Type, label: "Free Text" },
            { icon: Calendar, label: "Date Logic" },
            { icon: CheckSquare, label: "Rule Conditions" },
            { icon: Palette, label: "Weighted Categories" },
            { icon: FileText, label: "Nested Records" },
            { icon: Code, label: "API-ready JSON" },
          ].map(({ icon: Icon, label }) => (
            <div
              key={label}
              className="flex items-center gap-3 rounded-xl border border-white/5 bg-white/[0.02] p-4 transition-all hover:border-primary/30 hover:bg-primary/5 group"
            >
              <Icon className="h-5 w-5 flex-shrink-0 text-muted-foreground group-hover:text-primary transition-colors" />
              <span className="text-sm font-medium">{label}</span>
            </div>
          ))}
        </div>
      </section>

      <section className="space-y-10">
        <div className="text-center space-y-3">
          <h2 className="font-display text-4xl font-bold md:text-5xl">
            Export and Integrate Anywhere
          </h2>
          <p className="mx-auto max-w-2xl text-muted-foreground">
            One generation run can power analytics notebooks, staging databases,
            test pipelines, and benchmarking suites across your stack.
          </p>
        </div>

        <div className="grid gap-8 lg:grid-cols-2 items-center">
          {/* Glassmorphic Chart/Data Preview Mockup */}
          <div className="relative w-full rounded-2xl border border-white/10 bg-black/40 p-4 shadow-2xl backdrop-blur-xl">
            <div className="absolute -inset-0.5 rounded-2xl bg-gradient-to-tr from-primary/20 via-transparent to-secondary/20 blur-xl -z-10" />

            {/* Header */}
            <div className="flex items-center justify-between border-b border-white/5 pb-4 mb-4">
              <div className="flex items-center gap-3">
                <div className="h-8 w-8 rounded bg-primary/20 flex items-center justify-center">
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

            {/* Split View */}
            <div className="grid grid-cols-2 gap-4">
              {/* Fake Chart */}
              <div className="rounded-xl border border-white/5 bg-background/50 p-4 flex flex-col justify-end h-40 relative overflow-hidden">
                <div className="absolute top-4 left-4 text-xs font-medium text-muted-foreground">
                  Throughput (Rows/s)
                </div>
                <div className="flex items-end justify-between gap-1 mt-6 h-full opacity-60">
                  {[40, 60, 45, 80, 50, 95, 70, 90, 85].map((h, i) => (
                    <div
                      key={i}
                      className="w-full bg-primary/80 rounded-t-sm transition-all hover:bg-primary"
                      style={{ height: `${h}%` }}
                    />
                  ))}
                </div>
              </div>

              {/* Fake Code */}
              <div className="rounded-xl border border-white/5 bg-background/50 p-4 h-40 font-mono text-[10px] text-muted-foreground overflow-hidden">
                <div className="text-secondary/80">{"{"}</div>
                <div className="ml-2 text-primary">
                  "id":{" "}
                  <span className="text-muted-foreground">"usr_9f82...",</span>
                </div>
                <div className="ml-2 text-primary">
                  "profile": <span className="text-secondary/80">{"{"}</span>
                </div>
                <div className="ml-4 text-primary">
                  "name":{" "}
                  <span className="text-green-400/80">"Alex Morgan",</span>
                </div>
                <div className="ml-4 text-primary">
                  "status":{" "}
                  <span className="text-orange-400/80">"VERIFIED"</span>
                </div>
                <div className="ml-2 text-secondary/80">{"},"}</div>
                <div className="ml-2 text-primary">
                  "created_at":{" "}
                  <span className="text-green-400/80">"2026-03-18..."</span>
                </div>
                <div className="text-secondary/80">{"}"}</div>
                <div className="animate-pulse mt-2 h-2 w-16 bg-white/10 rounded" />
              </div>
            </div>
          </div>

          {/* Description */}
          <div className="space-y-6 lg:pl-8">
            <div className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs font-medium text-muted-foreground">
              <Sparkles className="h-3.5 w-3.5 text-primary" /> Multi-Format
              Support
            </div>
            <h3 className="font-display text-3xl font-bold">
              Built for real engineering workflows
            </h3>
            <p className="text-muted-foreground leading-relaxed">
              Export consistent datasets to JSON, CSV, JSONL, and Excel in a
              single run, then plug them directly into testing, BI analysis, and
              ML experimentation.
            </p>
            <div className="flex flex-wrap gap-3 pt-2">
              {["CSV", "JSON", "JSONL", "Excel", "API Ready"].map((fmt) => (
                <div
                  key={fmt}
                  className="rounded-md border border-white/5 bg-white/[0.02] px-4 py-2 font-mono text-sm font-semibold hover:border-primary/30 transition-colors cursor-default"
                >
                  {fmt}
                </div>
              ))}
            </div>
            <div className="pt-4">
              <Link
                href="/register"
                className="text-primary font-medium hover:underline underline-offset-4 inline-flex items-center gap-2"
              >
                Start Exporting Datasets <ArrowRight className="h-4 w-4" />
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* Final CTA */}
      <section className="relative overflow-hidden rounded-3xl border border-primary/30 bg-primary/5 py-24 text-center px-4">
        <div className="absolute top-0 left-1/2 -z-10 h-full w-full -translate-x-1/2 bg-glow-primary opacity-30" />
        <div className="relative z-10 space-y-8 max-w-2xl mx-auto">
          <h2 className="font-display text-4xl font-bold md:text-6xl tracking-tight leading-tight">
            Launch faster with{" "}
            <span className="text-primary">trustworthy synthetic data.</span>
          </h2>
          <p className="text-lg text-muted-foreground">
            Join teams using DataSim Lab to reduce data bottlenecks across
            testing, analytics, and model iteration.
          </p>
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <Link
              href="/register"
              className="btn-primary h-14 px-10 text-lg w-full sm:w-auto"
            >
              <span>Create a Dataset Now</span>
            </Link>
            <p className="text-sm text-muted-foreground">
              No credit card required. Get started in minutes.
            </p>
          </div>
        </div>
      </section>
    </div>
  );
}
