import type { GenerationJobStatus } from "@/lib/api-client";

export type {
  GenerationJobResponse,
  GenerationJobStatus,
} from "@/lib/api-client";
export type JobStatus = GenerationJobStatus;
export type JobStage = string;
