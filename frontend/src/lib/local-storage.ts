import type { ValidationSummary } from "@/lib/api-client";

const KEYS = {
  DATASET_ID: "datasim:dataset_id",
  DATASET_VERSION_ID: "datasim:dataset_version_id",
  VALIDATION_SUMMARY: "datasim:validation_summary",
} as const;

export function getStoredDatasetId(): string | null {
  return localStorage.getItem(KEYS.DATASET_ID);
}

export function setStoredDatasetId(id: string): void {
  localStorage.setItem(KEYS.DATASET_ID, id);
}

export function clearStoredDatasetId(): void {
  localStorage.removeItem(KEYS.DATASET_ID);
}

export function getStoredDatasetVersionId(): string | null {
  return localStorage.getItem(KEYS.DATASET_VERSION_ID);
}

export function setStoredDatasetVersionId(id: string): void {
  localStorage.setItem(KEYS.DATASET_VERSION_ID, id);
}

export function clearStoredDatasetVersionId(): void {
  localStorage.removeItem(KEYS.DATASET_VERSION_ID);
}

export function getStoredValidationSummary(): ValidationSummary | null {
  try {
    const raw = localStorage.getItem(KEYS.VALIDATION_SUMMARY);
    return raw ? (JSON.parse(raw) as ValidationSummary) : null;
  } catch {
    return null;
  }
}

export function setStoredValidationSummary(summary: ValidationSummary): void {
  localStorage.setItem(KEYS.VALIDATION_SUMMARY, JSON.stringify(summary));
}

export function clearStoredValidationSummary(): void {
  localStorage.removeItem(KEYS.VALIDATION_SUMMARY);
}
