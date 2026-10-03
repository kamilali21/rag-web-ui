// Added by ChatGPT: Public/Private separation and real public API interactions, not demo catalog state.
import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { api, ApiError } from "@/lib/api";
import { Library } from "../library";
import { emptyPublicFilters, publicDocumentsUrl } from "@/lib/public-library";

jest.mock("@/lib/api", () => ({ ...jest.requireActual("@/lib/api"), api: { get: jest.fn(), post: jest.fn(), delete: jest.fn() } }));
jest.mock("../document-upload-steps", () => ({ DocumentUploadSteps: ({ knowledgeBaseId }: { knowledgeBaseId: number }) => <div>Private upload {knowledgeBaseId}</div> }));

const document = { id: 9, is_bookmarked: false, knowledge_base_id: 8, file_name: "source.pdf", title: "Irrigation Efficiency",
  file_size: 1000, content_type: "application/pdf", created_at: "2026-09-20T12:00:00", publication_status: "published",
  authors_text: "Ayesha Rahman", department_id: 3, department_name: "Agronomy", publication_year: 2024, document_type: "paper" };
const metadata = { ...document, abstract: "Synthetic irrigation research.", keywords: ["water"], supervisor: null,
  language: "en", doi: "10.1234/example", publication_date: null };
const privateCollection = { id: 1, name: "My private collection", documents: [{ ...document, id: 1,
  knowledge_base_id: 1, file_name: "Private notes.pdf", processing_tasks: [{ id: 1, status: "completed" }] }] };
let admin = false;
const get = async (url: string): Promise<any> => {
  if (url.startsWith("/api/knowledge-base?")) return [privateCollection];
  if (url === "/api/knowledge-base/1") return privateCollection;
  if (url === "/api/corpus") return { id: 8, name: "UAF Research Corpus" };
  if (url === "/api/auth/me") return { roles: admin ? ["admin", "researcher"] : ["researcher"] };
  if (url.startsWith("/api/departments?")) return [{ id: 3, name: "Agronomy", code: "AGR", is_active: true }];
  if (url === "/api/departments/3") return { id: 3, name: "Agronomy", code: "AGR", is_active: true };
  if (url.startsWith("/api/corpus/documents?")) return [document];
  if (url === "/api/corpus/documents/9") return document;
  if (url === "/api/corpus/documents/9/metadata") return metadata;
  if (url === "/api/corpus/tasks/14") return { id: 14, status: "completed" };
  throw new Error(`Unexpected API ${url}`);
};

beforeEach(() => { jest.clearAllMocks(); admin = false; jest.mocked(api.get).mockImplementation(get); });
async function openPublic() {
  const user = userEvent.setup(); render(<Library />);
  await screen.findByText("Private notes.pdf");
  await user.click(screen.getByRole("button", { name: "Public" }));
  await screen.findByRole("table", { name: "Public research documents" });
  return user;
}

test("public toggle reads the shared corpus, hides researcher writes and returns to private uploads", async () => {
  const user = await openPublic();
  expect(screen.getByText("Irrigation Efficiency")).toBeInTheDocument();
  expect(screen.queryByText("Private notes.pdf")).not.toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Add Documents" })).not.toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Manage collections" })).not.toBeInTheDocument();
  expect(api.get).toHaveBeenCalledWith("/api/corpus/documents?limit=21", expect.anything());
  await user.click(screen.getByRole("button", { name: "Private" }));
  await screen.findByText("Private notes.pdf");
  expect(screen.queryByText("Irrigation Efficiency")).not.toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Add Documents" }));
  expect(await screen.findByText("Private upload 1")).toBeInTheDocument();
});

test("submits bounded metadata filters to the public server, not filename shortcuts", async () => {
  const user = await openPublic();
  await user.type(screen.getByRole("searchbox", { name: "Search public library" }), "water");
  await user.type(screen.getByLabelText("Author", { selector: "input" }), "Ayesha");
  await user.selectOptions(screen.getByLabelText("Department", { selector: "select" }), "3");
  await user.type(screen.getByLabelText("From year"), "2023");
  await user.type(screen.getByLabelText("To year"), "2024");
  await user.selectOptions(screen.getByLabelText("Type", { selector: "select" }), "paper");
  await user.click(screen.getByRole("button", { name: "Search" }));
  await waitFor(() => expect(api.get).toHaveBeenCalledWith("/api/corpus/documents?limit=21&search=water&author=Ayesha&department_id=3&year_from=2023&year_to=2024&document_type=paper", expect.anything()));
  await user.click(screen.getByRole("button", { name: "Clear public filters" }));
  expect(screen.getByLabelText("From year")).toHaveValue(null);
  expect(screen.getByRole("searchbox")).toHaveValue("");
});

