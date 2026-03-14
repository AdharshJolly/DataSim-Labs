"use client";

import Link from "next/link";
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
      setStatus("Dataset created. Moving to field setup...");
      window.setTimeout(() => {
        window.location.href = `/attribute-builder?datasetId=${response.dataset_id}`;
      }, 700);
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
        <h1 className="font-[var(--font-title)] text-3xl font-bold">
          Create a New Dataset
        </h1>
        <p className="text-muted-foreground">
          Start with a name and optional description. We will guide you through
          the next steps automatically.
        </p>
      </div>

      <div className="flex flex-wrap gap-2">
        <Link href="/dashboard" className="sk-btn sk-btn-muted">
          Back to Dashboard
        </Link>
      </div>

      <form onSubmit={onSubmit} className="sk-panel grid max-w-2xl gap-4">
        <label className="space-y-1 text-sm font-medium">
          Dataset Name
          <input
            className="sk-input"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="customer_profile_synthetic"
          />
        </label>

        <label className="space-y-1 text-sm font-medium">
          Description
          <textarea
            className="sk-textarea min-h-28"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Synthetic customer behavior dataset for experimentation"
          />
        </label>

        <button
          type="submit"
          disabled={isSubmitting}
          className="sk-btn sk-btn-primary w-fit"
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
