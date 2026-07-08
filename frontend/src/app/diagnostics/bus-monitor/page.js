'use client';
import { useState, useEffect } from 'react';

export default function BusMonitor() {
    const [telegrams, setTelegrams] = useState([]);
    const [isPaused, setIsPaused] = useState(false);

    useEffect(() => {
        if (isPaused) return;

        const eventSource = new EventSource('/api/bus/stream');
        
        eventSource.onmessage = (e) => {
            try {
                const data = JSON.parse(e.data);
                setTelegrams(prev => [data, ...prev].slice(0, 1000)); // Keep latest 1000
            } catch (err) {
                console.error("SSE Parse error", err);
            }
        };

        return () => {
            eventSource.close();
        };
    }, [isPaused]);

    const clearMonitor = () => setTelegrams([]);

    return (
        <div style={{ padding: '24px', maxWidth: '1400px', margin: '0 auto' }}>
            <header style={{ marginBottom: '24px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                    <h2 style={{ fontSize: '1.8rem', fontWeight: 'bold', color: '#facc15' }}>KNX Bus Monitor</h2>
                    <p style={{ color: 'var(--text-secondary)' }}>Diagnostic tool showing raw KNX telegrams on the bus.</p>
                </div>
                <div style={{ display: 'flex', gap: '12px' }}>
                    <button 
                        onClick={() => setIsPaused(!isPaused)}
                        style={{ padding: '8px 16px', borderRadius: '8px', background: isPaused ? '#10b981' : '#ef4444', color: '#fff', border: 'none', cursor: 'pointer', fontWeight: 'bold' }}
                    >
                        {isPaused ? '▶ Resume' : '⏸ Pause'}
                    </button>
                    <button 
                        onClick={clearMonitor}
                        style={{ padding: '8px 16px', borderRadius: '8px', background: 'rgba(255,255,255,0.1)', color: '#fff', border: '1px solid rgba(255,255,255,0.2)', cursor: 'pointer' }}
                    >
                        Clear
                    </button>
                </div>
            </header>

            <div className="glass-panel" style={{ overflow: 'hidden', background: '#0f172a' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.85rem', fontFamily: 'monospace' }}>
                    <thead>
                        <tr style={{ background: 'rgba(255,255,255,0.05)', borderBottom: '1px solid rgba(255,255,255,0.2)', color: '#94a3b8' }}>
                            <th style={{ padding: '8px 16px' }}>Timestamp</th>
                            <th style={{ padding: '8px 16px' }}>Direction</th>
                            <th style={{ padding: '8px 16px' }}>Source Address</th>
                            <th style={{ padding: '8px 16px' }}>Dest Address</th>
                            <th style={{ padding: '8px 16px' }}>Payload</th>
                        </tr>
                    </thead>
                    <tbody>
                        {telegrams.length === 0 ? (
                            <tr>
                                <td colSpan="5" style={{ padding: '24px', textAlign: 'center', color: '#475569' }}>
                                    No telegrams captured yet...
                                </td>
                            </tr>
                        ) : (
                            telegrams.map((t, idx) => (
                                <tr key={idx} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                                    <td style={{ padding: '6px 16px', color: '#94a3b8' }}>{new Date(t.timestamp * 1000).toISOString().split('T')[1].replace('Z', '')}</td>
                                    <td style={{ padding: '6px 16px', color: t.direction === 'Incoming' ? '#34d399' : '#60a5fa' }}>{t.direction}</td>
                                    <td style={{ padding: '6px 16px', color: '#facc15' }}>{t.source_address}</td>
                                    <td style={{ padding: '6px 16px', color: '#f472b6', fontWeight: 'bold' }}>{t.destination_address}</td>
                                    <td style={{ padding: '6px 16px', color: '#a78bfa' }}>{t.payload}</td>
                                </tr>
                            ))
                        )}
                    </tbody>
                </table>
            </div>
        </div>
    );
}
