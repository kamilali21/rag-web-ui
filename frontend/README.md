<!-- Added by ChatGPT: reference design implementation and local verification notes. -->
## Reference UI Update

The frontend now uses the supplied forest-green, lime, and warm-white Library design.
Added or replaced implementation blocks are marked with `Added by ChatGPT` comments.

- Library and collection pages use real private knowledge-base documents.
- Public remains unavailable until a shared-corpus backend is implemented.
- Papers, Theses, and Reports are filename filters; the backend does not yet supply academic document types.
- Collection management, upload/preview/process, and existing chat routes remain available.
- Small screens use a keyboard-accessible navigation drawer and stacked document rows.

With the existing Docker stack running on port 80, start an isolated frontend preview:

```bash
RAG_NEXT_DIST_DIR=.next-preview RAG_API_PROXY_URL=http://127.0.0.1 npm run dev -- --hostname 127.0.0.1 --port 3001
```

Open [Library](http://127.0.0.1:3001/dashboard/knowledge). Sign in normally; this port has its own browser storage.
The optional API proxy affects only this frontend preview. Docker still uses its Nginx routing.
The reference image's decorative browser frame is not rendered inside the application.

Verification commands:

```bash
npm run test:ci -- --runInBand
RAG_NEXT_DIST_DIR=.next-check npm run build
```

This is a [Next.js](https://nextjs.org) project bootstrapped with [`create-next-app`](https://nextjs.org/docs/app/api-reference/cli/create-next-app).

## Getting Started

First, run the development server:

```bash
npm run dev
# or
yarn dev
# or
pnpm dev
# or
bun dev
```

Open [http://localhost:3000](http://localhost:3000) with your browser to see the result.

You can start editing the page by modifying `app/page.tsx`. The page auto-updates as you edit the file.

<!-- Added by ChatGPT: typography follows the reference without a network font download. -->
The frontend uses the local Arial/Helvetica sans-serif stack defined in `src/app/globals.css`.

## Learn More

To learn more about Next.js, take a look at the following resources:

- [Next.js Documentation](https://nextjs.org/docs) - learn about Next.js features and API.
- [Learn Next.js](https://nextjs.org/learn) - an interactive Next.js tutorial.

You can check out [the Next.js GitHub repository](https://github.com/vercel/next.js) - your feedback and contributions are welcome!

## Deploy on Vercel

The easiest way to deploy your Next.js app is to use the [Vercel Platform](https://vercel.com/new?utm_medium=default-template&filter=next.js&utm_source=create-next-app&utm_campaign=create-next-app-readme) from the creators of Next.js.

Check out our [Next.js deployment documentation](https://nextjs.org/docs/app/building-your-application/deploying) for more details.
