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
          <span>V1.0 NOW AVAILABLE</span>
        </div>

        <h1 className="mt-8 font-display text-5xl font-extrabold tracking-tight md:text-7xl lg:text-8xl">
          Synthetic Data
          <br />
          <span className="bg-gradient-to-r from-primary via-secondary to-accent bg-clip-text text-transparent drop-shadow-sm">
            Without Limits.
          </span>
        </h1>

        <p className="mt-8 mx-auto max-w-2xl text-lg md:text-xl text-muted-foreground leading-relaxed">
          The research-grade platform for generating realistic datasets. 
          Define complex constraints, preview in real-time, and scale to millions of rows.
        </p>

        <div className="mt-10 flex flex-wrap items-center justify-center gap-4">
          <Link href="/register" className="btn-primary h-12 px-8 text-base shadow-lg shadow-primary/20">
            <span>Start Generating Now</span>
            <ArrowRight className="ml-2 h-5 w-5" />
          </Link>
          <Link
            href="/studio"
            className="group inline-flex h-12 items-center justify-center rounded-lg border border-border bg-white/5 px-8 font-medium transition-all hover:bg-white/10"
          >
            <span>Try the Studio</span>
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
                <div className="ml-4 h-5 w-64 rounded-md bg-white/5 flex items-center px-3">
                   <span className="text-[10px] text-muted-foreground font-mono">datasim-lab.com/studio/research-dataset-v1</span>
                </div>
             </div>
             <div className="aspect-[16/9] md:aspect-[21/9] bg-grid-white bg-[size:20px_20px] p-6 overflow-hidden relative">
                <div className="grid grid-cols-4 gap-4 opacity-50 select-none pointer-events-none">
                   {[...Array(12)].map((_, i) => (
                      <div key={i} className="h-24 rounded-lg border border-white/10 bg-white/5 animate-pulse" style={{ animationDelay: `${i * 100}ms` }} />
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
                            <p className="text-xs text-muted-foreground">Tweak constraints and see results instantly.</p>
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
          { label: "Data Quality", value: "99.9%", icon: Sparkles },
          { label: "Generation Speed", value: "< 2s", icon: Zap },
          { label: "Realistic Types", value: "50+", icon: Database },
          { label: "Privacy First", value: "100%", icon: ShieldCheck },
        ].map((stat) => (
          <div key={stat.label} className="text-center space-y-2">
            <div className="flex justify-center">
               <stat.icon className="h-5 w-5 text-primary/60" />
            </div>
            <p className="text-3xl font-bold tracking-tight">{stat.value}</p>
            <p className="text-xs uppercase tracking-widest text-muted-foreground font-semibold">{stat.label}</p>
          </div>
        ))}
      </section>

      {/* Process Section */}
      <section className="space-y-16">
        <div className="text-center space-y-4">
          <h2 className="font-display text-4xl font-bold md:text-5xl">Engineered for Efficiency</h2>
          <p className="mx-auto max-w-2xl text-muted-foreground">Four simple steps to transform your research requirements into production-ready data.</p>
        </div>
        
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
          {[
            {
              icon: Database,
              step: "01",
              title: "Context",
              desc: "Define the scope and domain of your dataset. Research-ready from the start.",
              color: "text-blue-400"
            },
            {
              icon: Code,
              step: "02",
              title: "Schema",
              desc: "Add complex fields with fine-tuned distributions and realistic constraints.",
              color: "text-primary"
            },
            {
              icon: Eye,
              step: "03",
              title: "Validation",
              desc: "Instant 10-row preview. Iterate until the statistical shape is perfect.",
              color: "text-secondary"
            },
            {
              icon: Download,
              step: "04",
              title: "Scale",
              desc: "Millions of rows generated in seconds. Export to any major format.",
              color: "text-accent"
            },
          ].map(({ icon: Icon, step, title, desc, color }) => (
            <article
              key={step}
              className="group relative rounded-2xl border border-white/5 bg-white/[0.02] p-8 transition-all hover:border-white/10 hover:bg-white/[0.04]"
            >
              <div className="flex items-center justify-between mb-8">
                <div className={`rounded-xl bg-white/5 p-3 group-hover:scale-110 transition-transform ${color}`}>
                  <Icon className="h-6 w-6" />
                </div>
                <span className="font-display text-4xl font-black opacity-10 group-hover:opacity-20 transition-opacity">
                  {step}
                </span>
              </div>
              <h3 className="font-display text-xl font-bold mb-2 group-hover:text-primary transition-colors">{title}</h3>
              <p className="text-sm text-muted-foreground leading-relaxed">{desc}</p>
            </article>
          ))}
        </div>
      </section>

      {/* Feature Grid */}
      <section className="space-y-16">
        <div className="flex flex-col md:flex-row md:items-end justify-between gap-6">
          <div className="space-y-4">
             <h2 className="font-display text-4xl font-bold">Comprehensive Field Support</h2>
             <p className="max-w-xl text-muted-foreground">From basic primitives to complex identity patterns, we support everything your research needs.</p>
          </div>
          <Link href="/register" className="text-primary font-medium flex items-center gap-2 hover:underline underline-offset-4">
             View all 50+ data types <ArrowRight className="h-4 w-4" />
          </Link>
        </div>
        
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5">
          {[
            { icon: Hash, label: "Numeric Ranges" },
            { icon: Users, label: "Full Identities" },
            { icon: Mail, label: "Smart Emails" },
            { icon: Milestone, label: "Geo-Addresses" },
            { icon: Type, label: "Semantic Text" },
            { icon: Calendar, label: "Temporal" },
            { icon: CheckSquare, label: "Logic Gates" },
            { icon: Palette, label: "Categorical" },
            { icon: FileText, label: "File Systems" },
            { icon: Code, label: "JSON Objects" },
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

      {/* Final CTA */}
      <section className="relative overflow-hidden rounded-3xl border border-primary/30 bg-primary/5 py-24 text-center px-4">
         <div className="absolute top-0 left-1/2 -z-10 h-full w-full -translate-x-1/2 bg-glow-primary opacity-30" />
         <div className="relative z-10 space-y-8 max-w-2xl mx-auto">
            <h2 className="font-display text-4xl font-bold md:text-6xl tracking-tight leading-tight">
              Build your next breakthrough with <span className="text-primary">better data.</span>
            </h2>
            <p className="text-lg text-muted-foreground">
              Join researchers and developers using DataSim Lab to speed up their development cycle.
            </p>
            <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
              <Link href="/register" className="btn-primary h-14 px-10 text-lg w-full sm:w-auto">
                <span>Create Your First Dataset</span>
              </Link>
              <p className="text-sm text-muted-foreground">
                No credit card required. Free forever tier.
              </p>
            </div>
         </div>
      </section>
    </div>
  );
}
