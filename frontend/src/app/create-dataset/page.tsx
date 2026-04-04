import { redirect } from "next/navigation";
import { buildStudioUrl } from "@/lib/redirect-to-studio";

export default function CreateDatasetPage() {
  redirect(buildStudioUrl());
}
