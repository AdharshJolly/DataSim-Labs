"use client";

import { FormEvent, useState } from "react";

import { createDataset } from "@/lib/api-client";

export default function CreateDatasetPage() {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [status, setStatus] = useState<string>("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const onSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!name.trim()) {
      setStatus("Dataset name is required.");
      return;
    }

    setIsSubmitting(true);
    setStatus("");
    try {
      const response = await createDataset({
        name: name.trim(),
        description: description.trim() || undefined,
      });
      localStorage.setItem("datasim:dataset_id", response.dataset_id);
      setStatus(`Created dataset: ${response.dataset_id}`);
    } catch (error) {
      setStatus(
        error instanceof Error ? error.message : "Failed to create dataset",
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <section className="space-y-5">
      <div className="space-y-2">
        <h1 className="text-3xl font-semibold">Create Dataset</h1>
        <p className="text-muted-foreground">
          Define dataset metadata and initialize a draft config.
        </p>
      </div>

      <form
        onSubmit={onSubmit}
        className="grid max-w-2xl gap-4 rounded-xl border bg-white/70 p-5"
      >
        <label className="space-y-1 text-sm font-medium">
          Dataset Name
          <input
            className="w-full rounded-md border border-border bg-white px-3 py-2"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="customer_profile_synthetic"
          />
        </label>

        <label className="space-y-1 text-sm font-medium">
          Description
          <textarea
            className="min-h-28 w-full rounded-md border border-border bg-white px-3 py-2"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Synthetic customer behavior dataset for experimentation"
          />
        </label>

        <button
          type="submit"
          disabled={isSubmitting}
          className="w-fit rounded-md bg-primary px-4 py-2 text-sm font-semibold text-white disabled:opacity-60"
        >
          {isSubmitting ? "Creating..." : "Create Dataset"}
        </button>

        {status ? (
          <p className="text-sm text-muted-foreground">{status}</p>
        ) : null}
      </form>
    </section>
  );
}
