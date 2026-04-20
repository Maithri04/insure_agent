import { useEffect, useRef, useState } from "react";
import Button from "../components/Button";
import Card from "../components/Card";
import SectionTitle from "../components/SectionTitle";
import { chat } from "../services/api";

const WELCOME = {
  role: "assistant",
  content: "Hello! I'm InsureMind AI — your medical assistant. I can help with ICD-10 codes, insurance prior authorization, clinical documentation, and any medical questions. How can I help you today?",
};

const SUGGESTIONS = [
  "What ICD code is used for acute MI?",
  "How do I write a prior authorization request?",
  "What documents are needed for cardiac surgery approval?",
  "Explain the difference between SOAP and APSO notes.",
];

export default function Chatbot() {
  const [messages, setMessages] = useState([WELCOME]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const send = async (text) => {
    const msg = (text || input).trim();
    if (!msg || loading) return;

    const userMsg   = { role: "user", content: msg };
    const history   = messages
      .filter((m) => m !== WELCOME)
      .map(({ role, content }) => ({ role, content }));

    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);

    try {
      const res = await chat({ message: msg, history });
      setMessages((prev) => [...prev, { role: "assistant", content: res.reply || res.message || "No response." }]);
    } catch {
      setMessages((prev) => [...prev, {
        role: "assistant",
        content: "I'm having trouble connecting right now. Please check that the API is running and try again.",
        error: true,
      }]);
    } finally {
      setLoading(false);
      inputRef.current?.focus();
    }
  };

  const handleKey = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  };

  return (
    <div className="space-y-4">
      <SectionTitle title="AI Chat Assistant" description="Ask for ICD suggestions, insurance clarifications and clinical support." />
      <Card className="p-0 overflow-hidden">
        <div className="bg-white border-b border-gray-200 px-6 py-4 flex items-center gap-3">
        <div className="w-9 h-9 bg-blue-600 rounded-xl flex items-center justify-center">
          <svg className="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
          </svg>
        </div>
        <div>
          <h1 className="text-base font-semibold text-gray-900">InsureMind AI Assistant</h1>
          <p className="text-xs text-gray-400">Medical documentation · ICD codes · Prior authorization</p>
        </div>
        <div className="ml-auto flex items-center gap-1.5">
          <span className="w-2 h-2 bg-green-400 rounded-full" />
          <span className="text-xs text-gray-400">Online</span>
        </div>
        </div>

      {/* Messages */}
        <div className="overflow-y-auto px-4 py-6 space-y-4 max-w-3xl mx-auto w-full min-h-[420px] max-h-[65vh]">

        {/* Suggestion chips — shown only at start */}
        {messages.length === 1 && (
          <div className="flex flex-wrap gap-2 mb-2">
            {SUGGESTIONS.map((s) => (
              <button key={s} onClick={() => send(s)}
                className="text-xs bg-white border border-gray-200 hover:border-blue-400 hover:text-blue-600 text-gray-600 px-3 py-1.5 rounded-full transition-colors">
                {s}
              </button>
            ))}
          </div>
        )}

        {messages.map((msg, i) => (
          <div key={i} className={`flex gap-3 ${msg.role === "user" ? "flex-row-reverse" : "flex-row"}`}>
            {/* Avatar */}
            <div className={`w-8 h-8 rounded-xl shrink-0 flex items-center justify-center text-xs font-bold ${
              msg.role === "user"
                ? "bg-gray-900 text-white"
                : "bg-blue-600 text-white"
            }`}>
              {msg.role === "user" ? "Dr" : "AI"}
            </div>

            {/* Bubble */}
            <div className={`max-w-[80%] ${msg.role === "user" ? "items-end" : "items-start"} flex flex-col`}>
              <div className={`rounded-2xl px-4 py-3 text-sm leading-relaxed ${
                msg.role === "user"
                  ? "bg-gray-900 text-white rounded-tr-sm"
                  : msg.error
                    ? "bg-red-50 text-red-700 border border-red-200 rounded-tl-sm"
                    : "bg-white text-gray-800 border border-gray-200 rounded-tl-sm"
              }`}>
                {msg.content.split("\n").map((line, j) => (
                  <span key={j}>{line}{j < msg.content.split("\n").length - 1 && <br />}</span>
                ))}
              </div>
            </div>
          </div>
        ))}

        {/* Typing indicator */}
        {loading && (
          <div className="flex gap-3 flex-row">
            <div className="w-8 h-8 rounded-xl bg-blue-600 shrink-0 flex items-center justify-center text-xs font-bold text-white">AI</div>
            <div className="bg-white border border-gray-200 rounded-2xl rounded-tl-sm px-4 py-3">
              <div className="flex gap-1 items-center h-4">
                {[0, 1, 2].map((i) => (
                  <span key={i} className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce"
                    style={{ animationDelay: `${i * 150}ms` }} />
                ))}
              </div>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
        </div>

      {/* Input */}
        <div className="bg-white border-t border-gray-200 px-4 py-4">
        <div className="max-w-3xl mx-auto flex gap-3 items-end">
          <div className="flex-1 border border-gray-300 rounded-xl overflow-hidden focus-within:ring-2 focus-within:ring-blue-500 focus-within:border-transparent">
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKey}
              rows={1}
              placeholder="Ask about ICD codes, prior authorization, medications..."
              className="w-full px-4 py-3 text-sm text-gray-800 resize-none focus:outline-none max-h-32"
              style={{ minHeight: "44px" }}
              disabled={loading}
            />
          </div>
            <Button onClick={() => send()} disabled={!input.trim() || loading} loading={loading}>
              Send
            </Button>
        </div>
        <p className="text-xs text-gray-400 text-center mt-2">
          Press Enter to send · Shift+Enter for new line
        </p>
      </div>
      </Card>
    </div>
  );
}
