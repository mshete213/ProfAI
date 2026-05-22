import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "../lib/api";
import type { ChatSource } from "../lib/types";

export interface UIMessage {
  role: "user" | "assistant";
  content: string;
  sources?: ChatSource[];
  streaming?: boolean;
}

const sessionKey = (courseId: string) => `edtech_session_${courseId}`;

export function useChat(courseId: string) {
  const [messages, setMessages] = useState<UIMessage[]>([]);
  const [sessionId, setSessionId] = useState<string | null>(() =>
    localStorage.getItem(sessionKey(courseId))
  );
  const [streaming, setStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const loadedRef = useRef(false);

  useEffect(() => {
    if (loadedRef.current) return;
    loadedRef.current = true;
    if (!sessionId) return;
    api
      .getChatHistory(courseId, sessionId)
      .then((history) => {
        setMessages(
          history.map((m) => ({
            role: m.role,
            content: m.content,
            sources: m.sources ?? undefined,
          }))
        );
      })
      .catch(() => {
        // Stale session — drop it
        localStorage.removeItem(sessionKey(courseId));
        setSessionId(null);
      });
  }, [courseId, sessionId]);

  const sendMessage = useCallback(
    async (text: string) => {
      setError(null);
      setMessages((m) => [...m, { role: "user", content: text }, { role: "assistant", content: "", streaming: true }]);
      setStreaming(true);
      try {
        let collected = "";
        let collectedSources: ChatSource[] = [];
        let newSessionId: string | null = sessionId;

        for await (const event of api.chatStream(courseId, text, sessionId ?? undefined)) {
          if (event.event === "session") {
            newSessionId = event.data.session_id;
          } else if (event.event === "sources") {
            collectedSources = event.data;
          } else if (event.event === "chunk") {
            collected += event.data;
            setMessages((m) => {
              const copy = [...m];
              copy[copy.length - 1] = {
                role: "assistant",
                content: collected,
                sources: collectedSources,
                streaming: true,
              };
              return copy;
            });
          } else if (event.event === "done") {
            setMessages((m) => {
              const copy = [...m];
              copy[copy.length - 1] = {
                role: "assistant",
                content: collected,
                sources: collectedSources,
                streaming: false,
              };
              return copy;
            });
          }
        }
        if (newSessionId && newSessionId !== sessionId) {
          localStorage.setItem(sessionKey(courseId), newSessionId);
          setSessionId(newSessionId);
        }
      } catch (err: any) {
        setError(err.message || "Stream failed");
        setMessages((m) => {
          const copy = [...m];
          if (copy.length > 0 && copy[copy.length - 1].role === "assistant") {
            copy[copy.length - 1] = {
              role: "assistant",
              content: "Sorry, something went wrong.",
              streaming: false,
            };
          }
          return copy;
        });
      } finally {
        setStreaming(false);
      }
    },
    [courseId, sessionId]
  );

  const startNewChat = useCallback(async () => {
    if (sessionId) {
      try {
        await api.deleteChatSession(sessionId);
      } catch {
        /* ignore */
      }
    }
    localStorage.removeItem(sessionKey(courseId));
    setSessionId(null);
    setMessages([]);
  }, [courseId, sessionId]);

  return { messages, sendMessage, streaming, error, sessionId, startNewChat };
}
