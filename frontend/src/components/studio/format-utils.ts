import type { DataType } from "@/lib/api-client";

import { ALL_TYPE_OPTIONS } from "./constants";

export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function typeLabel(t: DataType): string {
  return ALL_TYPE_OPTIONS.find((o) => o.value === t)?.label ?? t;
}
