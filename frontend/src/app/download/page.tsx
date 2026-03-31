"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import {
  ArrowLeft,
  Download,
  LoaderCircle,
  RefreshCw,
  FileText,
  AlertTriangle,
} from "lucide-react";

import {
  GeneratedFileInfo,
  downloadDatasetFile,
  listDatasetFiles,
} from "@/lib/api-client";
import { ValidationDashboard } from "@/components/studio/validation-dashboard";
import type { ValidationSummary } from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { useErrorNotifier } from "@/lib/use-error-notifier";

export default function DownloadPage() {
  const [datasetId, setDatasetId] = useState("");
  const [files, setFiles] = useState<GeneratedFileInfo[]>([]);
  const [status, setStatus] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const [validationSummary, setValidationSummary] =
    useState<ValidationSummary | null>(null);
  const [allowLowQualityDownloads, setAllowLowQualityDownloads] =
    useState(false);
  const { notifyError } = useErrorNotifier(setError);

  const hasFiles = useMemo(() => files.length > 0, [files.length]);
  const validationPassed = validationSummary?.passed ?? true;

  const loadFiles = async () => {
    if (!datasetId.trim()) {
      return;
    }

    setIsLoading(true);
    setStatus("");
    setError("");
    try {
      const response = await listDatasetFiles(datasetId.trim());
      setFiles(response.files);
      if (response.files.length === 0) {
        setStatus("No files generated for this dataset yet.");
      }
    } catch (err) {
      notifyError("Load Files Failed", err, "Failed to fetch generated files");
    } finally {
      setIsLoading(false);
    }
  };

  const onDownload = async (format: string) => {
    try {
      const { blob, fileName } = await downloadDatasetFile(
        datasetId.trim(),
        format,
      );
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = fileName;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(url);
    } catch (err) {
      notifyError("Download Failed", err, "Download failed");
    }
  };

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const datasetFromQuery = params.get("datasetId");
    if (datasetFromQuery) {
      setDatasetId(datasetFromQuery);
      return;
    }
    const stored = localStorage.getItem("datasim:dataset_id");
    if (stored) {
      setDatasetId(stored);
    }

    // Load cached validation summary if present
    try {
      const storedValidation = localStorage.getItem(
        "datasim:validation_summary",
      );
      if (storedValidation) {
        setValidationSummary(JSON.parse(storedValidation));
      }
    } catch {
      // ignore
    }
  }, []);

  useEffect(() => {
    if (!datasetId.trim()) {
      return;
    }
    void loadFiles();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [datasetId]);

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="font-display text-glow text-4xl font-bold tracking-tight">
            Downloads
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Retrieve your generated synthetic data artifacts.
          </p>
        </div>
        <Link
          href="/dashboard"
          className="group inline-flex items-center gap-2 font-medium text-muted-foreground transition-colors hover:text-foreground"
        >
          <ArrowLeft className="h-4 w-4 transition-transform group-hover:-translate-x-1" />
          Back to Dashboard
        </Link>
      </div>

      {/* Error / Status */}
      {error && (
        <Alert variant="destructive">
          <AlertTriangle className="h-5 w-5" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {/* Dataset Selector */}
      <Card className="max-w-xl space-y-4 rounded-xl border-border bg-card/70 p-6 backdrop-blur-sm">
        <div className="space-y-2">
          <label
            htmlFor="dataset-id"
            className="text-sm font-medium text-muted-foreground"
          >
            Dataset Identifier (UUID)
          </label>
          <div className="flex gap-2">
            <Input
              id="dataset-id"
              className="flex-1"
              value={datasetId}
              onChange={(e) => setDatasetId(e.target.value)}
              placeholder="e.g. 123e4567-e89b-12d3-a456-426614174000"
            />
            <Button
              type="button"
              variant="outline"
              disabled={isLoading || !datasetId.trim()}
              onClick={loadFiles}
            >
              {isLoading ? (
                <LoaderCircle className="h-4 w-4 animate-spin" />
              ) : (
                <RefreshCw className="h-4 w-4" />
              )}
            </Button>
          </div>
        </div>
        {status && !error && (
          <p className="text-sm text-muted-foreground">{status}</p>
        )}
      </Card>

      {/* Files Table */}
      {isLoading ? (
        <div className="flex h-64 flex-col items-center justify-center gap-4 text-muted-foreground">
          <LoaderCircle className="h-8 w-8 animate-spin text-primary" />
          <p className="font-medium">Searching for artifacts...</p>
        </div>
      ) : hasFiles ? (
        <Card className="overflow-hidden rounded-xl border-border bg-card/70 backdrop-blur-sm">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-border bg-card/70 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              <tr>
                <th className="px-6 py-4">Format</th>
                <th className="px-6 py-4">Filename</th>
                <th className="px-6 py-4">Size</th>
                <th className="px-6 py-4 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border/50">
              {files.map((file) => (
                <tr
                  key={file.file_name}
                  className="transition-colors hover:bg-card/70"
                >
                  <td className="px-6 py-4">
                    <Badge
                      variant="outline"
                      className="border-primary/30 bg-primary/10 text-primary uppercase tracking-tighter"
                    >
                      {file.format}
                    </Badge>
                  </td>
                  <td className="px-6 py-4 font-medium text-foreground">
                    <div className="flex items-center gap-2">
                      <FileText className="h-4 w-4 text-muted-foreground" />
                      {file.file_name}
                    </div>
                  </td>
                  <td className="px-6 py-4 text-muted-foreground">
                    {(file.size_bytes / 1024).toFixed(1)} KB
                  </td>
                  <td className="px-6 py-4 text-right">
                    <Button
                      type="button"
                      variant="cyber"
                      size="sm"
                      className="h-9 px-4 text-xs"
                      disabled={!validationPassed && !allowLowQualityDownloads}
                      onClick={() => void onDownload(file.format)}
                    >
                      <Download className="mr-1.5 h-3 w-3" />
                      Download
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      ) : null}

      {!validationPassed ? (
        <Alert>
          <AlertTriangle className="h-5 w-5" />
          <AlertDescription className="space-y-2">
            <p>
              Validation checks flagged this dataset as low-confidence. Review
              the dashboard before downloading.
            </p>
            <label className="inline-flex items-center gap-2 text-xs">
              <input
                type="checkbox"
                checked={allowLowQualityDownloads}
                onChange={(e) => setAllowLowQualityDownloads(e.target.checked)}
              />
              I understand the quality risk and want to continue.
            </label>
          </AlertDescription>
        </Alert>
      ) : datasetId.trim() && !isLoading && !hasFiles ? (
        <div className="flex flex-col items-center justify-center gap-4 rounded-xl border border-dashed border-border py-20 text-center">
          <div className="flex h-12 w-12 items-center justify-center rounded-full bg-muted/20 text-muted-foreground">
            <FileText className="h-6 w-6" />
          </div>
          <p className="text-muted-foreground">
            No files found for this dataset. Generate some first.
          </p>
          <Button asChild variant="cyber" className="h-10">
            <Link href={`/studio?datasetId=${datasetId}`}>Go to Studio</Link>
          </Button>
        </div>
      ) : null}

      {/* Validation Dashboard */}
      {validationSummary && <ValidationDashboard report={validationSummary} />}
    </div>
  );
}
