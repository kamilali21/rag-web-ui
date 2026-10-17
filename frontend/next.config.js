/** @type {import('next').NextConfig} */
const path = require("node:path");

module.exports = {
  output: "standalone",
  // Keep output tracing inside this app rather than a parent user's lockfile on Windows.
  outputFileTracingRoot: path.join(__dirname),
  // Added by ChatGPT: isolate local previews from the running Docker frontend's build output.
  distDir: process.env.RAG_NEXT_DIST_DIR || ".next",
  // Added by ChatGPT: optional local API proxy; Docker continues to use its existing Nginx routes.
  async rewrites() {
    const origin = process.env.RAG_API_PROXY_URL;
    return origin ? [{ source: "/api/:path*", destination: `${origin.replace(/\/$/, "")}/api/:path*` }] : [];
  },
};
