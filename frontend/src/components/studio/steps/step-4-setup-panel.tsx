import { AlertTriangle, LoaderCircle } from "lucide-react";

import { FORMAT_OPTIONS } from "@/lib/studio-constants";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import type {
  GenerationJobState,
  GenerationSetupState,
  Step,
} from "@/types/studio";

interface Step4SetupPanelProps {
  setupState: GenerationSetupState;
  jobState: GenerationJobState;
  busy: boolean;
  streamingBusy: boolean;
  streamedBytes: number;
  versionId: string;
  preflightBusy: boolean;
  preflightResult: { issues?: Array<{ code: string; message: string }> } | null;
  formatBytes: (bytes: number) => string;
  onSetStep: (step: Step) => void;
  onSetRowCount: (value: number) => void;
  onToggleFormat: (format: "csv" | "json" | "jsonl" | "excel") => void;
  onSetSeed: (value: string) => void;
  onGenerate: () => Promise<void>;
  onStreamCsvDownload: () => Promise<void>;
  onCancelJob: () => Promise<void>;
  onSetDriftEnabled: (enabled: boolean) => void;
  onSetDriftIntensity: (value: number) => void;
  onSetDriftColumnsText: (value: string) => void;
}

export function Step4SetupPanel({
  setupState,
  jobState,
  busy,
  streamingBusy,
  streamedBytes,
  versionId,
  preflightBusy,
  preflightResult,
  formatBytes,
  onSetStep,
  onSetRowCount,
  onToggleFormat,
  onSetSeed,
  onGenerate,
  onStreamCsvDownload,
  onCancelJob,
  onSetDriftEnabled,
  onSetDriftIntensity,
  onSetDriftColumnsText,
}: Step4SetupPanelProps) {
  const {
    rowCount,
    formats,
    seed,
    shouldUseAsyncGeneration,
    autoAsyncRowThreshold,
    autoAsyncCellThreshold,
    driftEnabled,
    driftIntensity,
    driftColumnsText,
  } = setupState;
  const { jobId, jobStatus, jobStage, jobProgress } = jobState;

  return (
    <>
      <header className="mb-8">
        <h1 className="font-display text-4xl font-bold">
          Generate Your Dataset
        </h1>
        <p className="mt-2 text-muted-foreground">
          Choose how many rows you need and which formats to export.
        </p>
      </header>

      <div className="max-w-xl space-y-8">
        <div className="space-y-2">
          <label
            htmlFor="row-count"
            className="text-sm font-medium text-muted-foreground"
          >
            Number of Rows
          </label>
          <div className="flex items-center gap-4">
            <input
              id="row-count"
              type="range"
              min={100}
              max={100000}
              step={100}
              value={rowCount}
              onChange={(e) => onSetRowCount(Number(e.target.value))}
              className="h-2 flex-1 cursor-pointer appearance-none rounded-lg bg-border accent-primary"
            />
            <input
              type="number"
              min={1}
              max={10000000}
              className="w-32 text-center font-semibold"
              value={rowCount}
              onChange={(e) =>
                onSetRowCount(Math.max(1, Number(e.target.value) || 1))
              }
            />
          </div>
        </div>

        <div className="space-y-2">
          <label className="text-sm font-medium text-muted-foreground">
            Output Format
          </label>
          <div className="mt-1 flex flex-wrap gap-3">
            {FORMAT_OPTIONS.map(({ value, label, icon: Icon }) => (
              <button
                key={value}
                type="button"
                onClick={() => onToggleFormat(value)}
                className={`flex h-24 w-24 flex-col items-center justify-center gap-1.5 rounded-lg border-2 text-sm font-semibold transition-all duration-150 ${
                  formats.includes(value)
                    ? "border-primary bg-primary/10 text-primary shadow-lg shadow-primary/10"
                    : "border-border bg-card/70 text-muted-foreground hover:border-primary/50 hover:bg-primary/5"
                }`}
              >
                <Icon className="h-6 w-6" />
                <span>{label}</span>
              </button>
            ))}
          </div>
        </div>

        <div className="space-y-2">
          <label
            htmlFor="generation-seed"
            className="text-sm font-medium text-muted-foreground"
          >
            Reproducibility Seed (optional)
          </label>
          <input
            id="generation-seed"
            type="number"
            min={0}
            className="w-48"
            value={seed}
            placeholder="e.g. 42"
            onChange={(e) => onSetSeed(e.target.value)}
          />
          <p className="pt-1 text-xs text-muted-foreground/70">
            Use the same seed to regenerate identical datasets.
          </p>
        </div>

        <div className="space-y-3 rounded-lg border border-border bg-card/70 p-4">
          <p className="text-sm font-medium text-foreground">
            Generation mode:{" "}
            {shouldUseAsyncGeneration ? "Background job" : "Immediate"}
          </p>
          <p className="text-xs text-muted-foreground">
            Auto-selected by thresholds (
            {autoAsyncRowThreshold.toLocaleString()} rows or{" "}
            {autoAsyncCellThreshold.toLocaleString()} estimated cells).
          </p>

          {(preflightBusy || preflightResult?.issues?.length) && (
            <div className="rounded border border-border/60 bg-background/40 p-3 text-xs text-muted-foreground">
              {preflightBusy ? (
                <p>Running preflight checks...</p>
              ) : (
                <>
                  <p className="font-medium text-foreground">
                    Preflight checks
                  </p>
                  {preflightResult?.issues?.length ? (
                    <ul className="mt-1 space-y-1">
                      {preflightResult.issues.map((issue) => (
                        <li key={`${issue.code}-${issue.message}`}>
                          {issue.message}
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="mt-1">No blocking risks detected.</p>
                  )}
                </>
              )}
            </div>
          )}

          {jobId && (
            <div className="space-y-2 text-xs text-muted-foreground">
              <div>
                <span className="text-foreground">Job ID:</span> {jobId}
              </div>
              <div>
                <span className="text-foreground">Status:</span>{" "}
                {jobStatus || "queued"}
              </div>
              <div>
                <span className="text-foreground">Stage:</span>{" "}
                {jobStage || "queued"}
              </div>
              <div>
                <span className="text-foreground">Progress:</span> {jobProgress}
                %
              </div>
              <div className="h-2 w-full overflow-hidden rounded bg-border">
                <div
                  className="h-full bg-primary transition-all"
                  style={{
                    width: `${Math.max(0, Math.min(100, jobProgress))}%`,
                  }}
                />
              </div>
            </div>
          )}
        </div>

        <div className="space-y-3 rounded-lg border border-border bg-card/70 p-4">
          <label className="inline-flex items-center gap-2 text-sm font-medium text-foreground">
            <input
              type="checkbox"
              className="h-4 w-4"
              checked={driftEnabled}
              onChange={(e) => onSetDriftEnabled(e.target.checked)}
            />
            Drift simulator
          </label>
          {driftEnabled && (
            <>
              <div className="space-y-2">
                <label className="text-xs text-muted-foreground">
                  Drift intensity ({driftIntensity.toFixed(2)})
                </label>
                <input
                  type="range"
                  min={0}
                  max={1}
                  step={0.05}
                  value={driftIntensity}
                  onChange={(e) => onSetDriftIntensity(Number(e.target.value))}
                  className="h-2 w-full cursor-pointer appearance-none rounded-lg bg-border accent-primary"
                />
              </div>
              <div className="space-y-1">
                <label className="text-xs text-muted-foreground">
                  Target columns (comma separated)
                </label>
                <input
                  type="text"
                  value={driftColumnsText}
                  placeholder="age, income"
                  onChange={(e) => onSetDriftColumnsText(e.target.value)}
                />
              </div>
            </>
          )}
        </div>

        <div className="flex flex-wrap items-center gap-3 pt-4">
          <Button type="button" variant="outline" onClick={() => onSetStep(3)}>
            ← Back to Preview
          </Button>
          <Button
            type="button"
            variant="default"
            disabled={busy || formats.length === 0}
            onClick={() => void onGenerate()}
          >
            {busy ? (
              <span className="flex items-center justify-center gap-2">
                <LoaderCircle className="h-4 w-4 animate-spin" /> Generating…
              </span>
            ) : (
              `Generate ${rowCount.toLocaleString()} Rows`
            )}
          </Button>
          <Button
            type="button"
            variant="outline"
            disabled={streamingBusy || !versionId}
            onClick={() => void onStreamCsvDownload()}
          >
            {streamingBusy
              ? `Streaming... ${formatBytes(streamedBytes)}`
              : "Live Stream CSV"}
          </Button>
          {shouldUseAsyncGeneration && jobId && busy && (
            <Button
              type="button"
              variant="outline"
              className="border-amber-400/50 text-amber-200 hover:bg-amber-500/10 hover:text-amber-100"
              onClick={() => void onCancelJob()}
            >
              Cancel Job
            </Button>
          )}
        </div>

        {!busy && preflightResult?.issues?.length ? (
          <Alert>
            <AlertTriangle className="h-5 w-5" />
            <AlertDescription>
              Large payload detected. Async mode is recommended to avoid request
              timeouts.
            </AlertDescription>
          </Alert>
        ) : null}
      </div>
    </>
  );
}
