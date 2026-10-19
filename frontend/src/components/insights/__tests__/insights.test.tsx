import { act, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Insights } from "../insights";
import { api, ApiError } from "@/lib/api";

jest.mock("@/lib/api", () => ({ ...jest.requireActual("@/lib/api"), api: { get: jest.fn(), post: jest.fn() } }));
const paper = (id: number, scope = "public") => ({ id, knowledge_base_id: scope === "public" ? 8 : 3, scope,
  title: `Research paper ${id}`, file_name: `paper-${id}.pdf`, file_size: 2048, content_type: "application/pdf",
  authors_text: "Ayesha", department_id: 2, department_name: "Agronomy", document_type: "paper", publication_year: 2025,
  abstract: "Irrigation evidence", publication_status: "published", created_at: "2026-10-19T10:00:00" });
const rows = [paper(9), paper(8)];
const get = async (url: string): Promise<any> => {
  if (url.startsWith("/api/insights/documents?")) return { items: url.includes("scope=private") ? [paper(3, "private")] : rows, has_more: false };
  if (url.startsWith("/api/departments?")) return [{ id: 2, name: "Agronomy", code: "AGR", is_active: true }];
  if (url === "/api/departments/2") return { id: 2, name: "Agronomy" };
  if (url === "/api/corpus/documents/9" || url === "/api/corpus/documents/9/metadata") return rows[0];
  if (url === "/api/insights/documents/3?scope=private") return paper(3, "private");
  throw new Error(`Unexpected GET ${url}`);
};
beforeEach(() => {
  jest.clearAllMocks(); jest.mocked(api.get).mockImplementation(get);
  jest.mocked(api.post).mockResolvedValue({ documents: rows, scope: "public", mode: "compare" });
});
async function open() { const user = userEvent.setup(); render(<Insights />); await screen.findByRole("table", { name: "Research documents" }); return user; }

test("defaults to live public records with the Library table styles and no sample corpus", async () => {
  await open();
  expect(api.get).toHaveBeenCalledWith("/api/insights/documents?scope=public&limit=20", expect.anything());
  expect(screen.getByRole("table", { name: "Research documents" })).toHaveClass("library-table", "public-library-table");
  expect(screen.queryByText(/Sample corpus/)).not.toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Compare" })).toBeDisabled();
  expect(screen.getByRole("button", { name: "Analyse" })).toBeDisabled();
  expect(screen.getByText("Page 1")).toBeInTheDocument();
});

test("sends combined server filters, year range and scope; scope change clears selection", async () => {
  const user = await open();
  await user.click(screen.getByRole("checkbox", { name: "Select Research paper 9" }));
  await user.click(screen.getByRole("button", { name: "Toggle Insights filters" }));
  await user.type(screen.getByRole("searchbox", { name: "Search documents" }), "irrigation");
  await user.type(screen.getByLabelText("Author", { selector: "input" }), "Ayesha");
  await user.selectOptions(screen.getByLabelText("Department"), "2");
  await user.type(screen.getByLabelText("From year"), "2024");
  await user.type(screen.getByLabelText("To year"), "2026");
  await user.selectOptions(screen.getByLabelText("Type"), "paper");
  await user.click(screen.getByRole("button", { name: "Search" }));
  await waitFor(() => expect(api.get).toHaveBeenCalledWith("/api/insights/documents?scope=public&limit=20&search=irrigation&author=Ayesha&department_id=2&year_from=2024&year_to=2026&document_type=paper", expect.anything()));
  expect(screen.getByText("1 of 5 selected")).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Private" }));
  await screen.findByRole("button", { name: "Details for Research paper 3" });
  expect(screen.getByText("0 of 5 selected")).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Details for Research paper 9" })).not.toBeInTheDocument();
});

test("pagination retains selected IDs from previous pages and rechecks them before comparison", async () => {
  jest.mocked(api.get).mockImplementation(async url => url.startsWith("/api/insights/documents?") ?
    url.includes("before_id=8") ? { items: [paper(7)], has_more: false } : { items: rows, has_more: true } : get(url));
  jest.mocked(api.post).mockResolvedValue({ documents: [rows[0], { ...paper(7), title: "Updated metadata" }] });
  const user = await open();
  await user.click(screen.getByRole("checkbox", { name: "Select Research paper 9" }));
  await user.click(screen.getByRole("button", { name: "Next page" }));
  await user.click(await screen.findByRole("checkbox", { name: "Select Research paper 7" }));
  expect(screen.getByRole("button", { name: "Next page" })).toBeDisabled();
  await user.click(screen.getByRole("button", { name: "Compare" }));
  const dialog = within(screen.getByRole("dialog"));
  await user.click(dialog.getByRole("button", { name: "Open workspace" }));
  await dialog.findByText("Updated metadata");
  expect(api.post).toHaveBeenCalledWith("/api/insights/selection", { scope: "public", mode: "compare", document_ids: [9, 7] }, expect.anything());
  expect(dialog.getByText(/No AI findings have been generated/)).toBeInTheDocument();
  await user.keyboard("{Escape}");
  expect(screen.getByRole("button", { name: "Compare" })).toHaveFocus();
});

