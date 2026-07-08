'use client';
import { useState, useEffect } from 'react';

export default function DatabasePage() {
  const [tables, setTables] = useState([]);
  const [loadingTables, setLoadingTables] = useState(true);
  const [viewMode, setViewMode] = useState('visual'); // 'visual' or 'sql'
  
  const [activeTable, setActiveTable] = useState('');
  const [tableData, setTableData] = useState({ columns: [], data: [] });
  const [loadingData, setLoadingData] = useState(false);
  const [editRowIdx, setEditRowIdx] = useState(-1);
  const [editFormData, setEditFormData] = useState({});
  const [showAddModal, setShowAddModal] = useState(false);
  
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
        setQuery(`SELECT * FROM ${tableName} LIMIT 50;`);
        setTimeout(handleExecute, 100);
    }
  };

  const createSnapshot = async () => {
      try {
          const res = await fetch('/api/database/snapshot', { method: 'POST' });
          if (!res.ok) throw new Error("Failed to create snapshot");
          return true;
      } catch (e) {
          alert("Safety Check Failed: Could not create snapshot. " + e.message);
          return false;
      }
  };

  const executeWriteQuery = async (sql) => {
      try {
          const res = await fetch('/api/database/query', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ query: sql })
          });
          const data = await res.json();
          if (!res.ok) throw new Error(data.detail || data.error || "Unknown error");
          return true;
      } catch (e) {
          alert("Query Error: " + e.message);
          return false;
      }
  };

  const handleSaveEdit = async () => {
      if (!await createSnapshot()) return;
      
      const oldRow = tableData.data[editRowIdx];
      let setClauses = [];
      for (const key of tableData.columns) {
          if (editFormData[key] !== oldRow[key]) {
              const val = editFormData[key];
              setClauses.push(`${key} = ${val === null || val === '' ? 'NULL' : `'${String(val).replace(/'/g, "''")}'`}`);
          }
      }
      if (setClauses.length === 0) {
          setEditRowIdx(-1);
          return;
      }

      // Try to use ID if exists, otherwise match all old values
      let whereClauses = [];
      if ('id' in oldRow) {
          whereClauses.push(`id = '${oldRow['id']}'`);
      } else {
          for (const key of tableData.columns) {
              const val = oldRow[key];
              if (val === null) whereClauses.push(`${key} IS NULL`);
              else whereClauses.push(`${key} = '${String(val).replace(/'/g, "''")}'`);
          }
      }

      const sql = `UPDATE ${activeTable} SET ${setClauses.join(', ')} WHERE ${whereClauses.join(' AND ')};`;
      if (await executeWriteQuery(sql)) {
          setEditRowIdx(-1);
          loadTableData(activeTable);
      }
  };

  const handleSaveAdd = async (e) => {
      e.preventDefault();
      if (!await createSnapshot()) return;

      const keys = [];
      const vals = [];
      for (const key of tableData.columns) {
          if (editFormData[key] !== undefined && editFormData[key] !== '') {
              keys.push(key);
              vals.push(`'${String(editFormData[key]).replace(/'/g, "''")}'`);
          }
      }

      const sql = `INSERT INTO ${activeTable} (${keys.join(', ')}) VALUES (${vals.join(', ')});`;
      if (await executeWriteQuery(sql)) {
          setShowAddModal(false);
          setEditFormData({});
          loadTableData(activeTable);
          fetchTables();
      }
  };

  const handleDelete = async (row) => {
      if (!confirm("Are you sure you want to delete this row?")) return;
      if (!await createSnapshot()) return;

      let whereClauses = [];
      if ('id' in row) {
          whereClauses.push(`id = '${row['id']}'`);
      } else {
          for (const key of tableData.columns) {
              const val = row[key];
              if (val === null) whereClauses.push(`${key} IS NULL`);
              else whereClauses.push(`${key} = '${String(val).replace(/'/g, "''")}'`);
          }
      }

      const sql = `DELETE FROM ${activeTable} WHERE ${whereClauses.join(' AND ')};`;
      if (await executeWriteQuery(sql)) {
          loadTableData(activeTable);
          fetchTables();
      }
  };

  const handleExecute = async () => {
    if (!query.trim()) return;
    setExecuting(true);
    setQueryError(null);
    setQueryResult(null);
    try {
      const res = await fetch('/api/database/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: query.trim() })
      });
      const data = await res.json();
      if (!res.ok) setQueryError(data.detail || data.error || 'Unknown error');
      else {
        setQueryResult(data);
        if (!query.trim().toUpperCase().startsWith('SELECT') && !query.trim().toUpperCase().startsWith('PRAGMA')) fetchTables();
      }
    } catch (e) {
      setQueryError(e.message);
    } finally {
      setExecuting(false);
    }
  };

  return (
    <>
      <header style={{ marginBottom: '24px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
            <h2 style={{ fontSize: '1.5rem', fontWeight: '600' }}>Database Manager</h2>
            <p style={{ color: 'var(--text-secondary)', marginTop: '4px' }}>Quản trị SQLite (smarthome.db) an toàn (Auto-backup)</p>
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
                Raw SQL
            </button>
        </div>
      </header>

      <div style={{ display: 'grid', gridTemplateColumns: '250px 1fr', gap: '24px', height: 'calc(100vh - 120px)' }}>
        {/* Left Sidebar - Tables */}
        <div className="glass-panel" style={{ padding: '16px', overflowY: 'auto' }}>
          <h3 style={{ fontSize: '1rem', marginBottom: '16px', color: '#10b981' }}>Tables</h3>
          {loadingTables ? (
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>Loading...</p>
          ) : tables.length === 0 ? (
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>No tables found.</p>
          ) : (
            <ul style={{ listStyle: 'none', padding: 0, margin: 0, display: 'flex', flexDirection: 'column', gap: '8px' }}>
              {tables.map(t => (
                <li key={t.name}>
                  <button 
                    onClick={() => handleTableClick(t.name)}
                    style={{ 
                      width: '100%', textAlign: 'left', background: activeTable === t.name ? 'rgba(59, 130, 246, 0.2)' : 'rgba(255,255,255,0.05)', 
                      border: activeTable === t.name ? '1px solid #3b82f6' : '1px solid rgba(255,255,255,0.1)', color: '#fff', 
                      padding: '8px 12px', borderRadius: '6px', cursor: 'pointer',
                      display: 'flex', justifyContent: 'space-between'
                    }}>
                    <span>{t.name}</span>
                    <span style={{ color: 'var(--text-secondary)', fontSize: '0.8rem' }}>{t.rows}</span>
                  </button>
                </li>
              ))}
            </ul>
          )}
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
                            <button onClick={() => { setEditFormData({}); setShowAddModal(true); }} style={{ background: '#10b981', color: 'white', border: 'none', padding: '6px 16px', borderRadius: '4px', cursor: 'pointer', fontWeight: 'bold' }}>+ Add Row</button>
                        </div>
                        {loadingData ? <p>Loading data...</p> : (
                            <div style={{ overflow: 'auto', flex: 1, border: '1px solid rgba(255,255,255,0.1)', borderRadius: '6px' }}>
                                <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.9rem' }}>
                                    <thead style={{ position: 'sticky', top: 0, background: '#252525', zIndex: 10 }}>
                                        <tr>
                                            {tableData.columns.map(col => <th key={col} style={{ padding: '10px 12px', borderBottom: '1px solid rgba(255,255,255,0.1)' }}>{col}</th>)}
                                            <th style={{ padding: '10px 12px', borderBottom: '1px solid rgba(255,255,255,0.1)', textAlign: 'right' }}>Actions</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {tableData.data.map((row, idx) => (
                                            <tr key={idx} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                                                {tableData.columns.map(col => (
                                                    <td key={col} style={{ padding: '8px 12px' }}>
                                                        {editRowIdx === idx ? (
                                                            <input type="text" value={editFormData[col] || ''} onChange={e => setEditFormData({...editFormData, [col]: e.target.value})} style={{ width: '100%', background: 'transparent', color: 'white', border: '1px solid #3b82f6', padding: '4px', borderRadius: '4px' }} />
                                                        ) : (
                                                            String(row[col] ?? 'NULL')
                                                        )}
                                                    </td>
                                                ))}
                                                <td style={{ padding: '8px 12px', textAlign: 'right', whiteSpace: 'nowrap' }}>
                                                    {editRowIdx === idx ? (
                                                        <>
                                                            <button onClick={handleSaveEdit} style={{ background: '#10b981', color: 'white', border: 'none', padding: '4px 8px', borderRadius: '4px', cursor: 'pointer', marginRight: '8px' }}>Save</button>
                                                            <button onClick={() => setEditRowIdx(-1)} style={{ background: '#ef4444', color: 'white', border: 'none', padding: '4px 8px', borderRadius: '4px', cursor: 'pointer' }}>Cancel</button>
                                                        </>
                                                    ) : (
                                                        <>
                                                            <button onClick={() => { setEditFormData({...row}); setEditRowIdx(idx); }} style={{ background: 'transparent', color: '#3b82f6', border: '1px solid #3b82f6', padding: '4px 8px', borderRadius: '4px', cursor: 'pointer', marginRight: '8px' }}>Edit</button>
                                                            <button onClick={() => handleDelete(row)} style={{ background: 'transparent', color: '#ef4444', border: '1px solid #ef4444', padding: '4px 8px', borderRadius: '4px', cursor: 'pointer' }}>Delete</button>
                                                        </>
                                                    )}
                                                </td>
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
                <h3 style={{ fontSize: '1rem' }}>Query Executor</h3>
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

                {queryResult && queryResult.affected_rows !== undefined && (
                <div style={{ color: '#10b981', fontFamily: 'monospace' }}>
                    {queryResult.message} ({queryResult.affected_rows} rows affected)
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

      {/* Add Modal */}
      {showAddModal && (
          <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: 'rgba(0,0,0,0.7)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 100 }}>
              <div className="glass-panel" style={{ padding: '24px', width: '500px', maxWidth: '90%' }}>
                  <h3 style={{ fontSize: '1.2rem', marginBottom: '16px' }}>Add Row to {activeTable}</h3>
                  <form onSubmit={handleSaveAdd} style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                      {tableData.columns.map(col => (
                          <div key={col}>
                              <label style={{ display: 'block', marginBottom: '4px', fontSize: '0.9rem', color: 'var(--text-secondary)' }}>{col}</label>
                              <input 
                                type="text" 
                                value={editFormData[col] || ''} 
                                onChange={e => setEditFormData({...editFormData, [col]: e.target.value})} 
                                style={{ width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid rgba(255,255,255,0.1)', background: 'rgba(0,0,0,0.2)', color: 'white' }} 
                              />
                          </div>
                      ))}
                      <div style={{ display: 'flex', gap: '12px', marginTop: '16px' }}>
                          <button type="submit" style={{ flex: 1, background: '#10b981', color: 'white', border: 'none', padding: '10px', borderRadius: '6px', cursor: 'pointer', fontWeight: 'bold' }}>Save</button>
                          <button type="button" onClick={() => setShowAddModal(false)} style={{ flex: 1, background: 'rgba(255,255,255,0.1)', color: 'white', border: 'none', padding: '10px', borderRadius: '6px', cursor: 'pointer' }}>Cancel</button>
                      </div>
                  </form>
              </div>
          </div>
      )}
    </>
  );
}
