// Untrusted model output must not load remote images containing private source text in URLs.
export function answerImagePlaceholder({ alt }: { alt?: string }) {
  return `[Image omitted${alt ? `: ${alt}` : ""}]`;
}
