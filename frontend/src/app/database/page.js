'use client';
import { useState, useEffect } from 'react';

const TABLE_GROUPS = [
  {
    name: '1. Quản lý Thiết bị',
    tables: ['devices'],
    desc: { devices: 'Cấu hình thiết bị KNX vật lý' }
  },
  {
    name: '2. Lịch sử & Thống kê',
    tables: ['device_history', 'command_audit', 'analytics_daily'],
    desc: { device_history: 'Lịch sử bật/tắt thiết bị', command_audit: 'Nhật ký các lệnh điều khiển', analytics_daily: 'Dữ liệu thống kê theo ngày' }
  },
  {
    name: '3. AI & Trợ lý ảo',
    tables: ['ai_conversations', 'ai_memories'],
    desc: { ai_conversations: 'Lịch sử chat với OpenClaw', ai_memories: 'Bộ nhớ / sở thích người dùng' }
  },
  {
    name: '4. Tự động hóa & Kịch bản',
    tables: ['scenes', 'scene_actions', 'scene_versions', 'automation_rules', 'automation_rules_v2', 'floor_plans', 'floor_plan_devices'],
    desc: {
      scenes: 'Tên Kịch bản', scene_actions: 'Hành động của Kịch bản', scene_versions: 'Lịch sử sửa Kịch bản',
      automation_rules: 'Luật tự động hóa', automation_rules_v2: 'Luật tự động hóa V2',
      floor_plans: 'Bản đồ mặt bằng', floor_plan_devices: 'Vị trí thiết bị trên bản đồ'
    }
  }
];


