import { useCallback, useEffect, useRef, useState } from "react";
import { useAuth } from "@/lib/auth";
import { api, refreshAccessToken } from "@/api/client";

/** A single chat turn shown in the UI. */
export interface ChatMessage {
  role: "user" | "assistant";
  text: string;
}

export function useChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [tools, setTools] = useState<string[]>([]);
  const [streaming, setStreaming] = useState(false);
  // The coach is ONE continuous conversation per user. We resume the latest one from the
  // backend (source of truth — survives storage clears); older context comes via RAG memory.
  const convIdRef = useRef<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const convs = await api<{ id: string }[]>("/agent/conversations");
        if (convs.length === 0) return;
        convIdRef.current = convs[0].id; // ordered by updated_at desc
        const rows = await api<{ role: string; text: string }[]>(
          `/agent/conversations/${convs[0].id}/messages`,
        );
        setMessages(rows.map((r) => ({ role: r.role === "assistant" ? "assistant" : "user", text: r.text })));
      } catch {
        /* not signed in yet / no history */
      }
    })();
  }, []);

  const send = useCallback(
    async (content: string, persona = "friendly") => {
      const trimmed = content.trim();
      if (!trimmed || streaming) return;

      setMessages((m) => [...m, { role: "user", text: trimmed }, { role: "assistant", text: "" }]);
      setTools([]);
      setStreaming(true);
      const controller = new AbortController();
      abortRef.current = controller;

      const setAssistant = (fn: (prev: string) => string) =>
        setMessages((m) => {
          const copy = [...m];
          const last = copy[copy.length - 1];
          if (last?.role === "assistant") copy[copy.length - 1] = { ...last, text: fn(last.text) };
          return copy;
        });

      const post = (token: string | null) =>
        fetch("/api/v1/agent/messages", {
          method: "POST",
          signal: controller.signal,
          headers: {
            "Content-Type": "application/json",
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
          },
          body: JSON.stringify({ content: trimmed, persona, conversation_id: convIdRef.current }),
        });

      let res = await post(useAuth.getState().accessToken);
      if (res.status === 401) {
        const newToken = await refreshAccessToken();
        if (newToken) res = await post(newToken);
      }
      if (!res.ok || !res.body) {
        setAssistant(() => "Your session expired. Please sign in again.");
        setStreaming(false);
        return;
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const frames = buffer.split(/\r?\n\r?\n/); // sse-starlette uses CRLF separators
        buffer = frames.pop() ?? "";
        for (const frame of frames) {
          const event = /event:\s*(.+)/.exec(frame)?.[1]?.trim();
          const dataLine = /data:\s*(.+)/.exec(frame)?.[1];
          if (!event || !dataLine) continue;
          const data = JSON.parse(dataLine);
          if (event === "conversation") convIdRef.current = data.conversation_id;
          else if (event === "content_delta") setAssistant((t) => t + (data.text ?? ""));
          else if (event === "tool_use") setTools((ts) => [...ts, data.name]);
          else if (event === "message_done" || event === "error") setStreaming(false);
        }
      }
      setStreaming(false);
    },
    [streaming],
  );

  return { messages, tools, streaming, send };
}
