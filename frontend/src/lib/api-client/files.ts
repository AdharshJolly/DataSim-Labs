import {
  API_BASE_URL,
  apiRequest,
  assertResponseOk,
  fetchWithAuth,
} from "./core";
import type { DownloadListResponse } from "./types";

export function listDatasetFiles(
  datasetId: string,
): Promise<DownloadListResponse> {
  return apiRequest<DownloadListResponse>(
    `/api/v1/dataset/download/${datasetId}`,
  );
}

export function buildDownloadUrl(datasetId: string, format: string): string {
  const search = new URLSearchParams({ format });
  return `${API_BASE_URL}/api/v1/dataset/download/${datasetId}?${search.toString()}`;
}

export async function downloadDatasetFile(
  datasetId: string,
  format: string,
): Promise<{ blob: Blob; fileName: string }> {
  const search = new URLSearchParams({ format });
  const response = await fetchWithAuth(
    `${API_BASE_URL}/api/v1/dataset/download/${datasetId}?${search.toString()}`,
    {
      method: "GET",
    },
  );
  await assertResponseOk(response);

  const contentDisposition = response.headers.get("Content-Disposition") || "";
  const match = contentDisposition.match(/filename="?([^";]+)"?/i);
  const fallback = `dataset_${datasetId}.${format === "excel" ? "xlsx" : format === "jsonl" ? "jsonl" : format}`;
  return {
    blob: await response.blob(),
    fileName: match?.[1] || fallback,
  };
}

export async function streamDatasetCsv(
  datasetVersionId: string,
  rowCount: number,
  options?: {
    chunkSize?: number;
    seed?: number;
    onProgressBytes?: (bytesRead: number) => void;
  },
): Promise<{ blob: Blob; fileName: string }> {
  const params = new URLSearchParams({
    dataset_version_id: datasetVersionId,
    row_count: String(rowCount),
  });
  if (options?.chunkSize) {
    params.set("chunk_size", String(options.chunkSize));
  }
  if (typeof options?.seed === "number") {
    params.set("seed", String(options.seed));
  }

  const response = await fetchWithAuth(
    `${API_BASE_URL}/api/v1/dataset/stream?${params.toString()}`,
    {
      method: "GET",
    },
  );
  await assertResponseOk(response);

  const reader = response.body?.getReader();
  if (!reader) {
    return {
      blob: await response.blob(),
      fileName: `dataset_${datasetVersionId}_stream.csv`,
    };
  }

  const chunks: BlobPart[] = [];
  let bytesRead = 0;
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    if (value) {
      chunks.push(
        value.buffer.slice(
          value.byteOffset,
          value.byteOffset + value.byteLength,
        ),
      );
      bytesRead += value.byteLength;
      options?.onProgressBytes?.(bytesRead);
    }
  }

  const contentDisposition = response.headers.get("Content-Disposition") || "";
  const match = contentDisposition.match(/filename="?([^";]+)"?/i);

  return {
    blob: new Blob(chunks, { type: "text/csv" }),
    fileName: match?.[1] || `dataset_${datasetVersionId}_stream.csv`,
  };
}
