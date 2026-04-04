"use client";

import { DownloadPageView } from "./download-page-view";
import { useDownloadPage } from "./use-download-page";

export default function DownloadPage() {
  const state = useDownloadPage();
  return <DownloadPageView {...state} />;
}
