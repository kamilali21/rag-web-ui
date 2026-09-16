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
