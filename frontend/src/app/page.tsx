import Link from "next/link";

export default function HomePage() {
  return (
    <section className="space-y-8">
      <div className="space-y-4">
        <h1 className="font-[var(--font-title)] text-4xl font-black tracking-tight md:text-5xl">
          DataSim Lab
        </h1>
        <p className="max-w-2xl text-lg text-muted-foreground">
          Create realistic synthetic datasets in a guided, beginner-friendly
          workflow.
        </p>
      </div>

      <div className="flex flex-wrap gap-3">
        <Link href="/register" className="sk-btn sk-btn-primary">
          Get Started
        </Link>
        <Link href="/login" className="sk-btn sk-btn-muted">
          I Already Have an Account
        </Link>
        <Link href="/dashboard" className="sk-btn sk-btn-muted">
          Go to Dashboard
        </Link>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <article className="sk-panel space-y-2">
          <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Step 1
          </p>
          <h2 className="font-[var(--font-title)] text-xl font-bold">Set Up</h2>
          <p className="text-sm text-muted-foreground">
            Create your dataset project and add basic details.
          </p>
        </article>

        <article className="sk-panel space-y-2">
          <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Step 2
          </p>
          <h2 className="font-[var(--font-title)] text-xl font-bold">
            Configure Fields
          </h2>
          <p className="text-sm text-muted-foreground">
            Define the columns you want and save your data structure.
          </p>
        </article>

        <article className="sk-panel space-y-2">
          <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Step 3
          </p>
          <h2 className="font-[var(--font-title)] text-xl font-bold">
            Generate and Download
          </h2>
          <p className="text-sm text-muted-foreground">
            Preview, generate full data, and download in one click.
          </p>
        </article>
      </div>
    </section>
  );
}
