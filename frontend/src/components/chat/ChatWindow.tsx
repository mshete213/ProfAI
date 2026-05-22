import { useEffect, useRef } from "react";
import { RotateCcw } from "lucide-react";
import { useChat } from "../../hooks/useChat";
import ChatInput from "./ChatInput";
import MessageBubble from "./MessageBubble";

export default function ChatWindow({ courseId, courseName }: { courseId: string; courseName: string }) {
  const { messages, sendMessage, streaming, error, startNewChat } = useChat(courseId);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  return (
    <div className="flex h-[calc(100vh-8rem)] flex-col rounded-lg border border-gray-200 bg-white shadow-sm">
      <div className="flex items-center justify-between border-b border-gray-200 px-4 py-2">
        <div>
          <div className="font-semibold">{courseName}</div>
          <div className="text-xs text-gray-500">Ask anything about the course materials</div>
        </div>
        <button onClick={startNewChat} className="btn-secondary flex items-center gap-1 text-xs">
          <RotateCcw size={12} />
          New chat
        </button>
      </div>

      <div className="flex-1 space-y-3 overflow-y-auto p-4">
        {messages.length === 0 && (
          <div className="mt-10 text-center text-sm text-gray-500">
            Start by asking a question about the course material.
          </div>
        )}
        {messages.map((m, i) => (
          <MessageBubble
            key={i}
            role={m.role}
            content={m.content}
            sources={m.sources}
            streaming={m.streaming}
          />
        ))}
        {error && <div className="rounded-md bg-red-50 p-2 text-sm text-red-700">{error}</div>}
        <div ref={bottomRef} />
      </div>

      <ChatInput onSend={sendMessage} disabled={streaming} />
    </div>
  );
}
