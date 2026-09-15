import type { Metadata } from "next";
import "./globals.css";
import "highlight.js/styles/github.css";
// 如果使用 App Router
import { Toaster } from "@/components/ui/toaster";

// Added by ChatGPT: use the reference's compact sans-serif through the local CSS font stack.

export const metadata: Metadata = {
  title: "RAG Web UI",
  description: "A web UI for RAG applications",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        {children}
        <Toaster />
      </body>
    </html>
  );
}
