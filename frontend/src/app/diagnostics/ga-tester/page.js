'use client';
import { useState, useRef, useEffect } from 'react';

export default function GATester() {
    const [address, setAddress] = useState('');
    const [valueType, setValueType] = useState('1byte_unsigned');
    const [writeValue, setWriteValue] = useState('');
    const [result, setResult] = useState(null);
    const [loading, setLoading] = useState(false);
    
    // Advanced UI state
    const [etsData, setEtsData] = useState([]);
    const [searchQuery, setSearchQuery] = useState('');
    const [history, setHistory] = useState([]);
    
    const fileInputRef = useRef(null);

    const DPT_OPTIONS = [
        { value: '', label: 'Auto / None (Bool)' },
        { value: '1byte_unsigned', label: '1-byte unsigned (DPT 5.*) - Percent/Dimming' },
        { value: '2byte_float', label: '2-byte float (DPT 9.*) - Temperature' },
        { value: 'scene_number', label: 'Scene Number (DPT 17.001)' },
        { value: 'rgb', label: 'RGB Color (DPT 232.600)' },
        { value: 'time', label: 'Time (DPT 10.001)' },
        { value: 'date', label: 'Date (DPT 11.001)' },
        { value: 'string', label: 'String (DPT 16.000)' }
    ];

    useEffect(() => {
        const stored = localStorage.getItem('ga_history');
        if(stored) {
            try { setHistory(JSON.parse(stored)); } catch(e){}
        }
    }, []);

    const saveHistory = (addr, type, val, op) => {
        const newHist = [{ addr, type, val, op, time: new Date().toISOString() }, ...history].slice(0, 50);
        setHistory(newHist);
        localStorage.setItem('ga_history', JSON.stringify(newHist));
    };

    const handleRead = async () => {
        if (!address) { alert('Please enter a Group Address'); return; }
        setLoading(true); setResult(null);
        try {
            const reqBody = { address };
            if (valueType) reqBody.value_type = valueType;
            
            const res = await fetch('/api/diagnostics/ga-tester/read', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(reqBody) });
            const data = await res.json();
            if (res.ok) {
                setResult({ type: 'success', data: data.value, raw: data });
                saveHistory(address, valueType, data.value, 'READ');
            } else {
                setResult({ type: 'error', data: data.detail || JSON.stringify(data) });
            }
        } catch (e) { setResult({ type: 'error', data: e.message }); } finally { setLoading(false); }
    };

    const handleWrite = async () => {
        if (!address) { alert('Please enter a Group Address'); return; }
        let parsedVal = writeValue;
        if (parsedVal === 'true' || parsedVal === '1' || parsedVal.toLowerCase() === 'on') parsedVal = true;
        else if (parsedVal === 'false' || parsedVal === '0' || parsedVal.toLowerCase() === 'off') parsedVal = false;
        else if (!isNaN(parsedVal) && parsedVal !== '') parsedVal = Number(parsedVal);
        // Arrays for RGB e.g. [255, 0, 0]
        if (typeof parsedVal === 'string' && parsedVal.startsWith('[') && parsedVal.endsWith(']')) {
            try { parsedVal = JSON.parse(parsedVal); } catch(e){}
        }
        
        setLoading(true); setResult(null);
        try {
            const reqBody = { address, value: parsedVal };
            if (valueType) reqBody.value_type = valueType;
            
            const res = await fetch('/api/diagnostics/ga-tester/write', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(reqBody) });
            const data = await res.json();
            if (res.ok) {
                setResult({ type: 'success', data: `Successfully wrote ${JSON.stringify(parsedVal)} to ${address}`, raw: data });
                saveHistory(address, valueType, parsedVal, 'WRITE');
            } else {
                setResult({ type: 'error', data: data.detail || JSON.stringify(data) });
            }
        } catch (e) { setResult({ type: 'error', data: e.message }); } finally { setLoading(false); }
    };

    const handleFileUpload = (e) => {
        const file = e.target.files[0];
        if (!file) return;
        const reader = new FileReader();
        reader.onload = (evt) => {
            const text = evt.target.result;
            const lines = text.split('\n');
            const data = [];
            // Basic CSV parsing
            for (let i = 1; i < lines.length; i++) {
                if(!lines[i].trim()) continue;
                // handle quotes
                const cols = lines[i].split(/,(?=(?:(?:[^"]*"){2})*[^"]*$)/);
                if(cols.length >= 3) {
                    let name = cols[0].replace(/^"|"$/g, '').trim();
                    let ga = cols[1].replace(/^"|"$/g, '').trim();
                    let dpt = cols[2] ? cols[2].replace(/^"|"$/g, '').trim() : '';
                    if(!ga) { ga = cols[2]; dpt = cols[3]; } // ETS formats vary
                    
                    if(ga && ga.match(/^\d+\/\d+\/\d+$/)) {
                        data.push({ name, ga, dpt });
                    }
                }
            }
            setEtsData(data);
            alert(`Loaded ${data.length} Group Addresses from ETS.`);
        };
        reader.readAsText(file);
    };

    const selectGA = (ga, dptStr) => {
        setAddress(ga);
        // Best effort DPT match
        if (dptStr) {
            if (dptStr.includes('DPST-1') || dptStr.toLowerCase().includes('switch')) setValueType('');
            else if (dptStr.includes('DPST-5') || dptStr.toLowerCase().includes('percent')) setValueType('1byte_unsigned');
            else if (dptStr.includes('DPST-9') || dptStr.toLowerCase().includes('temperature')) setValueType('2byte_float');
            else if (dptStr.includes('DPST-17')) setValueType('scene_number');
        }
    };

    const filteredEts = etsData.filter(d => d.name.toLowerCase().includes(searchQuery.toLowerCase()) || d.ga.includes(searchQuery));

    return (
        <div style={{ padding: '24px', maxWidth: '1200px', margin: '0 auto', display: 'grid', gridTemplateColumns: '1fr 350px', gap: '24px' }}>
            <div>
                <header style={{ marginBottom: '24px' }}>
                    <h2 style={{ fontSize: '1.8rem', fontWeight: 'bold', color: '#facc15' }}>Group Address Tester</h2>
                    <p style={{ color: 'var(--text-secondary)' }}>Directly read/write to any KNX Group Address on the bus.</p>
                </header>

                <div className="glass-panel" style={{ padding: '24px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
                        <div>
                            <label style={{ display: 'block', marginBottom: '8px', fontWeight: 'bold' }}>Group Address (e.g., 1/1/1)</label>
                            <input 
                                type="text" 
                                value={address} 
                                onChange={(e) => setAddress(e.target.value)}
                                placeholder="Group Address"
                                style={{ width: '100%', padding: '12px', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.2)', background: 'rgba(0,0,0,0.2)', color: '#fff', fontSize: '1.2rem', fontFamily: 'monospace' }}
                            />
                        </div>

                        <div>
                            <label style={{ display: 'block', marginBottom: '8px', fontWeight: 'bold' }}>Data Point Type (DPT)</label>
                            <select 
                                value={valueType} 
                                onChange={(e) => setValueType(e.target.value)}
                                style={{ width: '100%', padding: '12px', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.2)', background: 'rgba(0,0,0,0.2)', color: '#fff' }}
                            >
                                {DPT_OPTIONS.map(opt => (
                                    <option key={opt.value} value={opt.value} style={{ background: '#1e293b' }}>{opt.label}</option>
                                ))}
                            </select>
                        </div>
                    </div>

                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginTop: '16px' }}>
                        <div style={{ padding: '16px', background: 'rgba(255,255,255,0.05)', borderRadius: '8px', borderLeft: '4px solid #3b82f6', display: 'flex', flexDirection: 'column' }}>
                            <h3 style={{ marginBottom: '12px', fontSize: '1.1rem', fontWeight: 'bold' }}>Read Operation</h3>
                            <button 
                                onClick={handleRead}
                                disabled={loading}
                                style={{ padding: '12px 20px', borderRadius: '8px', background: '#3b82f6', color: '#fff', border: 'none', cursor: 'pointer', fontWeight: 'bold', opacity: loading ? 0.7 : 1, marginTop: 'auto' }}
                            >
                                {loading ? 'Reading...' : 'Read Value'}
                            </button>
                        </div>

                        <div style={{ padding: '16px', background: 'rgba(255,255,255,0.05)', borderRadius: '8px', borderLeft: '4px solid #10b981', display: 'flex', flexDirection: 'column' }}>
                            <h3 style={{ marginBottom: '12px', fontSize: '1.1rem', fontWeight: 'bold' }}>Write Operation</h3>
                            <input 
                                type="text" 
                                value={writeValue} 
                                onChange={(e) => setWriteValue(e.target.value)}
                                placeholder="Value (e.g. 1, 0, 100, true, 24.5)"
                                style={{ padding: '10px', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.2)', background: 'rgba(0,0,0,0.2)', color: '#fff', marginBottom: '12px' }}
                            />
                            <button 
                                onClick={handleWrite}
                                disabled={loading}
                                style={{ padding: '12px 20px', borderRadius: '8px', background: '#10b981', color: '#fff', border: 'none', cursor: 'pointer', fontWeight: 'bold', opacity: loading ? 0.7 : 1 }}
                            >
                                {loading ? 'Writing...' : 'Write Value'}
                            </button>
                        </div>
                    </div>

                    {result && (
                        <div style={{ marginTop: '16px', padding: '16px', borderRadius: '8px', background: result.type === 'error' ? 'rgba(239,68,68,0.2)' : 'rgba(16,185,129,0.2)', border: `1px solid ${result.type === 'error' ? '#ef4444' : '#10b981'}` }}>
                            <h4 style={{ fontWeight: 'bold', color: result.type === 'error' ? '#fca5a5' : '#6ee7b7', marginBottom: '8px' }}>
                                {result.type === 'error' ? 'Error' : 'Success'}
                            </h4>
                            <pre style={{ margin: 0, whiteSpace: 'pre-wrap', wordBreak: 'break-all', fontFamily: 'monospace', fontSize: '0.9rem' }}>
                                {JSON.stringify(result.data, null, 2)}
                            </pre>
                        </div>
                    )}
                </div>
            </div>
            
            {/* Right Sidebar: ETS Import & History */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
                
                {/* ETS Section */}
                <div className="glass-panel" style={{ padding: '16px', display: 'flex', flexDirection: 'column', height: '400px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                        <h3 style={{ fontWeight: 'bold', fontSize: '1.1rem' }}>ETS Project</h3>
                        <button onClick={() => fileInputRef.current.click()} style={{ background: '#3b82f6', color: '#fff', border: 'none', padding: '4px 8px', borderRadius: '4px', cursor: 'pointer', fontSize: '0.8rem' }}>
                            Import CSV
                        </button>
                        <input type="file" ref={fileInputRef} onChange={handleFileUpload} accept=".csv" style={{ display: 'none' }} />
                    </div>
                    
                    {etsData.length > 0 ? (
                        <>
                            <input 
                                type="text" 
                                placeholder="Search Name or GA..." 
                                value={searchQuery}
                                onChange={(e) => setSearchQuery(e.target.value)}
                                style={{ width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid rgba(255,255,255,0.2)', background: 'rgba(0,0,0,0.2)', color: '#fff', marginBottom: '12px' }}
                            />
                            <div style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '4px' }}>
                                {filteredEts.map((item, idx) => (
                                    <div key={idx} onClick={() => selectGA(item.ga, item.dpt)} style={{ padding: '8px', background: 'rgba(255,255,255,0.05)', borderRadius: '4px', cursor: 'pointer', fontSize: '0.85rem' }}>
                                        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                                            <strong style={{ color: '#60a5fa' }}>{item.ga}</strong>
                                            <span style={{ color: '#94a3b8', fontSize: '0.75rem' }}>{item.dpt}</span>
                                        </div>
                                        <div style={{ color: '#e2e8f0', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{item.name}</div>
                                    </div>
                                ))}
                            </div>
                        </>
                    ) : (
                        <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#64748b', textAlign: 'center', fontSize: '0.9rem' }}>
                            Import Group Addresses from ETS (CSV format) for quick access.
                        </div>
                    )}
                </div>

                {/* History Section */}
                <div className="glass-panel" style={{ padding: '16px', display: 'flex', flexDirection: 'column', flex: 1, maxHeight: '300px' }}>
                    <h3 style={{ fontWeight: 'bold', fontSize: '1.1rem', marginBottom: '12px' }}>Recent Activity</h3>
                    <div style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '8px' }}>
                        {history.length > 0 ? history.map((h, i) => (
                            <div key={i} onClick={() => selectGA(h.addr, h.type)} style={{ padding: '8px', background: 'rgba(255,255,255,0.05)', borderRadius: '4px', cursor: 'pointer', fontSize: '0.8rem', borderLeft: `3px solid ${h.op==='READ' ? '#3b82f6' : '#10b981'}` }}>
                                <div style={{ display: 'flex', justifyContent: 'space-between', color: '#94a3b8', marginBottom: '4px' }}>
                                    <span>{new Date(h.time).toLocaleTimeString()}</span>
                                    <span>{h.op}</span>
                                </div>
                                <div>
                                    <strong style={{ color: '#fff' }}>{h.addr}</strong> 
                                    {h.op === 'WRITE' ? ` ➔ ${JSON.stringify(h.val)}` : ` = ${JSON.stringify(h.val)}`}
                                </div>
                            </div>
                        )) : (
                            <div style={{ color: '#64748b', textAlign: 'center', fontSize: '0.9rem', marginTop: '20px' }}>No recent activity.</div>
                        )}
                    </div>
                </div>

            </div>
        </div>
    );
}
