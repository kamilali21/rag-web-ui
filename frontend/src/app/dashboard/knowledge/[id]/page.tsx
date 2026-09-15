"use client";

import { useParams } from "next/navigation";
import DashboardLayout from "@/components/layout/dashboard-layout";
import { Library } from "@/components/knowledge-base/library";

// Added by ChatGPT: collection views reuse the same design with the original knowledge-base scope.
export default function KnowledgeBasePage() {
  const params = useParams();
  return <DashboardLayout><Library knowledgeBaseId={Number(params.id)} /></DashboardLayout>;
}
