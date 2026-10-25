import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { AIProviderSettings } from "../ai-provider-settings";
import { api, ApiError } from "@/lib/api";

jest.mock("@/lib/api", () => ({ api: { get: jest.fn(), put: jest.fn(), post: jest.fn(), delete: jest.fn() },
  ApiError: class extends Error { constructor(public status: number, message: string) { super(message); } } }));
const none = { configured: false, provider: null, model: null, key_last4: null };
const saved = { configured: true, provider: "openrouter", model: "openrouter/free", key_last4: "1234" };
beforeEach(() => { jest.clearAllMocks(); (api.get as jest.Mock).mockResolvedValue(none); });

test("save sends only selected settings and clears key without browser storage", async () => {
  const storage = jest.spyOn(Storage.prototype, "setItem");
  (api.put as jest.Mock).mockResolvedValue(saved);
  render(<AIProviderSettings />);
  const key = await screen.findByLabelText("API key");
  fireEvent.change(key, { target: { value: "sk-private-test-value" } });
  fireEvent.click(screen.getByRole("checkbox"));
  fireEvent.click(screen.getByRole("button", { name: "Save AI settings" }));
  await screen.findByText(/Private AI settings saved/);
  expect(api.put).toHaveBeenCalledWith("/api/ai-settings", { provider: "openrouter", model: "openrouter/free", api_key: "sk-private-test-value", consent: true });
  expect(key).toHaveValue(""); expect(storage).not.toHaveBeenCalled();
  expect(screen.getByText(/key ending 1234/)).toBeInTheDocument();
  storage.mockRestore();
});

test("provider switch selects supported model and requires a replacement key", async () => {
  (api.get as jest.Mock).mockResolvedValue(saved);
  render(<AIProviderSettings />);
  await screen.findByText(/key ending 1234/);
  fireEvent.change(screen.getByLabelText("Provider"), { target: { value: "openai" } });
  expect(screen.getByLabelText("Model")).toHaveValue("gpt-4.1-mini");
  expect(screen.getByLabelText("API key")).toBeRequired();
});

test("check uses saved key, remove restores default, errors do not expose input", async () => {
  (api.get as jest.Mock).mockResolvedValue(saved);
  (api.post as jest.Mock).mockResolvedValue({ message: "Connection accepted" });
  (api.delete as jest.Mock).mockResolvedValue(none);
  render(<AIProviderSettings />);
  fireEvent.click(await screen.findByRole("button", { name: "Check saved connection" }));
  await screen.findByText("Connection accepted");
  expect(api.post).toHaveBeenCalledWith("/api/ai-settings/check");
  fireEvent.click(screen.getByRole("button", { name: "Remove personal key" }));
  await screen.findByText(/Personal key removed/);
  expect(screen.queryByRole("button", { name: "Check saved connection" })).not.toBeInTheDocument();
  (api.put as jest.Mock).mockRejectedValue(new ApiError(503, "Storage unavailable"));
  const key = screen.getByLabelText("API key");
  fireEvent.change(key, { target: { value: "sk-do-not-keep" } });
  fireEvent.click(screen.getByRole("checkbox"));
  fireEvent.click(screen.getByRole("button", { name: "Save AI settings" }));
  await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent("Storage unavailable"));
  expect(key).toHaveValue("");
});
