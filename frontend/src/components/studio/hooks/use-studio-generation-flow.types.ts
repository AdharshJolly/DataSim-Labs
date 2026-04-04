import type { AttrRow, OutputFormat } from "@/components/studio/types";
import type { GenerationJobStatus } from "@/lib/api-client";

export interface ToastInput {
  title: string;
  message: string;
  intent?: "success" | "info" | "error";
  durationMs?: number;
}

export interface UseStudioGenerationFlowArgs {
  datasetId: string;
  versionId: string;
  attrs: AttrRow[];
  formats: OutputFormat[];
  rowCount: number;
  seed: string;
  shouldUseAsyncGeneration: boolean;
  feedbackRating: number;
  feedbackComment: string;
  generationSignature: string;
  jobId: string;
  setError: (value: string) => void;
  setBusy: (value: boolean) => void;
  setStreamingBusy: (value: boolean) => void;
  setStreamedBytes: (value: number) => void;
  setFeedbackBusy: (value: boolean) => void;
  setFeedbackComment: (value: string) => void;
  setAllowLowQualityDownloads: (value: boolean) => void;
  setGeneratedFiles: (value: any[]) => void;
  setQualityReport: (value: Record<string, unknown> | null) => void;
  setQualityDashboard: (value: any) => void;
  setValidationSummary: (value: any) => void;
  setQualityGuardrails: (value: Record<string, unknown> | null) => void;
  setSemanticRuleMetrics: (value: Record<string, unknown> | null) => void;
  setGenerationSignature: (value: string) => void;
  setGenerationRunId: (value: string) => void;
  setRunComparison: (value: Record<string, unknown> | null) => void;
  setJobId: (value: string) => void;
  setJobStatus: (value: GenerationJobStatus | "") => void;
  setJobStage: (value: string) => void;
  setJobProgress: (value: number) => void;
  notifyError: (title: string, error: unknown, fallback: string) => void;
  pushToast: (toast: ToastInput) => void;
  asyncPollIntervalMs: number;
  asyncPollMaxAttempts: number;
}
