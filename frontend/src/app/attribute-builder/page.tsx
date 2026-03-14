"use client";

import { useEffect, useMemo, useState } from "react";

import {
  AttributeConfig,
  DataType,
  DistributionType,
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
  const [status, setStatus] = useState("");
  const [isSaving, setIsSaving] = useState(false);

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
    const stored = localStorage.getItem("datasim:dataset_id");
    if (stored) {
      setDatasetId(stored);
    }
  }, []);

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
      setStatus(
        `Saved ${response.attribute_count} attributes to version ${response.version_number}.`,
      );
    } catch (error) {
      setStatus(
        error instanceof Error ? error.message : "Failed to save attributes",
      );
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <section className="space-y-4">
      <div className="space-y-2">
        <h1 className="text-3xl font-semibold">Attribute Builder</h1>
        <p className="text-muted-foreground">
          Configure data types, constraints, distributions, and null rates.
        </p>
      </div>

      <div className="max-w-3xl rounded-lg border bg-white/70 p-4">
        <label className="space-y-1 text-sm font-medium">
          Dataset ID
          <input
            className="w-full rounded-md border border-border bg-white px-3 py-2"
            value={datasetId}
            onChange={(e) => setDatasetId(e.target.value)}
            placeholder="Paste dataset id from Create Dataset"
          />
        </label>
      </div>

      <div className="overflow-x-auto rounded-xl border bg-white/70">
        <table className="min-w-full text-sm">
          <thead className="bg-muted/60 text-left">
            <tr>
              <th className="px-3 py-2">Name</th>
              <th className="px-3 py-2">Type</th>
              <th className="px-3 py-2">Description</th>
              <th className="px-3 py-2">Distribution</th>
              <th className="px-3 py-2">Null %</th>
              <th className="px-3 py-2">Constraints (JSON)</th>
              <th className="px-3 py-2">Action</th>
            </tr>
          </thead>
          <tbody>
            {attributes.map((attribute, index) => (
              <tr key={`${attribute.name}-${index}`} className="border-t">
                <td className="px-3 py-2">
                  <input
                    className="w-40 rounded border border-border px-2 py-1"
                    value={attribute.name}
                    onChange={(e) =>
                      updateAttribute(index, "name", e.target.value)
                    }
                  />
                </td>
                <td className="px-3 py-2">
                  <select
                    className="rounded border border-border px-2 py-1"
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
                <td className="px-3 py-2">
                  <input
                    className="w-52 rounded border border-border px-2 py-1"
                    value={attribute.description}
                    onChange={(e) =>
                      updateAttribute(index, "description", e.target.value)
                    }
                  />
                </td>
                <td className="px-3 py-2">
                  <select
                    className="rounded border border-border px-2 py-1"
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
                <td className="px-3 py-2">
                  <input
                    type="number"
                    min={0}
                    max={100}
                    className="w-20 rounded border border-border px-2 py-1"
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
                <td className="px-3 py-2">
                  <textarea
                    className="h-16 w-60 rounded border border-border px-2 py-1 font-mono text-xs"
                    defaultValue={JSON.stringify(attribute.constraints)}
                    onBlur={(e) => updateConstraintsJson(index, e.target.value)}
                  />
                </td>
                <td className="px-3 py-2">
                  <button
                    type="button"
                    className="rounded border px-2 py-1"
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
          className="rounded-md border px-4 py-2 text-sm font-semibold"
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
          className="rounded-md bg-primary px-4 py-2 text-sm font-semibold text-white disabled:opacity-60"
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
