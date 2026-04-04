import { useState } from "react";

import type { GenerationPreflightResponse } from "@/lib/api-client";
import type { OutputFormat } from "@/lib/studio-constants";

export interface GenerationSetupHookState {
  rowCount: number;
  setRowCount: (value: number) => void;
  formats: OutputFormat[];
  setFormats: (formats: OutputFormat[]) => void;
  seed: string;
  setSeed: (value: string) => void;
  driftEnabled: boolean;
  setDriftEnabled: (value: boolean) => void;
  driftIntensity: number;
  setDriftIntensity: (value: number) => void;
  driftColumnsText: string;
  setDriftColumnsText: (value: string) => void;
  preflightResult: GenerationPreflightResponse | null;
  setPreflightResult: (value: GenerationPreflightResponse | null) => void;
  preflightBusy: boolean;
  setPreflightBusy: (value: boolean) => void;
  toggleFormat: (format: OutputFormat) => void;
}

export function useGenerationSetup(): GenerationSetupHookState {
  const [rowCount, setRowCount] = useState(1000);
  const [formats, setFormats] = useState<OutputFormat[]>(["csv"]);
  const [seed, setSeed] = useState("");
  const [driftEnabled, setDriftEnabled] = useState(false);
  const [driftIntensity, setDriftIntensity] = useState(0.1);
  const [driftColumnsText, setDriftColumnsText] = useState("");
  const [preflightResult, setPreflightResult] =
    useState<GenerationPreflightResponse | null>(null);
  const [preflightBusy, setPreflightBusy] = useState(false);

  const toggleFormat = (format: OutputFormat) => {
    setFormats((prev) =>
      prev.includes(format)
        ? prev.filter((value) => value !== format)
        : [...prev, format],
    );
  };

  return {
    rowCount,
    setRowCount,
    formats,
    setFormats,
    seed,
    setSeed,
    driftEnabled,
    setDriftEnabled,
    driftIntensity,
    setDriftIntensity,
    driftColumnsText,
    setDriftColumnsText,
    preflightResult,
    setPreflightResult,
    preflightBusy,
    setPreflightBusy,
    toggleFormat,
  };
}
