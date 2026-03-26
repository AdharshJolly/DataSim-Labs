"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import {
  AlertTriangle,
  CheckCircle2,
  LoaderCircle,
  UploadCloud,
} from "lucide-react";
import { AuthGuard } from "@/components/auth/auth-guard";
import { ThemedDropdown } from "@/components/ui/themed-dropdown";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  getDatasetVersions,
  listDatasets,
  uploadDatasetProfile,
  type DatasetProfile,
  type DatasetSummary,
  type DatasetVersionSummary,
} from "@/lib/api-client";
import { useFeedback } from "@/components/ui/feedback-provider";

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

export default function ProfileUploadPage() {
  const { pushToast, showErrorDialog } = useFeedback();
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

  const notifyError = (title: string, err: unknown, fallback: string) => {
    const message = err instanceof Error ? err.message : fallback;
    setError(message);
    pushToast({ title, message, intent: "error" });
    showErrorDialog({
      title,
      message,
      details: err instanceof Error ? err.stack : undefined,
    });
  };

  useEffect(() => {
    const loadDatasets = async () => {
      try {
        const response = await listDatasets();
        setDatasets(response.datasets ?? []);
      } catch (err) {
        notifyError("Load Datasets Failed", err, "Failed to load datasets");
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
        notifyError(
          "Load Versions Failed",
          err,
          "Failed to load dataset versions",
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
    } catch (err) {
      notifyError(
        "Profile Upload Failed",
        err,
        "Failed to upload and profile dataset",
      );
      setProfile(null);
    } finally {
      setIsUploading(false);
    }
  };

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
                <Link href="/studio">Create a Dataset First</Link>
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
              <p className="rounded-full border border-border px-3 py-1 text-xs text-muted-foreground">
                Rows analyzed: {profile.row_count.toLocaleString()}
              </p>
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

                    {(columnData.data_type === "float" ||
                      columnData.data_type === "integer") && (
                      <div className="mt-3 rounded-lg border border-border/70 bg-white/[0.02] p-3 text-xs text-muted-foreground">
                        <p>
                          Mean: {formatNumber(columnData.distribution?.mean)}
                        </p>
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
                      key={`${dependency.source}-${dependency.target}-${index}`}
                      className="rounded-lg border border-cyan-400/20 bg-cyan-400/10 p-3 text-sm"
                    >
                      <span className="font-semibold text-foreground">
                        {dependency.source} → {dependency.target}
                      </span>
                      <span className="text-muted-foreground">
                        {" "}
                        {dependency.type}
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
          </div>
        )}
      </section>
    </AuthGuard>
  );
}
