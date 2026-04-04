import type { GenerateResponse } from "@/lib/api-client";
export type { GeneratedFileInfo, ValidationSummary } from "@/lib/api-client";

export type QualityDashboard = NonNullable<
  GenerateResponse["quality_dashboard"]
>;

export type GenerationResult = GenerateResponse;
