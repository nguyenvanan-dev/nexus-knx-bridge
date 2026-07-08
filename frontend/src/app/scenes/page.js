'use client';
import { useState, useEffect } from 'react';

export default function ScenesPage() {
  const [scenes, setScenes] = useState({});
  const [devices, setDevices] = useState({});
  const [loading, setLoading] = useState(true);
  
  // Wizard state
  const [showWizard, setShowWizard] = useState(false);
  const [wizardMode, setWizardMode] = useState('create'); 
  const [currentScene, setCurrentScene] = useState({
    id: '', name: '', description: '', actions: []
  });
  
  // Versions state
  const [versions, setVersions] = useState([]);
  const [showVersions, setShowVersions] = useState(false);
  
  // Dry Run state
  const [dryRunLog, setDryRunLog] = useState([]);
  const [showDryRun, setShowDryRun] = useState(false);

  const fetchScenes = async () => {
    try {
      const res = await fetch('/api/scenes');
      const data = await res.json();
      setScenes(data);
    } catch (e) {
      console.error(e);
    }
  };

  const fetchDevices = async () => {
    try {
      const res = await fetch('/api/devices');
      const data = await res.json();
      setDevices(data);
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    Promise.all([fetchScenes(), fetchDevices()]).finally(() => setLoading(false));
  }, []);

  const handleAction = async (action, sceneId, payload = null) => {
    if (action === 'delete' && !confirm(`Are you sure you want to delete scene ${sceneId}?`)) return;
    
    try {
      let method = 'POST';
      let url = '/api/scenes';
      let reqBody = payload;
      
      if (action === 'update') {
        method = 'PUT';
        url = `/api/scenes/${sceneId}`;
      } else if (action === 'delete') {
        method = 'DELETE';
        url = `/api/scenes/${sceneId}`;
        reqBody = null;
      } else if (action === 'activate') {
        method = 'POST';
        url = '/api/actions';
        reqBody = { action: 'activate_scene', device: sceneId };
      }

      const options = {
        method,
        headers: { 'Content-Type': 'application/json' }
      };
      if (reqBody) options.body = JSON.stringify(reqBody);

      const res = await fetch(url, options);
      if (res.ok) {
        if (action !== 'activate') fetchScenes();
        setShowWizard(false);
      } else {
        const err = await res.json();
        alert('Error: ' + JSON.stringify(err));
      }
    } catch (e) {
      alert('Error performing action');
    }
  };

  // --- Wizard Logic ---

  const openAddWizard = () => {
    setWizardMode('create');
    setCurrentScene({
      id: '', name: '', description: '', 
      actions: [{ device: '', action: 'on', value: '', delay_seconds: 0, enabled: true, comment: '', retry_count: 0, timeout_seconds: 30, condition_json: '' }]
    });
    setVersions([]);
    setShowWizard(true);
  };

  const openEditWizard = async (key, scene) => {
    setWizardMode('update');
    setCurrentScene({
      id: key,
      name: scene.name || '',
      description: scene.description || '',
      actions: scene.actions?.map(a => ({
          ...a, 
          enabled: a.enabled !== false,
          comment: a.comment || '',
          retry_count: a.retry_count || 0,
          timeout_seconds: a.timeout_seconds || 30,
          condition_json: a.condition_json || ''
      })) || []
    });
    
    // Fetch versions
    try {
        const res = await fetch(`/api/scenes/${key}/versions`);
        if (res.ok) {
            setVersions(await res.json());
        }
    } catch (e) { console.error(e); }
    
    setShowWizard(true);
  };

  const duplicateScene = (key, scene) => {
    setWizardMode('create');
    setCurrentScene({
      id: `${key}_copy`,
      name: `${scene.name} (Copy)`,
      description: scene.description || '',
      actions: scene.actions || []
    });
    setVersions([]);
    setShowWizard(true);
  };

  const saveWizard = () => {
    if (!currentScene.id || !currentScene.name) {
      alert('Scene ID and Name are required');
      return;
    }
    const cleanActions = currentScene.actions.map(a => ({
      device: a.device,
      action: a.action,
      value: a.value || null,
      delay_seconds: parseFloat(a.delay_seconds) || 0.0,
      condition_json: a.condition_json || null,
      retry_count: parseInt(a.retry_count) || 0,
      timeout_seconds: parseFloat(a.timeout_seconds) || 30.0,
      comment: a.comment || null,
      enabled: a.enabled !== false
    }));

    const payload = {
      name: currentScene.name,
      description: currentScene.description,
      actions: cleanActions
    };
    handleAction(wizardMode, currentScene.id, payload);
  };

  const restoreVersion = (ver) => {
      if(!confirm("Restore this version? Current unsaved changes will be lost.")) return;
      setCurrentScene(prev => ({
          ...prev,
          actions: ver.actions.map(a => ({
              ...a, 
              enabled: a.enabled !== false,
              comment: a.comment || '',
              retry_count: a.retry_count || 0,
              timeout_seconds: a.timeout_seconds || 30,
              condition_json: a.condition_json || ''
          }))
      }));
      setShowVersions(false);
  };

  const runDryRun = async () => {
      setShowDryRun(true);
      let logs = [];
      let totalTime = 0;
      setDryRunLog([{ time: 0, msg: `Starting Dry Run for ${currentScene.name}...` }]);
      
      for (let i = 0; i < currentScene.actions.length; i++) {
          const act = currentScene.actions[i];
          if (!act.enabled) {
              logs.push({ time: totalTime, msg: `[Step ${i+1}] Skipped (Disabled)` });
              setDryRunLog([...logs]);
              continue;
          }
          if (act.condition_json) {
              logs.push({ time: totalTime, msg: `[Step ${i+1}] Checking condition: ${act.condition_json} -> Simulated TRUE` });
          }
          logs.push({ time: totalTime, msg: `[Step ${i+1}] Execute: [${act.device}] -> ${act.action} ${act.value ? '('+act.value+')' : ''}` });
          setDryRunLog([...logs]);
          
          if (act.delay_seconds > 0) {
              logs.push({ time: totalTime, msg: `[Step ${i+1}] Waiting ${act.delay_seconds}s...` });
              setDryRunLog([...logs]);
              await new Promise(r => setTimeout(r, Math.min(act.delay_seconds * 100, 1000))); // simulate delay faster
              totalTime += parseFloat(act.delay_seconds);
          }
      }
      logs.push({ time: totalTime, msg: `Dry Run completed in ~${totalTime.toFixed(1)}s estimated time.` });
      setDryRunLog([...logs]);
  };

  // --- Helpers ---
  const addAction = () => setCurrentScene(prev => ({ ...prev, actions: [...prev.actions, { device: '', action: 'on', value: '', delay_seconds: 0, enabled: true }] }));
  const removeAction = (index) => setCurrentScene(prev => { const a = [...prev.actions]; a.splice(index, 1); return { ...prev, actions: a }; });
  const updateAction = (index, field, value) => setCurrentScene(prev => { const a = [...prev.actions]; a[index][field] = value; return { ...prev, actions: a }; });
  const moveAction = (index, dir) => setCurrentScene(prev => {
    if (dir === -1 && index === 0) return prev;
    if (dir === 1 && index === prev.actions.length - 1) return prev;
    const a = [...prev.actions];
    const temp = a[index]; a[index] = a[index + dir]; a[index + dir] = temp;
    return { ...prev, actions: a };
  });

  const estimatedTime = currentScene.actions.filter(a => a.enabled !== false).reduce((sum, a) => sum + (parseFloat(a.delay_seconds) || 0), 0);

  return (
    <>
      <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
        <div>
          <h2 style={{ fontSize: '1.5rem', fontWeight: '600' }}>Scene Management</h2>
          <p style={{ color: 'var(--text-secondary)', marginTop: '4px' }}>Quản lý {Object.keys(scenes).length} kịch bản tự động</p>
        </div>
        <div>
          <button className="nav-item active" style={{ background: '#10b981', color: '#fff', border: 'none', padding: '8px 16px', borderRadius: '8px', cursor: 'pointer' }} onClick={openAddWizard}>
            + Add Scene Wizard
          </button>
        </div>
      </header>

      {loading ? (
        <div style={{ textAlign: 'center', color: 'var(--text-secondary)' }}>Loading scenes...</div>
      ) : (
        <div className="glass-panel" style={{ padding: '20px' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.1)' }}>
                <th style={{ padding: '12px' }}>Scene ID</th>
                <th style={{ padding: '12px' }}>Name</th>
                <th style={{ padding: '12px' }}>Description</th>
                <th style={{ padding: '12px' }}>Actions Count</th>
                <th style={{ padding: '12px' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(scenes).map(([key, scene]) => (
                <tr key={key} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                  <td style={{ padding: '12px', fontWeight: '500' }}>{key}</td>
                  <td style={{ padding: '12px' }}>{scene.name}</td>
                  <td style={{ padding: '12px', fontSize: '0.9rem', color: 'var(--text-secondary)' }}>
                    {scene.description || 'N/A'}
                  </td>
                  <td style={{ padding: '12px' }}>
                    <span style={{ padding: '4px 8px', background: 'rgba(59, 130, 246, 0.2)', color: '#3b82f6', borderRadius: '12px', fontSize: '0.8rem', fontWeight: '600' }}>
                      {scene.actions?.length || 0} steps
                    </span>
                  </td>
                  <td style={{ padding: '12px', display: 'flex', gap: '8px' }}>
                    <button style={{ background: 'transparent', border: '1px solid rgba(255,255,255,0.2)', color: '#fff', borderRadius: '4px', padding: '4px 8px', cursor: 'pointer' }} onClick={() => handleAction('activate', key)}>▶ Preview</button>
                    <button style={{ background: 'transparent', border: '1px solid rgba(255,255,255,0.2)', color: '#fff', borderRadius: '4px', padding: '4px 8px', cursor: 'pointer' }} onClick={() => openEditWizard(key, scene)}>Edit</button>
                    <button style={{ background: 'transparent', border: '1px solid rgba(255,255,255,0.2)', color: '#fff', borderRadius: '4px', padding: '4px 8px', cursor: 'pointer' }} onClick={() => duplicateScene(key, scene)}>Duplicate</button>
                    <button style={{ background: 'transparent', border: '1px solid #ef4444', color: '#ef4444', borderRadius: '4px', padding: '4px 8px', cursor: 'pointer' }} onClick={() => handleAction('delete', key)}>Delete</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {showWizard && (
        <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: 'rgba(0,0,0,0.85)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000, padding: '20px' }}>
          <div className="glass-panel" style={{ padding: '24px', width: '1000px', maxWidth: '100%', maxHeight: '90vh', overflowY: 'auto', position: 'relative' }}>
            
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid rgba(255,255,255,0.1)', paddingBottom: '16px', marginBottom: '16px' }}>
                <h3 style={{ fontSize: '1.4rem', fontWeight: 'bold' }}>
                {wizardMode === 'create' ? '✨ Create New Scene' : '✏️ Edit Scene'}
                </h3>
                <div style={{ display: 'flex', gap: '12px' }}>
                    {wizardMode === 'update' && versions.length > 0 && (
                        <button onClick={() => setShowVersions(!showVersions)} style={{ background: 'rgba(255,255,255,0.1)', color: '#fff', border: 'none', padding: '6px 12px', borderRadius: '6px', cursor: 'pointer' }}>
                            🕒 History ({versions.length})
                        </button>
                    )}
                    <button onClick={runDryRun} style={{ background: '#3b82f6', color: '#fff', border: 'none', padding: '6px 12px', borderRadius: '6px', cursor: 'pointer' }}>
                        ▶️ Dry Run
                    </button>
                </div>
            </div>
            
            {showVersions && (
                <div style={{ background: 'rgba(0,0,0,0.4)', borderRadius: '8px', padding: '12px', marginBottom: '16px', border: '1px solid rgba(255,255,255,0.1)' }}>
                    <h4 style={{ marginBottom: '8px', fontWeight: 'bold' }}>Version History</h4>
                    <ul style={{ listStyle: 'none', padding: 0, margin: 0, maxHeight: '150px', overflowY: 'auto' }}>
                        {versions.map((v, i) => (
                            <li key={v.id} style={{ display: 'flex', justifyContent: 'space-between', padding: '8px', borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                                <span>Version {versions.length - i} ({new Date(v.updated_at * 1000).toLocaleString()}) - {v.actions.length} actions</span>
                                <button onClick={() => restoreVersion(v)} style={{ background: '#f59e0b', color: '#fff', border: 'none', padding: '2px 8px', borderRadius: '4px', cursor: 'pointer', fontSize: '0.8rem' }}>Restore</button>
                            </li>
                        ))}
                    </ul>
                </div>
            )}

            {showDryRun && (
                <div style={{ background: '#0f172a', borderRadius: '8px', padding: '12px', marginBottom: '16px', border: '1px solid #3b82f6' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                        <h4 style={{ fontWeight: 'bold', color: '#60a5fa' }}>Dry Run Output</h4>
                        <button onClick={() => setShowDryRun(false)} style={{ color: '#94a3b8', background: 'transparent', border: 'none', cursor: 'pointer' }}>Close</button>
                    </div>
                    <pre style={{ margin: 0, fontSize: '0.85rem', color: '#a5b4fc', whiteSpace: 'pre-wrap', maxHeight: '200px', overflowY: 'auto' }}>
                        {dryRunLog.map((l, i) => (
                            <div key={i}><span style={{ color: '#475569' }}>[{l.time.toFixed(1)}s]</span> {l.msg}</div>
                        ))}
                    </pre>
                </div>
            )}
            
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: '16px', marginBottom: '16px' }}>
                <input 
                  placeholder="Scene ID (e.g. relax_mode)" 
                  value={currentScene.id} 
                  onChange={e => setCurrentScene({...currentScene, id: e.target.value})}
                  style={{ padding: '10px', background: 'rgba(0,0,0,0.2)', border: '1px solid rgba(255,255,255,0.1)', color: '#fff', borderRadius: '6px' }}
                  disabled={wizardMode === 'update'}
                />
                <input 
                  placeholder="Display Name (e.g. Relax Mode)" 
                  value={currentScene.name} 
                  onChange={e => setCurrentScene({...currentScene, name: e.target.value})}
                  style={{ padding: '10px', background: 'rgba(0,0,0,0.2)', border: '1px solid rgba(255,255,255,0.1)', color: '#fff', borderRadius: '6px' }}
                />
            </div>
            
            <textarea 
              placeholder="Description" 
              value={currentScene.description} 
              onChange={e => setCurrentScene({...currentScene, description: e.target.value})}
              style={{ width: '100%', padding: '10px', background: 'rgba(0,0,0,0.2)', border: '1px solid rgba(255,255,255,0.1)', color: '#fff', borderRadius: '6px', minHeight: '60px', marginBottom: '24px' }}
            />

            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px', background: 'rgba(255,255,255,0.02)', padding: '12px', borderRadius: '8px' }}>
                <div>
                    <h4 style={{ fontSize: '1.2rem', fontWeight: 'bold' }}>Actions Sequence</h4>
                    <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', margin: 0 }}>Estimated Runtime: <strong style={{ color: '#facc15' }}>{estimatedTime.toFixed(1)}s</strong></p>
                </div>
                <button onClick={addAction} style={{ background: '#10b981', color: '#fff', border: 'none', padding: '8px 16px', borderRadius: '6px', cursor: 'pointer', fontWeight: 'bold' }}>+ Add Step</button>
            </div>
            
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', marginBottom: '24px' }}>
                {currentScene.actions.map((act, idx) => (
                    <div key={idx} style={{ position: 'relative', background: act.enabled ? 'rgba(255,255,255,0.05)' : 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.1)', padding: '16px', borderRadius: '12px', opacity: act.enabled ? 1 : 0.6 }}>
                        
                        {/* Step Header */}
                        <div style={{ display: 'flex', gap: '12px', alignItems: 'center', marginBottom: '12px' }}>
                            <div style={{ width: '28px', height: '28px', borderRadius: '14px', background: 'rgba(255,255,255,0.1)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 'bold', color: '#cbd5e1' }}>{idx + 1}</div>
                            
                            <div style={{ display: 'flex', gap: '4px' }}>
                                <button onClick={() => moveAction(idx, -1)} disabled={idx === 0} style={{ background: 'transparent', border: 'none', color: idx === 0 ? 'transparent' : '#94a3b8', cursor: 'pointer' }}>▲</button>
                                <button onClick={() => moveAction(idx, 1)} disabled={idx === currentScene.actions.length - 1} style={{ background: 'transparent', border: 'none', color: idx === currentScene.actions.length - 1 ? 'transparent' : '#94a3b8', cursor: 'pointer' }}>▼</button>
                            </div>

                            <input 
                                type="text"
                                placeholder="Add comment (e.g. Turn on living room lights)"
                                value={act.comment || ''}
                                onChange={(e) => updateAction(idx, 'comment', e.target.value)}
                                style={{ flex: 1, background: 'transparent', border: 'none', color: '#94a3b8', fontStyle: 'italic', outline: 'none' }}
                            />

                            <label style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.85rem', cursor: 'pointer', color: '#cbd5e1' }}>
                                <input type="checkbox" checked={act.enabled} onChange={(e) => updateAction(idx, 'enabled', e.target.checked)} />
                                Enabled
                            </label>

                            <button onClick={() => removeAction(idx)} style={{ background: 'transparent', border: 'none', color: '#ef4444', cursor: 'pointer', fontSize: '1.2rem', marginLeft: '8px' }}>×</button>
                        </div>

                        {/* Step Body */}
                        <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr 1fr auto', gap: '12px' }}>
                            <select value={act.device} onChange={(e) => updateAction(idx, 'device', e.target.value)} style={{ padding: '10px', borderRadius: '6px', background: '#1e293b', border: '1px solid #334155', color: '#fff' }}>
                                <option value="">— Select Target Device —</option>
                                <option value="system">💻 System Event / Notify</option>
                                {Object.entries(devices).map(([dId, d]) => (
                                    <option key={dId} value={dId}>{d.name} ({dId})</option>
                                ))}
                            </select>

                            <select value={act.action} onChange={(e) => updateAction(idx, 'action', e.target.value)} style={{ padding: '10px', borderRadius: '6px', background: '#1e293b', border: '1px solid #334155', color: '#fff' }}>
                                <option value="on">Turn ON</option>
                                <option value="off">Turn OFF</option>
                                <option value="set">Set Value</option>
                                <option value="toggle">Toggle</option>
                                <option value="notify">Notify</option>
                            </select>

                            <input type="text" placeholder="Value" value={act.value || ''} onChange={(e) => updateAction(idx, 'value', e.target.value)} style={{ padding: '10px', borderRadius: '6px', background: '#1e293b', border: '1px solid #334155', color: '#fff' }} />
                            
                            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', background: '#1e293b', border: '1px solid #334155', borderRadius: '6px', padding: '0 12px' }}>
                                <span title="Delay after execution" style={{ color: '#94a3b8' }}>⏱</span>
                                <input type="number" min="0" step="0.1" value={act.delay_seconds} onChange={(e) => updateAction(idx, 'delay_seconds', e.target.value)} style={{ width: '60px', padding: '10px 0', background: 'transparent', border: 'none', color: '#facc15', textAlign: 'right', outline: 'none' }} />
                                <span style={{ color: '#94a3b8', fontSize: '0.8rem' }}>s</span>
                            </div>
                        </div>

                        {/* Step Advanced (Condition & Retry) */}
                        <div style={{ marginTop: '12px', display: 'grid', gridTemplateColumns: '2fr 1fr 1fr', gap: '12px' }}>
                            <div>
                                <label style={{ fontSize: '0.75rem', color: '#64748b', display: 'block', marginBottom: '4px' }}>Condition (JSON) - Optional</label>
                                <input type="text" placeholder='{"type":"device_state", "device_id":"sensor1", "state":"ON"}' value={act.condition_json || ''} onChange={(e) => updateAction(idx, 'condition_json', e.target.value)} style={{ width: '100%', padding: '8px', borderRadius: '6px', background: 'rgba(0,0,0,0.3)', border: '1px dashed #334155', color: '#a7f3d0', fontSize: '0.8rem', fontFamily: 'monospace' }} />
                            </div>
                            <div>
                                <label style={{ fontSize: '0.75rem', color: '#64748b', display: 'block', marginBottom: '4px' }}>Retry Count</label>
                                <input type="number" min="0" value={act.retry_count || 0} onChange={(e) => updateAction(idx, 'retry_count', e.target.value)} style={{ width: '100%', padding: '8px', borderRadius: '6px', background: 'rgba(0,0,0,0.3)', border: '1px dashed #334155', color: '#fff', fontSize: '0.85rem' }} />
                            </div>
                            <div>
                                <label style={{ fontSize: '0.75rem', color: '#64748b', display: 'block', marginBottom: '4px' }}>Timeout (s)</label>
                                <input type="number" min="1" value={act.timeout_seconds || 30} onChange={(e) => updateAction(idx, 'timeout_seconds', e.target.value)} style={{ width: '100%', padding: '8px', borderRadius: '6px', background: 'rgba(0,0,0,0.3)', border: '1px dashed #334155', color: '#fff', fontSize: '0.85rem' }} />
                            </div>
                        </div>
                    </div>
                ))}
                {currentScene.actions.length === 0 && (
                    <div style={{ textAlign: 'center', color: '#64748b', padding: '40px', border: '2px dashed rgba(255,255,255,0.1)', borderRadius: '12px' }}>
                        No actions added yet. Click "+ Add Step" to begin building your scene.
                    </div>
                )}
            </div>

            <div style={{ position: 'sticky', bottom: '-24px', background: 'rgba(15, 23, 42, 0.95)', backdropFilter: 'blur(10px)', padding: '16px 0', borderTop: '1px solid rgba(255,255,255,0.1)', display: 'flex', justifyContent: 'flex-end', gap: '12px', zIndex: 10 }}>
              <button onClick={() => setShowWizard(false)} style={{ background: 'transparent', border: '1px solid rgba(255,255,255,0.2)', color: '#fff', borderRadius: '8px', padding: '10px 24px', cursor: 'pointer', fontWeight: 'bold' }}>Cancel</button>
              <button onClick={saveWizard} style={{ background: '#10b981', border: 'none', color: '#fff', borderRadius: '8px', padding: '10px 24px', cursor: 'pointer', fontWeight: 'bold' }}>💾 Save Scene</button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
