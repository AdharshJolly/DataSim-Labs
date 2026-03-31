import { Code, Database, Download, Eye } from "lucide-react";

const STEPS = [
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
] as const;

export function ProcessSection() {
  return (
    <section className="space-y-16">
      <div className="space-y-4 text-center">
        <h2 className="font-display text-4xl font-bold md:text-5xl">
          From Idea to Dataset in Minutes
        </h2>
        <p className="mx-auto max-w-2xl text-muted-foreground">
          Follow a focused workflow to define schema logic, validate behavior,
          and generate large-scale outputs confidently.
        </p>
      </div>

      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
        {STEPS.map(({ icon: Icon, step, title, desc, color }) => (
          <article
            key={step}
            className="group relative rounded-2xl border border-border/50 bg-card/65 p-8 transition-all hover:border-border/70 hover:bg-muted/35"
          >
            <div className="mb-8 flex items-center justify-between">
              <div
                className={`rounded-xl bg-card/70 p-3 transition-transform group-hover:scale-110 ${color}`}
              >
                <Icon className="h-6 w-6" />
              </div>
              <span className="font-display text-4xl font-black opacity-10 transition-opacity group-hover:opacity-20">
                {step}
              </span>
            </div>
            <h3 className="mb-2 font-display text-xl font-bold transition-colors group-hover:text-primary">
              {title}
            </h3>
            <p className="text-sm leading-relaxed text-muted-foreground">
              {desc}
            </p>
          </article>
        ))}
      </div>
    </section>
  );
}
