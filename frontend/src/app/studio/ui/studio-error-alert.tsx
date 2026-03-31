"use client";

import { AlertTriangle, X } from "lucide-react";

import { Alert, AlertDescription } from "@/components/ui/alert";

type StudioErrorAlertProps = {
  error: string;
  onDismiss: () => void;
};

export function StudioErrorAlert({ error, onDismiss }: StudioErrorAlertProps) {
  if (!error) {
    return null;
  }

  return (
    <Alert variant="destructive" className="mb-6">
      <AlertTriangle className="h-5 w-5" />
      <AlertDescription className="flex items-center justify-between">
        <span>{error}</span>
        <button
          type="button"
          onClick={onDismiss}
          className="rounded-full p-1 transition-colors hover:bg-destructive/20"
          aria-label="Dismiss error"
        >
          <X className="h-4 w-4" />
        </button>
      </AlertDescription>
    </Alert>
  );
}
