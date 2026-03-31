import { Archive, CheckCircle2, LoaderCircle, Pencil } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { type DatasetSummary } from "@/lib/api-client";

interface StatusChipProps {
  status: DatasetSummary["status"];
}

const statusMap = {
  active: {
    icon: CheckCircle2,
    text: "Ready",
    variant: "success",
  },
  generating: {
    icon: LoaderCircle,
    text: "Generating",
    variant: "cyber",
  },
  draft: {
    icon: Pencil,
    text: "Draft",
    variant: "warning",
  },
  archived: {
    icon: Archive,
    text: "Archived",
    variant: "secondary",
  },
} as const;

export function StatusChip({ status }: StatusChipProps) {
  const current = statusMap[status];
  const shouldSpin = status === "generating";

  return (
    <Badge
      variant={
        current.variant as
          | "success"
          | "cyber"
          | "warning"
          | "secondary"
          | "default"
          | "destructive"
          | "outline"
      }
      className="gap-1.5 px-2 py-1 text-xs"
    >
      <current.icon
        className={shouldSpin ? "h-3 w-3 animate-spin" : "h-3 w-3"}
      />
      {current.text}
    </Badge>
  );
}
