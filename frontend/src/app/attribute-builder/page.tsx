import { redirect } from "next/navigation";

export default function AttributeBuilderPage({
  searchParams,
}: {
  searchParams?: { datasetId?: string };
}) {
  const datasetId = searchParams?.datasetId;
  redirect(
    datasetId
      ? `/studio?datasetId=${encodeURIComponent(datasetId)}`
      : "/studio",
  );
}
