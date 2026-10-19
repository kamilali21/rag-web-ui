import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import DashboardPage from "../page";
import { ThemeProvider } from "@/components/theme-provider";
import { api, ApiError } from "@/lib/api";

jest.mock("@/components/layout/dashboard-layout", () => ({ __esModule: true, default: ({ children }: { children: React.ReactNode }) => <>{children}</> }));
jest.mock("@/lib/api", () => ({ ...jest.requireActual("@/lib/api"), api: { get: jest.fn() } }));
let admin = false;
const get = async (path: string): Promise<any> => {
  if (path.startsWith("/api/knowledge-base/catalog?")) return { total: 120 };
  if (path === "/api/auth/me") return { roles: admin ? ["admin"] : ["researcher"] };
  if (path === "/api/researcher/admin/count") return { count: 7 };
  if (path === "/api/researcher/requests") return {
    publications: [
      { id: 1, metadata: { title: "Published paper" }, status: "published", publication_status: "published", created_at: "2026-10-01T12:00:00" },
      { id: 2, status: "published", publication_status: "published", created_at: "2026-10-02T12:00:00" },
      { id: 3, metadata: { title: "Pending paper" }, status: "pending", publication_status: null, created_at: "2026-10-03T12:00:00" },
      { id: 4, status: "published", publication_status: "archived", created_at: "2026-10-04T12:00:00" },
    ],
    withdrawals: [{ id: 11, publication_request_id: 2, status: "approved", created_at: "2026-10-05T12:00:00" }],
  };
  if (path === "/api/researcher/profile") return null;
  return [];
};
beforeEach(() => { jest.clearAllMocks(); localStorage.clear(); admin = false; jest.mocked(api.get).mockImplementation(get); });
const dashboard = () => render(<ThemeProvider><DashboardPage /></ThemeProvider>);

test("compact cards show owner counts, exclude archived/withdrawn papers, and retain the theme switch", async () => {
  localStorage.setItem("researchiq-theme", "dark");
  dashboard();
  expect(await screen.findByRole("link", { name: "My papers: 120" })).toHaveAttribute("href", "/dashboard/knowledge");
  expect(screen.getByRole("link", { name: "Published: 1" })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Publication requests: 1 awaiting review" })).toBeInTheDocument();
  expect(screen.queryByRole("link", { name: /add documents/i })).not.toBeInTheDocument();
  expect(screen.getByText("Pending paper")).toBeInTheDocument();
  expect(api.get).not.toHaveBeenCalledWith("/api/researcher/admin/count", expect.anything());
  const toggle = screen.getByRole("switch", { name: "Dark mode" });
  expect(toggle).toHaveAttribute("aria-checked", "true");
  await userEvent.click(toggle);
  expect(localStorage.getItem("researchiq-theme")).toBe("light");
});

test("researchers open the existing publication dialog directly from the dashboard", async () => {
  dashboard();
  await userEvent.click(await screen.findByRole("button", { name: "Publication requests: 1 awaiting review" }));
  const dialog = await screen.findByRole("dialog");
  expect(await within(dialog).findByText(/Complete your researcher profile/)).toBeInTheDocument();
  expect(within(dialog).getByRole("link", { name: "Open Profile" })).toHaveAttribute("href", "/dashboard/profile");
});

test("admins open the existing review queue and return to refreshed dashboard counts", async () => {
  admin = true; dashboard();
  await userEvent.click(await screen.findByRole("button", { name: "Publication requests: 7 awaiting review" }));
  expect(await screen.findByText("No requests need review")).toBeInTheDocument();
  expect(api.get).toHaveBeenCalledWith("/api/researcher/admin", expect.anything());
  await userEvent.click(screen.getByRole("button", { name: "Dashboard" }));
  expect(await screen.findByRole("heading", { name: "Your dashboard" })).toBeInTheDocument();
});

test("a failed admin count is unavailable, never a false zero", async () => {
  admin = true;
  jest.mocked(api.get).mockImplementation(path => path === "/api/researcher/admin/count" ? Promise.reject(new Error("offline")) : get(path));
  dashboard();
  await waitFor(() => expect(screen.getByRole("button", { name: "Publication requests: unavailable awaiting review" })).toBeEnabled());
  expect(screen.getByText("—")).toBeInTheDocument();
});

test("server denial removes admin review without exposing private data", async () => {
  admin = true;
  jest.mocked(api.get).mockImplementation(path => path === "/api/researcher/admin" ? Promise.reject(new ApiError(403, "Forbidden")) : get(path));
  dashboard();
  await userEvent.click(await screen.findByRole("button", { name: "Publication requests: 7 awaiting review" }));
  expect(await screen.findByText("Your publication review permission is no longer available.")).toBeInTheDocument();
  expect(screen.queryByRole("heading", { name: "Publication requests" })).not.toBeInTheDocument();
});

test("dashboard failure has a working retry and does not invent counts", async () => {
  jest.mocked(api.get).mockRejectedValue(new Error("offline")); dashboard();
  expect(await screen.findByRole("alert")).toHaveTextContent("Unable to load your dashboard");
  expect(screen.queryByRole("link", { name: /My papers:/ })).not.toBeInTheDocument();
  jest.mocked(api.get).mockImplementation(get);
  await userEvent.click(screen.getByRole("button", { name: "Retry" }));
  expect(await screen.findByRole("link", { name: "My papers: 120" })).toBeInTheDocument();
});
