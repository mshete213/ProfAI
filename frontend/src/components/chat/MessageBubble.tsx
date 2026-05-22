import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeHighlight from "rehype-highlight";
import SourceCitations from "./SourceCitations";
import type { ChatSource } from "../../lib/types";

interface Props {
  role: "user" | "assistant";
  content: string;
  sources?: ChatSource[];
  streaming?: boolean;
}

export default function MessageBubble({ role, content, sources, streaming }: Props) {
  const isUser = role === "user";
  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[80%] rounded-lg px-4 py-3 ${
          isUser ? "bg-primary-600 text-white" : "border border-gray-200 bg-white"
        }`}
      >
        {isUser ? (
          <p className="whitespace-pre-wrap text-sm">{content}</p>
        ) : (
          <div className="prose prose-sm max-w-none">
            <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeHighlight]}>
              {content || (streaming ? "…" : "")}
            </ReactMarkdown>
          </div>
        )}
        {!isUser && sources && sources.length > 0 && <SourceCitations sources={sources} />}
      </div>
    </div>
  );
}
