import Link from "next/link";
import {
  ArrowRight,
  Calendar,
  CheckSquare,
  Code,
  FileText,
  Hash,
  Mail,
  Milestone,
  Palette,
  Type,
} from "lucide-react";

const FEATURES = [
  { icon: Hash, label: "Numeric Ranges" },
  { icon: Mail, label: "Company Emails" },
  { icon: Milestone, label: "Geographic Fields" },
  { icon: Type, label: "Free Text" },
  { icon: Calendar, label: "Date Logic" },
  { icon: CheckSquare, label: "Rule Conditions" },
  { icon: Palette, label: "Weighted Categories" },
  { icon: FileText, label: "Nested Records" },
  { icon: Code, label: "API-ready JSON" },
] as const;

export function FeatureGridSection() {
  return (
    <section className="space-y-16">
      <div className="flex flex-col justify-between gap-6 md:flex-row md:items-end">
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
          className="flex items-center gap-2 font-medium text-primary underline-offset-4 hover:underline"
        >
          Explore supported schema types <ArrowRight className="h-4 w-4" />
        </Link>
      </div>

      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5">
        {FEATURES.map(({ icon: Icon, label }) => (
          <div
            key={label}
            className="group flex items-center gap-3 rounded-xl border border-border/50 bg-card/65 p-4 transition-all hover:border-primary/30 hover:bg-primary/5"
          >
            <Icon className="h-5 w-5 flex-shrink-0 text-muted-foreground transition-colors group-hover:text-primary" />
            <span className="text-sm font-medium">{label}</span>
          </div>
        ))}
      </div>
    </section>
  );
}
