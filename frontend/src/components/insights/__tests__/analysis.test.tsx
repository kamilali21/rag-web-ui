import { act, render, screen, within, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AnalysisWorkflow } from "../analysis-workflow";
import { AnalysisResult } from "../analysis-result";
import { Insights } from "../insights";
import { AnalysisRun, lastAnalysisKey } from "@/lib/research-analysis";
import { InsightsDocument } from "@/lib/insights";
import { api, ApiError } from "@/lib/api";
jest.mock("@/lib/api", () => ({ ...jest.requireActual("@/lib/api"), api: { get: jest.fn(), post: jest.fn() } }));
const paper = { id: 4, knowledge_base_id: 8, scope: "private", title: "Irrigation study", authors_text: "Researcher" } as InsightsDocument;
const evidence = { evidence_id: "E1", document_id: 4, knowledge_base_id: 8, scope: "private" as const, file_name: "Study.pdf", page: 1, excerpt: "Water use reduced.", evidence_hash: "hash" };
const section = { key: "summary", title: "Overall summary", claims: [{ text: "<script>alert(1)</script> is untrusted document text.", citations: [evidence] }] };
const run: AnalysisRun = { id: 30, status: "complete", error_message: null, result: {
  documents: [{ ...paper, role: "selected" }], profiles: [{ document_id: 4, fields: [section] }],
  sections: [section, { key: "trends", title: "Research trends", claims: [] }], question: "Water use", notice: "Bounded evidence only.",
  coverage: { candidate_count: 0, related_count: 0, selected_count: 1, evidence_count: 1, candidate_limit: 20, related_limit: 3, enabled: false },
} };
beforeEach(() => { jest.clearAllMocks(); sessionStorage.clear(); window.history.replaceState(null, "", "/dashboard/insights"); });

test("candidate gaps use the existing workflow and exact selected IDs", async () => {
  jest.mocked(api.post).mockResolvedValue(run);
  render(<AnalysisWorkflow selected={[paper]} scope="private" toggle={jest.fn()} onClose={jest.fn()} />);
  await userEvent.selectOptions(screen.getByLabelText("Analysis focus"), "candidate_gaps");
  expect(screen.getByText(/not proof of a gap in global research/)).toBeInTheDocument();
  await userEvent.click(screen.getByRole("button", { name: "Generate analysis" }));
  await screen.findByRole("region", { name: "Evidence-backed research analysis" });
  expect(api.post).toHaveBeenCalledWith("/api/insights/analyses", expect.objectContaining({ focus: "candidate_gaps", document_ids: [4], include_related: false }), expect.anything());
});

test("gap results show qualification, source quotes and citations as text", async () => {
  const gapRun: AnalysisRun = { ...run, result: { ...run.result!, focus: "candidate_gaps", sections: [], candidate_gaps: [{
    category: "limited_field_validation", title: "Limited Field Validation", topic: "Multi-season validation", qualification: "Candidate research gap within the indexed corpus.",
    evidence_pattern: { text: "Only one season is documented.", citations: [evidence] },
    evidence_quotes: [{ quote: "<script>untrusted source</script>", citation: evidence }], timeframe: null,
  }] } };
  render(<AnalysisResult run={gapRun} />);
  expect(screen.getByRole("region", { name: "Candidate research gaps" })).toBeVisible();
  expect(screen.getByText("Candidate research gap within the indexed corpus.")).toBeVisible();
  await userEvent.click(screen.getByText("Supporting source quotations (1)"));
  expect(screen.getByText("<script>untrusted source</script>")).toBeVisible();
  expect(document.querySelector("script")).toBeNull();
  expect(screen.getAllByRole("link", { name: "Open Study.pdf, page 2" })[0]).toHaveAttribute("href", "/api/knowledge-base/8/documents/4/content?inline=true#page=2");
});

test("empty gap result does not claim gaps do not exist", () => {
  render(<AnalysisResult run={{ ...run, status: "insufficient_evidence", result: { ...run.result!, focus: "candidate_gaps", candidate_gaps: [], sections: [] } }} />);
  expect(screen.getByText(/does not establish that no research gaps exist/)).toBeVisible();
});

test("renders cited synthesis, missing sections, profiles and saved link without HTML execution", async () => {
  render(<AnalysisResult run={run} />);
  expect(screen.getByRole("region", { name: "Evidence-backed research analysis" })).toBeInTheDocument();
  expect(screen.getByText("Not identified in retrieved evidence.")).toBeInTheDocument();
  expect(document.querySelector("script")).toBeNull();
  expect(screen.getAllByRole("link", { name: "Open Study.pdf, page 2" })[0]).toHaveAttribute("href", "/api/knowledge-base/8/documents/4/content?inline=true#page=2");
  await userEvent.click(screen.getByText("Research profiles (1)"));
  expect(screen.getByRole("table", { name: "Research profile for Irrigation study" })).toBeVisible();
  await userEvent.click(screen.getByText("Inspect evidence snapshots (1)"));
  expect(screen.getByText("Water use reduced.")).toBeVisible();
  expect(screen.getByRole("link", { name: "Reopen saved analysis #30" })).toHaveAttribute("href", "/dashboard/insights?analysis=30");
});

