import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import DashboardLayout, { dashboardConfig } from "../dashboard-layout";
import { api } from "@/lib/api";

const mockReplace = jest.fn();
let mockActivePath = "/dashboard";
jest.mock("next/navigation", () => ({
  usePathname: () => mockActivePath,
  useRouter: () => ({ replace: mockReplace }),
}));
jest.mock("@/lib/api", () => ({ api: { get: jest.fn(), post: jest.fn() }, ApiError: class ApiError extends Error {} }));
jest.mock("@/components/theme-provider", () => ({ useTheme: () => ({ isDark: false }) }));

beforeEach(() => {
  jest.clearAllMocks();
  mockActivePath = "/dashboard";
  jest.mocked(api.get).mockImplementation(async (path) => String(path) === "/api/auth/me"
    ? { username: "researcher1" }
    : { full_name: "Amina Researcher", photo_url: null });
});

test("hides API Keys from navigation and places Profile last", () => {
  const navigation = dashboardConfig.sidebarNav;
  expect(navigation.map(({ title }) => title)).not.toContain("API Keys");
  expect(navigation[navigation.length - 1]).toMatchObject({ title: "Profile", href: "/dashboard/profile" });
});

test("shows Insights locked and opens the identity-backed account menu from the profile card", async () => {
  mockActivePath = "/dashboard/insights";
  render(<DashboardLayout><div>Page content</div></DashboardLayout>);
  const insights = await screen.findByRole("link", { name: "Insights, locked preview" });
  expect(insights).toHaveAttribute("href", "/dashboard/insights");
  const accountButton = await screen.findByRole("button", { name: "Open account menu" });
  expect(accountButton).toHaveTextContent("Amina Researcher");
  expect(screen.queryByRole("button", { name: "Sign out" })).not.toBeInTheDocument();
  await userEvent.click(accountButton);
  expect(accountButton).toHaveAttribute("aria-expanded", "true");
  expect(screen.getAllByText("@researcher1")).toHaveLength(2);
  expect(screen.getByRole("link", { name: "View profile" })).toHaveAttribute("href", "/dashboard/profile");
  expect(screen.getByRole("button", { name: "Sign out" })).toBeInTheDocument();
});

test("falls back to the signed-in username when no researcher profile exists", async () => {
  jest.mocked(api.get).mockImplementation(async (path) => String(path) === "/api/auth/me"
    ? { username: "researcher1" } : null);
  render(<DashboardLayout><div>Page content</div></DashboardLayout>);
  expect(await screen.findByRole("button", { name: "Open account menu" })).toHaveTextContent("researcher1");
});

test("sign out still revokes the server session and routes to login", async () => {
  jest.mocked(api.post).mockResolvedValue({ message: "Signed out" });
  render(<DashboardLayout><div>Page content</div></DashboardLayout>);
  await userEvent.click(await screen.findByRole("button", { name: "Open account menu" }));
  await userEvent.click(await screen.findByRole("button", { name: "Sign out" }));
  expect(api.post).toHaveBeenCalledWith("/api/auth/logout");
  expect(mockReplace).toHaveBeenCalledWith("/login");
});
