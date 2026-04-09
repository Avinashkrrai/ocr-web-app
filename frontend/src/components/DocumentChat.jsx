import { useState, useRef, useEffect } from "react";
import { askDocument } from "../services/api";

export default function DocumentChat({ imageId }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function handleSend(e) {
    e?.preventDefault();
    const question = input.trim();
    if (!question || loading) return;

    setMessages((prev) => [...prev, { role: "user", text: question }]);
    setInput("");
    setLoading(true);

    try {
      const res = await askDocument(imageId, question);
      setMessages((prev) => [...prev, { role: "ai", text: res.answer }]);
    } catch (err) {
      const detail = err.response?.data?.detail || err.message;
      setMessages((prev) => [...prev, { role: "error", text: detail }]);
    } finally {
      setLoading(false);
      inputRef.current?.focus();
    }
  }

  function handleKeyDown(e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  return (
    <div className="chat-panel">
      <div className="chat-header">
        <h3>Ask About This Document</h3>
        <span className="chat-hint">Ask any question — Gemini reads the document to answer</span>
      </div>

      <div className="chat-messages">
        {messages.length === 0 && (
          <div className="chat-empty">
            <p>Try asking:</p>
            <div className="suggestion-chips">
              {[
                "Who is the owner of this land?",
                "What is the survey number?",
                "Summarize this document",
                "What is the total area mentioned?",
                "When was this document created?",
              ].map((q) => (
                <button
                  key={q}
                  className="suggestion-chip"
                  onClick={() => {
                    setInput(q);
                    inputRef.current?.focus();
                  }}
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg, i) => (
          <div key={i} className={`chat-msg chat-msg-${msg.role}`}>
            <div className="msg-label">
              {msg.role === "user" ? "You" : msg.role === "error" ? "Error" : "Gemini"}
            </div>
            <div className="msg-text">{msg.text}</div>
          </div>
        ))}

        {loading && (
          <div className="chat-msg chat-msg-ai">
            <div className="msg-label">Gemini</div>
            <div className="msg-text typing">Thinking...</div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      <form className="chat-input-bar" onSubmit={handleSend}>
        <input
          ref={inputRef}
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask a question about the document..."
          disabled={loading}
        />
        <button type="submit" className="btn btn-send" disabled={!input.trim() || loading}>
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <line x1="22" y1="2" x2="11" y2="13" />
            <polygon points="22 2 15 22 11 13 2 9 22 2" />
          </svg>
        </button>
      </form>
    </div>
  );
}
