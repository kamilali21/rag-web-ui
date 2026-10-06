// Added by ChatGPT: verify source triggers independently of ESM Markdown parser internals.
import React from "react";
import { fireEvent, render, screen } from "@testing-library/react";
import { Answer } from "../answer";

jest.mock("@/lib/api", () => ({ api: { get: jest.fn() } }));
jest.mock("remark-gfm", () => ({}));
jest.mock("rehype-highlight", () => ({}));
jest.mock("react-file-icon", () => ({ FileIcon: () => null }));
jest.mock("react-markdown", () => function MockMarkdown({ components }: any) {
  const Link = components.a;
  return <><Link href="#citation-1">[1]</Link><Link href="https://example.com">Original link</Link></>;
});

it("opens the current source immediately when streaming citations arrive", () => {
  const { rerender } = render(<Answer markdown="Answer" citations={[]} />);
  expect(screen.queryByRole("button", { name: "Source 1" })).not.toBeInTheDocument();
  rerender(<Answer markdown="Answer" citations={[{ id: 1, text: "Verified source excerpt", metadata: { page: 2 } }]} />);
  fireEvent.click(screen.getByRole("button", { name: "Source 1" }));
  expect(screen.getByText("Verified source excerpt")).toBeVisible();
  expect(screen.getByText("Page 3")).toBeVisible();
  expect(screen.getByRole("link", { name: "Original link" })).toHaveAttribute("href", "https://example.com");
});

it("shows SQL bibliography and opens the public PDF at its cited page", async () => {
  render(<Answer markdown="Answer" citations={[{ id: 1, text: "Measured excerpt", metadata: {
    kb_id: 4, document_id: 9, scope: "public", page: 2,
    title: "Verified study", knowledge_base_name: "UAF Corpus", authors: "SQL Author",
    department: "Agronomy", year: 2026,
  } }]} />);
  fireEvent.click(screen.getByRole("button", { name: "Source 1" }));
  expect(await screen.findByText("UAF Corpus / Verified study")).toBeVisible();
  expect(screen.getByText("SQL Author")).toBeVisible();
  expect(screen.getByText("Agronomy · 2026")).toBeVisible();
  expect(screen.getByRole("link", { name: "Open source document" })).toHaveAttribute("href", "/api/corpus/documents/9/content?inline=true#page=3");
  expect(require("@/lib/api").api.get).not.toHaveBeenCalled();
});
