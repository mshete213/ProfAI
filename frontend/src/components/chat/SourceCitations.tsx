import { useState } from "react";
import { ChevronDown, ChevronRight } from "lucide-react";
import type { ChatSource } from "../../lib/types";

export default function SourceCitations({ sources }: { sources: ChatSource[] }) {
  const [open, setOpen] = useState(false);

  if (!sources || sources.length === 0) return null;

  return (
    <div className="mt-2 rounded-md border border-gray-200 bg-gray-50 text-xs">
      <button
        onClick={() => setOpen(!open)}
        className="flex w-full items-center gap-1 px-3 py-2 text-left font-medium text-gray-700 hover:bg-gray-100"
      >
        {open ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
        {sources.length} source{sources.length === 1 ? "" : "s"}
      </button>
      {open && (
        <ul className="divide-y divide-gray-200 px-3 pb-2">
          {sources.map((src, i) => (
            <li key={i} className="py-2">
              <div className="font-medium text-gray-700">
                {src.filename || src.title || "Unknown source"}
                {src.page_number && <span className="ml-1 text-gray-500">p. {src.page_number}</span>}
                {src.slide_number && <span className="ml-1 text-gray-500">slide {src.slide_number}</span>}
                {src.timestamp_start !== undefined && (
                  <span className="ml-1 text-gray-500">
                    t={Math.round(src.timestamp_start)}s
                  </span>
                )}
              </div>
              {src.text && (
                <p className="mt-1 line-clamp-3 text-gray-600">{src.text}</p>
              )}
              {src.source_url && (
                <a
                  href={src.source_url}
                  target="_blank"
                  rel="noreferrer"
                  className="mt-1 inline-block text-primary-600 hover:underline"
                >
                  Open source
                </a>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
