"use client";

import { ChevronRight } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";

// Added by ChatGPT: reference-style labels preserve the existing URLs.
const labels: Record<string, string> = { knowledge: "Library", "api-keys": "API Keys", "test-retrieval": "Test Retrieval" };

export default function Breadcrumb() {
  const paths = usePathname().split("/").filter(Boolean);
  return (
    <nav aria-label="Breadcrumb" className="app-breadcrumb">
      <Link href="/">Home</Link>
      {paths.map((path, index) => {
        const label = labels[path] || (/^\d+$/.test(path) ? "Collection" : path.charAt(0).toUpperCase() + path.slice(1));
        const href = "/" + paths.slice(0, index + 1).join("/");
        return (
          <span key={href} className="breadcrumb-part">
            <ChevronRight size={16} aria-hidden="true" />
            {index === paths.length - 1 ? <span aria-current="page">{label}</span> : <Link href={href}>{label}</Link>}
          </span>
        );
      })}
    </nav>
  );
}
