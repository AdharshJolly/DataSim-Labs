"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import {
  AttributeConfig,
  DataType,
  DistributionType,
  getDatasetVersions,
  saveAttributes,
} from "@/lib/api-client";

const DATA_TYPES: DataType[] = [
  "integer",
  "float",
  "categorical",
  "boolean",
  "date",
  "text",
  "email",
  "name",
  "address",
];

const DISTRIBUTIONS: DistributionType[] = [
  "uniform",
  "normal",
  "skewed",
  "weighted_categorical",
];

function createDefaultAttribute(index: number): AttributeConfig {
  return {
    name: `field_${index + 1}`,
    type: "integer",
    description: "",
    constraints: { min: 0, max: 100 },
    distribution: "uniform",
    null_percentage: 0,
  };
}

export default function AttributeBuilderPage() {
  const [datasetId, setDatasetId] = useState("");
  const [attributes, setAttributes] = useState<AttributeConfig[]>([
    createDefaultAttribute(0),
  ]);
  const [availableVersions, setAvailableVersions] = useState<
    Array<{ id: string; version_number: number }>
  >([]);
  const [selectedVersionId, setSelectedVersionId] = useState("");
  const [status, setStatus] = useState("");
  const [isSaving, setIsSaving] = useState(false);
  const [isLoadingVersions, setIsLoadingVersions] = useState(false);

  const canSave = useMemo(
    () => datasetId.trim().length > 0 && attributes.length > 0 && !isSaving,
    [datasetId, attributes.length, isSaving],
  );

  const updateAttribute = <K extends keyof AttributeConfig>(
    index: number,
    key: K,
    value: AttributeConfig[K],
  ) => {
    setAttributes((prev) =>
      prev.map((item, i) => (i === index ? { ...item, [key]: value } : item)),
    );
  };

  useEffect(() => {
    const fromQuery = new URLSearchParams(window.location.search).get(
      "datasetId",
    );
    if (fromQuery) {
      setDatasetId(fromQuery);
      return;
    }
    const stored = localStorage.getItem("datasim:dataset_id");
    if (stored) {
      setDatasetId(stored);
    }
  }, []);

  const onLoadVersions = async () => {
    if (!datasetId.trim()) {
      setStatus("Dataset id is required to load versions.");
      return;
    }
    setIsLoadingVersions(true);
    try {
      const response = await getDatasetVersions(datasetId.trim());
      const versions = response.versions.map((version) => ({
        id: version.id,
        version_number: version.version_number,
      }));
      setAvailableVersions(versions);
      if (versions.length > 0) {
        const latest = response.versions[0];
        const configuredAttributes =
          (latest.config_json.attributes as AttributeConfig[] | undefined) ??
          [];
        if (configuredAttributes.length > 0) {
          setAttributes(configuredAttributes);
          setSelectedVersionId(latest.id);
          setStatus(`Loaded version ${latest.version_number} for editing.`);
        }
      } else {
        setStatus("No versions available yet. Create attributes to start v1.");
      }
    } catch (error) {
      setStatus(
        error instanceof Error ? error.message : "Failed to load versions",
      );
    } finally {
      setIsLoadingVersions(false);
    }
  };

  const onLoadSpecificVersion = async (versionId: string) => {
    if (!datasetId.trim() || !versionId) {
      return;
    }
    try {
      const response = await getDatasetVersions(datasetId.trim());
      const selected = response.versions.find(
        (version) => version.id === versionId,
      );
      if (!selected) {
        setStatus("Selected version not found.");
        return;
      }
      const configuredAttributes =
        (selected.config_json.attributes as AttributeConfig[] | undefined) ??
        [];
      if (configuredAttributes.length > 0) {
        setAttributes(configuredAttributes);
      }
      setSelectedVersionId(versionId);
      setStatus(`Loaded version ${selected.version_number} for editing.`);
    } catch (error) {
      setStatus(
        error instanceof Error
          ? error.message
          : "Failed to load selected version",
      );
    }
  };

  const updateConstraintsJson = (index: number, raw: string) => {
    try {
      const parsed = raw.trim()
        ? (JSON.parse(raw) as Record<string, unknown>)
        : {};
      updateAttribute(index, "constraints", parsed);
      setStatus("");
    } catch {
      setStatus("Invalid constraints JSON in one row.");
    }
  };

  const onSave = async () => {
    if (!canSave) {
      return;
    }

    setIsSaving(true);
    setStatus("");
    try {
      const payload = {
        dataset_id: datasetId.trim(),
        attributes: attributes.map((attr) => ({
          ...attr,
          name: attr.name.trim(),
        })),
      };
      const response = await saveAttributes(payload);
      localStorage.setItem("datasim:dataset_version_id", response.version_id);
      setSelectedVersionId(response.version_id);
      setStatus("Fields saved. Opening preview...");
      window.setTimeout(() => {
        window.location.href = `/dataset-preview?datasetVersionId=${response.version_id}`;
      }, 700);
    } catch (error) {
      setStatus(
        error instanceof Error ? error.message : "Failed to save attributes",
      );
    } finally {
      setIsSaving(false);
    }
  };

  useEffect(() => {
    if (!datasetId.trim()) {
      return;
    }
    void onLoadVersions();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [datasetId]);

  return (
    <section className="space-y-4">
      <div className="space-y-2">
        <h1 className="font-[var(--font-title)] text-3xl font-bold">
          Attribute Builder
        </h1>
        <p className="text-muted-foreground">
          Configure fields once, save, and continue to preview.
        </p>
      </div>

      <div className="flex flex-wrap gap-2">
        <Link href="/dashboard" className="sk-btn sk-btn-muted">
          Back to Dashboard
        </Link>
        {selectedVersionId ? (
          <Link
            href={`/dataset-preview?datasetVersionId=${selectedVersionId}`}
            className="sk-btn sk-btn-primary"
          >
            Continue to Preview
          </Link>
        ) : null}
      </div>

      <div className="sk-panel max-w-3xl">
        <label className="space-y-1 text-sm font-medium">
          Current Dataset
          <input
            className="sk-input"
            value={datasetId}
            onChange={(e) => setDatasetId(e.target.value)}
            placeholder="Dataset selected from previous step"
          />
        </label>
        <div className="mt-3 flex flex-wrap items-center gap-3">
          <button
            type="button"
            className="sk-btn sk-btn-muted"
            disabled={isLoadingVersions}
            onClick={() => void onLoadVersions()}
          >
            {isLoadingVersions ? "Loading..." : "Refresh Versions"}
          </button>
          {availableVersions.length > 0 ? (
            <select
              className="sk-select max-w-48"
              value={selectedVersionId}
              onChange={(e) => void onLoadSpecificVersion(e.target.value)}
            >
              <option value="">Select version</option>
              {availableVersions.map((version) => (
                <option key={version.id} value={version.id}>
                  v{version.version_number}
                </option>
              ))}
            </select>
          ) : null}
        </div>
      </div>

      <div className="sk-table-shell">
        <table className="sk-table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Type</th>
              <th>Description</th>
              <th>Distribution</th>
              <th>Null %</th>
              <th>Constraints (JSON)</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {attributes.map((attribute, index) => (
              <tr key={`${attribute.name}-${index}`}>
                <td>
                  <input
                    className="sk-input w-40"
                    value={attribute.name}
                    onChange={(e) =>
                      updateAttribute(index, "name", e.target.value)
                    }
                  />
                </td>
                <td>
                  <select
                    className="sk-select"
                    value={attribute.type}
                    onChange={(e) =>
                      updateAttribute(index, "type", e.target.value as DataType)
                    }
                  >
                    {DATA_TYPES.map((type) => (
                      <option key={type} value={type}>
                        {type}
                      </option>
                    ))}
                  </select>
                </td>
                <td>
                  <input
                    className="sk-input w-52"
                    value={attribute.description}
                    onChange={(e) =>
                      updateAttribute(index, "description", e.target.value)
                    }
                  />
                </td>
                <td>
                  <select
                    className="sk-select"
                    value={attribute.distribution}
                    onChange={(e) =>
                      updateAttribute(
                        index,
                        "distribution",
                        e.target.value as DistributionType,
                      )
                    }
                  >
                    {DISTRIBUTIONS.map((distribution) => (
                      <option key={distribution} value={distribution}>
                        {distribution}
                      </option>
                    ))}
                  </select>
                </td>
                <td>
                  <input
                    type="number"
                    min={0}
                    max={100}
                    className="sk-input w-20"
                    value={attribute.null_percentage}
                    onChange={(e) =>
                      updateAttribute(
                        index,
                        "null_percentage",
                        Number(e.target.value || 0),
                      )
                    }
                  />
                </td>
                <td>
                  <textarea
                    className="sk-textarea h-16 w-60 font-mono text-xs"
                    defaultValue={JSON.stringify(attribute.constraints)}
                    onBlur={(e) => updateConstraintsJson(index, e.target.value)}
                  />
                </td>
                <td>
                  <button
                    type="button"
                    className="sk-btn sk-btn-danger px-3 py-1.5"
                    onClick={() =>
                      setAttributes((prev) =>
                        prev.filter((_, i) => i !== index),
                      )
                    }
                  >
                    Remove
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="flex flex-wrap gap-3">
        <button
          type="button"
          className="sk-btn sk-btn-muted"
          onClick={() =>
            setAttributes((prev) => [
              ...prev,
              createDefaultAttribute(prev.length),
            ])
          }
        >
          Add Attribute
        </button>
        <button
          type="button"
          disabled={!canSave}
          className="sk-btn sk-btn-primary"
          onClick={onSave}
        >
          {isSaving ? "Saving..." : "Save Attributes"}
        </button>
      </div>

      {status ? (
        <p className="text-sm text-muted-foreground">{status}</p>
      ) : null}
    </section>
  );
}
