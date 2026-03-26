"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import {
  AlertTriangle,
  CheckCircle2,
  Download,
  LoaderCircle,
  Sparkles,
  UploadCloud,
} from "lucide-react";
import { AuthGuard } from "@/components/auth/auth-guard";
import { ThemedDropdown } from "@/components/ui/themed-dropdown";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  generateDataFromProfile,
  getDatasetVersions,
  listDatasets,
  uploadDatasetProfile,
  type DatasetProfile,
  type DatasetSummary,
  type DatasetVersionSummary,
  type ValidationSummary,
} from "@/lib/api-client";

function formatNumber(value: number | undefined): string {
  if (typeof value !== "number" || Number.isNaN(value)) return "-";
  return value.toLocaleString(undefined, { maximumFractionDigits: 2 });
}

function formatDate(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Unknown date";
  return date.toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

function getNewestVersion(
  versions: DatasetVersionSummary[],
): DatasetVersionSummary {
  return versions.reduce((latest, current) => {
    if (current.version_number > latest.version_number) return current;
    if (current.version_number < latest.version_number) return latest;
    return new Date(current.created_at) > new Date(latest.created_at)
      ? current
      : latest;
  });
}

const STRONG_CORRELATION_THRESHOLD = 0.8;
const MODERATE_CORRELATION_THRESHOLD = 0.5;

function getValidationStatusConfig(status: string | undefined): {
  label: string;
  classes: string;
} {
  if (status === "good") {
    return {
      label: "Good",
      classes:
        "border-green-500/40 bg-green-500/10 text-green-300",
    };
  }

  if (status === "acceptable") {
    return {
      label: "Acceptable",
      classes:
        "border-amber-500/40 bg-amber-500/10 text-amber-300",
    };
  }

  return {
    label: "Poor",
    classes: "border-red-500/40 bg-red-500/10 text-red-300",
  };
}

function getCorrelationStrengthLabel(strength: number | undefined): string {
  if (typeof strength !== "number" || Number.isNaN(strength)) {
    return "Unknown";
  }
  if (strength >= STRONG_CORRELATION_THRESHOLD) {
    return "Strong";
  }
  if (strength >= MODERATE_CORRELATION_THRESHOLD) {
    return "Moderate";
  }
  return "Weak";
}

export default function ProfileUploadPage() {
  const [datasets, setDatasets] = useState<DatasetSummary[]>([]);
  const [versions, setVersions] = useState<DatasetVersionSummary[]>([]);
  const [selectedDatasetId, setSelectedDatasetId] = useState("");
  const [selectedVersionId, setSelectedVersionId] = useState("");
  const [useLatestVersion, setUseLatestVersion] = useState(true);
  const [file, setFile] = useState<File | null>(null);
  const [profile, setProfile] = useState<DatasetProfile | null>(null);
  const [isLoadingDatasets, setIsLoadingDatasets] = useState(true);
  const [isLoadingVersions, setIsLoadingVersions] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState("");
  const [successMessage, setSuccessMessage] = useState("");
  const [generationRows, setGenerationRows] = useState(100);
  const [generationSeed, setGenerationSeed] = useState("");
  const [enableFeedbackLoop, setEnableFeedbackLoop] = useState(true);
  const [maxIterations, setMaxIterations] = useState(3);
  const [isGenerating, setIsGenerating] = useState(false);
  const [generatedData, setGeneratedData] = useState<Record<string, unknown>[]>(
    [],
  );
  const [validationSummary, setValidationSummary] =
    useState<ValidationSummary | null>(null);

  useEffect(() => {
    const loadDatasets = async () => {
      try {
        const response = await listDatasets();
        setDatasets(response.datasets ?? []);
      } catch (err) {
        setError(
          err instanceof Error ? err.message : "Failed to load datasets",
        );
      } finally {
        setIsLoadingDatasets(false);
      }
    };

    void loadDatasets();
  }, []);

  useEffect(() => {
    const loadVersions = async () => {
      if (!selectedDatasetId) {
        setVersions([]);
        setSelectedVersionId("");
        return;
      }

      setIsLoadingVersions(true);
      setError("");
      try {
        const response = await getDatasetVersions(selectedDatasetId);
        const nextVersions = response.versions ?? [];
        setVersions(nextVersions);

        if (nextVersions.length === 0) {
          setSelectedVersionId("");
          return;
        }

        const pickedDataset = datasets.find(
          (item) => item.id === selectedDatasetId,
        );
        const preferredVersion =
          nextVersions.find(
            (version) => version.id === pickedDataset?.latest_version_id,
          ) ?? getNewestVersion(nextVersions);
        setSelectedVersionId(preferredVersion.id);
      } catch (err) {
        setVersions([]);
        setSelectedVersionId("");
        setError(
          err instanceof Error
            ? err.message
            : "Failed to load dataset versions",
        );
      } finally {
        setIsLoadingVersions(false);
      }
    };

    void loadVersions();
  }, [selectedDatasetId, datasets]);

  useEffect(() => {
    if (!useLatestVersion || versions.length === 0) return;

    const pickedDataset = datasets.find(
      (item) => item.id === selectedDatasetId,
    );
    const preferredVersion =
      versions.find(
        (version) => version.id === pickedDataset?.latest_version_id,
      ) ?? getNewestVersion(versions);

    if (preferredVersion.id !== selectedVersionId) {
      setSelectedVersionId(preferredVersion.id);
    }
  }, [
    useLatestVersion,
    versions,
    datasets,
    selectedDatasetId,
    selectedVersionId,
  ]);

  const selectedDataset = datasets.find(
    (dataset) => dataset.id === selectedDatasetId,
  );
  const selectedVersion = versions.find(
    (version) => version.id === selectedVersionId,
  );

  const datasetOptions = datasets.map((dataset) => ({
    value: dataset.id,
    label: dataset.name,
    description: `${dataset.description?.trim() || "No description"} • Created ${formatDate(dataset.created_at)}`,
  }));

  const versionOptions = versions.map((version) => ({
    value: version.id,
    label: `Version ${version.version_number}`,
    description: `Created ${formatDate(version.created_at)}`,
  }));

  const handleUpload = async () => {
    if (!selectedDatasetId || !selectedVersionId || !file) {
      setError("Select a dataset, version, and file before uploading.");
      return;
    }

    setIsUploading(true);
    setError("");
    setSuccessMessage("");

    try {
      const response = await uploadDatasetProfile(selectedVersionId, file);
      setProfile(response.profile);
      setSuccessMessage("Profile learned successfully.");
      setGeneratedData([]);
      setValidationSummary(null);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Failed to upload and profile dataset",
      );
      setProfile(null);
    } finally {
      setIsUploading(false);
    }
  };

  const handleGenerateFromProfile = async () => {
    if (!selectedVersionId || !profile) {
      setError("Upload and learn a profile before generating data.");
      return;
    }

    if (generationRows < 1) {
      setError("Row count must be at least 1.");
      return;
    }

    setIsGenerating(true);
    setError("");
    try {
      const response = await generateDataFromProfile(selectedVersionId, {
        row_count: generationRows,
        seed: generationSeed.trim() === "" ? undefined : Number(generationSeed),
        enable_feedback_loop: enableFeedbackLoop,
        max_iterations: maxIterations,
      });
      setGeneratedData(response.data ?? []);
      setValidationSummary(response.validation_summary ?? null);
      pushToast({
        title: "Profile Generation Complete",
        message: `Generated ${response.rows} rows from learned profile.`,
        intent: "success",
      });
    } catch (err) {
      notifyError(
        "Generate from Profile Failed",
        err,
        "Failed to generate data from profile",
      );
    } finally {
      setIsGenerating(false);
    }
  };

  const downloadJson = () => {
    const blob = new Blob([JSON.stringify(generatedData, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `profile-generated-${selectedVersionId || "dataset"}.json`;
    anchor.click();
    URL.revokeObjectURL(url);
  };

  const downloadCsv = () => {
    if (generatedData.length === 0) return;
    const headers = Object.keys(generatedData[0] ?? {});
    const rows = generatedData.map((row) =>
      headers
        .map((header) => {
          const cell = row[header];
          const safe = String(cell ?? "").replace(/"/g, '""');
          return `"${safe}"`;
        })
        .join(","),
    );
    const csv = [headers.join(","), ...rows].join("\n");

    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `profile-generated-${selectedVersionId || "dataset"}.csv`;
    anchor.click();
    URL.revokeObjectURL(url);
  };

  const validationScore =
    validationSummary?.score ??
    (typeof validationSummary?.realism_score === "number"
      ? validationSummary.realism_score / 100
      : null);
  const validationStatus = validationSummary?.status;
  const validationStatusConfig = getValidationStatusConfig(validationStatus);

  return (
    <AuthGuard>
      <section className="space-y-8">
        <div className="space-y-3">
          <p className="inline-flex rounded-full border border-cyan-300/30 bg-cyan-400/10 px-3 py-1 text-xs font-semibold uppercase tracking-[0.14em] text-cyan-200">
            Profile Builder
          </p>
          <h1 className="font-display text-4xl font-bold tracking-tight text-foreground">
            Upload Real Dataset to Learn Profile
          </h1>
          <p className="max-w-3xl text-sm leading-relaxed text-muted-foreground">
            Choose a dataset and version, upload a real sample file, and
            generate statistical profile signals used to guide synthetic
            generation quality.
          </p>
        </div>

        <div className="rounded-2xl border border-border bg-gradient-to-br from-white/[0.06] via-white/[0.03] to-transparent p-6 shadow-xl shadow-black/20">
          <div className="grid gap-4 md:grid-cols-2">
            <div className="space-y-2">
              <label
                htmlFor="dataset-select"
                className="text-sm font-semibold text-foreground"
              >
                Dataset
              </label>
              <ThemedDropdown
                id="dataset-select"
                name="dataset"
                value={selectedDatasetId}
                options={datasetOptions}
                placeholder={
                  isLoadingDatasets ? "Loading datasets..." : "Select a dataset"
                }
                disabled={isLoadingDatasets || isUploading}
                onChange={(nextValue) => {
                  setSelectedDatasetId(nextValue);
                  setUseLatestVersion(true);
                  setProfile(null);
                  setSuccessMessage("");
                  setError("");
                }}
              />
              {selectedDataset && (
                <p className="text-xs text-muted-foreground">
                  {selectedDataset.description?.trim() || "No description"} •
                  Created {formatDate(selectedDataset.created_at)}
                </p>
              )}
            </div>

            <div className="space-y-2">
              <label
                htmlFor="version-select"
                className="text-sm font-semibold text-foreground"
              >
                Dataset Version
              </label>
              <ThemedDropdown
                id="version-select"
                name="datasetVersion"
                value={selectedVersionId}
                options={versionOptions}
                placeholder={
                  !selectedDatasetId
                    ? "Select a dataset first"
                    : isLoadingVersions
                      ? "Loading versions..."
                      : "Select a version"
                }
                disabled={
                  !selectedDatasetId ||
                  isLoadingVersions ||
                  isUploading ||
                  useLatestVersion
                }
                onChange={(nextValue) => {
                  setUseLatestVersion(false);
                  setSelectedVersionId(nextValue);
                  setProfile(null);
                  setSuccessMessage("");
                  setError("");
                }}
              />
              <label className="inline-flex items-center gap-2 text-xs text-muted-foreground">
                <input
                  type="checkbox"
                  name="useLatestVersion"
                  checked={useLatestVersion}
                  onChange={(event) =>
                    setUseLatestVersion(event.target.checked)
                  }
                  disabled={
                    !selectedDatasetId || isLoadingVersions || isUploading
                  }
                  className="h-4 w-4 rounded border-border"
                />
                Always use latest version
              </label>
              {selectedVersion && (
                <p className="text-xs text-muted-foreground">
                  Active: Version {selectedVersion.version_number} • Created{" "}
                  {formatDate(selectedVersion.created_at)}
                </p>
              )}
            </div>
          </div>

          <div className="mt-5 space-y-2">
            <label
              htmlFor="dataset-file"
              className="text-sm font-semibold text-foreground"
            >
              Dataset File
            </label>
            <Input
              id="dataset-file"
              name="datasetFile"
              type="file"
              accept=".csv,.json,.xls,.xlsx"
              onChange={(event) => {
                const nextFile = event.target.files?.[0] ?? null;
                setFile(nextFile);
                setProfile(null);
                setSuccessMessage("");
                setError("");
              }}
              disabled={isUploading}
            />
            <p className="text-xs text-muted-foreground">
              Supported formats: CSV, JSON, XLS, XLSX.
            </p>
          </div>

          {error && (
            <div className="mt-5 flex items-start gap-2 rounded-lg border border-destructive/50 bg-destructive/10 p-3 text-sm text-destructive">
              <AlertTriangle className="mt-0.5 h-4 w-4 flex-shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {successMessage && (
            <div className="mt-5 flex items-start gap-2 rounded-lg border border-green-400/40 bg-green-400/10 p-3 text-sm text-green-300">
              <CheckCircle2 className="mt-0.5 h-4 w-4 flex-shrink-0" />
              <span>{successMessage}</span>
            </div>
          )}

          <div className="mt-6 flex flex-wrap items-center gap-3">
            <Button
              type="button"
              onClick={() => void handleUpload()}
              disabled={isUploading || !selectedVersionId || !file}
            >
              {isUploading ? (
                <>
                  <LoaderCircle className="mr-2 h-4 w-4 animate-spin" />
                  Profiling...
                </>
              ) : (
                <>
                  <UploadCloud className="mr-2 h-4 w-4" />
                  Upload and Learn Profile
                </>
              )}
            </Button>

            {datasets.length === 0 && !isLoadingDatasets && (
              <Button asChild variant="outline">
                <Link href="/studio">
                  Create a Dataset First
                </Link>
              </Button>
            )}
          </div>
        </div>

        {profile && (
          <div className="space-y-5 rounded-2xl border border-border bg-white/[0.03] p-6">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <h2 className="font-display text-2xl font-bold text-foreground">
                Profile Preview
              </h2>
              <div className="flex flex-wrap items-center gap-2">
                <p className="rounded-full border border-border px-3 py-1 text-xs text-muted-foreground">
                  Rows analyzed: {profile.row_count.toLocaleString()}
                </p>
                <p className="rounded-full border border-border px-3 py-1 text-xs text-muted-foreground">
                  Confidence:{" "}
                  {profile.explainability?.meta?.confidence || "unknown"}
                </p>
              </div>
            </div>

            <div className="rounded-xl border border-cyan-400/20 bg-cyan-500/5 p-4">
              <h3 className="text-base font-semibold text-foreground">
                Generate Data from Profile
              </h3>
              <p className="mt-1 text-sm text-muted-foreground">
                Regenerate synthetic rows using learned distributions,
                dependencies, and optional feedback refinement.
              </p>

              <div className="mt-4 grid gap-4 md:grid-cols-2 lg:grid-cols-4">
                <div className="space-y-2">
                  <label className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                    Row Count
                  </label>
                  <Input
                    type="number"
                    min={1}
                    value={generationRows}
                    onChange={(event) =>
                      setGenerationRows(
                        Math.max(1, Number(event.target.value) || 1),
                      )
                    }
                    disabled={isGenerating}
                  />
                </div>

                <div className="space-y-2">
                  <label className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                    Seed (optional)
                  </label>
                  <Input
                    type="number"
                    value={generationSeed}
                    onChange={(event) => setGenerationSeed(event.target.value)}
                    disabled={isGenerating}
                    placeholder="Random"
                  />
                </div>

                <div className="space-y-2">
                  <label className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                    Max Iterations
                  </label>
                  <Input
                    type="number"
                    min={1}
                    max={10}
                    value={maxIterations}
                    onChange={(event) =>
                      setMaxIterations(
                        Math.min(
                          10,
                          Math.max(1, Number(event.target.value) || 1),
                        ),
                      )
                    }
                    disabled={isGenerating || !enableFeedbackLoop}
                  />
                </div>

                <div className="flex items-end pb-2">
                  <label className="inline-flex items-center gap-2 text-sm text-muted-foreground">
                    <input
                      type="checkbox"
                      checked={enableFeedbackLoop}
                      onChange={(event) =>
                        setEnableFeedbackLoop(event.target.checked)
                      }
                      disabled={isGenerating}
                      className="h-4 w-4 rounded border-border"
                    />
                    Enable feedback loop
                  </label>
                </div>
              </div>

              <div className="mt-4 flex flex-wrap items-center gap-3">
                <Button
                  type="button"
                  onClick={() => void handleGenerateFromProfile()}
                  disabled={isGenerating}
                >
                  {isGenerating ? (
                    <>
                      <LoaderCircle className="mr-2 h-4 w-4 animate-spin" />
                      Generating realistic data using learned profile...
                    </>
                  ) : (
                    <>
                      <Sparkles className="mr-2 h-4 w-4" />
                      Generate Data from Profile
                    </>
                  )}
                </Button>
              </div>
            </div>

            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
              {Object.entries(profile.columns).map(
                ([columnName, columnData]) => (
                  <article
                    key={columnName}
                    className="rounded-xl border border-border bg-background/30 p-4"
                  >
                    <h3 className="truncate text-base font-semibold text-foreground">
                      {columnName}
                    </h3>
                    <p className="mt-2 text-sm text-muted-foreground">
                      Type:{" "}
                      <span className="text-foreground">
                        {columnData.data_type}
                      </span>
                    </p>
                    {typeof columnData.unique_ratio === "number" && (
                      <p className="text-sm text-muted-foreground">
                        Unique Ratio:{" "}
                        <span className="text-foreground">
                          {formatNumber(columnData.unique_ratio)}
                        </span>
                      </p>
                    )}
                    <p className="text-sm text-muted-foreground">
                      Null Percentage:{" "}
                      <span className="text-foreground">
                        {formatNumber(columnData.null_percentage)}%
                      </span>
                    </p>
                    {columnData.distribution?.type && (
                      <p className="text-sm text-muted-foreground">
                        Distribution:{" "}
                        <span className="text-foreground">
                          {columnData.distribution.type}
                        </span>
                      </p>
                    )}
                    {columnData.data_type === "semantic" && (
                      <p className="text-sm text-muted-foreground">
                        Generator:{" "}
                        <span className="text-foreground">
                          {columnData.distribution?.generator || "faker.text"}
                        </span>
                      </p>
                    )}

                    {(columnData.data_type === "float" ||
                      columnData.data_type === "integer") && (
                      <div className="mt-3 rounded-lg border border-border/70 bg-white/[0.02] p-3 text-xs text-muted-foreground">
                        <p>
                          Mean: {formatNumber(columnData.distribution?.mean)}
                        </p>
                        <p>Std: {formatNumber(columnData.distribution?.std)}</p>
                        <p>Min: {formatNumber(columnData.distribution?.min)}</p>
                        <p>Max: {formatNumber(columnData.distribution?.max)}</p>
                      </div>
                    )}
                  </article>
                ),
              )}
            </div>

            <div>
              <h3 className="text-lg font-semibold text-foreground">
                Correlations and Dependencies
              </h3>
              {profile.dependency_graph &&
              profile.dependency_graph.length > 0 ? (
                <div className="mt-3 space-y-2">
                  {profile.dependency_graph.map((dependency, index) => (
                    <div
                      key={`${String(dependency.source || dependency.sources)}-${String(dependency.target || dependency.columns)}-${index}`}
                      className="rounded-lg border border-cyan-400/20 bg-cyan-400/10 p-3 text-sm"
                    >
                      <span className="font-semibold text-foreground">
                        {dependency.source ||
                          dependency.sources?.join(", ") ||
                          "multiple"}{" "}
                        →{" "}
                        {dependency.target ||
                          dependency.columns?.join(", ") ||
                          "multiple"}
                      </span>
                      <span className="text-muted-foreground">
                        {" "}
                        {dependency.type === "multivariate_copula"
                          ? `${getCorrelationStrengthLabel(
                              typeof dependency.strength === "number"
                                ? dependency.strength
                                : undefined,
                            )} correlation`
                          : dependency.type}
                      </span>
                      {typeof dependency.correlation === "number" && (
                        <span className="text-muted-foreground">
                          {" "}
                          (Correlation: {formatNumber(dependency.correlation)})
                        </span>
                      )}
                    </div>
                  ))}
                </div>
              ) : (
                <p className="mt-2 text-sm text-muted-foreground">
                  No strong correlations or dependencies detected.
                </p>
              )}
            </div>

            {generatedData.length > 0 && (
              <div className="space-y-3">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <h3 className="text-lg font-semibold text-foreground">
                    Generated Preview
                  </h3>
                  {validationScore !== null && (
                    <div className="flex flex-wrap items-center gap-2">
                      <span
                        className={`rounded-full border px-3 py-1 text-xs font-semibold ${validationStatusConfig.classes}`}
                      >
                        Validation: {validationStatusConfig.label}
                      </span>
                      <span className="rounded-full border border-border px-3 py-1 text-xs font-semibold text-foreground">
                        Score: {(validationScore * 100).toFixed(1)}%
                      </span>
                    </div>
                  )}
                  <div className="flex flex-wrap gap-2">
                    <Button
                      type="button"
                      variant="outline"
                      onClick={downloadCsv}
                    >
                      <Download className="mr-2 h-4 w-4" />
                      Download CSV
                    </Button>
                    <Button
                      type="button"
                      variant="outline"
                      onClick={downloadJson}
                    >
                      <Download className="mr-2 h-4 w-4" />
                      Download JSON
                    </Button>
                  </div>
                </div>

                <div className="overflow-x-auto rounded-xl border border-border">
                  <table className="min-w-full divide-y divide-border text-left text-sm">
                    <thead className="bg-background/50">
                      <tr>
                        {Object.keys(generatedData[0] ?? {}).map((key) => (
                          <th
                            key={key}
                            className="whitespace-nowrap px-3 py-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground"
                          >
                            {key}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border">
                      {generatedData.slice(0, 10).map((row, rowIndex) => (
                        <tr key={`generated-row-${rowIndex}`}>
                          {Object.keys(generatedData[0] ?? {}).map((key) => (
                            <td
                              key={`${rowIndex}-${key}`}
                              className="whitespace-nowrap px-3 py-2 text-muted-foreground"
                            >
                              {String(row[key] ?? "")}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        )}
      </section>
    </AuthGuard>
  );
}
