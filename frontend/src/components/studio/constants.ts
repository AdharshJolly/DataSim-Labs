import type { DataType, DistributionType } from "@/lib/api-client";
import {
  Hash,
  Binary,
  ListFilter,
  ToggleLeft,
  Calendar,
  Type,
  Mail,
  User,
  MapPin,
  FileText,
  Database,
  FileSpreadsheet,
  FileJson,
} from "lucide-react";
import type { OutputFormat } from "./types";

export const STEP_LABELS: [string, string][] = [
  ["1", "Setup"],
  ["2", "Define Fields"],
  ["3", "Preview & Refine"],
  ["4", "Generate"],
];

export const TYPE_OPTIONS = [
  {
    category: "Basic",
    options: [
      { value: "integer" as DataType, label: "Integer", icon: Hash, description: "Whole numbers only" },
      { value: "float" as DataType, label: "Decimal", icon: Binary, description: "Numbers with decimal points" },
      { value: "boolean" as DataType, label: "True/False", icon: ToggleLeft, description: "Yes/No, 1/0, True/False" },
      { value: "categorical" as DataType, label: "Category", icon: ListFilter, description: "Pick from a list of values" },
    ]
  },
  {
    category: "Identity",
    options: [
      { value: "name" as DataType, label: "Full Name", icon: User, description: "Realistic first and last names" },
      { value: "email" as DataType, label: "Email", icon: Mail, description: "Randomized valid email addresses" },
      { value: "address" as DataType, label: "Address", icon: MapPin, description: "Street, city, and zip codes" },
    ]
  },
  {
    category: "Temporal & Content",
    options: [
      { value: "date" as DataType, label: "Date", icon: Calendar, description: "Calendar dates and timestamps" },
      { value: "text" as DataType, label: "Text", icon: Type, description: "Random words or sentences" },
    ]
  },
];

// Flattened version for easy lookup
export const ALL_TYPE_OPTIONS = TYPE_OPTIONS.flatMap(group => group.options);

export const DIST_OPTIONS: { value: DistributionType; label: string }[] = [
  { value: "uniform", label: "Uniform" },
  { value: "normal", label: "Normal" },
  { value: "skewed", label: "Skewed" },
  { value: "weighted_categorical", label: "Weighted" },
];

export const FORMAT_OPTIONS = [
  { value: "csv" as OutputFormat, label: "CSV", ext: ".csv", icon: FileText },
  { value: "json" as OutputFormat, label: "JSON", ext: ".json", icon: Database },
  { value: "jsonl" as OutputFormat, label: "JSONL", ext: ".jsonl", icon: FileJson },
  { value: "excel" as OutputFormat, label: "Excel", ext: ".xlsx", icon: FileSpreadsheet },
];

export const NUMERIC_TYPES: DataType[] = ["integer", "float"];
export const DIST_TYPES: DataType[] = ["integer", "float", "categorical"];
