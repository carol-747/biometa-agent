import React, { useState, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import { chatAPI } from '../utils/api';

const EXAMPLE_QUERIES = [
  "What metabolites does E. coli produce?",
  "How does Lactobacillus regulate butyrate?",
  "What microbes consume bile acids?",
  "Which bacteria produce short-chain fatty acids?",
  "What is the relationship between gut microbiome and TMAO?",
];

function MessageBubble({ msg }) {
  const isUser = msg.role === 'user';
  return (
    <div style={{
      display: 'flex',
      justifyContent: isUser ? 'flex-end' : 'flex-start',
      marginBottom: '16px',
    }}>
      {!isUser && (
        <div style={{
          width: 32, height: 32, borderRadius: '50%',
          background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: 14, fontWeight: 700, marginRight: 10, flexShrink: 0,
          marginTop: 4,
        }}>B</div>
      )}
      <div style={{
        maxWidth: '75%',
        background: isUser
          ? 'linear-gradient(135deg, #6366f1, #4f46e5)'
          : 'rgba(255,255,255,0.07)',
        borderRadius: isUser ? '18px 18px 4px 18px' : '18px 18px 18px 4px',
        padding: '12px 16px',
        fontSize: 14,
        lineHeight: 1.6,
        color: '#e2e8f0',
        border: isUser ? 'none' : '1px solid rgba(255,255,255,0.1)',
      }}>
        {isUser
          ? msg.content
          : <ReactMarkdown
              components={{
                p: ({ children }) => <p style={{ marginBottom: 8 }}>{children}</p>,
                code: ({ children }) => (
                  <code style={{
                    background: 'rgba(0,0,0,0.3)', padding: '2px 6px',
                    borderRadius: 4, fontSize: 12, fontFamily: 'monospace',
                  }}>{children}</code>
                ),
              }}
            >{msg.content}</ReactMarkdown>
        }
        {msg.relationships?.length > 0 && (
          <RelationshipBadges relationships={msg.relationships} />
        )}
      </div>
    </div>
  );
}

function RelationshipBadges({ relationships }) {
  const [expanded, setExpanded] = useState(false);
  const shown = expanded ? relationships : relationships.slice(0, 3);
  return (
    <div style={{ marginTop: 10, borderTop: '1px solid rgba(255,255,255,0.1)', paddingTop: 8 }}>
      <div style={{ fontSize: 11, color: '#94a3b8', marginBottom: 6 }}>
        {relationships.length} relationship{relationships.length !== 1 ? 's' : ''} found
      </div>
      {shown.map((r, i) => (
        <div key={i} style={{
          display: 'flex', alignItems: 'center', gap: 6,
          marginBottom: 4, fontSize: 12, flexWrap: 'wrap',
        }}>
          <span style={{
            background: 'rgba(99,102,241,0.3)', padding: '2px 6px',
            borderRadius: 12, color: '#a5b4fc',
          }}>{r.microbe}</span>
          <span style={{ color: '#64748b' }}>→</span>
          <span style={{
            background: 'rgba(16,185,129,0.2)', padding: '2px 8px',
            borderRadius: 10, color: '#6ee7b7', fontSize: 11,
          }}>{r.relationship_type}</span>
          <span style={{ color: '#64748b' }}>→</span>
          <span style={{
            background: 'rgba(245,158,11,0.2)', padding: '2px 6px',
            borderRadius: 12, color: '#fcd34d',
          }}>{r.metabolite}</span>
          <span style={{
            marginLeft: 'auto', color: '#64748b', fontSize: 11,
          }}>{Math.round((r.confidence || 0) * 100)}% · {r.pmid}</span>
        </div>
      ))}
      {relationships.length > 3 && (
        <button
          onClick={() => setExpanded(e => !e)}
          style={{
            background: 'none', border: 'none', color: '#6366f1',
            cursor: 'pointer', fontSize: 12, padding: 0, marginTop: 4,
          }}
        >
          {expanded ? 'Show less' : `Show ${relationships.length - 3} more...`}
        </button>
      )}
    </div>
  );
}

export default function ChatInterface({ onNetworkData }) {
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      content: `Hi! I'm **BiometaAgent**, your AI assistant for exploring microbe-metabolite relationships from scientific literature.\n\nYou can ask me things like:\n- "What metabolites does *E. coli* produce?"\n- "Which bacteria regulate butyrate?"\n- "What is the relationship between gut microbiota and TMAO?"\n\nHow can I help you today?`,
      relationships: [],
    }
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [sessionId, setSessionId] = useState(null);
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const sendMessage = async (text) => {
    if (!text.trim() || loading) return;
    const userMsg = { role: 'user', content: text, relationships: [] };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setLoading(true);

    try {
      const res = await chatAPI.send(text, sessionId);
      const data = res.data;
      if (!sessionId) setSessionId(data.session_id);

      const botMsg = {
        role: 'assistant',
        content: data.reply,
        relationships: data.relationships || [],
      };
      setMessages(prev => [...prev, botMsg]);

      // Update network visualization if relationships found
      if (data.relationships?.length > 0 && onNetworkData) {
        onNetworkData(data.relationships, data.articles);
      }
    } catch (err) {
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: `Sorry, I encountered an error: ${err.response?.data?.detail || err.message}`,
        relationships: [],
      }]);
    } finally {
      setLoading(false);
    }
  };

  const clearChat = async () => {
    if (sessionId) {
      try { await chatAPI.clearSession(sessionId); } catch {}
    }
    setMessages([{
      role: 'assistant',
      content: 'Chat cleared. How can I help you?',
      relationships: [],
    }]);
    setSessionId(null);
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      {/* Messages */}
      <div style={{
        flex: 1, overflowY: 'auto', padding: '20px',
        scrollbarWidth: 'thin', scrollbarColor: '#334155 transparent',
      }}>
        {messages.map((msg, i) => (
          <MessageBubble key={i} msg={msg} />
        ))}
        {loading && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 16 }}>
            <div style={{
              width: 32, height: 32, borderRadius: '50%',
              background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontSize: 14, fontWeight: 700,
            }}>B</div>
            <div style={{
              background: 'rgba(255,255,255,0.07)', borderRadius: '18px 18px 18px 4px',
              padding: '12px 20px', border: '1px solid rgba(255,255,255,0.1)',
              display: 'flex', gap: 6,
            }}>
              {[0, 1, 2].map(i => (
                <div key={i} style={{
                  width: 8, height: 8, borderRadius: '50%',
                  background: '#6366f1',
                  animation: `bounce 0.8s ease-in-out ${i * 0.2}s infinite`,
                }} />
              ))}
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Example queries */}
      <div style={{
        padding: '0 20px 8px', display: 'flex', gap: 8,
        flexWrap: 'wrap', borderTop: '1px solid rgba(255,255,255,0.05)',
        paddingTop: 10,
      }}>
        {EXAMPLE_QUERIES.slice(0, 3).map((q, i) => (
          <button
            key={i}
            onClick={() => sendMessage(q)}
            disabled={loading}
            style={{
              background: 'rgba(99,102,241,0.1)', border: '1px solid rgba(99,102,241,0.3)',
              borderRadius: 20, padding: '4px 12px', fontSize: 12, color: '#a5b4fc',
              cursor: 'pointer', whiteSpace: 'nowrap',
            }}
          >{q}</button>
        ))}
      </div>

      {/* Input area */}
      <div style={{
        padding: '12px 20px 20px', display: 'flex', gap: 10, alignItems: 'flex-end',
      }}>
        <button
          onClick={clearChat}
          title="Clear chat"
          style={{
            background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.1)',
            borderRadius: 12, padding: '10px 14px', color: '#64748b',
            cursor: 'pointer', fontSize: 16, flexShrink: 0,
          }}
        >↺</button>
        <textarea
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault();
              sendMessage(input);
            }
          }}
          placeholder="Ask about microbe-metabolite relationships..."
          rows={2}
          disabled={loading}
          style={{
            flex: 1, background: 'rgba(255,255,255,0.06)',
            border: '1px solid rgba(255,255,255,0.12)',
            borderRadius: 14, padding: '12px 16px', color: '#e2e8f0',
            fontSize: 14, resize: 'none', outline: 'none',
            fontFamily: 'inherit', lineHeight: 1.5,
          }}
        />
        <button
          onClick={() => sendMessage(input)}
          disabled={loading || !input.trim()}
          style={{
            background: loading || !input.trim()
              ? 'rgba(99,102,241,0.3)'
              : 'linear-gradient(135deg, #6366f1, #4f46e5)',
            border: 'none', borderRadius: 12, padding: '12px 20px',
            color: '#fff', cursor: loading || !input.trim() ? 'not-allowed' : 'pointer',
            fontSize: 16, flexShrink: 0, fontWeight: 600,
          }}
        >→</button>
      </div>

      <style>{`
        @keyframes bounce {
          0%, 100% { transform: translateY(0); }
          50% { transform: translateY(-6px); }
        }
      `}</style>
    </div>
  );
}
