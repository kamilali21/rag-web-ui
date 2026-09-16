import React, {
  FC,
  useMemo,
  useEffect,
  useState,
  ClassAttributes,
} from "react";
import { AnchorHTMLAttributes } from "react";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { Skeleton } from "@/components/ui/skeleton";
import { Divider } from "@/components/ui/divider";
import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeHighlight from "rehype-highlight";
import { api } from "@/lib/api";
import { FileIcon } from "react-file-icon";
import { remarkCitations } from "@/lib/citations";

// Debounce hook to prevent rapid state updates during streaming
const useDebouncedValue = <T,>(value: T, delay: number): T => {
  const [debouncedValue, setDebouncedValue] = useState<T>(value);

  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    return () => {
      clearTimeout(handler);
    };
  }, [value, delay]);

  return debouncedValue;
};

interface Citation {
  id: number;
  text: string;
  metadata: Record<string, any>;
}

interface KnowledgeBaseInfo {
  name: string;
}

interface DocumentInfo {
  file_name: string;
  knowledge_base: KnowledgeBaseInfo;
}

interface CitationInfo {
  knowledge_base: KnowledgeBaseInfo;
  document: DocumentInfo;
}

export const Answer: FC<{
  markdown: string;
  citations?: Citation[];
}> = ({ markdown, citations = [] }) => {
  const [citationInfoMap, setCitationInfoMap] = useState<
    Record<string, CitationInfo>
  >({});

  // Debounce citations to prevent rapid API calls during streaming
  const debouncedCitations = useDebouncedValue(citations, 300);

  const processedMarkdown = useMemo(() => {
    return markdown
      .replace(/<think>/g, "## 💭 深度思考\n```think")
      .replace(/<\/think>/g, "```");
  }, [markdown]);

  useEffect(() => {
    const fetchCitationInfo = async () => {
      const infoMap: Record<string, CitationInfo> = {};

      for (const citation of debouncedCitations) {
        const { kb_id, document_id } = citation.metadata;
        if (!kb_id || !document_id) continue;

        const key = `${kb_id}-${document_id}`;
        if (infoMap[key]) continue;

        try {
          const [kb, doc] = await Promise.all([
            api.get(`/api/knowledge-base/${kb_id}`),
            api.get(`/api/knowledge-base/${kb_id}/documents/${document_id}`),
          ]);

          infoMap[key] = {
            knowledge_base: {
              name: kb.name,
            },
            document: {
              file_name: doc.file_name,
              knowledge_base: {
                name: kb.name,
              },
            },
          };
        } catch (error) {
          console.error("Failed to fetch citation info:", error);
        }
      }

      setCitationInfoMap(infoMap);
    };

    if (debouncedCitations.length > 0) {
      fetchCitationInfo();
    }
  }, [debouncedCitations]);

  const CitationLink = useMemo(
    () =>
      (
        props: ClassAttributes<HTMLAnchorElement> &
          AnchorHTMLAttributes<HTMLAnchorElement>
      ) => {
        // Added by ChatGPT: support normalized markers and existing saved numeric citation links.
        const citationId = props.href?.match(/^(?:#citation-)?(\d+)$/)?.[1];
        const citation = citationId
          ? citations.find((item) => item.id === Number(citationId))
          : null;

        if (!citation) {
          return citationId ? <span title="Source unavailable">[{citationId}]</span> :
            <a href={props.href} className="text-blue-600 underline">{props.children}</a>;
        }

        const citationInfo =
          citationInfoMap[
            `${citation.metadata.kb_id}-${citation.metadata.document_id}`
          ];

        return (
          <Popover>
            <PopoverTrigger asChild>
              <button
                type="button"
                aria-label={`Source ${citationId}`}
                className="inline-flex min-w-6 items-center justify-center px-1 py-0.5 text-xs font-medium text-blue-600 bg-blue-50 rounded hover:bg-blue-100 transition-colors align-baseline"
              >
                [{citationId}]
              </button>
            </PopoverTrigger>
            <PopoverContent
              side="top"
              align="start"
              className="max-w-2xl w-[calc(100vw-100px)] p-4 rounded-lg shadow-lg"
            >
              <div className="text-sm space-y-3">
                {citationInfo && (
                  <div className="flex items-center gap-2 text-xs font-medium text-gray-700 bg-gray-50 p-2 rounded">
                    <div className="w-5 h-5 flex items-center justify-center">
                      <FileIcon
                        extension={
                          citationInfo.document.file_name.split(".").pop() || ""
                        }
                        color="#E2E8F0"
                        labelColor="#94A3B8"
                      />
                    </div>
                    <span className="truncate">
                      {citationInfo.knowledge_base.name} /{" "}
                      {citationInfo.document.file_name}
                    </span>
                  </div>
                )}
                <Divider />
                <p className="text-gray-700 leading-relaxed">{citation.text}</p>
                {/* Added by ChatGPT: show source location without exposing internal storage metadata. */}
                {Number.isInteger(citation.metadata.page) && citation.metadata.page >= 0 &&
                  <p className="text-xs text-gray-500">Page {citation.metadata.page + 1}</p>}
              </div>
            </PopoverContent>
          </Popover>
        );
      },
    [citations, citationInfoMap]
  );

  if (!markdown) {
    return (
      <div className="flex flex-col gap-2">
        <Skeleton className="max-w-sm h-4 bg-zinc-200" />
        <Skeleton className="max-w-lg h-4 bg-zinc-200" />
        <Skeleton className="max-w-2xl h-4 bg-zinc-200" />
        <Skeleton className="max-w-lg h-4 bg-zinc-200" />
        <Skeleton className="max-w-xl h-4 bg-zinc-200" />
      </div>
    );
  }

  return (
    <div className="prose prose-sm max-w-full">
      <Markdown
        remarkPlugins={[remarkGfm, [remarkCitations, { citationIds: citations.map((citation) => citation.id) }]]}
        rehypePlugins={[rehypeHighlight]}
        components={{
          a: CitationLink,
        }}
      >
        {processedMarkdown}
      </Markdown>
    </div>
  );
};
