// Added by ChatGPT: admin forms and lifecycle actions use real API contracts with explicit confirmation.
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { api, ApiError } from "@/lib/api";
import { CorpusManager } from "../corpus-manager";
import { AdminActionDialog, AdminTask, DepartmentManager, MetadataEditor } from "../corpus-admin-dialogs";

jest.mock("@/lib/api", () => ({ ...jest.requireActual("@/lib/api"), api: { get: jest.fn(), patch: jest.fn(), post: jest.fn(), delete: jest.fn() } }));
const task: AdminTask = { id: 7, document_id: 9, upload_id: 4, title: "Irrigation study", file_name: "research.pdf", status: "completed", publication_status: "draft", created_at: "2026-09-22T10:00:00", error_message: null };
const metadata = { title: "Irrigation study", authors_text: "QA Author", abstract: "Existing abstract", department_id: 3,
  document_type: "paper", publication_year: 2024, publication_date: null, supervisor: null, keywords: ["water"], doi: null, language: "en" };
const department = { id: 3, name: "Agronomy", code: "AGR", is_active: false };
const callbacks = { onClose: jest.fn(), onChanged: jest.fn(), onForbidden: jest.fn() };
beforeEach(() => {
  jest.clearAllMocks();
  jest.mocked(api.get).mockImplementation(async url => {
    if (url.startsWith("/api/corpus/tasks?")) return [task];
    if (url.includes("/metadata")) return metadata;
    if (url.startsWith("/api/departments?")) return [department];
    throw Error(url);
  });
});

test("admin inbox submits server filters and handles forbidden access", async () => {
  const user = userEvent.setup();
  render(<CorpusManager onBack={jest.fn()} onForbidden={callbacks.onForbidden} />);
  await screen.findByRole("table", { name: "Corpus uploads" });
  await user.type(screen.getByLabelText("Title or filename"), "water");
  await user.selectOptions(screen.getByLabelText("Processing"), "failed");
  await user.selectOptions(screen.getByLabelText("Publication"), "draft");
  await user.click(screen.getByRole("button", { name: "Search" }));
  await waitFor(() => expect(api.get).toHaveBeenCalledWith("/api/corpus/tasks?limit=21&search=water&status=failed&publication_status=draft", expect.anything()));
  jest.mocked(api.get).mockRejectedValue(new ApiError(403, "Administrator required"));
  await user.click(screen.getByRole("button", { name: "Refresh management" }));
  await waitFor(() => expect(callbacks.onForbidden).toHaveBeenCalled());
});

test("metadata editor sends changed fields only, preserving inactive references", async () => {
  const user = userEvent.setup();
  jest.mocked(api.patch).mockResolvedValue({});
  render(<MetadataEditor task={task} {...callbacks} />);
  const title = await screen.findByLabelText("Title");
  expect(screen.getByRole("textbox", { name: "Authors" })).toHaveValue("QA Author");
  expect(screen.getByRole("combobox", { name: "Department" })).toBeInTheDocument();
  expect(screen.getByRole("option", { name: "Agronomy (inactive)" })).toBeDisabled();
  await user.clear(title); await user.type(title, "Updated title");
  await user.click(screen.getByRole("button", { name: "Save changes" }));
  expect(api.patch).toHaveBeenCalledWith("/api/corpus/documents/9/metadata", { title: "Updated title" });
  expect(callbacks.onChanged).toHaveBeenCalled(); expect(callbacks.onClose).toHaveBeenCalled();
});

