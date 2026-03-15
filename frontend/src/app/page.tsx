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
} from "lucide-react";

export default function HomePage() {
  return (
    <div className="space-y-24 md:space-y-32">
      {/* Hero */}
      <section className="mt-12 space-y-8 text-center">
        <div className="inline-flex items-center justify-center rounded-full border border-primary/30 bg-primary/10 px-4 py-2 text-xs font-medium uppercase tracking-widest text-primary">
          <span className="text-glow">Research · Synthetic Data · Generation</span>
        </div>
        <h1 className="font-display animate-flicker text-5xl font-extrabold tracking-tight md:text-6xl lg:text-7xl">
          Generate Synthetic
          <br />
          <span className="text-glow text-primary">Research Datasets</span>
        </h1>
        <p className="mx-auto max-w-2xl text-lg text-muted-foreground">
          Design your data structure, preview a 10-row sample, refine it until
          it looks right, then generate millions of realistic rows ready for
          research and development.
        </p>
        <div className="flex flex-wrap items-center justify-center gap-4">
          <Link href="/register" className="btn-cyber">
            <span>Get Started — Free</span>
            <ArrowRight className="ml-2 h-5 w-5" />
          </Link>
          <Link
            href="/login"
            className="group inline-flex items-center font-medium text-muted-foreground transition-colors hover:text-foreground"
          >
            <span>Sign In</span>
            <span className="ml-2 transition-transform group-hover:translate-x-1">&rarr;</span>
          </Link>
        </div>
      </section>

      {/* How it works */}
      <section className="space-y-8">
        <h2 className="text-center font-display text-4xl font-bold">How It Works</h2>
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
          {[
            {
              icon: Database,
              step: "01",
              title: "Name Your Dataset",
              desc: "Give it a name and describe what it represents — survey data, patient records, financial transactions.",
            },
            {
              icon: Code,
              step: "02",
              title: "Define Fields",
              desc: "Add columns with types (integer, text, date, category…), distributions, and allow null values per field.",
            },
            {
              icon: Eye,
              step: "03",
              title: "Preview & Refine",
              desc: "See 10 realistic rows instantly. Tweak constraints and regenerate until the data looks exactly right.",
            },
            {
              icon: Download,
              step: "04",
              title: "Generate & Export",
              desc: "Choose your row count and export as CSV, JSON, or Excel. Download in seconds.",
            },
          ].map(({ icon: Icon, step, title, desc }) => (
            <article
              key={step}
              className="animate-subtle-float rounded-2xl border border-border bg-white/5 p-6 backdrop-blur-sm transition-all duration-300 hover:border-primary/60 hover:shadow-2xl hover:shadow-primary/10"
            >
              <div className="flex items-center justify-between">
                <Icon className="h-8 w-8 text-secondary" />
                <span className="font-display text-5xl font-black text-primary/20">
                  {step}
                </span>
              </div>
              <h3 className="mt-4 font-display text-2xl font-bold">{title}</h3>
              <p className="mt-2 text-sm text-muted-foreground">{desc}</p>
            </article>
          ))}
        </div>
      </section>

      {/* Feature highlights */}
      <section className="space-y-8">
        <h2 className="text-center font-display text-4xl font-bold">
          What can you generate?
        </h2>
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5">
          {[
            { icon: Hash, label: "Numbers" },
            { icon: Users, label: "Full Names" },
            { icon: Mail, label: "Emails" },
            { icon: Milestone, label: "Addresses" },
            { icon: Type, label: "Free Text" },
            { icon: Calendar, label: "Dates" },
            { icon: CheckSquare, label: "Booleans" },
            { icon: Palette, label: "Colors" },
            { icon: FileText, label: "File Paths" },
            { icon: Code, label: "Code Snippets" },
          ].map(({ icon: Icon, label }) => (
            <div
              key={label}
              className="flex items-center gap-3 rounded-lg border border-border bg-white/5 p-4 transition-colors hover:border-accent/50 hover:bg-accent/10"
            >
              <Icon className="h-6 w-6 flex-shrink-0 text-accent" />
              <span className="text-sm font-medium">{label}</span>
            </div>
          ))}
        </div>
      </section>

      {/* CTA */}
      <section className="overflow-hidden rounded-2xl border border-primary/30 bg-primary/10 py-20 text-center backdrop-blur-lg">
         <div className="space-y-6">
            <h2 className="font-display text-4xl font-bold">
              Ready to generate your dataset?
            </h2>
            <p className="text-muted-foreground">
              Free to use. No credit card required.
            </p>
            <Link href="/register" className="btn-cyber">
              <span>Create a Free Account</span>
               <ArrowRight className="ml-2 h-5 w-5" />
            </Link>
         </div>
      </section>
    </div>
  );
}
