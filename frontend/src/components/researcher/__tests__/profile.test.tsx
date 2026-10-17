import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ResearcherProfile } from "../profile";
import { api } from "@/lib/api";

const mockReplace = jest.fn();
jest.mock("next/navigation", () => ({ useRouter: () => ({ replace: mockReplace }) }));
jest.mock("@/lib/api", () => ({ api: { get: jest.fn(), post: jest.fn(), put: jest.fn(), delete: jest.fn() }, ApiError: class ApiError extends Error {} }));

beforeEach(() => {
  jest.clearAllMocks();
  jest.mocked(api.get).mockImplementation(async (path) => {
    if (String(path) === "/api/researcher/profile") return null;
    if (String(path) === "/api/departments?limit=100") return [];
    return { publications: [], withdrawals: [] };
  });
  jest.mocked(api.post).mockResolvedValue({ message: "Signed out" });
});

test("Profile offers the same red sign-out action and preserves the existing logout flow", async () => {
  render(<ResearcherProfile />);
  const button = await screen.findByRole("button", { name: "Sign out" });
  expect(button).toHaveClass("profile-signout-button");
  await userEvent.click(button);
  expect(api.post).toHaveBeenCalledWith("/api/auth/logout");
  expect(mockReplace).toHaveBeenCalledWith("/login");
});
