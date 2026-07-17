'use client';

import { useState, useEffect, useRef } from 'react';

export default function MessagesPage() {
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(true);
  const chatEndRef = useRef(null);

  // Group Name Mapping State (LocalStorage)
  const [groupAliases, setGroupAliases] = useState({
    'group:zgr-7a8fa64983246a7a3335': 'Nhóm SmartHome (Zalo)',
  });

  /* eslint-disable react-hooks/set-state-in-effect */
  useEffect(() => {
    // Load aliases from localStorage on mount
    const saved = localStorage.getItem('nexus_group_aliases');
    if (saved) {
      try {
        setGroupAliases(JSON.parse(saved));
      } catch (e) {}
    }
  }, []);
  /* eslint-enable react-hooks/set-state-in-effect */

  const getGroupName = (id) => groupAliases[id] || id;

  const handleRenameGroup = () => {
    if (selectedGroup === 'All') return;
    const currentName = getGroupName(selectedGroup);
    const newName = window.prompt("Nhập tên hiển thị mới cho nhóm này:", currentName);
    if (newName !== null && newName.trim() !== "") {
      const updatedAliases = { ...groupAliases, [selectedGroup]: newName.trim() };
      setGroupAliases(updatedAliases);
      localStorage.setItem('nexus_group_aliases', JSON.stringify(updatedAliases));
    }
  };

  // 3-Panel State
  const [selectedGroup, setSelectedGroup] = useState('All');
  const [timeRange, setTimeRange] = useState('24h');
  const [summaryType, setSummaryType] = useState('general');
  const [summaryLoading, setSummaryLoading] = useState(false);
  const [summaryResult, setSummaryResult] = useState(null);
  const [customPrompt, setCustomPrompt] = useState('');

  // Responsive state for Mobile (Drill down)
  const [activePanel, setActivePanel] = useState('groups'); // 'groups', 'chat', 'summary'

  const fetchLogs = async () => {
    try {
      const res = await fetch('/api/chat-logs');
      if (res.ok) {
        const data = await res.json();
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

  /* eslint-disable react-hooks/set-state-in-effect */
  useEffect(() => {
    fetchLogs();
    const interval = setInterval(fetchLogs, 5000);
    return () => clearInterval(interval);
  }, []);
  /* eslint-enable react-hooks/set-state-in-effect */

  useEffect(() => {
    if (activePanel === 'chat') {
      chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, activePanel]);

  // Extract unique groups
  const groups = ['All', ...Array.from(new Set(messages.map(m => m.group_name || 'Direct'))).filter(Boolean)];

  const filteredMessages = selectedGroup === 'All' 
    ? messages 
    : messages.filter(m => (m.group_name || 'Direct') === selectedGroup);

  const formatTime = (ts) => {
    const ms = ts > 9999999999999 ? Math.floor(ts / 1000) : ts;
    const date = new Date(ms);
    return date.toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' });
  };

  const handleGenerateSummary = async () => {
    setSummaryLoading(true);
    setSummaryResult(null);
    try {
      const res = await fetch('/api/ask-ai', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          text: `Summarize the ${selectedGroup} group chats for the last ${timeRange}. Focus on ${summaryType}. Structure the response with Overview, Key Events, Decisions, Action Items, and Unresolved Issues.` 
        })
      });
      const data = await res.json();
      setSummaryResult(data.reply || "No summary generated.");
    } catch (err) {
      setSummaryResult(`Error: ${err.message}`);
    } finally {
      setSummaryLoading(false);
    }
  };

  const handleAskAI = async () => {
    if (!customPrompt.trim()) return;
    setSummaryLoading(true);
    setSummaryResult(null);
    try {
      const res = await fetch('/api/ask-ai', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          text: `Context: Group chats from ${selectedGroup} for the last ${timeRange}.\n\nUser Question: ${customPrompt}\n\nPlease analyze the chat context and answer the user's question directly.` 
        })
      });
      const data = await res.json();
      setSummaryResult(data.reply || "No response generated.");
      setCustomPrompt('');
    } catch (err) {
      setSummaryResult(`Error: ${err.message}`);
    } finally {
      setSummaryLoading(false);
    }
  };

  return (
    <div className="page-container-wide animate-fade-in flex flex-col h-screen max-h-screen p-4 md:p-6 overflow-hidden">
      
      {/* Header */}
      <header className="flex justify-between items-center mb-6 shrink-0" style={{ marginBottom: '24px' }}>
        <div>
          <h2 className="text-2xl font-semibold mb-1 text-[var(--text-primary)]">AI Assistant</h2>
          <p className="text-sm text-[var(--text-secondary)]">Zalo & Telegram Intelligence</p>
        </div>
        {/* Mobile Panel Toggles */}
        <div className="flex md:hidden gap-2" style={{ gap: '8px' }}>
          <button className={`btn-secondary ${activePanel === 'groups' ? 'bg-[var(--bg-hover)]' : ''}`} onClick={() => setActivePanel('groups')}>Groups</button>
          <button className={`btn-secondary ${activePanel === 'chat' ? 'bg-[var(--bg-hover)]' : ''}`} onClick={() => setActivePanel('chat')}>Chat</button>
          <button className={`btn-secondary ${activePanel === 'summary' ? 'bg-[var(--bg-hover)]' : ''}`} onClick={() => setActivePanel('summary')}>AI</button>
        </div>
      </header>

      {/* 3-Panel Layout */}
      <div className="flex gap-6 flex-1 min-h-0" style={{ gap: '24px' }}>
        
        {/* PANEL 1: Groups (Left) */}
        <div className={`glass-panel w-full md:w-1/3 lg:w-1/4 flex flex-col ${activePanel === 'groups' ? 'block' : 'hidden md:flex'}`}>
          <div className="p-4 border-b border-[var(--border)] font-semibold text-[var(--text-secondary)] uppercase tracking-wider text-sm" style={{ padding: '16px' }}>
            Sources
          </div>
          <div className="flex-1 overflow-y-auto custom-scrollbar p-2" style={{ padding: '8px' }}>
            {groups.map(g => (
              <button 
                key={g}
                onClick={() => { setSelectedGroup(g); setActivePanel('chat'); }}
                className={`w-full text-left rounded-lg transition-colors mb-1 ${
                  selectedGroup === g 
                    ? 'bg-[var(--accent-soft)] border-l-2 border-[var(--accent)] text-[var(--text-primary)]' 
                    : 'text-[var(--text-secondary)] hover:bg-[var(--bg-hover)]'
                }`}
                style={{ padding: '12px 16px', marginBottom: '4px' }}
              >
                <div className="font-medium truncate">{getGroupName(g)}</div>
                <div className="text-xs mt-1 opacity-70">
                  {g === 'All' ? `${messages.length} messages` : `${messages.filter(m => (m.group_name || 'Direct') === g).length} messages`}
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* PANEL 2: Conversation (Center) */}
        <div className={`glass-panel w-full md:w-2/3 lg:w-2/4 flex flex-col ${activePanel === 'chat' ? 'block' : 'hidden md:flex'}`}>
          <div className="p-4 border-b border-[var(--border)] font-semibold flex justify-between items-center" style={{ padding: '16px' }}>
            <div className="flex items-center gap-2 overflow-hidden">
              <span className="truncate">{getGroupName(selectedGroup)} Conversation</span>
              {selectedGroup !== 'All' && (
                <button 
                  onClick={handleRenameGroup}
                  className="text-[var(--text-secondary)] hover:text-white transition-colors flex-shrink-0"
                  title="Đổi tên nhóm"
                >
                  ✏️
                </button>
              )}
            </div>
            {loading && <span className="text-xs text-[var(--text-secondary)] shrink-0 ml-2">Syncing...</span>}
          </div>
          
          <div className="flex-1 overflow-y-auto custom-scrollbar p-4 flex flex-col gap-4" style={{ padding: '16px', gap: '16px' }}>
            {filteredMessages.length === 0 ? (
              <div className="empty-state">No messages in this group.</div>
            ) : (
              [...filteredMessages].reverse().map(msg => {
                const isBot = (msg.sender_name || '').toLowerCase().includes('bot') || (msg.sender_name || '').toLowerCase().includes('assistant');
                return (
                  <div key={msg.id} className={`flex flex-col max-w-[85%] ${isBot ? 'self-end' : 'self-start'}`}>
                    <div className={`text-xs text-[var(--text-secondary)] mb-1 flex items-center gap-2 ${isBot ? 'flex-row-reverse' : 'flex-row'}`} style={{ marginBottom: '4px', gap: '8px' }}>
                      <span className="font-semibold text-white">{msg.sender_name || 'Unknown'}</span>
                      <span className="opacity-50">{formatTime(msg.timestamp)}</span>
                    </div>
                    <div className={`p-3 rounded-2xl whitespace-pre-wrap ${
                      isBot 
                        ? 'bg-[var(--accent-soft)] border border-[var(--accent)] text-white rounded-tr-sm' 
                        : 'bg-[var(--bg-hover)] border border-[var(--border)] text-white rounded-tl-sm'
                    }`} style={{ padding: '12px', lineHeight: '1.5' }}>
                      {msg.text}
                    </div>
                  </div>
                );
              })
            )}
            <div ref={chatEndRef} />
          </div>
        </div>

        {/* PANEL 3: AI Summary (Right) */}
        <div className={`glass-panel w-full lg:w-1/4 flex flex-col ${activePanel === 'summary' ? 'block' : 'hidden lg:flex'}`}>
          <div className="p-4 border-b border-[var(--border)] font-semibold text-[var(--success)] flex items-center gap-2" style={{ padding: '16px', gap: '8px' }}>
            ✨ AI Assistant
          </div>
          
          <div className="flex-1 overflow-y-auto custom-scrollbar p-4 flex flex-col gap-6" style={{ padding: '16px', gap: '24px' }}>
            
            {/* Controls */}
            <div className="flex flex-col gap-4" style={{ gap: '16px' }}>
              <div>
                <label className="block text-xs text-[var(--text-secondary)] mb-1" style={{ marginBottom: '4px' }}>Time Range</label>
                <select className="input-primary py-2 text-sm w-full" style={{ padding: '8px 12px' }} value={timeRange} onChange={e => setTimeRange(e.target.value)}>
                  <option value="today">Today</option>
                  <option value="24h">Last 24 Hours</option>
                  <option value="7d">Last 7 Days</option>
                </select>
              </div>
              <div>
                <label className="block text-xs text-[var(--text-secondary)] mb-1" style={{ marginBottom: '4px' }}>Summary Type</label>
                <select className="input-primary py-2 text-sm w-full" style={{ padding: '8px 12px' }} value={summaryType} onChange={e => setSummaryType(e.target.value)}>
                  <option value="general">General Overview</option>
                  <option value="tasks">Tasks & Actions</option>
                  <option value="issues">Issues & Blockers</option>
                </select>
              </div>
              <button 
                className="btn-primary w-full py-2 mt-2 flex justify-center items-center gap-2"
                style={{ marginTop: '8px', padding: '10px 0', gap: '8px' }}
                onClick={handleGenerateSummary}
                disabled={summaryLoading}
              >
                {summaryLoading ? 'Generating...' : 'Generate Summary'}
              </button>
            </div>

            {/* Results */}
            {summaryLoading ? (
              <div className="flex flex-col gap-3 mt-4 flex-1">
                <div className="skeleton h-4 w-3/4"></div>
                <div className="skeleton h-4 w-full"></div>
                <div className="skeleton h-4 w-5/6"></div>
              </div>
            ) : summaryResult ? (
              <div className="mt-4 p-4 rounded-xl bg-[var(--bg-hover)] border border-[var(--border)] text-sm text-[var(--text-primary)] whitespace-pre-wrap leading-relaxed flex-1 overflow-y-auto custom-scrollbar">
                {summaryResult}
              </div>
            ) : (
              <div className="empty-state mt-4 opacity-50 flex-1">
                Select options and generate a summary to see insights.
              </div>
            )}
            
            {/* Custom Prompt Input */}
            <div className="mt-auto border-t border-[var(--border)] pt-4 shrink-0" style={{ marginTop: 'auto', paddingTop: '16px' }}>
              <div className="flex gap-2" style={{ gap: '8px', alignItems: 'stretch' }}>
                <input 
                  type="text" 
                  className="input-primary flex-1 bg-[var(--bg-hover)]" 
                  style={{ padding: '12px' }}
                  placeholder="Hỏi AI về đoạn chat này..." 
                  value={customPrompt}
                  onChange={e => setCustomPrompt(e.target.value)}
                  onKeyDown={e => e.key === 'Enter' && handleAskAI()}
                  disabled={summaryLoading}
                />
                <button 
                  className="btn-primary px-4 font-bold"
                  style={{ padding: '0 20px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}
                  onClick={handleAskAI}
                  disabled={summaryLoading || !customPrompt.trim()}
                >
                  ➤
                </button>
              </div>
            </div>
            
          </div>
        </div>
      </div>

    </div>
  );
}
