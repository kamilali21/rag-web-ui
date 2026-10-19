import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { api } from "@/lib/api";
import { Library } from "../library";
import { PublicationRequestDialog } from "../researcher-publication-dialogs";

jest.mock("@/lib/api", () => ({ ...jest.requireActual("@/lib/api"), api: { get: jest.fn(), post: jest.fn(), delete: jest.fn(), put: jest.fn() } }));
jest.mock("../document-upload-steps", () => ({ DocumentUploadSteps: () => <div>Upload flow</div> }));

const readyFile = { id: 41, knowledge_base_id: 7, file_name: "study.pdf", file_size: 5000, content_type: "application/pdf",
  created_at: "2026-10-01T12:00:00", processing_tasks: [{ id: 51, status: "completed" }] };

beforeEach(() => {
  jest.clearAllMocks();
  jest.mocked(api.get).mockImplementation(async (url: string) => {
    if (url.startsWith("/api/knowledge-base/catalog?")) return { items: [readyFile], total: 1, has_active_tasks: false };
    if (url.startsWith("/api/knowledge-base?")) return [{ id: 7, name: "My papers", documents: [] }];
    if (url === "/api/researcher/eligible-documents") return [readyFile];
    if (url === "/api/researcher/profile") return { full_name: "Ayesha", department_id: 3 };
    if (url.startsWith("/api/departments?")) return [{ id: 3, name: "Agronomy", code: "AGR", is_active: true }];
    throw new Error(`Unexpected API GET ${url}`);
  });
  jest.mocked(api.post).mockResolvedValue({ id: 12, status: "pending" });
});

test("shared publication dialog submits a single ready document with required metadata and explicit card consent", async () => {
  const user = userEvent.setup();
  render(<PublicationRequestDialog open onOpenChange={jest.fn()} onCreated={jest.fn()} />);
  const dialog = await screen.findByRole("dialog");
  await within(dialog).findByLabelText("Private document");
  await user.type(within(dialog).getByLabelText("Title"), "Water efficient farming");
  await user.type(within(dialog).getByLabelText("Author(s)"), "Ayesha Researcher");
  await user.selectOptions(within(dialog).getByLabelText("Department"), "3");
  await user.selectOptions(within(dialog).getByLabelText("Document type"), "paper");
  await user.click(within(dialog).getByRole("checkbox"));
  await user.click(within(dialog).getByRole("button", { name: "Send request" }));
  await within(dialog).findByText(/Your request was sent for review/);
  await waitFor(() => expect(api.post).toHaveBeenCalledWith("/api/researcher/requests", expect.objectContaining({
    source_document_id: 41, public_card_consent: true,
    metadata: expect.objectContaining({ title: "Water efficient farming", authors_text: "Ayesha Researcher", department_id: 3, document_type: "paper" }),
  })));
});

test("publication request requires a profile before showing the submission form", async () => {
  jest.mocked(api.get).mockImplementation(async (url: string) => {
    if (url.startsWith("/api/knowledge-base/catalog?")) return { items: [readyFile], total: 1, has_active_tasks: false };
    if (url.startsWith("/api/knowledge-base?")) return [{ id: 7, name: "My papers", documents: [] }];
    if (url === "/api/researcher/eligible-documents") return [readyFile];
    if (url === "/api/researcher/profile") return null;
    if (url.startsWith("/api/departments?")) return [{ id: 3, name: "Agronomy", code: "AGR", is_active: true }];
    throw new Error(`Unexpected API GET ${url}`);
  });
  const user = userEvent.setup();
  render(<PublicationRequestDialog open onOpenChange={jest.fn()} onCreated={jest.fn()} />);
  const dialog = await screen.findByRole("dialog");
  expect(await within(dialog).findByText(/Complete your researcher profile/)).toBeInTheDocument();
  expect(within(dialog).getByRole("link", { name: "Open Profile" })).toHaveAttribute("href", "/dashboard/profile");
  expect(within(dialog).queryByLabelText("Author(s)")).not.toBeInTheDocument();
});

test("ready private document details offer the temporary summary action", async () => {
  const user = userEvent.setup();
  render(<Library />);
  await screen.findByText("study.pdf");
  await user.click(screen.getByRole("button", { name: "Details for study.pdf" }));
  const dialog = await screen.findByRole("dialog");
  expect(await within(dialog).findByRole("button", { name: "Summarize paper" })).toBeInTheDocument();
});
