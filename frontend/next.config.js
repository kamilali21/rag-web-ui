/** @type {import('next').NextConfig} */
module.exports = {
  output: "standalone",
  // Added by ChatGPT: isolate local previews from the running Docker frontend's build output.
  distDir: process.env.RAG_NEXT_DIST_DIR || ".next",
  // Added by ChatGPT: optional local API proxy; Docker continues to use its existing Nginx routes.
  async rewrites() {
    const origin = process.env.RAG_API_PROXY_URL;
    return origin ? [{ source: "/api/:path*", destination: `${origin.replace(/\/$/, "")}/api/:path*` }] : [];
  },
  experimental: {
    // This is needed for standalone output to work correctly
    outputFileTracingRoot: undefined,
    outputStandalone: true,
    skipMiddlewareUrlNormalize: true,
    skipTrailingSlashRedirect: true,
  },
};