test("pages with server cursors and resets pagination on filter changes", async () => {
  jest.mocked(api.get).mockImplementation(async url => url.startsWith("/api/corpus/documents?") ?
    url.includes("before_id=") ? [{ ...document, id: 20, title: "Older study" }] :
      Array.from({ length: 21 }, (_, i) => ({ ...document, id: 40 - i, title: `Study ${40 - i}` })) : get(url));
  const user = await openPublic();
  expect(screen.queryByText("Study 20")).not.toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Next page" }));
  await screen.findByText("Older study");
  expect(api.get).toHaveBeenCalledWith("/api/corpus/documents?limit=21&before_id=21", expect.anything());
  expect(screen.getByRole("button", { name: "Next page" })).toBeDisabled();
  await user.click(screen.getByRole("button", { name: "Previous page" }));
  await screen.findByText("Study 40");
  await user.click(screen.getByRole("button", { name: "Next page" })); await screen.findByText("Older study");
  await user.click(screen.getByRole("button", { name: "Search" }));
  await screen.findByText("Study 40");
  expect(screen.getByRole("button", { name: "Previous page" })).toBeDisabled();
});

test("detail popup loads authorized metadata and offers only safe corpus file links", async () => {
  const user = await openPublic();
  await user.click(screen.getByRole("button", { name: "Details for Irrigation Efficiency" }));
  const dialog = await screen.findByRole("dialog");
  expect(await within(dialog).findByText("Synthetic irrigation research.")).toBeInTheDocument();
  expect(within(dialog).getByRole("link", { name: "Open document" })).toHaveAttribute("href", "/api/corpus/documents/9/content?inline=true");
  expect(within(dialog).getByRole("link", { name: "Download" })).toHaveAttribute("href", "/api/corpus/documents/9/content");
  expect(within(dialog).queryByRole("button", { name: /delete|edit|publish/i })).not.toBeInTheDocument();
});

test("a document unpublished after listing cannot be opened from a stale row", async () => {
  const user = await openPublic();
  jest.mocked(api.get).mockImplementation(async url => url === "/api/corpus/documents/9/metadata" ? Promise.reject(new ApiError(404, "Not found")) : get(url));
  await user.click(screen.getByRole("button", { name: "Details for Irrigation Efficiency" }));
  expect(await screen.findByText("This document is no longer available in the public corpus.")).toBeInTheDocument();
  expect(screen.queryByRole("link", { name: "Open document" })).not.toBeInTheDocument();
});

test("queries published evidence through the existing API and opens its source", async () => {
  const user = await openPublic();
  jest.mocked(api.post).mockResolvedValue({ results: [{ content: "731 litres saved.", metadata: { chunk_id: "abc", document_id: 9, file_name: "source.pdf", page: 0 } }] });
  await user.click(screen.getByRole("button", { name: "Query corpus" }));
  await user.type(screen.getByLabelText("Question"), "How much water?");
  await user.click(screen.getByRole("button", { name: "Find evidence" }));
  await screen.findByText("731 litres saved.");
  expect(api.post).toHaveBeenCalledWith("/api/corpus/query", { query: "How much water?", top_k: 5 }, expect.anything());
  await user.click(screen.getByRole("button", { name: "source.pdf, page 1" }));
  expect(await screen.findByText("Synthetic irrigation research.")).toBeInTheDocument();
});

test("query failure and empty evidence are distinct states", async () => {
  const user = await openPublic();
  jest.mocked(api.post).mockRejectedValueOnce(new ApiError(503, "Corpus retrieval unavailable")).mockResolvedValueOnce({ results: [] });
  await user.click(screen.getByRole("button", { name: "Query corpus" }));
  await user.type(screen.getByLabelText("Question"), "water");
  await user.click(screen.getByRole("button", { name: "Find evidence" }));
  await screen.findByText("Corpus retrieval unavailable");
  expect(screen.queryByText("No published evidence found.")).not.toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Find evidence" }));
  await screen.findByText("No published evidence found.");
});

test("only authorized admins get the basic public uploader; completion remains a draft", async () => {
  admin = true;
  const user = await openPublic();
  jest.mocked(api.post).mockResolvedValue({ id: 14, status: "pending" });
  await user.click(screen.getByRole("button", { name: "Add Documents" }));
  const file = new File(["test"], "research.txt", { type: "text/plain" });
  const input = screen.getByLabelText("PDF, DOCX, TXT or MD (up to 20 MB)") as HTMLInputElement;
  await user.upload(input, file);
  expect(input.files?.[0]).toBe(file);
  expect(screen.getByRole("button", { name: "Upload document" })).toBeEnabled();
  // JSDOM's native required-file validity does not see userEvent's FileList; real clicks are checked in Chrome.
  fireEvent.submit(input.closest("form")!);
  expect(api.post).toHaveBeenCalled();
  await screen.findByText("Processed. Draft awaiting publication.");
  const call = jest.mocked(api.post).mock.calls[0];
  expect(call[0]).toBe("/api/corpus/documents/upload");
  expect((call[1] as FormData).get("file")).toBe(file);
  expect(screen.queryByRole("button", { name: /^(publish|delete|edit)$/i })).not.toBeInTheDocument();
});

