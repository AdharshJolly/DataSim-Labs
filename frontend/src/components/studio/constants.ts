import type { DataType, DistributionType } from "@/lib/api-client";
import type { OutputFormat } from "./types";

export const STEP_LABELS: [string, string][] = [
  ["1", "Setup"],
  ["2", "Define Fields"],
  ["3", "Preview & Refine"],
  ["4", "Generate"],
];

export const TYPE_OPTIONS: { value: DataType; label: string; icon: string }[] =
  [
    { value: "integer", label: "Integer", icon: "#" },
    { value: "float", label: "Decimal", icon: "~" },
    { value: "categorical", label: "Category", icon: "≡" },
    { value: "boolean", label: "True/False", icon: "◎" },
    { value: "date", label: "Date", icon: "▦" },
    { value: "text", label: "Text", icon: "T" },
    { value: "email", label: "Email", icon: "@" },
    { value: "name", label: "Full Name", icon: "✦" },
    { value: "address", label: "Address", icon: "⌂" },
  ];

export const DIST_OPTIONS: { value: DistributionType; label: string }[] = [
  { value: "uniform", label: "Uniform" },
  { value: "normal", label: "Normal" },
  { value: "skewed", label: "Skewed" },
  { value: "weighted_categorical", label: "Weighted" },
];

export const FORMAT_OPTIONS: {
  value: OutputFormat;
  label: string;
  ext: string;
}[] = [
  { value: "csv", label: "CSV", ext: ".csv" },
  { value: "json", label: "JSON", ext: ".json" },
  { value: "excel", label: "Excel", ext: ".xlsx" },
];

export const NUMERIC_TYPES: DataType[] = ["integer", "float"];
export const DIST_TYPES: DataType[] = ["integer", "float", "categorical"];
