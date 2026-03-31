import Link from "next/link";
import { Clock3, Download, LoaderCircle, Pencil, Trash2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { type DatasetSummary } from "@/lib/api-client";
import { StatusChip } from "@/components/dashboard/status-chip";

interface DatasetCardProps {
  dataset: DatasetSummary;
  deletingId: string | null;
  onDelete: (datasetId: string) => void;
}

export function DatasetCard({
  dataset,
  deletingId,
  onDelete,
}: DatasetCardProps) {
  return (
    <Card className="group flex flex-col gap-4 rounded-2xl bg-gradient-to-br from-card/90 to-transparent p-5 backdrop-blur-sm transition-all duration-300 hover:-translate-y-1 hover:border-primary/50 hover:shadow-xl hover:shadow-primary/10">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <h2 className="truncate font-display text-xl font-bold">
            {dataset.name}
          </h2>
          <p className="mt-1 text-xs text-muted-foreground">
            Created:{" "}
            {new Date(dataset.created_at).toLocaleDateString(undefined, {
              year: "numeric",
              month: "short",
              day: "numeric",
            })}
          </p>
        </div>
        <StatusChip status={dataset.status} />
      </div>

      {dataset.description && (
        <p className="line-clamp-2 text-sm text-muted-foreground">
          {dataset.description}
        </p>
      )}

      {dataset.status === "draft" && dataset.latest_version_id && (
        <p className="text-xs text-amber-300/90">
          <Clock3 className="mr-1 inline h-3 w-3" />
          No active export files found. Regenerate to download again.
        </p>
      )}

      <div className="mt-auto flex flex-wrap gap-2 pt-2">
        <Button asChild variant="cyber" className="h-9 flex-1 px-3 text-xs">
          <Link href={`/studio?datasetId=${dataset.id}`}>
            <Pencil className="mr-1.5 h-3 w-3" />
            Open Studio
          </Link>
        </Button>
        {dataset.latest_version_id && dataset.status !== "draft" && (
          <Button
            asChild
            variant="outline"
            size="sm"
            className="h-9 px-3 hover:border-secondary hover:text-secondary"
          >
            <Link href={`/download?datasetId=${dataset.id}`}>
              <Download className="h-3 w-3" />
            </Link>
          </Button>
        )}
        <Button
          type="button"
          variant="outline"
          size="sm"
          disabled={deletingId === dataset.id}
          className="h-9 px-3 hover:border-destructive hover:bg-destructive/20 hover:text-destructive"
          onClick={() => onDelete(dataset.id)}
        >
          {deletingId === dataset.id ? (
            <LoaderCircle className="h-4 w-4 animate-spin" />
          ) : (
            <Trash2 className="h-3 w-3" />
          )}
        </Button>
      </div>
    </Card>
  );
}
