import type { DataType, DistributionType } from "@/lib/api-client";
import type { OutputFormat, Step } from "@/lib/studio-constants";
import type {
  GeneratedFileInfo,
  QualityDashboard,
  ValidationSummary,
} from "@/types/generation";

export type { OutputFormat, Step };

export interface AttrRow {
  /** Internal unique row identifier (not sent to API). */
  _id: string;
  /** Column name as it will appear in generated outputs. */
  name: string;
  /** Optional free-text description for documentation and hints. */
  description: string;
  /** DataSim data type (e.g. "integer", "float", "categorical"). */
  type: DataType;
  /** Distribution strategy selected for this attribute. */
  distribution: DistributionType;
  /** Whether null injection is enabled for this attribute. */
  allow_nulls: boolean;
  /** Null percentage applied when allow_nulls is true. */
  null_percentage: number;
  /** Lower bound for numeric values, stored as text input. */
  min: string;
  /** Upper bound for numeric values, stored as text input. */
  max: string;
  /** Comma-separated category labels, e.g. "Red,Green,Blue". */
  categories: string;
  /** Comma-separated weights matching categories length. */
  weights: string;
  /** Inclusive start date bound for date attributes (ISO string). */
  start_date: string;
  /** Inclusive end date bound for date attributes (ISO string). */
  end_date: string;
  /** Decimal precision for float attributes. */
  precision: string;
  /** Maximum text length for text attributes. */
  max_length: string;
  /** Probability of generating true for boolean attributes (0-1). */
  true_probability: string;
  /** Skew direction when using skewed numeric distribution. */
  skew_direction: "left" | "right";
  /** Skew intensity value when skewed distribution is selected. */
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