test("private scope cannot enable related discovery and posts exact selected IDs", async () => {
  jest.mocked(api.post).mockResolvedValue(run);
  render(<AnalysisWorkflow selected={[paper]} scope="private" toggle={jest.fn()} onClose={jest.fn()} />);
  expect(screen.getByRole("checkbox", { name: /Include up to/ })).toBeDisabled();
  expect(screen.getByRole("checkbox", { name: /Include up to/ })).not.toBeChecked();
  await userEvent.click(screen.getByRole("button", { name: "Generate analysis" }));
  await screen.findByRole("region", { name: "Evidence-backed research analysis" });
  expect(api.post).toHaveBeenCalledWith("/api/insights/analyses", { document_ids: [4], scope: "private", question: "", include_related: false, request_id: expect.any(String) }, expect.anything());
});

test("failed generation offers retry and uses a new id after server failure", async () => {
  jest.mocked(api.post).mockRejectedValueOnce(new ApiError(503, "Free model busy")).mockResolvedValueOnce(run);
  render(<AnalysisWorkflow selected={[paper]} scope="both" toggle={jest.fn()} onClose={jest.fn()} />);
  const user = userEvent.setup();
  await user.click(screen.getByRole("button", { name: "Generate analysis" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("Free model busy");
  await user.click(screen.getByRole("button", { name: "Generate analysis" }));
  await screen.findByRole("region", { name: "Evidence-backed research analysis" });
  const calls = jest.mocked(api.post).mock.calls;
  expect((calls[0][1] as any).request_id).not.toBe((calls[1][1] as any).request_id);
});

test("saved analysis route opens and reads without regenerating", async () => {
  window.history.replaceState(null, "", "/dashboard/insights?analysis=30");
  jest.mocked(api.get).mockImplementation(async url => url === "/api/insights/analyses/30" ? run : url.startsWith("/api/departments") ? [] : { items: [], has_more: false });
  render(<Insights />);
  expect(await screen.findByRole("region", { name: "Evidence-backed research analysis" })).toBeInTheDocument();
  expect(api.get).toHaveBeenCalledWith("/api/insights/analyses/30", expect.objectContaining({ cache: "no-store" }));
  expect(api.post).not.toHaveBeenCalled();
  await userEvent.click(screen.getByRole("button", { name: "Close analysis" }));
  await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
  expect(window.location.search).toBe("");
});

test("revoked saved analysis hides result and retries read only", async () => {
  window.history.replaceState(null, "", "/dashboard/insights?analysis=30");
  jest.mocked(api.get).mockRejectedValue(new ApiError(404, "Sources unavailable"));
  render(<AnalysisWorkflow selected={[]} scope="public" toggle={jest.fn()} onClose={jest.fn()} />);
  expect(await screen.findByRole("alert")).toHaveTextContent("Sources unavailable");
  expect(screen.queryByText("Irrigation study")).not.toBeInTheDocument();
  await userEvent.click(screen.getByRole("button", { name: "Retry saved analysis" }));
  await waitFor(() => expect(api.get).toHaveBeenCalledTimes(2));
  expect(api.post).not.toHaveBeenCalled();
});

test("pending and insufficient evidence states never claim success", () => {
  const { rerender } = render(<AnalysisResult run={{ ...run, status: "processing", result: null }} />);
  expect(screen.getByRole("status")).toHaveTextContent("still processing");
  rerender(<AnalysisResult run={{ ...run, status: "insufficient_evidence" }} />);
  expect(screen.getByRole("status")).toHaveTextContent("insufficient retrieved evidence");
});

test("closing a slow generation retains only its request ID for recovery", async () => {
  jest.mocked(api.post).mockImplementation(() => new Promise(() => {}));
  const started = jest.fn(), close = jest.fn();
  const { unmount } = render(<AnalysisWorkflow selected={[paper]} scope="private" toggle={jest.fn()} onClose={close} onStarted={started} />);
  await userEvent.click(screen.getByRole("button", { name: "Generate analysis" }));
  const id = started.mock.calls[0][0];
  expect(sessionStorage.getItem(lastAnalysisKey)).toBe(id);
  expect(window.location.search).toContain(`analysisRequest=${id}`);
  expect(screen.getByRole("status")).toHaveTextContent("Resume last analysis");
  await userEvent.click(screen.getByRole("button", { name: "Close and resume later" }));
  expect(close).toHaveBeenCalled();
  unmount();
});

test("request recovery opens saved results without another generation", async () => {
  const id = "12345678-1234-4234-8234-123456789abc";
  sessionStorage.setItem(lastAnalysisKey, id);
  window.history.replaceState(null, "", `/dashboard/insights?analysisRequest=${id}`);
  jest.mocked(api.get).mockImplementation(async url => url.includes("/analyses/requests/") ? run : url.startsWith("/api/departments") ? [] : { items: [], has_more: false });
  render(<Insights />);
  expect(await screen.findByRole("region", { name: "Evidence-backed research analysis" })).toBeInTheDocument();
  await userEvent.click(screen.getByRole("button", { name: "Close analysis" }));
  await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
  expect(screen.getByRole("link", { name: "Resume last analysis" })).toHaveAttribute("href", `/dashboard/insights?analysisRequest=${id}`);
  expect(api.post).not.toHaveBeenCalled();
});

test("saved processing result polls until complete without re-posting", async () => {
  jest.useFakeTimers();
  window.history.replaceState(null, "", "/dashboard/insights?analysis=30");
  jest.mocked(api.get).mockResolvedValueOnce({ ...run, status: "processing", result: null }).mockResolvedValueOnce(run);
  const { unmount } = render(<AnalysisWorkflow selected={[]} scope="public" toggle={jest.fn()} onClose={jest.fn()} />);
  await waitFor(() => expect(screen.getByRole("status")).toHaveTextContent("still processing"));
  await act(async () => { jest.advanceTimersByTime(5000); });
  expect(await screen.findByRole("region", { name: "Evidence-backed research analysis" })).toBeInTheDocument();
  expect(api.get).toHaveBeenCalledTimes(2); expect(api.post).not.toHaveBeenCalled();
  unmount(); jest.useRealTimers();
});

test("evidence interpretation requires two papers and posts the chosen focus", async () => {
  jest.mocked(api.post).mockResolvedValue(run);
  const props = { scope: "both" as const, toggle: jest.fn(), onClose: jest.fn() };
  const { rerender } = render(<AnalysisWorkflow {...props} selected={[paper]} />);
  await userEvent.selectOptions(screen.getByRole("combobox", { name: "Analysis focus" }), "contradictions");
  expect(screen.getByRole("button", { name: "Generate analysis" })).toBeDisabled();
  rerender(<AnalysisWorkflow {...props} selected={[paper, { ...paper, id: 5, scope: "public" }]} />);
  await userEvent.click(screen.getByRole("button", { name: "Generate analysis" }));
  await screen.findByRole("region", { name: "Evidence-backed research analysis" });
  expect(api.post).toHaveBeenCalledWith("/api/insights/analyses", expect.objectContaining({ focus: "contradictions", document_ids: [4, 5] }), expect.anything());
});

test("interpretation shows evidence roles, context, source links and escaped text", async () => {
  const opposite = { ...evidence, evidence_id: "E2", document_id: 5, scope: "public" as const, file_name: "Other.pdf" };
  const interpreted: AnalysisRun = { ...run, result: { ...run.result!, focus: "contradictions", sections: [], interpretations: [{
    claim: "<script>unsafe()</script>", label: "Potential disagreement", supporting: [evidence], contradicting: [opposite], qualifying: [],
    interpretation: { text: "Conditions may differ; no verdict on validity.", citations: [evidence, opposite] },
    context_factors: [{ key: "environment", title: "Location / environment", text: "Field and greenhouse conditions differ.", citations: [evidence, opposite] }],
  }] } };
  const { rerender } = render(<AnalysisResult run={interpreted} />);
  const region = within(screen.getByRole("region", { name: "Evidence interpretation" }));
  expect(region.getByText("Supporting evidence")).toBeInTheDocument();
  expect(region.getByText("Contradicting evidence")).toBeInTheDocument();
  expect(region.getByText("Qualifying evidence")).toBeInTheDocument();
  expect(region.getByText("Field and greenhouse conditions differ.", { exact: false })).toBeInTheDocument();
  expect(region.getAllByRole("link", { name: "Open Other.pdf, page 2" })[0]).toHaveAttribute("href", "/api/corpus/documents/5/content?inline=true#page=2");
  expect(document.querySelector("script")).toBeNull();
  await userEvent.click(screen.getByText("Inspect evidence snapshots (2)"));
  expect(screen.getAllByText("Water use reduced.").length).toBe(2);
  rerender(<AnalysisResult run={{ ...interpreted, status: "insufficient_evidence", result: { ...interpreted.result!, interpretations: [] } }} />);
  expect(screen.getByText(/This does not establish that the papers agree/)).toBeInTheDocument();
});
