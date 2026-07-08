'use client';

import { useState, useEffect, useRef } from 'react';

export default function MessagesPage() {
  const [messages, setMessages] = useState([]);
  const [aiConversations, setAiConversations] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [aiInput, setAiInput] = useState('');
  const [loading, setLoading] = useState(true);
  const chatEndRef = useRef(null);

  const fetchLogs = async () => {
    try {
      const res = await fetch('/api/chat-logs');
      if (res.ok) {
        const data = await res.json();
        // Check if data changed
        setMessages(prev => {
            if (prev.length !== data.length || JSON.stringify(prev[0]) !== JSON.stringify(data[0])) {
                return data;
            }
            return prev;
        });
      }
    } catch (err) {
      console.error("Failed to fetch chat logs", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLogs();
    const interval = setInterval(fetchLogs, 5000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, aiConversations]);

  const isBot = (name) => {
      if (!name) return false;
      return name.toLowerCase().includes('bot') || name.toLowerCase().includes('assistant');
  };

  const formatTime = (ts) => {
    const ms = ts > 9999999999999 ? Math.floor(ts / 1000) : ts;
    const date = new Date(ms);
    return date.toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit', second: '2-digit' }) + ' - ' + date.toLocaleDateString('vi-VN');
  };

  const filteredMessages = messages.filter(m => 
    (m.text && m.text.toLowerCase().includes(searchQuery.toLowerCase())) || 
    (m.sender_name && m.sender_name.toLowerCase().includes(searchQuery.toLowerCase()))
  );

  const handleAskAI = async () => {
    if (!aiInput.trim()) return;
    
    const question = aiInput.trim();
    setAiInput('');
    
    const newConv = { id: Date.now(), question, answer: '', loading: true };
    setAiConversations(prev => [...prev, newConv]);

    try {
      const res = await fetch('/api/ask-ai', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: question })
      });
      const data = await res.json();
      
      setAiConversations(prev => prev.map(c => 
        c.id === newConv.id ? { ...c, answer: data.reply || "No response", loading: false } : c
      ));
    } catch (err) {
      setAiConversations(prev => prev.map(c => 
        c.id === newConv.id ? { ...c, answer: `Error: ${err.message}`, loading: false } : c
      ));
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
        <div>
          <h1 className="gradient-text" style={{ fontSize: '2rem', fontWeight: 'bold' }}>Message Management & AI Chat</h1>
          <p style={{ color: 'var(--text-secondary)' }}>Zalo Intelligence Stream</p>
        </div>
        <div>
          <input 
            type="text" 
            placeholder="Search messages..." 
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            style={{ 
              padding: '10px 16px', 
              borderRadius: '99px', 
              background: 'rgba(0,0,0,0.2)', 
              border: '1px solid var(--glass-border)',
              color: 'white',
              width: '250px'
            }}
          />
        </div>
      </div>

      <div className="glass-panel" style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        <div style={{ flex: 1, overflowY: 'auto', padding: '24px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {loading && <div style={{ textAlign: 'center', color: 'var(--text-secondary)' }}>Loading data stream...</div>}
          
          {[...filteredMessages].reverse().map(msg => {
            const bot = isBot(msg.sender_name);
            return (
              <div key={msg.id} style={{ 
                display: 'flex', 
                flexDirection: 'column', 
                alignSelf: bot ? 'flex-end' : 'flex-start',
                maxWidth: '80%'
              }}>
                <div style={{ 
                  fontSize: '12px', 
                  color: 'var(--text-secondary)', 
                  marginBottom: '6px', 
                  display: 'flex', 
                  gap: '8px',
                  alignItems: 'center',
                  flexDirection: bot ? 'row-reverse' : 'row'
                }}>
                  <span style={{ fontWeight: '600', color: '#e2e8f0' }}>{msg.sender_name || 'Unknown User'}</span>
                  <span style={{ background: 'rgba(255,255,255,0.1)', padding: '2px 8px', borderRadius: '12px', fontSize: '10px' }}>
                    {(msg.group_name && msg.group_name !== msg.sender_name) ? msg.group_name : 'Direct'}
                  </span>
                  <span>{formatTime(msg.timestamp)}</span>
                </div>
                <div style={{
                  padding: '16px 20px',
                  borderRadius: '18px',
                  borderTopLeftRadius: bot ? '18px' : '4px',
                  borderTopRightRadius: bot ? '4px' : '18px',
                  background: bot ? 'rgba(59, 130, 246, 0.15)' : 'rgba(255, 255, 255, 0.05)',
                  border: `1px solid ${bot ? 'rgba(59, 130, 246, 0.3)' : 'rgba(255, 255, 255, 0.1)'}`,
                  color: 'white',
                  whiteSpace: 'pre-wrap'
                }}>
                  {msg.text}
                </div>
              </div>
            );
          })}

          {aiConversations.map(conv => (
            <div key={conv.id} style={{ alignSelf: 'center', width: '90%', margin: '10px 0' }}>
              <div style={{
                padding: '20px',
                borderRadius: '12px',
                background: 'rgba(139, 92, 246, 0.15)',
                border: '1px solid rgba(139, 92, 246, 0.3)',
                color: '#e2e8f0'
              }}>
                <div style={{ fontWeight: 'bold', color: '#a78bfa', marginBottom: '8px', fontSize: '16px' }}>🧠 AI Analysis Report</div>
                <div style={{ marginBottom: '12px' }}><b>You asked:</b> {conv.question}</div>
                <div>
                  <b>AI Response:</b><br/>
                  {conv.loading ? (
                    <span style={{ color: 'var(--text-secondary)' }}>Thinking...</span>
                  ) : (
                    <span style={{ whiteSpace: 'pre-wrap' }}>{conv.answer}</span>
                  )}
                </div>
              </div>
            </div>
          ))}
          <div ref={chatEndRef} />
        </div>
        
        <div style={{ padding: '20px 24px', borderTop: '1px solid var(--glass-border)', display: 'flex', gap: '16px', background: 'rgba(15, 23, 42, 0.4)' }}>
          <input 
            type="text" 
            placeholder="Ask AI to analyze chat (e.g. What did Thang say earlier?)..." 
            value={aiInput}
            onChange={(e) => setAiInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleAskAI()}
            style={{
              flex: 1,
              padding: '14px 20px',
              borderRadius: '12px',
              background: 'rgba(0,0,0,0.3)',
              border: '1px solid var(--glass-border)',
              color: 'white',
              outline: 'none'
            }}
          />
          <button 
            onClick={handleAskAI}
            style={{
              padding: '0 24px',
              borderRadius: '12px',
              background: 'var(--accent)',
              color: 'white',
              fontWeight: 'bold',
              border: 'none',
              cursor: 'pointer'
            }}
          >
            ✨ Ask AI
          </button>
        </div>
      </div>
    </div>
  );
}
