export function buildStudioUrl(datasetId?: string): string {
  return datasetId
    ? `/studio?datasetId=${encodeURIComponent(datasetId)}`
    : "/studio";
}
