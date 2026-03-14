"use client";

import { useEffect, useState } from "react";

import { generateDataset } from "@/lib/api-client";

type OutputFormat = "csv" | "json" | "excel";

const ALL_FORMATS: OutputFormat[] = ["csv", "json", "excel"];

export default function GenerateDatasetPage() {
  const [datasetId, setDatasetId] = useState("");
  const [rowCount, setRowCount] = useState(1000);
  const [formats, setFormats] = useState<OutputFormat[]>(["csv"]);
  const [status, setStatus] = useState("");
  const [isRunning, setIsRunning] = useState(false);

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
        row_count: rowCount,
        formats,
      });
      localStorage.setItem("datasim:last_generation", JSON.stringify(response));
      setStatus(`Generation completed. ${response.files.length} files ready.`);
    } catch (error) {
      setStatus(
        error instanceof Error ? error.message : "Dataset generation failed",
      );
    } finally {
      setIsRunning(false);
    }
  };

  useEffect(() => {
    const stored = localStorage.getItem("datasim:dataset_id");
    if (stored) {
      setDatasetId(stored);
    }
  }, []);

  return (
    <section className="space-y-4">
      <div className="space-y-2">
        <h1 className="text-3xl font-semibold">Generate Dataset</h1>
        <p className="text-muted-foreground">
          Run large generation jobs and monitor job progress.
        </p>
      </div>

      <div className="grid max-w-3xl gap-4 rounded-xl border bg-white/70 p-5">
        <label className="space-y-1 text-sm font-medium">
          Dataset ID
          <input
            className="w-full rounded-md border border-border bg-white px-3 py-2"
            value={datasetId}
            onChange={(e) => setDatasetId(e.target.value)}
            placeholder="Paste dataset id"
          />
        </label>

        <label className="space-y-1 text-sm font-medium">
          Row Count
          <input
            type="number"
            min={1}
            max={10000000}
            className="w-full rounded-md border border-border bg-white px-3 py-2"
            value={rowCount}
            onChange={(e) => setRowCount(Number(e.target.value || 1))}
          />
        </label>

        <fieldset className="space-y-2">
          <legend className="text-sm font-medium">Output Formats</legend>
          <div className="flex flex-wrap gap-3">
            {ALL_FORMATS.map((format) => (
              <label
                key={format}
                className="flex items-center gap-2 rounded border px-3 py-2"
              >
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

        <button
          type="button"
          onClick={onGenerate}
          disabled={isRunning}
          className="w-fit rounded-md bg-primary px-4 py-2 text-sm font-semibold text-white disabled:opacity-60"
        >
          {isRunning ? "Generating..." : "Start Generation"}
        </button>

        {status ? (
          <p className="text-sm text-muted-foreground">{status}</p>
        ) : null}
      </div>
    </section>
  );
}
