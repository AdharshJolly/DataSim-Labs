import type { DataType, DistributionType } from "@/lib/api-client";
import type {
  GeneratedFileInfo,
  QualityDashboard,
  ValidationSummary,
} from "@/types/generation";

export type Step = 1 | 2 | 3 | 4;
export type OutputFormat = "csv" | "json" | "jsonl" | "excel";

export interface AttrRow {
  _id: string;
  name: string;
  description: string;
  type: DataType;
  distribution: DistributionType;
  allow_nulls: boolean;
  null_percentage: number;
  min: string;
  max: string;
  categories: string;
  weights: string;
  start_date: string;
  end_date: string;
  precision: string;
  max_length: string;
  true_probability: string;
  skew_direction: "left" | "right";
  skew_intensity: string;
}

export type AttrUpdate = <K extends keyof AttrRow>(
  i: number,
  key: K,
  val: AttrRow[K],
) => void;

export interface GenerationSetupState {
  rowCount: number;
  formats: OutputFormat[];
  seed: string;
  shouldUseAsyncGeneration: boolean;
  autoAsyncRowThreshold: number;
  autoAsyncCellThreshold: number;
  driftEnabled: boolean;
  driftIntensity: number;
  driftColumnsText: string;
}

export interface GenerationJobState {
  jobId: string;
  jobStatus: string;
  jobStage: string;
  jobProgress: number;
}

export interface GenerationResultState {
  generatedFiles: GeneratedFileInfo[];
  qualityDashboard: QualityDashboard | null;
  validationSummary: ValidationSummary | null;
  qualityReport: Record<string, unknown> | null;
  qualityGuardrails: Record<string, unknown> | null;
  semanticRuleMetrics: Record<string, unknown> | null;
  runComparison: Record<string, unknown> | null;
  generationRunId: string;
  generationSignature: string;
  guardrailsPassed: boolean;
}
