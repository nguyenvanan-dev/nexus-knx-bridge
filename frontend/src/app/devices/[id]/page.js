'use client';
import { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { controlDevice } from '../../../api/controlApi';
import { showDialog, showToast } from '../../../utils/ui';

export default function DeviceDetailsPage() {
    const params = useParams();
    const router = useRouter();
    const { id } = params;

    const [deviceInfo, setDeviceInfo] = useState(null);
    const [status, setStatus] = useState("UNKNOWN");
    const [history, setHistory] = useState([]);
    const [loading, setLoading] = useState(true);

    // Fetch static device config
    const fetchDeviceInfo = async () => {
        try {
            const res = await fetch('/api/devices');
            const data = await res.json();
            if (data[id]) {
                setDeviceInfo(data[id]);
            } else {
                showDialog("Not Found", "Device not found!", "warning", () => {
                    router.push('/devices');
                });
            }
        } catch (e) {
            console.error("Error fetching device info", e);
        }
    };

    // Fetch dynamic status & history
    const fetchStatusAndHistory = async () => {
        try {
            const [statusRes, historyRes] = await Promise.all([
                fetch(`/api/devices/${id}/status`),
                fetch(`/api/devices/${id}/history`)
            ]);
            
            if (statusRes.ok) {
                const sData = await statusRes.json();
                setStatus(sData.state);
            }
            if (historyRes.ok) {
                const hData = await historyRes.json();
                setHistory(hData.history || []);
            }
        } catch (e) {
            console.error("Error fetching dynamic data", e);
        } finally {
            setLoading(false);
        }
    };

    /* eslint-disable react-hooks/set-state-in-effect, react-hooks/exhaustive-deps */
    useEffect(() => {
        if (!id) return;
        fetchDeviceInfo();
        fetchStatusAndHistory();

        // Server-Sent Events for Realtime Updates
        const eventSource = new EventSource('/api/events/stream');
        
        eventSource.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                // If the event is for this device, update state and history
                if (data.device_id === id) {
                    setStatus(data.state);
                    setHistory(prev => [data, ...prev].slice(0, 50)); // Keep latest 50
                }
            } catch (err) {
                console.error("SSE Parse error", err);
            }
        };

        eventSource.onerror = (err) => {
            console.error("SSE Error", err);
            // Browser will auto-reconnect EventSource
        };

        return () => {
            eventSource.close();
        };
    }, [id]);
    /* eslint-enable react-hooks/set-state-in-effect, react-hooks/exhaustive-deps */

    const handleControl = async (action) => {
        try {
            // Using the shared api helper
            const res = await controlDevice({ deviceId: id, action });
            
            // fetchApi returns the parsed json if ok, or throws error if not ok.
            // But we need to handle success here based on it not throwing.
            setStatus(action === 'on' ? 'ON' : 'OFF');
            fetchStatusAndHistory();
            showToast("Command executed successfully", "success");
        } catch (e) {
            showDialog("Error", "Error: " + e.message, "danger");
        }
    };

    if (loading || !deviceInfo) {
        return <div style={{ textAlign: 'center', color: 'var(--text-secondary)', padding: '50px' }}>Loading...</div>;
    }

    const isLightOn = status === 'ON' || status === '1' || status === 'True';

    return (
        <div style={{ maxWidth: '1000px', margin: '0 auto' }}>
            <header style={{ display: 'flex', alignItems: 'center', gap: '16px', marginBottom: '24px' }}>
                <button onClick={() => router.push('/devices')} style={{ background: 'rgba(255,255,255,0.1)', border: 'none', color: '#fff', borderRadius: '50%', width: '40px', height: '40px', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '1.2rem' }}>
                    &larr;
                </button>
                <div>
                    <h2 style={{ fontSize: '1.8rem', fontWeight: '600', margin: 0 }}>{id}</h2>
                    <p style={{ color: 'var(--text-secondary)', marginTop: '4px' }}>{deviceInfo.type.toUpperCase()}</p>
                </div>
            </header>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: '24px' }}>
                {/* Left Panel: Status & Control */}
                <div className="glass-panel" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', padding: '32px 20px' }}>
                    <div style={{ 
                        width: '120px', height: '120px', borderRadius: '50%', 
                        background: isLightOn ? 'rgba(250, 204, 21, 0.2)' : 'rgba(255,255,255,0.05)',
                        border: `2px solid ${isLightOn ? '#facc15' : 'rgba(255,255,255,0.1)'}`,
                        display: 'flex', alignItems: 'center', justifyContent: 'center',
                        fontSize: '3rem', marginBottom: '24px',
                        boxShadow: isLightOn ? '0 0 30px rgba(250, 204, 21, 0.4)' : 'none',
                        transition: 'all 0.3s ease'
                    }}>
                        💡
                    </div>
                    <h3 style={{ fontSize: '1.5rem', marginBottom: '8px' }}>
                        {status}
                    </h3>
                    <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', marginBottom: '32px' }}>Realtime Status</p>

                    <div style={{ display: 'flex', gap: '16px', width: '100%' }}>
                        <button onClick={() => handleControl('on')} style={{ flex: 1, background: '#10b981', color: '#fff', border: 'none', padding: '16px', borderRadius: '12px', fontSize: '1.1rem', fontWeight: 'bold', cursor: 'pointer' }}>ON</button>
                        <button onClick={() => handleControl('off')} style={{ flex: 1, background: '#ef4444', color: '#fff', border: 'none', padding: '16px', borderRadius: '12px', fontSize: '1.1rem', fontWeight: 'bold', cursor: 'pointer' }}>OFF</button>
                    </div>
                </div>

                {/* Right Panel: Configuration & History */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
                    
                    {/* Config Box */}
                    <div className="glass-panel" style={{ padding: '20px' }}>
                        <h4 style={{ marginBottom: '16px', color: '#3b82f6' }}>Group Addresses Configuration</h4>
                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', fontSize: '0.9rem' }}>
                            <div>
                                <span style={{ color: 'var(--text-secondary)' }}>ON/OFF Address</span>
                                <div style={{ background: 'rgba(0,0,0,0.3)', padding: '8px 12px', borderRadius: '6px', marginTop: '4px' }}>{deviceInfo.onoff_ga || 'N/A'}</div>
                            </div>
                            <div>
                                <span style={{ color: 'var(--text-secondary)' }}>Status Address</span>
                                <div style={{ background: 'rgba(0,0,0,0.3)', padding: '8px 12px', borderRadius: '6px', marginTop: '4px' }}>{deviceInfo.status_ga || 'N/A'}</div>
                            </div>
                            {deviceInfo.type === 'dimmer' && (
                                <>
                                    <div>
                                        <span style={{ color: 'var(--text-secondary)' }}>Brightness Target</span>
                                        <div style={{ background: 'rgba(0,0,0,0.3)', padding: '8px 12px', borderRadius: '6px', marginTop: '4px' }}>{deviceInfo.brightness_ga || 'N/A'}</div>
                                    </div>
                                    <div>
                                        <span style={{ color: 'var(--text-secondary)' }}>Brightness Status</span>
                                        <div style={{ background: 'rgba(0,0,0,0.3)', padding: '8px 12px', borderRadius: '6px', marginTop: '4px' }}>{deviceInfo.brightness_status_ga || 'N/A'}</div>
                                    </div>
                                </>
                            )}
                        </div>
                    </div>

                    {/* History Log */}
                    <div className="glass-panel" style={{ padding: '20px', flex: 1 }}>
                        <h4 style={{ marginBottom: '16px', color: '#10b981' }}>Operation History</h4>
                        {history.length === 0 ? (
                            <div style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', textAlign: 'center', padding: '20px' }}>No events recorded yet.</div>
                        ) : (
                            <div style={{ maxHeight: '300px', overflowY: 'auto' }}>
                                <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.9rem' }}>
                                    <thead>
                                        <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.1)', color: 'var(--text-secondary)' }}>
                                            <th style={{ padding: '8px' }}>Time</th>
                                            <th style={{ padding: '8px' }}>Action/Source</th>
                                            <th style={{ padding: '8px' }}>State</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {history.map((item, idx) => (
                                            <tr key={idx} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                                                <td style={{ padding: '8px' }}>{new Date(item.timestamp * 1000).toLocaleString()}</td>
                                                <td style={{ padding: '8px' }}>
                                                    <span style={{ padding: '2px 6px', background: 'rgba(255,255,255,0.1)', borderRadius: '4px', fontSize: '0.8rem' }}>{item.action}</span>
                                                </td>
                                                <td style={{ padding: '8px', color: (item.state === 'ON' || item.state === '1') ? '#10b981' : '#ef4444' }}>
                                                    {item.state}
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}