test("metadata validation and failed saves retain form data", async () => {
  const user = userEvent.setup();
  render(<MetadataEditor task={task} {...callbacks} />);
  await screen.findByLabelText("Title");
  fireEvent.change(screen.getByLabelText("Publication date"), { target: { value: "2023-01-01" } });
  await user.click(screen.getByRole("button", { name: "Save changes" }));
  await screen.findByText("Publication year must match the publication date.");
  expect(api.patch).not.toHaveBeenCalled();
  fireEvent.change(screen.getByLabelText("Publication date"), { target: { value: "2024-01-01" } });
  jest.mocked(api.patch).mockRejectedValue(new ApiError(409, "Document is no longer editable"));
  await user.click(screen.getByRole("button", { name: "Save changes" }));
  await screen.findByText("Document is no longer editable");
  expect(screen.getByLabelText("Publication date")).toHaveValue("2024-01-01");
  expect(callbacks.onClose).not.toHaveBeenCalled();
});

test.each([
  ["publish", "Publish document", "/api/corpus/documents/9/publish"],
  ["unpublish", "Unpublish document", "/api/corpus/documents/9/unpublish"],
  ["archive", "Archive document", "/api/corpus/documents/9/archive"],
  ["retry", "Retry processing", "/api/corpus/tasks/7/retry"],
] as const)("%s waits for explicit confirmation", async (action, label, path) => {
  const user = userEvent.setup(); jest.mocked(api.post).mockResolvedValue({});
  render(<AdminActionDialog task={task} action={action} {...callbacks} />);
  expect(api.post).not.toHaveBeenCalled();
  await user.click(screen.getByRole("button", { name: label }));
  expect(api.post).toHaveBeenCalledWith(path); expect(callbacks.onChanged).toHaveBeenCalled();
});

test("deletion failure remains visible and never claims success", async () => {
  const user = userEvent.setup(); jest.mocked(api.delete).mockRejectedValue(new ApiError(503, "Document hidden; cleanup failed"));
  render(<AdminActionDialog task={task} action="delete" {...callbacks} />);
  await user.click(screen.getByRole("button", { name: "Delete permanently" }));
  expect(api.delete).toHaveBeenCalledWith("/api/corpus/documents/9");
  await screen.findByText("Document hidden; cleanup failed"); expect(callbacks.onClose).not.toHaveBeenCalled();
});

test("failed upload without a document uses the upload cleanup endpoint", async () => {
  const user = userEvent.setup(); jest.mocked(api.delete).mockResolvedValue({});
  render(<AdminActionDialog task={{ ...task, document_id: null, status: "failed" }} action="delete" {...callbacks} />);
  await user.click(screen.getByRole("button", { name: "Delete permanently" }));
  expect(api.delete).toHaveBeenCalledWith("/api/corpus/tasks/7");
});

test("rename is a distinct operation from academic title editing", async () => {
  const user = userEvent.setup(); jest.mocked(api.patch).mockResolvedValue({});
  render(<AdminActionDialog task={task} action="rename" {...callbacks} />);
  await user.clear(screen.getByLabelText("File name")); await user.type(screen.getByLabelText("File name"), "updated.pdf");
  await user.click(screen.getByRole("button", { name: "Rename file" }));
  expect(api.patch).toHaveBeenCalledWith("/api/corpus/documents/9", { file_name: "updated.pdf" });
});

test("department form creates and edits normalized reference data", async () => {
  const user = userEvent.setup(); jest.mocked(api.post).mockResolvedValue({}); jest.mocked(api.patch).mockResolvedValue({});
  render(<DepartmentManager {...callbacks} />);
  await screen.findByText("Agronomy");
  await user.type(screen.getByLabelText("Department name"), "Food Science"); await user.type(screen.getByLabelText("Code"), "food");
  await user.click(screen.getByRole("button", { name: "Create department" }));
  expect(api.post).toHaveBeenCalledWith("/api/departments", { name: "Food Science", code: "FOOD", is_active: true });
  await user.click(await screen.findByRole("button", { name: "Edit Agronomy" }));
  await user.click(screen.getByRole("checkbox", { name: "Active" }));
  await user.click(screen.getByRole("button", { name: "Save department" }));
  expect(api.patch).toHaveBeenCalledWith("/api/departments/3", { name: "Agronomy", code: "AGR", is_active: true });
});
