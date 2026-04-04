import { redirect } from "next/navigation";
import { buildStudioUrl } from "@/lib/redirect-to-studio";

export default function GenerateDatasetPage({
  searchParams,
}: {
  searchParams?: { datasetId?: string };
}) {
  const datasetId = searchParams?.datasetId;
  redirect(buildStudioUrl(datasetId));
}
