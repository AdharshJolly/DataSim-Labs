import type {
  GenerationJobResponse as ApiGenerationJobResponse,
  GenerationJobStatus as ApiGenerationJobStatus,
} from "@/lib/api-client";

export type JobStatus = ApiGenerationJobStatus;
export type GenerationJobResponse = ApiGenerationJobResponse;
export type JobStage = string;
