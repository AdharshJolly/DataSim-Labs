export function resolveGenerationMode(
  rowCount: number,
  attributeCount: number,
  autoAsyncRowThreshold: number,
  autoAsyncCellThreshold: number,
  requiresAsyncFromPreflight: boolean,
) {
  const estimatedCells = rowCount * Math.max(1, attributeCount);
  const useAsyncGeneration =
    rowCount >= autoAsyncRowThreshold ||
    estimatedCells >= autoAsyncCellThreshold;

  return {
    estimatedCells,
    useAsyncGeneration,
    shouldUseAsyncGeneration: useAsyncGeneration || requiresAsyncFromPreflight,
  };
}
