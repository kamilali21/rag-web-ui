import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { api, ApiError } from "@/lib/api";
import APIKeysPage from "../page";

jest.mock("@/components/layout/dashboard-layout", () => ({
  __esModule: true,
  default: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));
jest.mock("@/lib/api", () => ({
  ...jest.requireActual("@/lib/api"),
  api: { get: jest.fn(), delete: jest.fn() },
}));
const mockToast = jest.fn();
jest.mock("@/components/ui/use-toast", () => ({ useToast: () => ({ toast: mockToast }) }));

beforeEach(() => {
  jest.clearAllMocks();
  jest.mocked(api.get).mockResolvedValue([{
    id: 7, name: "Test integration", key: "test-key", is_active: true,
    created_at: "2026-10-09T00:00:00Z", last_used_at: null,
  }]);
});

test("successful API key deletion accepts the helper's empty response", async () => {
  jest.mocked(api.delete).mockResolvedValue(undefined);
  const user = userEvent.setup();
  render(<APIKeysPage />);
  await screen.findByText("Test integration");
  await act(async () => { await user.click(screen.getByRole("button", { name: "Delete" })); });
  expect(api.delete).toHaveBeenCalledWith("/api/api-keys/7");
  await waitFor(() => expect(screen.queryByText("Test integration")).not.toBeInTheDocument());
  expect(mockToast).toHaveBeenCalledWith(expect.objectContaining({ title: "Success" }));
});

test("failed API key deletion retains the row and shows an error", async () => {
  jest.mocked(api.delete).mockRejectedValue(new ApiError(503, "Unavailable"));
  const user = userEvent.setup();
  render(<APIKeysPage />);
  await screen.findByText("Test integration");
  await act(async () => { await user.click(screen.getByRole("button", { name: "Delete" })); });
  await waitFor(() => expect(mockToast).toHaveBeenCalledWith(expect.objectContaining({ title: "Error" })));
  expect(screen.getByText("Test integration")).toBeInTheDocument();
});
