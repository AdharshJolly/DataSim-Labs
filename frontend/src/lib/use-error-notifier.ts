"use client";

import { useFeedback } from "@/components/ui/feedback-provider";

export function useErrorNotifier(setError: (message: string) => void) {
  const { pushToast, showErrorDialog } = useFeedback();

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

  return { notifyError };
}
