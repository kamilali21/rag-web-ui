// Added by ChatGPT: shared citation decoding for both saved and streamed answers.
export interface Citation {
  id: number;
  text: string;
  metadata: Record<string, any>;
}

export function decodeChatAnswer(content: string): { content: string; citations?: Citation[] } {
  const separator = "__LLM_RESPONSE__";
  const position = content.indexOf(separator);
  if (position < 0) return { content };
  const answer = content.slice(position + separator.length);
  try {
    const bytes = Uint8Array.from(atob(content.slice(0, position).trim()), (char) => char.charCodeAt(0));
    const data = JSON.parse(new TextDecoder().decode(bytes));
    if (!Array.isArray(data.context)) return { content: answer };
    return { content: answer, citations: data.context.map((item: { page_content?: string; metadata?: Record<string, any> }, index: number) => ({
      id: index + 1, text: item.page_content ?? "", metadata: item.metadata ?? {},
    })) };
  } catch {
    return { content: answer };
  }
}

type MarkdownNode = { type: string; value?: string; url?: string; children?: MarkdownNode[] };

// Added by ChatGPT: transform parsed text nodes only, never code, HTML, or existing links.
export function remarkCitations({ citationIds }: { citationIds: number[] }) {
  const allowed = new Set(citationIds);
  return (tree: MarkdownNode) => {
    const visit = (parent: MarkdownNode) => {
      if (["link", "linkReference", "code", "inlineCode", "html"].includes(parent.type) || !parent.children) return;
      parent.children = parent.children.flatMap((node): MarkdownNode[] => {
        if (node.type !== "text" || !node.value) { visit(node); return [node]; }
        const pieces: MarkdownNode[] = [];
        let offset = 0;
        for (const match of node.value.matchAll(/\[?\[\s*(?:citation\s*:\s*)?(\d+)\s*\]\]?/gi)) {
          const id = Number(match[1]);
          if (!allowed.has(id)) continue;
          const index = match.index!;
          if (index > offset) pieces.push({ type: "text", value: node.value.slice(offset, index) });
          pieces.push({ type: "link", url: `#citation-${id}`, children: [{ type: "text", value: `[${id}]` }] });
          offset = index + match[0].length;
        }
        if (!offset) return [node];
        if (offset < node.value.length) pieces.push({ type: "text", value: node.value.slice(offset) });
        return pieces;
      });
    };
    visit(tree);
  };
}
