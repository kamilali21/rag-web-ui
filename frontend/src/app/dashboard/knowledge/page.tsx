import DashboardLayout from "@/components/layout/dashboard-layout";
import { Library } from "@/components/knowledge-base/library";

// Added by ChatGPT: keep the original URL while presenting documents in the reference Library.
export default function KnowledgeBasePage() {
  return <DashboardLayout><Library /></DashboardLayout>;
}
