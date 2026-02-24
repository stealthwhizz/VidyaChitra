import React, { useEffect, useRef, useState } from 'react';

interface Message { role: 'user' | 'model'; content: string; }

interface ChatInterfaceProps {
  sessionId: string;
  language: string;
  chapterName: string;
}

function TypingIndicator() {
  return (
    <div className="flex items-center gap-1.5 px-2 py-1">
      {[0, 1, 2].map(i => (
        <span
          key={i}
          className="w-2 h-2 rounded-full animate-pulse-dot"
          style={{
            background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
            animationDelay: `${i * 0.2}s`,
          }}
        />
      ))}
    </div>
  );
}

export default function ChatInterface({ sessionId, language, chapterName }: ChatInterfaceProps) {
  const [isOpen,      setIsOpen]      = useState(false);
  const [messages,    setMessages]    = useState<Message[]>([]);
  const [input,       setInput]       = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef       = useRef<HTMLInputElement>(null);
  const abortRef       = useRef<AbortController | null>(null);

  useEffect(() => {
    if (isOpen && messages.length === 0) {
      setMessages([{
        role: 'model',
        content: `नमस्ते! I'm VidyaChitra, your AI study companion for "${chapterName}". Ask me anything about this chapter and I'll answer only from your textbook! 📚`,
      }]);
    }
  }, [isOpen]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const sendMessage = async () => {
    const question = input.trim();
    if (!question || isStreaming) return;

    setInput('');
    const userMsg: Message = { role: 'user', content: question };
    setMessages(prev => [...prev, userMsg]);
    setIsStreaming(true);

    const history = messages
      .filter((_, i) => i > 0)
      .map(m => ({ role: m.role, content: m.content }));

    setMessages(prev => [...prev, { role: 'model', content: '' }]);
    abortRef.current = new AbortController();

    try {
      const resp = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, question, language, history }),
        signal: abortRef.current.signal,
      });

      if (!resp.ok) throw new Error(`Server error: ${resp.status}`);

      const reader  = resp.body!.getReader();
      const decoder = new TextDecoder();
      let accumulated = '';

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        accumulated += decoder.decode(value, { stream: true });
        setMessages(prev => {
          const next = [...prev];
          next[next.length - 1] = { role: 'model', content: accumulated };
          return next;
        });
      }
    } catch (e: unknown) {
      if (e instanceof Error && e.name === 'AbortError') return;
      setMessages(prev => {
        const next = [...prev];
        next[next.length - 1] = { role: 'model', content: 'Sorry, I encountered an error. Please try again.' };
        return next;
      });
    } finally {
      setIsStreaming(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); }
  };

  return (
    <>
      {/* ── Floating toggle button ──────────────────────────────── */}
      <button
        onClick={() => {
          setIsOpen(prev => !prev);
          setTimeout(() => inputRef.current?.focus(), 300);
        }}
        className="fixed bottom-6 right-6 w-14 h-14 rounded-full shadow-2xl
                   flex items-center justify-center text-xl transition-all
                   active:scale-90 hover:scale-110 z-50"
        style={{
          background: isOpen
            ? 'linear-gradient(135deg, #ef4444 0%, #f97316 100%)'
            : 'linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%)',
          boxShadow: `0 8px 32px ${isOpen ? 'rgba(239,68,68,0.40)' : 'rgba(99,102,241,0.45)'}`,
        }}
        aria-label="Open chat"
      >
        {isOpen ? '✕' : '💬'}
      </button>

      {/* ── Chat panel ───────────────────────────────────────────── */}
      <div
        className={`fixed bottom-24 right-4 left-4 sm:left-auto sm:w-96 z-40
                    flex flex-col transition-all duration-300 ${
          isOpen ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4 pointer-events-none'
        }`}
        style={{
          maxHeight: 'calc(100vh - 8rem)',
          background: 'var(--glass-bg)',
          backdropFilter: 'blur(32px) saturate(200%)',
          WebkitBackdropFilter: 'blur(32px) saturate(200%)',
          border: '1px solid var(--glass-border)',
          boxShadow: 'var(--glass-shadow-lg)',
          borderRadius: '1rem',
        }}
      >
        {/* Header */}
        <div
          className="flex items-center gap-3 px-4 py-3 border-b flex-shrink-0"
          style={{ borderColor: 'var(--glass-border)' }}
        >
          <div
            className="w-8 h-8 rounded-full flex items-center justify-center text-base flex-shrink-0"
            style={{
              background: 'rgba(99,102,241,0.15)',
              border: '1px solid rgba(99,102,241,0.25)',
            }}
          >
            🤖
          </div>
          <div className="flex-1 min-w-0">
            <p className="font-semibold text-slate-900 dark:text-slate-100 text-sm">VidyaChitra Chat</p>
            <p className="text-xs text-slate-500 dark:text-slate-400 truncate">{chapterName}</p>
          </div>
          {/* Online dot */}
          <div
            className="flex-shrink-0 w-2 h-2 rounded-full"
            style={{ background: '#10b981', boxShadow: '0 0 6px rgba(16,185,129,0.6)' }}
            title="Connected"
          />
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-4 space-y-3 min-h-0">
          {messages.map((msg, i) => (
            <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div
                className="max-w-[85%] px-4 py-2.5 text-sm leading-relaxed whitespace-pre-wrap"
                style={msg.role === 'user' ? {
                  background: 'linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%)',
                  color: 'white',
                  borderRadius: '1rem 1rem 0.25rem 1rem',
                  boxShadow: '0 2px 12px rgba(99,102,241,0.30)',
                } : {
                  background: 'var(--glass-bg)',
                  border: '1px solid var(--glass-border)',
                  color: 'var(--text-1, inherit)',
                  borderRadius: '1rem 1rem 1rem 0.25rem',
                }}
                // light / dark text on model bubble via Tailwind
              >
                <span className={msg.role === 'model' ? 'text-slate-800 dark:text-slate-200' : ''}>
                  {msg.content}
                </span>
                {msg.role === 'model' && isStreaming && i === messages.length - 1 && !msg.content && (
                  <TypingIndicator />
                )}
              </div>
            </div>
          ))}

          {isStreaming && messages[messages.length - 1]?.content === '' && (
            <div className="flex justify-start">
              <div
                className="rounded-2xl rounded-bl-sm px-3 py-2"
                style={{ background: 'var(--glass-bg)', border: '1px solid var(--glass-border)' }}
              >
                <TypingIndicator />
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input */}
        <div
          className="flex items-center gap-2 px-3 py-3 border-t flex-shrink-0"
          style={{ borderColor: 'var(--glass-border)' }}
        >
          <input
            ref={inputRef}
            type="text"
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask anything about this chapter…"
            disabled={isStreaming}
            className="flex-1 glass-input disabled:opacity-50"
          />
          <button
            onClick={sendMessage}
            disabled={!input.trim() || isStreaming}
            className="flex-shrink-0 w-9 h-9 rounded-xl flex items-center justify-center
                       transition-all active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed"
            style={{
              background: 'linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%)',
              boxShadow: '0 2px 10px rgba(99,102,241,0.30)',
            }}
            aria-label="Send"
          >
            {isStreaming ? (
              <svg className="animate-spin w-4 h-4 text-white" viewBox="0 0 24 24" fill="none">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z" />
              </svg>
            ) : (
              <svg viewBox="0 0 24 24" fill="currentColor" className="w-4 h-4 text-white">
                <path d="M2 21l21-9L2 3v7l15 2-15 2v7z" />
              </svg>
            )}
          </button>
        </div>

        <p className="text-center text-xs text-slate-400 dark:text-slate-500 pb-2">
          Answers grounded only in your textbook
        </p>
      </div>
    </>
  );
}
