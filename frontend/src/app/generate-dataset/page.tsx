"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { generateDataset, getGenerationStatus } from "@/lib/api-client";

type OutputFormat = "csv" | "json" | "excel";

const ALL_FORMATS: OutputFormat[] = ["csv", "json", "excel"];

export default function GenerateDatasetPage() {
  const [datasetId, setDatasetId] = useState("");
  const [datasetVersionId, setDatasetVersionId] = useState("");
  const [rowCount, setRowCount] = useState(1000);
  const [formats, setFormats] = useState<OutputFormat[]>(["csv"]);
  const [status, setStatus] = useState("");
  const [isRunning, setIsRunning] = useState(false);
  const [showAdvanced, setShowAdvanced] = useState(false);

  const wait = (ms: number) =>
    new Promise<void>((resolve) => {
      window.setTimeout(resolve, ms);
    });

  const pollGenerationStatus = async (
    jobId: string,
    currentDatasetId: string,
  ) => {
    for (let attempt = 0; attempt < 180; attempt += 1) {
      const result = await getGenerationStatus(jobId);
      if (result.status === "completed") {
        localStorage.setItem("datasim:last_generation", JSON.stringify(result));
        setStatus("Generation completed. Opening downloads...");
        window.setTimeout(() => {
          window.location.href = `/download?datasetId=${currentDatasetId}`;
        }, 700);
        return;
      }

      if (result.status === "failed") {
        throw new Error(result.message || "Dataset generation failed");
      }

      setStatus(result.message || "Generation in progress...");
      await wait(2000);
    }

    throw new Error(
      "Generation is taking longer than expected. Please retry shortly.",
    );
  };

  const toggleFormat = (format: OutputFormat) => {
    setFormats((prev) => {
      if (prev.includes(format)) {
        return prev.filter((item) => item !== format);
      }
      return [...prev, format];
    });
  };

  const onGenerate = async () => {
    if (!datasetId.trim()) {
      setStatus("Dataset id is required.");
      return;
    }
    if (formats.length === 0) {
      setStatus("Choose at least one output format.");
      return;
    }

    setIsRunning(true);
    setStatus("");
    try {
      const response = await generateDataset({
        dataset_id: datasetId.trim(),
        dataset_version_id: datasetVersionId.trim() || undefined,
        row_count: rowCount,
        formats,
        async_mode: true,
      });
      const currentDatasetId = datasetId.trim();
      localStorage.setItem("datasim:dataset_id", currentDatasetId);

      if (response.status === "completed") {
        localStorage.setItem(
          "datasim:last_generation",
          JSON.stringify(response),
        );
        setStatus("Generation completed. Opening downloads...");
        window.setTimeout(() => {
          window.location.href = `/download?datasetId=${currentDatasetId}`;
        }, 700);
      } else if (response.job_id) {
        setStatus("Generation queued. Preparing files...");
        await pollGenerationStatus(response.job_id, currentDatasetId);
      } else {
        throw new Error("Generation could not be started");
      }
    } catch (error) {
      setStatus(
        error instanceof Error ? error.message : "Dataset generation failed",
      );
    } finally {
      setIsRunning(false);
    }
  };

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const datasetFromQuery = params.get("datasetId");
    const versionFromQuery = params.get("datasetVersionId");
    if (datasetFromQuery) {
      setDatasetId(datasetFromQuery);
    }
    if (versionFromQuery) {
      setDatasetVersionId(versionFromQuery);
    }

    const stored = localStorage.getItem("datasim:dataset_id");
    if (stored && !datasetFromQuery) {
      setDatasetId(stored);
    }
  }, []);

  return (
    <section className="space-y-4">
      <div className="space-y-2">
        <h1 className="font-[var(--font-title)] text-3xl font-bold">
          Generate Dataset
        </h1>
        <p className="text-muted-foreground">
          Use the recommended defaults or fine-tune advanced options.
        </p>
      </div>

      <div className="flex flex-wrap gap-2">
        <Link href="/dashboard" className="sk-btn sk-btn-muted">
          Back to Dashboard
        </Link>
        <button
          type="button"
          className="sk-btn sk-btn-muted"
          onClick={() => setShowAdvanced((prev) => !prev)}
        >
          {showAdvanced ? "Hide Advanced Options" : "Show Advanced Options"}
        </button>
      </div>

      <div className="sk-panel grid max-w-3xl gap-4">
        {showAdvanced ? (
          <label className="space-y-1 text-sm font-medium">
            Dataset ID
            <input
              className="sk-input"
              value={datasetId}
              onChange={(e) => setDatasetId(e.target.value)}
              placeholder="Dataset selected from previous step"
            />
          </label>
        ) : null}

        {showAdvanced ? (
          <label className="space-y-1 text-sm font-medium">
            Dataset Version ID (optional)
            <input
              className="sk-input"
              value={datasetVersionId}
              onChange={(e) => setDatasetVersionId(e.target.value)}
              placeholder="Leave empty to use latest"
            />
          </label>
        ) : null}

        <label className="space-y-1 text-sm font-medium">
          Row Count (recommended: 1,000)
          <input
            type="number"
            min={1}
            max={10000000}
            className="sk-input"
            value={rowCount}
            onChange={(e) => setRowCount(Number(e.target.value || 1))}
          />
        </label>

        {showAdvanced ? (
          <fieldset className="space-y-2">
            <legend className="text-sm font-medium">Output Formats</legend>
            <div className="flex flex-wrap gap-3">
              {ALL_FORMATS.map((format) => (
                <label key={format} className="sk-chip flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={formats.includes(format)}
                    onChange={() => toggleFormat(format)}
                  />
                  <span className="text-sm uppercase">{format}</span>
                </label>
              ))}
            </div>
          </fieldset>
        ) : (
          <p className="text-sm text-muted-foreground">
            Output format: CSV (default). Enable advanced options to change
            format.
          </p>
        )}

        <button
          type="button"
          onClick={onGenerate}
          disabled={isRunning}
          className="sk-btn sk-btn-primary w-fit"
        >
          {isRunning ? "Generating..." : "Generate Dataset"}
        </button>

        {status ? (
          <p className="text-sm text-muted-foreground">{status}</p>
        ) : null}
      </div>
    </section>
  );
}