test("selection is capped at five without discarding earlier selections", async () => {
  jest.mocked(api.get).mockImplementation(async url => url.startsWith("/api/insights/documents?") ? { items: [9,8,7,6,5,4].map(id => paper(id)), has_more: false } : get(url));
  const user = await open();
  await user.click(screen.getByRole("checkbox", { name: "Select visible documents" }));
  expect(screen.getByText("5 of 5 selected")).toBeInTheDocument();
  expect(screen.getByRole("checkbox", { name: "Select Research paper 4" })).toBeDisabled();
  await user.click(screen.getByRole("checkbox", { name: "Select Research paper 9" }));
  expect(screen.getByRole("checkbox", { name: "Select Research paper 4" })).toBeEnabled();
});

test("revoked selection shows an error and never opens a fake result; retry revalidates", async () => {
  jest.mocked(api.post).mockRejectedValueOnce(new ApiError(404, "Selected documents are unavailable. Refresh your selection."));
  const user = await open();
  await user.click(screen.getByRole("checkbox", { name: "Select visible documents" }));
  await user.click(screen.getByRole("button", { name: "Compare" }));
  const dialog = within(screen.getByRole("dialog"));
  await user.click(dialog.getByRole("button", { name: "Open workspace" }));
  expect(await dialog.findByRole("alert")).toHaveTextContent("Selected documents are unavailable");
  expect(dialog.queryByRole("table")).not.toBeInTheDocument();
  await user.click(dialog.getByRole("button", { name: "Open workspace" }));
  expect(await dialog.findByRole("table", { name: "Verified document metadata" })).toBeInTheDocument();
});

test("analysis allows one document but contradictions configuration needs two", async () => {
  const user = await open();
  await user.click(screen.getByRole("checkbox", { name: "Select Research paper 9" }));
  await user.click(screen.getByRole("button", { name: "Analyse" }));
  const dialog = within(screen.getByRole("dialog"));
  expect(dialog.getByRole("button", { name: "Open workspace" })).toBeEnabled();
  await user.selectOptions(dialog.getByLabelText("Analysis focus"), "Contradictions");
  expect(dialog.getByRole("button", { name: "Open workspace" })).toBeDisabled();
  expect(api.post).not.toHaveBeenCalled();
});

test("public details reuse authorized file links and summaries; private details stay owner scoped", async () => {
  const user = await open();
  await user.click(screen.getByRole("button", { name: "Details for Research paper 9" }));
  let dialog = within(screen.getByRole("dialog"));
  expect(await dialog.findByRole("link", { name: "Open document" })).toHaveAttribute("href", "/api/corpus/documents/9/content?inline=true");
  expect(dialog.getByRole("button", { name: "Summarize paper" })).toBeInTheDocument();
  await user.keyboard("{Escape}");
  await user.click(screen.getByRole("button", { name: "Private" }));
  await user.click(await screen.findByRole("button", { name: "Details for Research paper 3" }));
  dialog = within(screen.getByRole("dialog"));
  expect(await dialog.findByRole("link", { name: "Open document" })).toHaveAttribute("href", "/api/knowledge-base/3/documents/3/content?inline=true");
});

test("empty and failed catalogs have honest states and a working retry", async () => {
  jest.mocked(api.get).mockImplementation(async url => url.startsWith("/api/insights/documents?") ? Promise.reject(new ApiError(503, "Catalog unavailable")) : get(url));
  const user = userEvent.setup(); render(<Insights />);
  expect(await screen.findByRole("alert")).toHaveTextContent("Catalog unavailable");
  expect(screen.queryByRole("table")).not.toBeInTheDocument();
  jest.mocked(api.get).mockImplementation(async url => url.startsWith("/api/insights/documents?") ? { items: [], has_more: false } : get(url));
  await user.click(screen.getByRole("button", { name: "Retry" }));
  expect(await screen.findByText("No ready documents in this scope")).toBeInTheDocument();
});

test("a late response cannot leak previous-scope rows after switching", async () => {
  let complete!: (value: any) => void;
  jest.mocked(api.get).mockImplementation(url => url.startsWith("/api/insights/documents?scope=public") ? new Promise(resolve => { complete = resolve; }) : get(url));
  const user = userEvent.setup(); render(<Insights />);
  await user.click(screen.getByRole("button", { name: "Private" }));
  await screen.findByRole("button", { name: "Details for Research paper 3" });
  await act(async () => complete({ items: rows, has_more: false }));
  expect(screen.queryByRole("button", { name: "Details for Research paper 9" })).not.toBeInTheDocument();
});
