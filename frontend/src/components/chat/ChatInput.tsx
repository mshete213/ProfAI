import { Send } from "lucide-react";
import { useState } from "react";

interface Props {
  onSend: (text: string) => void;
  disabled?: boolean;
}

export default function ChatInput({ onSend, disabled }: Props) {
  const [text, setText] = useState("");

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!text.trim() || disabled) return;
    onSend(text.trim());
    setText("");
  };

  const onKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit(e as unknown as React.FormEvent);
    }
  };

  return (
    <form onSubmit={submit} className="border-t border-gray-200 bg-white p-3">
      <div className="flex gap-2">
        <textarea
          rows={1}
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={onKeyDown}
          placeholder="Ask anything about the course materials… (Enter to send, Shift+Enter for newline)"
          className="input min-h-[44px] resize-none"
          disabled={disabled}
        />
        <button type="submit" disabled={disabled || !text.trim()} className="btn-primary">
          <Send size={16} />
        </button>
      </div>
    </form>
  );
}
