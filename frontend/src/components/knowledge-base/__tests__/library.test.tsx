// Added by ChatGPT: regression coverage for document scope, real states, and filename filtering.
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Library } from "../library";
import { api } from "@/lib/api";
import { documentDate, documentStatus } from "@/lib/library";

jest.mock("@/lib/api", () => ({
  api: { get: jest.fn(), post: jest.fn(), delete: jest.fn() },
  ApiError: class ApiError extends Error {},
}));
jest.mock("../document-upload-steps", () => ({
  DocumentUploadSteps: ({ knowledgeBaseId }: { knowledgeBaseId: number }) => <div>Upload to collection {knowledgeBaseId}</div>,
}));

const document = {
  id: 11, file_name: "Research_Paper_ML.pdf", file_size: 2097152,
  content_type: "application/pdf", knowledge_base_id: 7, created_at: "2026-09-15T08:00:00",
  processing_tasks: [{ id: 3, status: "processing" }, { id: 1, status: "completed" }],
};
const collections = [{ id: 7, name: "Research", documents: [document] },
  { id: 8, name: "Theses", documents: [{ ...document, id: 12, knowledge_base_id: 8, file_name: "My_Thesis.pdf" }] }];

beforeEach(() => { jest.clearAllMocks(); jest.mocked(api.get).mockResolvedValue(collections); });

test("lists real documents, searches filenames, and clears a category filter", async () => {
  const user = userEvent.setup();
  render(<Library />);
  await screen.findByText("Research_Paper_ML.pdf");
  expect(screen.getByText("My_Thesis.pdf")).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Find filenames containing paper" }));
  expect(screen.queryByText("My_Thesis.pdf")).not.toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Clear filters" }));
  await user.type(screen.getByRole("searchbox"), "THESIS");
  expect(screen.queryByText("Research_Paper_ML.pdf")).not.toBeInTheDocument();
  expect(screen.getByText("My_Thesis.pdf")).toBeInTheDocument();
});

test("enables the public toggle and keeps uploads in the chosen private collection", async () => {
  const user = userEvent.setup();
  render(<Library />);
  await screen.findByText("Research_Paper_ML.pdf");
  expect(screen.getByRole("button", { name: "Public" })).toBeEnabled();
  await user.click(screen.getByRole("button", { name: "Add Documents" }));
  await user.click(screen.getByRole("button", { name: "Theses" }));
  expect(screen.getByText("Upload to collection 8")).toBeInTheDocument();
});

test("collection routes request only their own original knowledge-base endpoint", async () => {
  jest.mocked(api.get).mockResolvedValue(collections[0]);
  render(<Library knowledgeBaseId={7} />);
  await screen.findByText("Research_Paper_ML.pdf");
  expect(api.get).toHaveBeenCalledWith("/api/knowledge-base/7", expect.objectContaining({ signal: expect.any(AbortSignal) }));
  expect(screen.queryByText("My_Thesis.pdf")).not.toBeInTheDocument();
});

test("a failed load displays retry rather than a misleading empty library", async () => {
  jest.mocked(api.get).mockRejectedValueOnce(new Error("offline"));
  const user = userEvent.setup();
  render(<Library />);
  await screen.findByRole("alert");
  expect(screen.queryByText("No documents yet")).not.toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Retry" }));
  await screen.findByText("Research_Paper_ML.pdf");
});

test("empty libraries create a real private collection before presenting the uploader", async () => {
  jest.mocked(api.get).mockResolvedValue([]);
  jest.mocked(api.post).mockResolvedValue({ id: 19, name: "My documents", documents: [] });
  const user = userEvent.setup();
  render(<Library />);
  await screen.findByText("No documents yet");
  await user.click(screen.getAllByRole("button", { name: "Add Documents" })[0]);
  await user.click(screen.getByRole("button", { name: "Create collection" }));
  await waitFor(() => expect(api.post).toHaveBeenCalledWith("/api/knowledge-base", { name: "My documents", description: "" }));
  expect(await screen.findByText("Upload to collection 19")).toBeInTheDocument();
});

test("uses the latest processing attempt and normalizes server UTC timestamps", () => {
  expect(documentStatus(document)).toEqual({ status: "processing", label: "Processing" });
  expect(documentStatus({ ...document, processing_tasks: [] }).label).toBe("Unknown");
  expect(documentDate("2026-09-15T08:00:00").toISOString()).toBe("2026-09-15T08:00:00.000Z");
});

test("filters private documents by their latest processing state and combines filename search", async () => {
  const ready = { ...document, id: 14, file_name: "Ready_Paper.pdf", processing_tasks: [{ id: 9, status: "completed" }] };
  const failed = { ...document, id: 15, file_name: "Failed_Paper.pdf", processing_tasks: [{ id: 8, status: "failed" }, { id: 2, status: "completed" }] };
  jest.mocked(api.get).mockResolvedValue([{ ...collections[0], documents: [document, ready, failed] }]);
  const user = userEvent.setup();
  render(<Library />);
  await screen.findByText("Ready_Paper.pdf");
  await user.selectOptions(screen.getByRole("combobox", { name: "Processing status" }), "completed");
  expect(screen.getByRole("button", { name: "Details for Ready_Paper.pdf" })).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Details for Failed_Paper.pdf" })).not.toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Details for Research_Paper_ML.pdf" })).not.toBeInTheDocument();
  await user.selectOptions(screen.getByRole("combobox", { name: "Processing status" }), "failed");
  expect(screen.getByRole("button", { name: "Details for Failed_Paper.pdf" })).toBeInTheDocument();
  await user.type(screen.getByRole("searchbox"), "Ready");
  expect(screen.getByText("No matching documents")).toBeInTheDocument();
  await user.click(screen.getAllByRole("button", { name: "Clear filters" })[0]);
  expect(screen.getByRole("combobox", { name: "Processing status" })).toHaveValue("all");
  expect(screen.getAllByRole("button", { name: /^Details for/ })).toHaveLength(3);
  expect(documentStatus(ready)).toEqual({ status: "completed", label: "Ready" });
});
