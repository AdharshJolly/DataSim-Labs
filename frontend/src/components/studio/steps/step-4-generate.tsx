import { formatBytes } from "@/components/studio/format-utils";
import { Step4ResultsPanel } from "@/components/studio/steps/step-4-results-panel";
import { Step4SetupPanel } from "@/components/studio/steps/step-4-setup-panel";
import type { Step } from "@/components/studio/types";
import type { GeneratedFileInfo } from "@/lib/api-client";

interface Step4GenerateProps {
  generatedFiles: GeneratedFileInfo[];
  rowCount: number;
  formats: Array<"csv" | "json" | "jsonl" | "excel">;
  seed: string;
  attrsCount: number;
  busy: boolean;
  streamingBusy: boolean;
  streamedBytes: number;
  versionId: string;
  shouldUseAsyncGeneration: boolean;
  preflightBusy: boolean;
  preflightResult: {
    issues?: Array<{ code: string; message: string }>;
  } | null;
  jobId: string;
  jobStatus: string;
  jobStage: string;
  jobProgress: number;
  driftEnabled: boolean;
  driftIntensity: number;
  driftColumnsText: string;
  guardrailsPassed: boolean;
  allowLowQualityDownloads: boolean;
  feedbackRating: number;
  feedbackComment: string;
  feedbackBusy: boolean;
  qualityDashboard: {
    overall_score: number;
    metrics: {
      distribution_fidelity: number;
      relationship_integrity: number;
      null_pattern_match: number;
      uniqueness: number;
      freshness: number;
    };
    warnings: string[];
    recommendations: string[];
  } | null;
  validationSummary: any;
  qualityReport: Record<string, unknown> | null;
  qualityGuardrails: Record<string, unknown> | null;
  semanticRuleMetrics: Record<string, unknown> | null;
  runComparison: Record<string, unknown> | null;
  generationRunId: string;
  generationSignature: string;
  autoAsyncRowThreshold: number;
  autoAsyncCellThreshold: number;
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
  onDownload: (format: string) => Promise<void>;
  onSetAllowLowQualityDownloads: (enabled: boolean) => void;
  onFeedbackRatingSelect: (rating: number) => void;
  onFeedbackCommentChange: (value: string) => void;
  onSubmitFeedback: () => Promise<void>;
  onGenerateAgain: () => void;
}

export function Step4Generate(props: Step4GenerateProps) {
  if (props.generatedFiles.length === 0) {
    return (
      <Step4SetupPanel
        rowCount={props.rowCount}
        formats={props.formats}
        seed={props.seed}
        busy={props.busy}
        streamingBusy={props.streamingBusy}
        streamedBytes={props.streamedBytes}
        versionId={props.versionId}
        shouldUseAsyncGeneration={props.shouldUseAsyncGeneration}
        preflightBusy={props.preflightBusy}
        preflightResult={props.preflightResult}
        jobId={props.jobId}
        jobStatus={props.jobStatus}
        jobStage={props.jobStage}
        jobProgress={props.jobProgress}
        driftEnabled={props.driftEnabled}
        driftIntensity={props.driftIntensity}
        driftColumnsText={props.driftColumnsText}
        autoAsyncRowThreshold={props.autoAsyncRowThreshold}
        autoAsyncCellThreshold={props.autoAsyncCellThreshold}
        formatBytes={formatBytes}
        onSetStep={props.onSetStep}
        onSetRowCount={props.onSetRowCount}
        onToggleFormat={props.onToggleFormat}
        onSetSeed={props.onSetSeed}
        onGenerate={props.onGenerate}
        onStreamCsvDownload={props.onStreamCsvDownload}
        onCancelJob={props.onCancelJob}
        onSetDriftEnabled={props.onSetDriftEnabled}
        onSetDriftIntensity={props.onSetDriftIntensity}
        onSetDriftColumnsText={props.onSetDriftColumnsText}
      />
    );
  }

  return (
    <Step4ResultsPanel
      generatedFiles={props.generatedFiles}
      rowCount={props.rowCount}
      attrsCount={props.attrsCount}
      guardrailsPassed={props.guardrailsPassed}
      allowLowQualityDownloads={props.allowLowQualityDownloads}
      feedbackRating={props.feedbackRating}
      feedbackComment={props.feedbackComment}
      feedbackBusy={props.feedbackBusy}
      qualityDashboard={props.qualityDashboard}
      validationSummary={props.validationSummary}
      qualityReport={props.qualityReport}
      qualityGuardrails={props.qualityGuardrails}
      semanticRuleMetrics={props.semanticRuleMetrics}
      runComparison={props.runComparison}
      generationRunId={props.generationRunId}
      generationSignature={props.generationSignature}
      driftEnabled={props.driftEnabled}
      driftIntensity={props.driftIntensity}
      formatBytes={formatBytes}
      onDownload={props.onDownload}
      onSetAllowLowQualityDownloads={props.onSetAllowLowQualityDownloads}
      onFeedbackRatingSelect={props.onFeedbackRatingSelect}
      onFeedbackCommentChange={props.onFeedbackCommentChange}
      onSubmitFeedback={props.onSubmitFeedback}
      onGenerateAgain={props.onGenerateAgain}
    />
  );
}
