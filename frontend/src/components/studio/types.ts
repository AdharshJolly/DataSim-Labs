import type { DataType, DistributionType } from "@/lib/api-client";

export type Step = 1 | 2 | 3 | 4;
export type OutputFormat = "csv" | "json" | "excel";

export interface AttrRow {
  _id: string;
  name: string;
  description: string;
  type: DataType;
  distribution: DistributionType;
  allow_nulls: boolean;
  null_percentage: number;
  min: string;
  max: string;
  categories: string;
  start_date: string;
  end_date: string;
}

export type AttrUpdate = <K extends keyof AttrRow>(
  i: number,
  key: K,
  val: AttrRow[K],
) => void;
