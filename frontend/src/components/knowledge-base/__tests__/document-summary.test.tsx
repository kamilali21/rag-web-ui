import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { api, ApiError } from "@/lib/api";
import { DocumentSummaryPanel } from "../document-summary";

jest.mock("@/lib/api", () => ({ ...jest.requireActual("@/lib/api"), api: { post: jest.fn() } }));

const result = {
  status: "complete",
  message: null,
  document: { id: 28, knowledge_base_id: 4, scope: "private", file_name: "water-study.pdf" },
  sections: [
    { key: "objective", title: "Research objective or question", unavailable: false,
      claims: [{ text: "The study evaluates irrigation efficiency.", citations: [
        { id: 1, document_id: 28, knowledge_base_id: 4, scope: "private", file_name: "water-study.pdf", page: 2 },
      ] }] },
    { key: "methods_context", title: "Methods, design, and context", unavailable: true, claims: [] },
  ],
};

beforeEach(() => jest.clearAllMocks());

test("requests a saved summary for the selected scope and links verified citations to its source page", async () => {
  jest.mocked(api.post).mockResolvedValue(result);
  const user = userEvent.setup();
  render(<DocumentSummaryPanel documentId={28} scope="private" />);

  await user.click(screen.getByRole("button", { name: "Summarize paper" }));
  expect(await screen.findByText("The study evaluates irrigation efficiency.")).toBeInTheDocument();
  expect(screen.getByText("Not identified in retrieved evidence.")).toBeInTheDocument();
  expect(api.post).toHaveBeenCalledWith("/api/retrieval/documents/summarize", { document_id: 28, scope: "private", request_id: expect.any(String) }, expect.anything());
  expect(screen.getByRole("link", { name: "Open water-study.pdf, page 3" })).toHaveAttribute(
    "href", "/api/knowledge-base/4/documents/28/content?inline=true#page=3",
  );
});

test("shows a retry action after an API error and succeeds on retry", async () => {
  jest.mocked(api.post)
    .mockRejectedValueOnce(new ApiError(503, "The free AI service is temporarily busy. Try again shortly."))
    .mockResolvedValueOnce(result);
  const user = userEvent.setup();
  render(<DocumentSummaryPanel documentId={28} scope="public" />);

  await user.click(screen.getByRole("button", { name: "Summarize paper" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("temporarily busy");
  await user.click(screen.getByRole("button", { name: "Retry summary" }));
  await screen.findByText("The study evaluates irrigation efficiency.");
  await waitFor(() => expect(api.post).toHaveBeenCalledTimes(2));
  expect(api.post).toHaveBeenLastCalledWith("/api/retrieval/documents/summarize", { document_id: 28, scope: "public", request_id: expect.any(String) }, expect.anything());
});
