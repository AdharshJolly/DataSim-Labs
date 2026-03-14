import Link from "next/link";

export default function HomePage() {
  return (
    <div className="space-y-12">
      {/* Hero */}
      <section className="space-y-6 pt-4">
        <div className="inline-flex items-center gap-2 rounded-full border border-[hsl(var(--border))] bg-[rgba(220,196,160,0.4)] px-4 py-1.5 text-xs font-semibold uppercase tracking-widest text-[hsl(var(--primary))]">
          Research · Synthetic Data · Generation
        </div>
        <h1 className="font-[var(--font-title)] text-4xl font-black leading-tight tracking-tight md:text-5xl lg:text-6xl">
          Generate Synthetic
          <br />
          <span className="text-[hsl(var(--primary))]">Research Datasets</span>
        </h1>
        <p className="max-w-xl text-lg text-[hsl(var(--muted-foreground))]">
          Design your data structure, preview a 10-row sample, refine it until
          it looks right, then generate millions of realistic rows ready for
          research and development.
        </p>
        <div className="flex flex-wrap gap-3">
          <Link
            href="/register"
            className="sk-btn sk-btn-primary px-8 py-3 text-base"
          >
            Get Started — Free
          </Link>
          <Link
            href="/login"
            className="sk-btn sk-btn-muted px-6 py-3 text-base"
          >
            Sign In
          </Link>
        </div>
      </section>

      {/* How it works */}
      <section className="space-y-4">
        <p className="text-xs font-bold uppercase tracking-widest text-[hsl(var(--muted-foreground))]">
          How It Works
        </p>
        <div className="grid gap-4 md:grid-cols-4">
          {[
            {
              step: "01",
              title: "Name Your Dataset",
              desc: "Give it a name and describe what it represents — survey data, patient records, financial transactions.",
            },
            {
              step: "02",
              title: "Define Fields",
              desc: "Add columns with types (integer, text, date, category…), distributions, and allow null values per field.",
            },
            {
              step: "03",
              title: "Preview & Refine",
              desc: "See 10 realistic rows instantly. Tweak constraints and regenerate until the data looks exactly right.",
            },
            {
              step: "04",
              title: "Generate & Export",
              desc: "Choose your row count and export as CSV, JSON, or Excel. Download in seconds.",
            },
          ].map(({ step, title, desc }) => (
            <article key={step} className="sk-panel space-y-3 p-5">
              <span className="font-[var(--font-title)] text-3xl font-black text-[hsl(var(--primary)/0.25)]">
                {step}
              </span>
              <h2 className="font-[var(--font-title)] text-lg font-bold">
                {title}
              </h2>
              <p className="text-sm text-[hsl(var(--muted-foreground))]">
                {desc}
              </p>
            </article>
          ))}
        </div>
      </section>

      {/* Feature highlights */}
      <section className="sk-panel space-y-4 p-6 md:p-8">
        <h2 className="font-[var(--font-title)] text-2xl font-bold">
          What can you generate?
        </h2>
        <div className="grid gap-3 sm:grid-cols-2 md:grid-cols-3">
          {[
            { icon: "#", label: "Integer & decimal numbers" },
            { icon: "≡", label: "Categorical / enum values" },
            { icon: "◎", label: "Boolean flags" },
            { icon: "▦", label: "Dates with custom ranges" },
            { icon: "@", label: "Realistic email addresses" },
            { icon: "✦", label: "Full names" },
            { icon: "⌂", label: "Street addresses" },
            { icon: "T", label: "Free-form text" },
            { icon: "∅", label: "Null values at any rate" },
          ].map(({ icon, label }) => (
            <div
              key={label}
              className="flex items-center gap-3 rounded-xl border border-[hsl(var(--border))] bg-[rgba(240,228,210,0.4)] px-4 py-3"
            >
              <span className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-lg bg-[hsl(var(--primary)/0.12)] font-mono text-sm font-bold text-[hsl(var(--primary))]">
                {icon}
              </span>
              <span className="text-sm font-medium">{label}</span>
            </div>
          ))}
        </div>
      </section>

      {/* CTA */}
      <section className="flex flex-col items-center gap-4 rounded-2xl border border-[hsl(var(--border))] bg-[rgba(200,158,100,0.12)] py-12 text-center">
        <h2 className="font-[var(--font-title)] text-2xl font-bold">
          Ready to generate your dataset?
        </h2>
        <p className="text-[hsl(var(--muted-foreground))]">
          Free to use. No credit card required.
        </p>
        <Link
          href="/register"
          className="sk-btn sk-btn-primary px-10 py-3 text-base"
        >
          Create a Free Account
        </Link>
      </section>
    </div>
  );
}
