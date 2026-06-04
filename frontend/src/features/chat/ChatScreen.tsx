import { useEffect, useRef, useState } from "react";
import { useChat } from "./useChat";
import { Markdown } from "./Markdown";

/** AI Chat / conversational onboarding screen (docs/08 §5). */
export function ChatScreen() {
  const { messages, tools, streaming, send } = useChat();
  const [input, setInput] = useState("");
  const endRef = useRef<HTMLDivElement>(null);

  // Follow the conversation as it streams / grows.
  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streaming]);

  const onSend = () => {
    if (!input.trim()) return;
    void send(input.trim());
    setInput("");
  };

  return (
    <div className="chat">
      <header className="chat__header">
        <span>Forge Coach</span>
      </header>

      <div className="chat__messages">
        {messages.length === 0 && (
          <div className="chat__bubble chat__bubble--assistant">
            Ask me anything about your training or nutrition.
          </div>
        )}

        {messages.map((m, i) => {
          const isLast = i === messages.length - 1;
          return (
            <div key={i} className={`chat__bubble chat__bubble--${m.role}`}>
              {m.role === "assistant" && m.text ? (
                <Markdown>{m.text}</Markdown>
              ) : (
                m.text || (streaming && isLast ? "…" : "")
              )}
            </div>
          );
        })}

        {streaming && tools.length > 0 && (
          <div className="chat__tools">
            {tools.map((t, i) => (
              <span key={i} className="chip">
                checking {t.replace(/_/g, " ")}…
              </span>
            ))}
          </div>
        )}

        <div ref={endRef} />
      </div>

      <div className="chat__composer">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && onSend()}
          placeholder="Message your coach…"
          disabled={streaming}
        />
        <button onClick={onSend} disabled={streaming}>
          Send
        </button>
      </div>
    </div>
  );
}
