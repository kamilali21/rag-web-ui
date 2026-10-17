import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Library } from "../library";
import { api } from "@/lib/api";
import { documentDate, documentStatus } from "@/lib/library";

jest.mock("@/lib/api", () => ({ api: { get: jest.fn(), post: jest.fn(), delete: jest.fn() }, ApiError: class ApiError extends Error {} }));
jest.mock("../document-upload-steps", () => ({ DocumentUploadSteps: ({ knowledgeBaseId }: { knowledgeBaseId: number }) => <div>Upload to collection {knowledgeBaseId}</div> }));
const document = { id: 11, file_name: "Research_Paper_ML.pdf", file_size: 2097152, content_type: "application/pdf", knowledge_base_id: 7, created_at: "2026-09-15T08:00:00", processing_tasks: [{ id: 3, status: "completed" }] };
const collections = [{ id: 7, name: "Research", documents: [] }, { id: 8, name: "Theses", documents: [] }];
let catalog: { items: typeof document[]; total: number; has_active_tasks: boolean };
beforeEach(() => {
  jest.clearAllMocks();
  catalog = { items: [document], total: 1, has_active_tasks: false };
  jest.mocked(api.get).mockImplementation(async (url) => String(url).includes("/catalog?") ? catalog : collections);
  jest.spyOn(window, "confirm").mockReturnValue(true);
});
afterEach(() => jest.restoreAllMocks());
afterEach(() => window.history.replaceState({}, "", "/"));
const expectCatalog = (part: string) => waitFor(() => expect(api.get).toHaveBeenCalledWith(expect.stringContaining(part), expect.objectContaining({ signal: expect.any(AbortSignal) })));

test("search and state/category filters are sent to the bounded server catalog", async () => {
  const user = userEvent.setup(); render(<Library />);
  await screen.findByText(document.file_name);
  await user.type(screen.getByRole("searchbox"), "wheat");
  await expectCatalog("search=wheat");
  await user.selectOptions(screen.getByRole("combobox", { name: "Processing status" }), "failed");
  await expectCatalog("status=failed");
  await user.click(await screen.findByRole("button", { name: "Find filenames containing paper" }));
  await expectCatalog("category=Papers");
  await user.click(screen.getByRole("button", { name: "Clear filters" }));
  expect(screen.getByRole("searchbox")).toHaveValue("");
  expect(screen.getByRole("combobox", { name: "Processing status" })).toHaveValue("all");
});

test("collection routes scope the document catalog and uploads use the selected collection", async () => {
  const user = userEvent.setup(); render(<Library knowledgeBaseId={7} />);
  await screen.findByText(document.file_name);
  await expectCatalog("kb_id=7");
  await user.click(screen.getByRole("button", { name: "Add Documents" }));
  expect(screen.getByText("Upload to collection 7")).toBeInTheDocument();
});

test("pagination sends a bounded offset and filtering resets to page one", async () => {
  catalog.total = 21;
  const user = userEvent.setup(); render(<Library />);
  await screen.findByText(document.file_name);
  await user.click(screen.getByRole("button", { name: "Next page" }));
  await expectCatalog("skip=20&limit=20");
  expect(screen.getByText("Page 2")).toBeInTheDocument();
  await user.selectOptions(screen.getByRole("combobox", { name: "Filter by collection" }), "8");
  await expectCatalog("kb_id=8");
  expect(screen.getByText("Page 1")).toBeInTheDocument();
});

test("persistent failed uploads display after remount and use the upload deletion route", async () => {
  catalog.items = [{ ...document, id: -9, upload_id: 9, processing_tasks: [{ id: 0, status: "failed" }] } as typeof document];
  const user = userEvent.setup(); render(<Library />);
  await user.click(await screen.findByRole("button", { name: `Details for ${document.file_name}` }));
  expect(screen.getByText(/has not produced a document/)).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Delete file" }));
  await waitFor(() => expect(api.delete).toHaveBeenCalledWith("/api/knowledge-base/7/uploads/9"));
});

test("a failed document cleanup stays open for retry and a cancelled delete does nothing", async () => {
  jest.mocked(api.delete).mockRejectedValue(new Error("storage offline"));
  const user = userEvent.setup(); render(<Library />);
  await user.click(await screen.findByRole("button", { name: `Details for ${document.file_name}` }));
  jest.mocked(window.confirm).mockReturnValueOnce(false);
  await user.click(screen.getByRole("button", { name: "Delete file" }));
  expect(api.delete).not.toHaveBeenCalled();
  await user.click(screen.getByRole("button", { name: "Delete file" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("Cleanup incomplete");
  expect(api.delete).toHaveBeenCalledWith("/api/knowledge-base/7/documents/11");
  expect(screen.getByRole("button", { name: "Delete file" })).toBeEnabled();
});

test("a failed catalog load shows retry rather than a misleading empty library", async () => {
  jest.mocked(api.get).mockRejectedValueOnce(new Error("offline"));
  const user = userEvent.setup(); render(<Library />);
  await screen.findByRole("alert");
  expect(screen.queryByText("No documents yet")).not.toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Retry" }));
  await screen.findByText(document.file_name);
});

test("empty library creates a real collection before uploading", async () => {
  catalog.items = []; catalog.total = 0;
  jest.mocked(api.get).mockImplementation(async (url) => String(url).includes("/catalog?") ? catalog : []);
  jest.mocked(api.post).mockResolvedValue({ id: 19, name: "My documents", documents: [] });
  const user = userEvent.setup(); render(<Library />);
  await screen.findByText("No documents yet");
  await user.click(screen.getAllByRole("button", { name: "Add Documents" })[0]);
  await user.click(screen.getByRole("button", { name: "Create collection" }));
  expect(await screen.findByText("Upload to collection 19")).toBeInTheDocument();
});

test("dashboard publication shortcut opens the existing request dialog and removes its URL flag", async () => {
  window.history.replaceState({}, "", "/dashboard/knowledge?requestPublication=1");
  jest.mocked(api.get).mockImplementation(async (url) => {
    if (String(url).includes("/catalog?")) return catalog;
    if (String(url).includes("/eligible-documents")) return [];
    if (String(url).includes("/researcher/profile")) return null;
    if (String(url).includes("/departments")) return [];
    return collections;
  });
  render(<Library />);
  expect(await screen.findByRole("heading", { name: "Request publication" })).toBeInTheDocument();
  expect(window.location.search).toBe("");
});

test("latest processing attempt and UTC timestamps remain truthful", () => {
  expect(documentStatus({ ...document, processing_tasks: [{ id: 3, status: "failed" }, { id: 1, status: "completed" }] }).label).toBe("Failed");
  expect(documentStatus(document).label).toBe("Ready");
  expect(documentStatus({ ...document, processing_tasks: [] }).label).toBe("Unknown");
  expect(documentDate("2026-09-15T08:00:00").toISOString()).toBe("2026-09-15T08:00:00.000Z");
});
