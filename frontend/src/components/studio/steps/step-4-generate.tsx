import { formatBytes } from "@/components/studio/format-utils";
import { Step4ResultsPanel } from "@/components/studio/steps/step-4-results-panel";
import { Step4SetupPanel } from "@/components/studio/steps/step-4-setup-panel";
import type {
  GenerationJobState,
  GenerationResultState,
  GenerationSetupState,
  Step,
} from "@/types/studio";

interface Step4GenerateProps {
  setupState: GenerationSetupState;
  jobState: GenerationJobState;
  resultState: GenerationResultState;
  attrsCount: number;
  busy: boolean;
  streamingBusy: boolean;
  streamedBytes: number;
  versionId: string;
  preflightBusy: boolean;
  preflightResult: {
    issues?: Array<{ code: string; message: string }>;
  } | null;
  feedbackRating: number;
  feedbackComment: string;
  feedbackBusy: boolean;
  allowLowQualityDownloads: boolean;
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
  if (props.resultState.generatedFiles.length === 0) {
    return (
      <Step4SetupPanel
        setupState={props.setupState}
        jobState={props.jobState}
        busy={props.busy}
        streamingBusy={props.streamingBusy}
        streamedBytes={props.streamedBytes}
        versionId={props.versionId}
        preflightBusy={props.preflightBusy}
        preflightResult={props.preflightResult}
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
      resultState={props.resultState}
      rowCount={props.setupState.rowCount}
      attrsCount={props.attrsCount}
      allowLowQualityDownloads={props.allowLowQualityDownloads}
      feedbackRating={props.feedbackRating}
      feedbackComment={props.feedbackComment}
      feedbackBusy={props.feedbackBusy}
      driftEnabled={props.setupState.driftEnabled}
      driftIntensity={props.setupState.driftIntensity}
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
