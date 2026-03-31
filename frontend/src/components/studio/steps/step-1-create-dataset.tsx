import Link from "next/link";
import { LoaderCircle } from "lucide-react";

import { Button } from "@/components/ui/button";

interface Step1CreateDatasetProps {
  dsName: string;
  dsDesc: string;
  busy: boolean;
  onNameChange: (value: string) => void;
  onDescriptionChange: (value: string) => void;
  onCreate: () => void;
}

export function Step1CreateDataset({
  dsName,
  dsDesc,
  busy,
  onNameChange,
  onDescriptionChange,
  onCreate,
}: Step1CreateDatasetProps) {
  return (
    <div>
      <header className="mb-8">
        <h1 className="font-display text-4xl font-bold">Start a New Dataset</h1>
        <p className="mt-2 text-muted-foreground">
          Give your synthetic dataset a name and describe what it represents.
          You&apos;ll define the fields next.
        </p>
      </header>

      <div className="max-w-lg space-y-6">
        <div className="space-y-2">
          <label
            htmlFor="ds-name"
            className="text-sm font-medium text-muted-foreground"
          >
            Dataset Name <span className="text-red-500">*</span>
          </label>
          <input
            id="ds-name"
            className="w-full"
            placeholder="e.g. Project Chimera"
            value={dsName}
            onChange={(e) => onNameChange(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && onCreate()}
            autoFocus
          />
        </div>

        <div className="space-y-2">
          <label
            htmlFor="ds-desc"
            className="text-sm font-medium text-muted-foreground"
          >
            Description (optional)
          </label>
          <textarea
            id="ds-desc"
            className="h-24 w-full resize-none"
            placeholder="What is this dataset for? Who will use it? What does it represent?"
            value={dsDesc}
            onChange={(e) => onDescriptionChange(e.target.value)}
          />
        </div>
      </div>

      <div className="mt-8 flex items-center gap-3">
        <Button
          type="button"
          variant="default"
          disabled={busy || !dsName.trim()}
          onClick={onCreate}
        >
          {busy ? (
            <span className="flex items-center justify-center gap-2">
              <LoaderCircle className="h-4 w-4 animate-spin" /> Creating…
            </span>
          ) : (
            "Create & Define Fields →"
          )}
        </Button>
        <Button asChild variant="outline">
          <Link href="/dashboard">Cancel</Link>
        </Button>
      </div>
    </div>
  );
}
