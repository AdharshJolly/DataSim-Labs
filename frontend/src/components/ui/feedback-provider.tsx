"use client";

import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { AlertTriangle, CheckCircle2, Info, X } from "lucide-react";

type ToastIntent = "error" | "success" | "info";

interface ToastItem {
  id: string;
  title: string;
  message: string;
  intent: ToastIntent;
}

interface ErrorDialogState {
  title: string;
  message: string;
  details?: string;
}

interface FeedbackContextValue {
  pushToast: (input: {
    title: string;
    message: string;
    intent?: ToastIntent;
    durationMs?: number;
  }) => void;
  showErrorDialog: (input: ErrorDialogState) => void;
  closeErrorDialog: () => void;
}

const FeedbackContext = createContext<FeedbackContextValue | null>(null);

function intentStyles(intent: ToastIntent): string {
  if (intent === "success") {
    return "border-green-400/40 bg-green-500/15 text-green-100";
  }
  if (intent === "error") {
    return "border-destructive/50 bg-destructive/20 text-red-100";
  }
  return "border-cyan-400/40 bg-cyan-500/15 text-cyan-100";
}

function intentIcon(intent: ToastIntent) {
  if (intent === "success") {
    return <CheckCircle2 className="mt-0.5 h-4 w-4 flex-shrink-0" />;
  }
  if (intent === "error") {
    return <AlertTriangle className="mt-0.5 h-4 w-4 flex-shrink-0" />;
  }
  return <Info className="mt-0.5 h-4 w-4 flex-shrink-0" />;
}

export function FeedbackProvider({ children }: { children: ReactNode }) {
  const enableToasts = process.env.NEXT_PUBLIC_ENABLE_ERROR_TOAST !== "false";
  const enableDialogs = process.env.NEXT_PUBLIC_ENABLE_ERROR_DIALOG !== "false";
  const [toasts, setToasts] = useState<ToastItem[]>([]);
  const [dialog, setDialog] = useState<ErrorDialogState | null>(null);

  const pushToast: FeedbackContextValue["pushToast"] = useCallback(
    ({ title, message, intent = "info", durationMs = 4500 }) => {
      if (!enableToasts) {
        return;
      }
      const id = `${Date.now()}-${Math.random().toString(36).slice(2)}`;
      setToasts((prev) => [...prev, { id, title, message, intent }]);
      window.setTimeout(() => {
        setToasts((prev) => prev.filter((toast) => toast.id !== id));
      }, durationMs);
    },
    [enableToasts],
  );

  const showErrorDialog = useCallback(
    (input: ErrorDialogState) => {
      if (!enableDialogs) {
        return;
      }
      setDialog(input);
    },
    [enableDialogs],
  );

  const closeErrorDialog = useCallback(() => {
    setDialog(null);
  }, []);

  const contextValue = useMemo<FeedbackContextValue>(
    () => ({ pushToast, showErrorDialog, closeErrorDialog }),
    [pushToast, showErrorDialog, closeErrorDialog],
  );

  return (
    <FeedbackContext.Provider value={contextValue}>
      {children}

      <div className="pointer-events-none fixed right-4 top-24 z-[120] flex w-[min(92vw,24rem)] flex-col gap-2">
        {toasts.map((toast) => (
          <div
            key={toast.id}
            className={`pointer-events-auto rounded-lg border p-3 shadow-lg backdrop-blur-sm ${intentStyles(toast.intent)}`}
            role="status"
            aria-live="polite"
          >
            <div className="flex items-start gap-2">
              {intentIcon(toast.intent)}
              <div className="min-w-0 flex-1">
                <p className="text-sm font-semibold">{toast.title}</p>
                <p className="mt-1 text-xs leading-relaxed opacity-90">
                  {toast.message}
                </p>
              </div>
              <button
                type="button"
                className="rounded p-1 opacity-80 transition hover:opacity-100"
                onClick={() =>
                  setToasts((prev) =>
                    prev.filter((item) => item.id !== toast.id),
                  )
                }
                aria-label="Dismiss notification"
              >
                <X className="h-3.5 w-3.5" />
              </button>
            </div>
          </div>
        ))}
      </div>

      {dialog && (
        <div className="fixed inset-0 z-[130] flex items-center justify-center bg-black/60 p-4">
          <div
            className="w-full max-w-lg rounded-xl border border-destructive/50 bg-background p-5 shadow-2xl"
            role="dialog"
            aria-modal="true"
            aria-label={dialog.title}
          >
            <div className="flex items-start gap-3">
              <AlertTriangle className="mt-0.5 h-5 w-5 text-destructive" />
              <div className="min-w-0 flex-1">
                <h3 className="text-base font-semibold text-foreground">
                  {dialog.title}
                </h3>
                <p className="mt-2 text-sm text-muted-foreground">
                  {dialog.message}
                </p>
                {dialog.details ? (
                  <pre className="mt-3 max-h-40 overflow-auto rounded border border-border bg-muted/40 p-2 text-[11px] leading-relaxed text-muted-foreground">
                    {dialog.details}
                  </pre>
                ) : null}
              </div>
            </div>
            <div className="mt-4 flex justify-end">
              <button
                type="button"
                className="rounded-md border border-border bg-background px-3 py-1.5 text-sm font-medium text-foreground transition hover:bg-muted"
                onClick={closeErrorDialog}
              >
                Got it
              </button>
            </div>
          </div>
        </div>
      )}
    </FeedbackContext.Provider>
  );
}

export function useFeedback(): FeedbackContextValue {
  const context = useContext(FeedbackContext);
  if (!context) {
    throw new Error("useFeedback must be used inside FeedbackProvider");
  }
  return context;
}
