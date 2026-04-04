import { useCallback } from "react";

import type { AttrRow, OutputFormat } from "@/components/studio/types";
import { submitDatasetFeedback } from "@/lib/api-client";

interface ToastInput {
  title: string;
  message: string;
  intent?: "success" | "info" | "error";
  durationMs?: number;
}

interface UseFeedbackActionsArgs {
  datasetId: string;
  versionId: string;
  rowCount: number;
  formats: OutputFormat[];
  attrs: AttrRow[];
  feedbackRating: number;
  feedbackComment: string;
  generationSignature: string;
  setError: (value: string) => void;
  setFeedbackBusy: (value: boolean) => void;
  setFeedbackComment: (value: string) => void;
  pushToast: (toast: ToastInput) => void;
  notifyError: (title: string, error: unknown, fallback: string) => void;
}

export function useFeedbackActions({
  datasetId,
  versionId,
  rowCount,
  formats,
  attrs,
  feedbackRating,
  feedbackComment,
  generationSignature,
  setError,
  setFeedbackBusy,
  setFeedbackComment,
  pushToast,
  notifyError,
}: UseFeedbackActionsArgs) {
  const handleSubmitFeedback = useCallback(async () => {
    if (!datasetId || feedbackRating < 1) {
      setError("Select a rating before submitting feedback.");
      return;
    }

    setFeedbackBusy(true);
    setError("");
    try {
      await submitDatasetFeedback({
        dataset_id: datasetId,
        dataset_version_id: versionId || undefined,
        rating: feedbackRating,
        comment: feedbackComment.trim() || undefined,
        generation_signature: generationSignature || undefined,
        config_snapshot: {
          row_count: rowCount,
          formats,
          attribute_count: attrs.length,
        },
      });
      pushToast({
        title: "Feedback Submitted",
        message: "Thanks! Your rating was recorded for adaptive tuning.",
        intent: "success",
      });
      setFeedbackComment("");
    } catch (error) {
      notifyError(
        "Feedback Failed",
        error,
        "Unable to submit feedback right now.",
      );
    } finally {
      setFeedbackBusy(false);
    }
  }, [
    datasetId,
    feedbackRating,
    setError,
    setFeedbackBusy,
    versionId,
    feedbackComment,
    generationSignature,
    rowCount,
    formats,
    attrs.length,
    pushToast,
    setFeedbackComment,
    notifyError,
  ]);

  return { handleSubmitFeedback };
}
