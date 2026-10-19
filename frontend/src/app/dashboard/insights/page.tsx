import DashboardLayout from "@/components/layout/dashboard-layout";
import { Insights } from "@/components/insights/insights";

// Catalog-backed discovery; generation and persisted analysis have later phase gates.
export default function InsightsPage() {
  return <DashboardLayout><Insights /></DashboardLayout>;
}
