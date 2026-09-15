// Added by ChatGPT: behavior coverage for filtering, persistent selection and local-only workflows.
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Insights } from "../insights";
import { sampleDocuments } from "../sample-documents";

test("combines search, department and dates, and clears an empty result", async () => {
  const user = userEvent.setup();
  render(<Insights />);
  await user.click(screen.getByRole("button", { name: "Filters" }));
  await user.selectOptions(screen.getByLabelText("Department"), "Agronomy");
  expect(screen.getByRole("button", { name: sampleDocuments[2].name })).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: sampleDocuments[0].name })).not.toBeInTheDocument();
  await user.type(screen.getByRole("searchbox", { name: "Search documents" }), "fatima");
  expect(screen.getByRole("button", { name: sampleDocuments[2].name })).toBeInTheDocument();
  await user.type(screen.getByLabelText("From date"), "2024-03-09");
  expect(screen.getByText("No matching documents")).toBeInTheDocument();
  await user.click(screen.getAllByRole("button", { name: "Clear filters" })[0]);
  expect(screen.getAllByRole("checkbox")).toHaveLength(6);
});

test("preserves hidden selections and enforces the comparison minimum", async () => {
  const user = userEvent.setup();
  render(<Insights />);
  await user.click(screen.getByRole("checkbox", { name: `Select ${sampleDocuments[0].name}` }));
  await user.type(screen.getByRole("searchbox", { name: "Search documents" }), "soil");
  await user.click(screen.getByRole("checkbox", { name: "Select all visible documents" }));
  await user.click(screen.getByRole("button", { name: "Compare" }));
  const dialog = within(screen.getByRole("dialog"));
  expect(dialog.getByRole("button", { name: "Open comparison" })).toBeEnabled();
  await user.click(dialog.getByLabelText(new RegExp(sampleDocuments[0].name.replace(".pdf", ""))));
  expect(dialog.getByRole("button", { name: "Open comparison" })).toBeDisabled();
  await user.click(dialog.getByLabelText(new RegExp(sampleDocuments[0].name.replace(".pdf", ""))));
  await user.type(dialog.getByRole("textbox", { name: /Research question/ }), "Compare crop resilience");
  await user.click(dialog.getByRole("button", { name: "Open comparison" }));
  expect(dialog.getByText("Compare crop resilience")).toBeInTheDocument();
  expect(dialog.getByRole("table")).toBeInTheDocument();
  await user.click(dialog.getByRole("button", { name: "Key findings" }));
  expect(dialog.getByText(/No findings have been generated/)).toBeInTheDocument();
  await user.click(dialog.getByRole("button", { name: "Edit selection" }));
  expect(dialog.getByRole("textbox", { name: /Research question/ })).toHaveValue("Compare crop resilience");
  await user.keyboard("{Escape}");
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Compare" })).toHaveFocus();
});

test("requires two documents for contradictions and never requests an analysis backend", async () => {
  const user = userEvent.setup();
  const originalFetch = global.fetch;
  const fetchMock = jest.fn();
  global.fetch = fetchMock;
  try {
    render(<Insights />);
    await user.click(screen.getByRole("button", { name: "Analyse" }));
    const dialog = within(screen.getByRole("dialog"));
    expect(dialog.getByRole("button", { name: "Open analysis" })).toBeDisabled();
    await user.click(dialog.getByLabelText(new RegExp(sampleDocuments[0].name.replace(".pdf", ""))));
    expect(dialog.getByRole("button", { name: "Open analysis" })).toBeEnabled();
    await user.selectOptions(dialog.getByLabelText("Analysis focus"), "Contradictions");
    expect(dialog.getByRole("button", { name: "Open analysis" })).toBeDisabled();
    await user.click(dialog.getByLabelText(new RegExp(sampleDocuments[1].name.replace(".pdf", ""))));
    await user.click(dialog.getByRole("button", { name: "Open analysis" }));
    await user.click(dialog.getByRole("button", { name: "Contradictions" }));
    expect(dialog.getByText(/Conflicting claims need source passages/)).toBeInTheDocument();
    expect(fetchMock).not.toHaveBeenCalled();
  } finally { global.fetch = originalFetch; }
});

test("sorts documents and updates selection through the document details dialog", async () => {
  const user = userEvent.setup();
  render(<Insights />);
  await user.selectOptions(screen.getByRole("combobox", { name: "Sort documents" }), "oldest");
  const rows = screen.getAllByRole("row");
  expect(within(rows[1]).getByRole("button", { name: sampleDocuments[4].name })).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: sampleDocuments[4].name }));
  await user.click(within(screen.getByRole("dialog")).getByRole("button", { name: "Select document" }));
  await user.keyboard("{Escape}");
  expect(screen.getByRole("checkbox", { name: `Select ${sampleDocuments[4].name}` })).toBeChecked();
});
