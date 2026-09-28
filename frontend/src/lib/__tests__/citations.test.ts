// Added by ChatGPT: saved/streaming citation decoding and safe Markdown transformations.
import { TextDecoder } from "util";
import { decodeChatAnswer, remarkCitations } from "../citations";

Object.assign(globalThis, { TextDecoder });

describe("citation decoding", () => {
  it("decodes UTF-8 evidence and preserves the rest of an answer", () => {
    const source = { context: [{ page_content: "Research café", metadata: { page: 2 } }] };
    const envelope = Buffer.from(JSON.stringify(source)).toString("base64");
    expect(decodeChatAnswer(`${envelope}__LLM_RESPONSE__Result [citation:1] __LLM_RESPONSE__`)).toEqual({
      content: "Result [citation:1] __LLM_RESPONSE__",
      citations: [{ id: 1, text: "Research café", metadata: { page: 2 } }],
    });
  });

  it("leaves plain messages intact and tolerates malformed metadata", () => {
    expect(decodeChatAnswer("Plain answer")).toEqual({ content: "Plain answer" });
    expect(decodeChatAnswer("invalid__LLM_RESPONSE__Answer")).toEqual({ content: "Answer" });
  });
});

describe("citation Markdown transform", () => {
  it.each(["[citation:1]", "[citation: 1]", "[[citation:1]]", "[1]", "【1】", "【citation:1】"]) ("links known marker %s", (value) => {
    const tree = { type: "root", children: [{ type: "text", value }] };
    remarkCitations({ citationIds: [1] })(tree);
    expect(tree.children).toEqual([{ type: "link", url: "#citation-1", children: [{ type: "text", value: "[1]" }] }]);
  });

  it("preserves unknown references, code and existing links", () => {
    const tree = { type: "root", children: [
      { type: "text", value: "Unknown [citation:9]" },
      { type: "inlineCode", value: "[citation:1]" },
      { type: "code", value: "[1]" },
      { type: "link", url: "https://example.com", children: [{ type: "text", value: "[1]" }] },
    ] };
    const before = JSON.stringify(tree);
    remarkCitations({ citationIds: [1] })(tree);
    expect(JSON.stringify(tree)).toBe(before);
  });
});