test("a revoked admin loses the uploader on server denial", async () => {
  admin = true;
  const user = await openPublic();
  jest.mocked(api.post).mockRejectedValue(new ApiError(403, "Corpus administrator required"));
  await user.click(screen.getByRole("button", { name: "Add Documents" }));
  const input = screen.getByLabelText("PDF, DOCX, TXT or MD (up to 20 MB)") as HTMLInputElement;
  await user.upload(input, new File(["test"], "test.txt", { type: "text/plain" }));
  fireEvent.submit(input.closest("form")!);
  await screen.findByText("Your public upload permission is no longer available.");
  expect(screen.queryByRole("button", { name: "Add Documents" })).not.toBeInTheDocument();
});

test("public API failures show retry, never a false empty catalog", async () => {
  let failed = true;
  jest.mocked(api.get).mockImplementation(async url => url.startsWith("/api/corpus/documents?") && failed ? Promise.reject(new Error("offline")) : get(url));
  const user = userEvent.setup(); render(<Library />); await screen.findByText("Private notes.pdf");
  await user.click(screen.getByRole("button", { name: "Public" }));
  await screen.findByText("Public library unavailable");
  expect(screen.queryByText("No published research yet")).not.toBeInTheDocument();
  failed = false;
  await user.click(screen.getByRole("button", { name: "Retry" }));
  await screen.findByText("Irrigation Efficiency");
});

test("switching scope aborts public work and prevents late results from replacing private documents", async () => {
  let resolve!: (value: unknown) => void;
  let signal: AbortSignal | undefined;
  jest.mocked(api.get).mockImplementation((url, options) => {
    if (url.startsWith("/api/corpus/documents?")) { signal = options?.signal as AbortSignal; return new Promise(done => { resolve = done; }); }
    return get(url);
  });
  const user = userEvent.setup(); render(<Library />); await screen.findByText("Private notes.pdf");
  await user.click(screen.getByRole("button", { name: "Public" }));
  await waitFor(() => expect(signal).toBeDefined());
  await user.click(screen.getByRole("button", { name: "Private" }));
  expect(signal?.aborted).toBe(true);
  await act(async () => resolve([document]));
  await screen.findByText("Private notes.pdf");
  expect(screen.queryByText("Irrigation Efficiency")).not.toBeInTheDocument();
});

test("filter URLs encode user input and never accept a private KB scope", () => {
  expect(publicDocumentsUrl({ ...emptyPublicFilters, search: "a&kb_id=1", author: "100%" }, 9))
    .toBe("/api/corpus/documents?limit=21&search=a%26kb_id%3D1&author=100%25&before_id=9");
});

test("saves and removes a personal public bookmark and submits the saved-only filter", async () => {
  const user = await openPublic();
  jest.mocked(api.post).mockResolvedValue(undefined);
  jest.mocked(api.delete).mockResolvedValue(undefined);
  const titleCell = screen.getByRole("button", { name: "Details for Irrigation Efficiency" }).closest("td")!;
  expect(within(titleCell).getByRole("button", { name: "Bookmark Irrigation Efficiency" })).toHaveAttribute("aria-pressed", "false");
  await user.click(screen.getByRole("button", { name: "Bookmark Irrigation Efficiency" }));
  const saved = await screen.findByRole("button", { name: "Remove bookmark for Irrigation Efficiency" });
  expect(saved).toHaveAttribute("aria-pressed", "true");
  expect(api.post).toHaveBeenCalledWith("/api/corpus/documents/9/bookmark");
  await user.click(saved);
  await screen.findByRole("button", { name: "Bookmark Irrigation Efficiency" });
  expect(api.delete).toHaveBeenCalledWith("/api/corpus/documents/9/bookmark");
  await user.click(screen.getByRole("checkbox", { name: "Saved only" }));
  await user.click(screen.getByRole("button", { name: "Search" }));
  await waitFor(() => expect(api.get).toHaveBeenCalledWith("/api/corpus/documents?limit=21&bookmarked=true", expect.anything()));
});

test("refresh is a list action outside pagination and reloads the public catalog", async () => {
  const user = await openPublic();
  const pages = screen.getByRole("navigation", { name: "Public library pages" });
  expect(within(pages).queryByRole("button", { name: "Refresh public library" })).not.toBeInTheDocument();
  jest.mocked(api.get).mockClear();
  await user.click(screen.getByRole("button", { name: "Refresh public library" }));
  await waitFor(() => expect(api.get).toHaveBeenCalledWith("/api/corpus/documents?limit=21", expect.anything()));
});

test("failed bookmark saves retain their original state and show an error", async () => {
  const user = await openPublic();
  jest.mocked(api.post).mockRejectedValue(new ApiError(404, "Document not found"));
  await user.click(screen.getByRole("button", { name: "Bookmark Irrigation Efficiency" }));
  await screen.findByText("Document not found");
  expect(screen.getByRole("button", { name: "Bookmark Irrigation Efficiency" })).toHaveAttribute("aria-pressed", "false");
});
