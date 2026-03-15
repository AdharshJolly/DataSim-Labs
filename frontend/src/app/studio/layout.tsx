import Link from "next/link";
import { ArrowLeft } from "lucide-react";

export default function StudioLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div>
      <Link
        href="/dashboard"
        className="group mb-6 inline-flex items-center gap-2 text-sm font-medium text-muted-foreground transition-colors hover:text-foreground"
      >
        <ArrowLeft className="h-4 w-4 transition-transform group-hover:-translate-x-1" />
        <span>Back to Dashboard</span>
      </Link>
      <div className="relative rounded-xl border border-border bg-card p-4 md:p-8">
        <div className="relative z-10">{children}</div>
      </div>
    </div>
  );
}
