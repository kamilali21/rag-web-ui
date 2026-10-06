import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import NewChatPage from "@/app/dashboard/chat/new/page";
import { api } from "@/lib/api";

const push = jest.fn();
jest.mock("next/navigation", () => ({ useRouter: () => ({ push, back: jest.fn() }) }));
jest.mock("@/components/layout/dashboard-layout", () => ({ __esModule: true, default: ({ children }: any) => <main>{children}</main> }));
jest.mock("@/lib/api", () => ({ api: { get: jest.fn(), post: jest.fn() }, ApiError: class extends Error {} }));

beforeEach(() => { jest.clearAllMocks(); window.history.replaceState({}, "", "/dashboard/chat/new"); });

it("starts a public conversation without private collections", async () => {
  (api.get as jest.Mock).mockResolvedValue([]);
  (api.post as jest.Mock).mockResolvedValue({ id: 42 });
  render(<NewChatPage />);
  fireEvent.change(screen.getByLabelText("Conversation title"), { target: { value: "Study" } });
  await waitFor(() => expect(screen.getByText(/No private collections/)).toBeVisible());
  expect(screen.getByRole("button", { name: "Start conversation" })).toBeDisabled();
  fireEvent.click(screen.getByRole("radio", { name: "Public" }));
  fireEvent.click(screen.getByRole("button", { name: "Start conversation" }));
  await waitFor(() => expect(api.post).toHaveBeenCalledWith("/api/chat/", {
    title: "Study", source_scope: "public", knowledge_base_ids: [],
  }));
  expect(push).toHaveBeenCalledWith("/dashboard/chat/42");
});

it("sends only checked private collections in Both mode", async () => {
  (api.get as jest.Mock).mockResolvedValue([{ id: 7, name: "Keep" }, { id: 8, name: "Exclude" }]);
  (api.post as jest.Mock).mockResolvedValue({ id: 43 });
  render(<NewChatPage />);
  fireEvent.click(await screen.findByRole("checkbox", { name: "Exclude" }));
  fireEvent.click(screen.getByRole("radio", { name: "Both" }));
  fireEvent.change(screen.getByLabelText("Conversation title"), { target: { value: "Combined" } });
  fireEvent.click(screen.getByRole("button", { name: "Start conversation" }));
  await waitFor(() => expect(api.post).toHaveBeenCalledWith("/api/chat/", {
    title: "Combined", source_scope: "both", knowledge_base_ids: [7],
  }));
});

it("honors the public Library entry and exposes request failures", async () => {
  window.history.replaceState({}, "", "/dashboard/chat/new?scope=public");
  (api.get as jest.Mock).mockResolvedValue([]);
  (api.post as jest.Mock).mockRejectedValue(new Error("offline"));
  render(<NewChatPage />);
  expect(screen.getByRole("radio", { name: "Public" })).toBeChecked();
  fireEvent.change(screen.getByLabelText("Conversation title"), { target: { value: "Study" } });
  fireEvent.click(screen.getByRole("button", { name: "Start conversation" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("Conversation could not be started");
  expect(push).not.toHaveBeenCalled();
});