export default function DatabasePage() {
  const [tables, setTables] = useState([]);
  const [loadingTables, setLoadingTables] = useState(true);
  const [viewMode, setViewMode] = useState('visual'); // 'visual' or 'sql'
  
  const [activeTable, setActiveTable] = useState('');
  const [tableData, setTableData] = useState({ columns: [], data: [] });
  const [loadingData, setLoadingData] = useState(false);
  // SQL Mode state
  const [query, setQuery] = useState('SELECT * FROM scenes LIMIT 10;');
  const [queryResult, setQueryResult] = useState(null);
  const [queryError, setQueryError] = useState(null);
  const [executing, setExecuting] = useState(false);

  const fetchTables = async () => {
    try {
      const res = await fetch('/api/database/tables');
      const data = await res.json();
      if (data.tables) {
        setTables(data.tables);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoadingTables(false);
    }
  };

  useEffect(() => {
    fetchTables();
  }, []);

  const loadTableData = async (tableName) => {
    setActiveTable(tableName);
    setLoadingData(true);
    try {
      const res = await fetch('/api/database/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: `SELECT * FROM ${tableName} LIMIT 100;` })
      });
      const data = await res.json();
      if (res.ok) {
        setTableData({ columns: data.columns || [], data: data.data || [] });
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoadingData(false);
    }
  };

  const handleTableClick = (tableName) => {
    if (viewMode === 'visual') {
        loadTableData(tableName);
    } else {
        const nextQuery = `SELECT * FROM ${tableName} LIMIT 50;`;
        setQuery(nextQuery);
        handleExecute(nextQuery);
    }
  };

  const handleExecute = async (sql = query) => {
    if (!sql.trim()) return;
    setExecuting(true);
    setQueryError(null);
    setQueryResult(null);
    try {
      const res = await fetch('/api/database/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: sql.trim() })
      });
      const data = await res.json();
      if (!res.ok) setQueryError(data.detail || data.error || 'Unknown error');
      else {
        setQueryResult(data);
      }
    } catch (e) {
      setQueryError(e.message);
    } finally {
      setExecuting(false);
    }
  };

  return (
    <div className="page-container animate-fade-in flex flex-col h-full max-h-full">
      <header className="shrink-0" style={{ marginBottom: '24px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
            <h2 style={{ fontSize: '1.5rem', fontWeight: '600' }}>Database Manager</h2>
            <p style={{ color: 'var(--text-secondary)', marginTop: '4px' }}>Read-only browser for approved smarthome.db tables</p>
        </div>
        <div style={{ background: 'rgba(0,0,0,0.3)', padding: '4px', borderRadius: '8px', display: 'flex' }}>
            <button 
                onClick={() => setViewMode('visual')}
                style={{ background: viewMode === 'visual' ? '#3b82f6' : 'transparent', color: viewMode === 'visual' ? 'white' : 'var(--text-secondary)', border: 'none', padding: '6px 16px', borderRadius: '4px', cursor: 'pointer', fontWeight: 'bold' }}>
                Visual Browser
            </button>
            <button 
                onClick={() => setViewMode('sql')}
                style={{ background: viewMode === 'sql' ? '#3b82f6' : 'transparent', color: viewMode === 'sql' ? 'white' : 'var(--text-secondary)', border: 'none', padding: '6px 16px', borderRadius: '4px', cursor: 'pointer', fontWeight: 'bold' }}>
                Read-only SQL
            </button>
        </div>
      </header>

      <div className="flex-1 overflow-hidden" style={{ display: 'grid', gridTemplateColumns: '320px 1fr', gap: '24px', minHeight: 0 }}>
        {/* Left Sidebar - Tables */}
        <div className="glass-panel flex flex-col overflow-hidden" style={{ padding: '16px', display: 'flex', minHeight: 0 }}>
          <h3 className="shrink-0" style={{ fontSize: '1rem', marginBottom: '16px', color: '#10b981' }}>Tables</h3>
          <div className="flex-1 overflow-y-auto custom-scrollbar" style={{ paddingRight: '4px' }}>
            {loadingTables ? (
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>Loading...</p>
          ) : tables.length === 0 ? (
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>No tables found.</p>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
              {TABLE_GROUPS.map(group => {
                  const groupTables = tables.filter(t => group.tables.includes(t.name));
                  if (groupTables.length === 0) return null;
                  return (
                      <div key={group.name}>
                          <h4 style={{ fontSize: '0.75rem', textTransform: 'uppercase', color: 'var(--text-secondary)', marginBottom: '8px', fontWeight: 'bold', letterSpacing: '0.05em' }}>{group.name}</h4>
                          <ul style={{ listStyle: 'none', padding: 0, margin: 0, display: 'flex', flexDirection: 'column', gap: '6px' }}>
                            {groupTables.map(t => (
                              <li key={t.name}>
                                <button 
                                  onClick={() => handleTableClick(t.name)}
                                  style={{ 
                                    width: '100%', textAlign: 'left', background: activeTable === t.name ? 'rgba(59, 130, 246, 0.2)' : 'rgba(255,255,255,0.05)', 
                                    border: activeTable === t.name ? '1px solid #3b82f6' : '1px solid rgba(255,255,255,0.1)', color: '#fff', 
                                    padding: '8px 12px', borderRadius: '6px', cursor: 'pointer',
                                    display: 'flex', flexDirection: 'column', gap: '2px'
                                  }}>
                                  <div style={{ display: 'flex', justifyContent: 'space-between', width: '100%' }}>
                                    <span style={{ fontWeight: '500', fontSize: '0.95rem' }}>{t.name}</span>
                                    <span style={{ color: activeTable === t.name ? '#93c5fd' : 'var(--text-secondary)', fontSize: '0.8rem', background: 'rgba(0,0,0,0.2)', padding: '2px 6px', borderRadius: '12px' }}>{t.rows} rows</span>
                                  </div>
                                  <span style={{ fontSize: '0.75rem', color: activeTable === t.name ? '#bfdbfe' : 'var(--text-secondary)' }}>{group.desc[t.name]}</span>
                                </button>
                              </li>
                            ))}
                          </ul>
                      </div>
                  );
              })}
              
              {(() => {
                  const otherTables = tables.filter(t => !TABLE_GROUPS.some(g => g.tables.includes(t.name)));
                  if (otherTables.length === 0) return null;
                  return (
                      <div key="Others">
                          <h4 style={{ fontSize: '0.75rem', textTransform: 'uppercase', color: 'var(--text-secondary)', marginBottom: '8px', fontWeight: 'bold', letterSpacing: '0.05em' }}>Bảng khác</h4>
                          <ul style={{ listStyle: 'none', padding: 0, margin: 0, display: 'flex', flexDirection: 'column', gap: '6px' }}>
                            {otherTables.map(t => (
                              <li key={t.name}>
                                <button 
                                  onClick={() => handleTableClick(t.name)}
                                  style={{ 
                                    width: '100%', textAlign: 'left', background: activeTable === t.name ? 'rgba(59, 130, 246, 0.2)' : 'rgba(255,255,255,0.05)', 
                                    border: activeTable === t.name ? '1px solid #3b82f6' : '1px solid rgba(255,255,255,0.1)', color: '#fff', 
                                    padding: '8px 12px', borderRadius: '6px', cursor: 'pointer',
                                    display: 'flex', justifyContent: 'space-between', alignItems: 'center'
                                  }}>
                                  <span style={{ fontWeight: '500', fontSize: '0.95rem' }}>{t.name}</span>
                                  <span style={{ color: activeTable === t.name ? '#93c5fd' : 'var(--text-secondary)', fontSize: '0.8rem', background: 'rgba(0,0,0,0.2)', padding: '2px 6px', borderRadius: '12px' }}>{t.rows} rows</span>
                                </button>
                              </li>
                            ))}
                          </ul>
                      </div>
                  );
              })()}
            </div>
          )}
          </div>
        </div>

        {/* Right Content */}
        {viewMode === 'visual' ? (
            <div className="glass-panel" style={{ padding: '16px', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
                {!activeTable ? (
                    <div style={{ color: 'var(--text-secondary)', textAlign: 'center', marginTop: '40px' }}>Select a table from the sidebar to view data.</div>
                ) : (
                    <>
                        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '16px', alignItems: 'center' }}>
                            <h3 style={{ fontSize: '1.2rem', color: '#3b82f6' }}>{activeTable}</h3>
                            <span style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>Read only</span>
                        </div>
                        {loadingData ? <p>Loading data...</p> : (
                            <div style={{ overflow: 'auto', flex: 1, border: '1px solid rgba(255,255,255,0.1)', borderRadius: '6px' }}>
                                <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.9rem' }}>
                                    <thead style={{ position: 'sticky', top: 0, background: '#252525', zIndex: 10 }}>
                                        <tr>
                                            {tableData.columns.map(col => <th key={col} style={{ padding: '10px 12px', borderBottom: '1px solid rgba(255,255,255,0.1)' }}>{col}</th>)}
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {tableData.data.map((row, idx) => (
                                            <tr key={idx} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                                                {tableData.columns.map(col => (
                                                    <td key={col} style={{ padding: '8px 12px' }}>
                                                        {String(row[col] ?? 'NULL')}
                                                    </td>
                                                ))}
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        )}
                    </>
                )}
            </div>
        ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <div className="glass-panel" style={{ padding: '16px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '12px' }}>
                <div>
                    <h3 style={{ fontSize: '1rem' }}>Read-only Query</h3>
                    <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', marginTop: '4px' }}>Only one SELECT statement against approved tables. Maximum 500 rows.</p>
                </div>
                <button 
                    onClick={handleExecute}
                    disabled={executing}
                    style={{ 
                    background: '#3b82f6', color: '#fff', border: 'none', 
                    padding: '6px 16px', borderRadius: '6px', cursor: executing ? 'not-allowed' : 'pointer',
                    opacity: executing ? 0.7 : 1, fontWeight: '500'
                    }}>
                    {executing ? 'Executing...' : '▶ Run Query'}
                </button>
                </div>
                <textarea 
                value={query}
                onChange={e => setQuery(e.target.value)}
                style={{ 
                    width: '100%', height: '120px', background: '#1e1e1e', 
                    border: '1px solid rgba(255,255,255,0.1)', color: '#10b981', 
                    fontFamily: 'monospace', borderRadius: '6px', padding: '12px',
                    resize: 'vertical', fontSize: '1rem'
                }}
                spellCheck="false"
                />
            </div>

            <div className="glass-panel" style={{ padding: '16px', flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
                <h3 style={{ fontSize: '1rem', marginBottom: '12px' }}>Result</h3>
                
                {queryError && (
                <div style={{ padding: '12px', background: 'rgba(239, 68, 68, 0.1)', border: '1px solid #ef4444', color: '#ef4444', borderRadius: '6px', fontFamily: 'monospace' }}>
                    {queryError}
                </div>
                )}

                {!queryError && !queryResult && (
                <div style={{ color: 'var(--text-secondary)', textAlign: 'center', marginTop: '40px' }}>
                    Enter a query and run to see results
                </div>
                )}

                {queryResult && queryResult.columns && (
                <div style={{ overflow: 'auto', flex: 1, border: '1px solid rgba(255,255,255,0.1)', borderRadius: '6px' }}>
                    <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.9rem' }}>
                    <thead style={{ position: 'sticky', top: 0, background: '#252525', zIndex: 10 }}>
                        <tr>
                        {queryResult.columns.map((col, idx) => (
                            <th key={idx} style={{ padding: '10px 12px', borderBottom: '1px solid rgba(255,255,255,0.1)', whiteSpace: 'nowrap' }}>
                            {col}
                            </th>
                        ))}
                        </tr>
                    </thead>
                    <tbody>
                        {queryResult.data.length === 0 ? (
                        <tr>
                            <td colSpan={queryResult.columns.length} style={{ padding: '16px', textAlign: 'center', color: 'var(--text-secondary)' }}>
                            No rows returned.
                            </td>
                        </tr>
                        ) : (
                        queryResult.data.map((row, r_idx) => (
                            <tr key={r_idx} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                            {queryResult.columns.map((col, c_idx) => {
                                let val = row[col];
                                if (val === null) val = <span style={{ color: 'var(--text-secondary)', fontStyle: 'italic' }}>NULL</span>;
                                else if (typeof val === 'object') val = JSON.stringify(val);
                                else val = String(val);
                                
                                return (
                                <td key={c_idx} style={{ padding: '8px 12px', maxWidth: '300px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                                    {val}
                                </td>
                                );
                            })}
                            </tr>
                        ))
                        )}
                    </tbody>
                    </table>
                </div>
                )}
            </div>
            </div>
        )}
      </div>

    </div>
  );
}
