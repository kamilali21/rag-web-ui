import { render, screen, within, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ComparisonResult } from "../comparison-result";
import { Insights } from "../insights";
import { ComparisonRun } from "@/lib/comparison";
import { api, ApiError } from "@/lib/api";
jest.mock("@/lib/api", () => ({ ...jest.requireActual("@/lib/api"), api: { get: jest.fn(), post: jest.fn() } }));
const evidence = { evidence_id: "E1", document_id: 1, knowledge_base_id: 7, scope: "private" as const,
  file_name: "Private study.pdf", page: 2, excerpt: "Synthetic supporting passage.", evidence_hash: "hash" };
const run = { id: 22, status: "complete", error_message: null, result: {
  documents: [{ id: 1, title: "Private study", scope: "private" }, { id: 2, title: "Public study", scope: "public" }],
  question: "Compare methods", notice: "Retrieved evidence only.",
  compatibility: { label: "Weakly related", explanation: "Different contexts.", citations: [evidence] },
  criteria: [{ criterion: "methodology", title: "Methodology", values: [
    { document_id: 1, unavailable: false, claims: [{ text: "<script>unsafe()</script> is document text.", citations: [evidence] }] },
    { document_id: 2, unavailable: true, claims: [] }]}] }} as ComparisonRun;
beforeEach(() => { jest.clearAllMocks(); window.history.replaceState(null, "", "/dashboard/insights"); });
test("comparison table shows claims, missing evidence, page links and auditable excerpts safely", async () => {
  render(<ComparisonResult run={run} />);
  expect(screen.getByRole("table", { name: "Evidence-backed research comparison" })).toBeInTheDocument();
  expect(screen.getByText("Not identified in retrieved evidence.")).toBeInTheDocument();
  expect(screen.getByText(/<script>unsafe/)).toBeInTheDocument();
  expect(document.querySelector("script")).toBeNull();
  expect(screen.getAllByRole("link", { name: "Open Private study.pdf, page 3" })[0]).toHaveAttribute("href", "/api/knowledge-base/7/documents/1/content?inline=true#page=3");
  await userEvent.click(screen.getByText("Inspect evidence snapshots (1)"));
  expect(screen.getByText("Synthetic supporting passage.")).toBeVisible();
  expect(screen.getByRole("link", { name: "Reopen saved comparison #22" })).toHaveAttribute("href", "/dashboard/insights?comparison=22");
});
test("saved run reload checks the API and never regenerates", async () => {
  window.history.replaceState(null, "", "/dashboard/insights?comparison=22");
  jest.mocked(api.get).mockImplementation(async url => url === "/api/insights/comparisons/22" ? run : url.startsWith("/api/departments") ? [] : { items: [], has_more: false });
  render(<Insights />);
  expect(await screen.findByRole("table", { name: "Evidence-backed research comparison" })).toBeInTheDocument();
  expect(api.get).toHaveBeenCalledWith("/api/insights/comparisons/22", expect.objectContaining({ cache: "no-store" }));
  expect(api.post).not.toHaveBeenCalled();
});
test("revoked saved source never reveals an old result and offers retry", async () => {
  window.history.replaceState(null, "", "/dashboard/insights?comparison=22");
  jest.mocked(api.get).mockImplementation(async url => { if (url === "/api/insights/comparisons/22") throw new ApiError(404, "Comparison unavailable"); return url.startsWith("/api/departments") ? [] : { items: [], has_more: false }; });
  render(<Insights />);
  expect(await screen.findByRole("alert")).toHaveTextContent("Comparison unavailable");
  expect(screen.queryByText("Private study")).not.toBeInTheDocument();
  await userEvent.click(screen.getByRole("button", { name: "Retry saved comparison" }));
  await waitFor(() => expect(jest.mocked(api.get).mock.calls.filter(([url]) => url === "/api/insights/comparisons/22")).toHaveLength(2));
});
test("insufficient and pending results are honest states", () => {
  const { rerender } = render(<ComparisonResult run={{ ...run, status: "processing", result: null }} />);
  expect(screen.getByRole("status")).toHaveTextContent("still processing");
  rerender(<ComparisonResult run={{ ...run, status: "insufficient_evidence" }} />);
  expect(screen.getByRole("status")).toHaveTextContent("insufficient retrieved evidence");
});
