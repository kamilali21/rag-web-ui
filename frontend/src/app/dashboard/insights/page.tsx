import DashboardLayout from "@/components/layout/dashboard-layout";
import { Insights } from "@/components/insights/insights";

// Added by ChatGPT: Insights is a local-only workspace inside the existing dashboard.
export default function InsightsPage() {
  return <DashboardLayout><Insights /></DashboardLayout>;
}
