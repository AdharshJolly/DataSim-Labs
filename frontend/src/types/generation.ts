import type {
  GenerateResponse,
  GeneratedFileInfo as ApiGeneratedFileInfo,
  ValidationSummary as ApiValidationSummary,
} from "@/lib/api-client";

export type GeneratedFileInfo = ApiGeneratedFileInfo;
export type ValidationSummary = ApiValidationSummary;

export type QualityDashboard = NonNullable<
  GenerateResponse["quality_dashboard"]
>;

export type GenerationResult = GenerateResponse;
