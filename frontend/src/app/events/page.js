'use client';
import { useState, useEffect } from 'react';

export default function EventCenter() {
    const [events, setEvents] = useState([]);
    const [filter, setFilter] = useState('ALL'); // ALL, Dashboard/AI, Wall Switch, KNX Bus

    useEffect(() => {
        // Fetch historical initially
        // We don't have a global history endpoint yet, but we can just accumulate realtime for now
        // For production, we'd add `GET /api/events/history`.
        const eventSource = new EventSource('/api/events/stream');
        
        eventSource.onmessage = (e) => {
            try {
                const data = JSON.parse(e.data);
                setEvents(prev => [data, ...prev].slice(0, 500)); // Keep latest 500
            } catch (err) {
                console.error("SSE Parse error", err);
            }
        };

        return () => {
            eventSource.close();
        };
    }, []);

    const filteredEvents = events.filter(e => {
        if (filter === 'ALL') return true;
        return e.source === filter;
    });

    return (
        <div style={{ padding: '24px', maxWidth: '1200px', margin: '0 auto' }}>
            <header style={{ marginBottom: '24px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                    <h2 style={{ fontSize: '1.8rem', fontWeight: 'bold' }}>Event Center (Realtime)</h2>
                    <p style={{ color: 'var(--text-secondary)' }}>Live monitoring of system-wide state changes.</p>
                </div>
                <div>
                    <select 
                        value={filter} 
                        onChange={(e) => setFilter(e.target.value)}
                        style={{ padding: '8px 16px', borderRadius: '8px', background: 'rgba(255,255,255,0.1)', color: '#fff', border: '1px solid rgba(255,255,255,0.2)' }}
                    >
                        <option value="ALL">All Sources</option>
                        <option value="Dashboard/AI">Dashboard / AI</option>
                        <option value="Wall Switch">Wall Switch</option>
                        <option value="KNX Bus">Other KNX Bus</option>
                    </select>
                </div>
            </header>

            <div className="glass-panel" style={{ overflow: 'hidden' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.95rem' }}>
                    <thead>
                        <tr style={{ background: 'rgba(255,255,255,0.05)', borderBottom: '1px solid rgba(255,255,255,0.1)' }}>
                            <th style={{ padding: '12px 16px' }}>Timestamp</th>
                            <th style={{ padding: '12px 16px' }}>Device ID</th>
                            <th style={{ padding: '12px 16px' }}>Action</th>
                            <th style={{ padding: '12px 16px' }}>State</th>
                            <th style={{ padding: '12px 16px' }}>Source</th>
                        </tr>
                    </thead>
                    <tbody>
                        {filteredEvents.length === 0 ? (
                            <tr>
                                <td colSpan="5" style={{ padding: '24px', textAlign: 'center', color: 'var(--text-secondary)' }}>
                                    Waiting for events... (Try pressing a switch or using the Dashboard)
                                </td>
                            </tr>
                        ) : (
                            filteredEvents.map((evt, idx) => (
                                <tr key={idx} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                                    <td style={{ padding: '12px 16px' }}>{new Date(evt.timestamp * 1000).toLocaleString()}</td>
                                    <td style={{ padding: '12px 16px', fontWeight: 'bold', color: '#3b82f6' }}>{evt.device_id}</td>
                                    <td style={{ padding: '12px 16px' }}>{evt.action}</td>
                                    <td style={{ padding: '12px 16px', color: (evt.state === 'ON' || evt.state === '1') ? '#10b981' : '#ef4444', fontWeight: 'bold' }}>
                                        {evt.state}
                                    </td>
                                    <td style={{ padding: '12px 16px' }}>
                                        <span style={{ 
                                            padding: '4px 8px', borderRadius: '4px', fontSize: '0.85rem',
                                            background: evt.source === 'Dashboard/AI' ? 'rgba(59, 130, 246, 0.2)' : 'rgba(16, 185, 129, 0.2)',
                                            color: evt.source === 'Dashboard/AI' ? '#60a5fa' : '#34d399'
                                        }}>
                                            {evt.source}
                                        </span>
                                    </td>
                                </tr>
                            ))
                        )}
                    </tbody>
                </table>
            </div>
        </div>
    );
}
