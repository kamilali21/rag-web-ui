import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import DashboardPage from "../page";
import { ThemeProvider } from "@/components/theme-provider";
import { api } from "@/lib/api";

jest.mock("@/components/layout/dashboard-layout", () => ({
  __esModule: true,
  default: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));
jest.mock("@/lib/api", () => ({ api: { get: jest.fn() } }));

beforeEach(() => {
  localStorage.clear();
  jest.mocked(api.get).mockResolvedValue([]);
});

test("dashboard replaces Add Documents with a persistent dark-mode switch", async () => {
  localStorage.setItem("researchiq-theme", "dark");
  render(<ThemeProvider><DashboardPage /></ThemeProvider>);

  const toggle = await screen.findByRole("switch", { name: "Dark mode" });
  expect(toggle).toHaveAttribute("aria-checked", "true");
  expect(screen.queryByRole("link", { name: /add documents/i })).not.toBeInTheDocument();

  await userEvent.click(toggle);
  expect(toggle).toHaveAttribute("aria-checked", "false");
  expect(localStorage.getItem("researchiq-theme")).toBe("light");
});
