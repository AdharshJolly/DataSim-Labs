import Link from "next/link";

const routes = [
  "/dashboard",
  "/create-dataset",
  "/attribute-builder",
  "/dataset-preview",
  "/generate-dataset",
  "/download",
];

export default function HomePage() {
  return (
    <section className="space-y-6">
      <h1 className="text-4xl font-semibold tracking-tight">DataSim Lab</h1>
      <p className="max-w-2xl text-muted-foreground">
        Synthetic Dataset Generation Platform scaffold using Next.js and
        FastAPI.
      </p>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {routes.map((route) => (
          <Link
            key={route}
            href={route}
            className="rounded-lg border border-border bg-white/70 px-4 py-3 text-sm font-medium shadow-sm transition hover:-translate-y-0.5 hover:shadow"
          >
            {route}
          </Link>
        ))}
      </div>
    </section>
  );
}
