import Link from "next/link";
import { LoaderCircle, RefreshCw, X } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { type GenerationJobResponse } from "@/lib/api-client";

interface JobsPanelProps {
  showJobsPanel: boolean;
  jobs: GenerationJobResponse[];
  datasetNameById: Map<string, string>;
  retryingJobId: string | null;
  onClose: () => void;
  onRetryJob: (jobId: string) => void;
}

export function JobsPanel({
  showJobsPanel,
  jobs,
  datasetNameById,
  retryingJobId,
  onClose,
  onRetryJob,
}: JobsPanelProps) {
  return (
    <>
      {showJobsPanel && (
        <button
          type="button"
          aria-label="Close jobs panel"
          onClick={onClose}
          className="fixed inset-0 z-[70] bg-muted/35 backdrop-blur-[1px]"
        />
      )}

      <aside
        className={`fixed right-0 top-0 bottom-0 z-[80] w-full max-w-md transform border-l border-border bg-[#0b0f1a]/95 shadow-2xl transition-transform duration-300 ease-out will-change-transform ${
          showJobsPanel ? "translate-x-0" : "translate-x-full"
        }`}
        aria-hidden={!showJobsPanel}
      >
        <div className="flex h-full flex-col">
          <div className="flex items-center justify-between border-b border-border px-5 py-4">
            <div>
              <h2 className="font-display text-2xl font-bold">My Jobs</h2>
              <p className="text-xs text-muted-foreground">
                Latest {jobs.length}
              </p>
            </div>
            <Button
              type="button"
              variant="outline"
              size="sm"
              className="h-8 w-8 p-0"
              onClick={onClose}
              aria-label="Close jobs panel"
            >
              <X className="h-4 w-4" />
            </Button>
          </div>

          <div className="flex-1 overflow-y-auto p-4">
            {jobs.length === 0 ? (
              <Card className="p-5 text-sm text-muted-foreground">
                No jobs yet. Start a generation run to see activity here.
              </Card>
            ) : (
              <div className="space-y-2">
                {jobs.slice(0, 12).map((job) => {
                  const canRetry =
                    job.status === "failed" || job.status === "cancelled";
                  return (
                    <div
                      key={job.job_id}
                      className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-border/70 bg-background/40 p-3 text-sm"
                    >
                      <div className="min-w-0">
                        <p className="truncate font-medium text-foreground">
                          {datasetNameById.get(job.dataset_id) ||
                            `Dataset ${job.dataset_id.slice(0, 8)}...`}
                        </p>
                        <p className="text-xs text-muted-foreground">
                          {job.status.toUpperCase()} · {job.progress_percentage}
                          % · {new Date(job.created_at).toLocaleString()}
                        </p>
                      </div>
                      <div className="flex items-center gap-2">
                        <Button
                          asChild
                          variant="outline"
                          size="sm"
                          className="h-8"
                        >
                          <Link href={`/studio?datasetId=${job.dataset_id}`}>
                            Open
                          </Link>
                        </Button>
                        {canRetry && (
                          <Button
                            type="button"
                            variant="outline"
                            size="sm"
                            className="h-8 hover:border-cyan-300 hover:text-cyan-300"
                            disabled={retryingJobId === job.job_id}
                            onClick={() => onRetryJob(job.job_id)}
                          >
                            {retryingJobId === job.job_id ? (
                              <LoaderCircle className="h-3 w-3 animate-spin" />
                            ) : (
                              <RefreshCw className="h-3 w-3" />
                            )}
                          </Button>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      </aside>
    </>
  );
}
