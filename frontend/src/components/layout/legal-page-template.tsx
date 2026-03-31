import Link from "next/link";
import { ArrowUpRight } from "lucide-react";

type LegalSection = {
  id: string;
  title: string;
  paragraphs: string[];
};

type LegalPageTemplateProps = {
  eyebrow: string;
  title: string;
  summary: string;
  updatedAt: string;
  sections: LegalSection[];
  scope: string[];
};

export function LegalPageTemplate({
  eyebrow,
  title,
  summary,
  updatedAt,
  sections,
  scope,
}: LegalPageTemplateProps) {
  return (
    <div className="space-y-10">
      <section className="relative overflow-hidden rounded-2xl border border-border/70 bg-card/75 p-8 md:p-10">
        <div className="absolute -right-20 -top-20 h-64 w-64 rounded-full bg-glow-primary blur-3xl" />
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-primary/90">
          {eyebrow}
        </p>
        <h1 className="mt-4 font-display text-4xl font-bold tracking-tight md:text-5xl">
          {title}
        </h1>
        <p className="mt-5 max-w-3xl text-sm leading-7 text-muted-foreground md:text-base">
          {summary}
        </p>
        <div className="mt-6 inline-flex rounded-lg border border-primary/20 bg-primary/5 px-3 py-1.5 text-xs font-medium text-primary">
          Last updated: {updatedAt}
        </div>
      </section>

      <section className="grid gap-8 lg:grid-cols-[280px_1fr]">
        <aside className="h-fit rounded-xl border border-border/70 bg-card/75 p-5 lg:sticky lg:top-24">
          <h2 className="text-xs font-semibold uppercase tracking-[0.15em] text-muted-foreground">
            On this page
          </h2>
          <nav className="mt-4 space-y-2">
            {sections.map((section) => (
              <a
                key={section.id}
                href={`#${section.id}`}
                className="block rounded-md px-2 py-1.5 text-sm text-muted-foreground transition-colors hover:bg-muted/60 hover:text-primary"
              >
                {section.title}
              </a>
            ))}
          </nav>

          <div className="mt-6 rounded-lg border border-border/70 bg-muted/35 p-3">
            <p className="text-xs font-semibold uppercase tracking-[0.12em] text-muted-foreground">
              Related
            </p>
            <div className="mt-2 space-y-2 text-sm">
              <Link
                href="/privacy"
                className="flex items-center justify-between text-muted-foreground transition-colors hover:text-primary"
              >
                Privacy
                <ArrowUpRight className="h-3.5 w-3.5" />
              </Link>
              <Link
                href="/terms"
                className="flex items-center justify-between text-muted-foreground transition-colors hover:text-primary"
              >
                Terms
                <ArrowUpRight className="h-3.5 w-3.5" />
              </Link>
              <Link
                href="/cookies"
                className="flex items-center justify-between text-muted-foreground transition-colors hover:text-primary"
              >
                Cookie Policy
                <ArrowUpRight className="h-3.5 w-3.5" />
              </Link>
            </div>
          </div>
        </aside>

        <div className="space-y-6">
          <article className="rounded-xl border border-border/70 bg-card/75 p-6 md:p-7">
            <h2 className="font-display text-xl font-semibold">Policy scope</h2>
            <ul className="mt-4 space-y-2 text-sm leading-7 text-muted-foreground">
              {scope.map((item) => (
                <li key={item}>• {item}</li>
              ))}
            </ul>
          </article>

          {sections.map((section) => (
            <article
              key={section.id}
              id={section.id}
              className="scroll-mt-28 rounded-xl border border-border/70 bg-card/75 p-6 md:p-7"
            >
              <h2 className="font-display text-xl font-semibold">
                {section.title}
              </h2>
              <div className="mt-4 space-y-4 text-sm leading-7 text-muted-foreground md:text-[15px]">
                {section.paragraphs.map((paragraph) => (
                  <p key={paragraph}>{paragraph}</p>
                ))}
              </div>
            </article>
          ))}
        </div>
      </section>
    </div>
  );
}
