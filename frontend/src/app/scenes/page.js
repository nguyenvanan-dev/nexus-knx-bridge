'use client';
import { useState, useEffect } from 'react';
import { showDialog, showToast } from '../../utils/ui';

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

  /* eslint-disable react-hooks/set-state-in-effect */
  useEffect(() => {
    Promise.all([fetchScenes(), fetchDevices()]).finally(() => setLoading(false));
  }, []);
  /* eslint-enable react-hooks/set-state-in-effect */

  const handleAction = async (action, sceneId, payload = null) => {
    if (action === 'delete') {
        showDialog('Delete Scene', `Are you sure you want to delete scene ${sceneId}?`, 'danger', async () => {
            await performAction('delete', sceneId, null);
        });
        return;
    }
    await performAction(action, sceneId, payload);
  };

  const performAction = async (action, sceneId, payload) => {
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
        showDialog('Error', JSON.stringify(err), 'danger');
      }
    } catch (e) {
      showDialog('Error', 'Error performing action', 'danger');
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
      showDialog('Validation Error', 'Scene ID and Name are required', 'info');
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
      showDialog('Restore Version', 'Restore this version? Current unsaved changes will be lost.', 'warning', () => {
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
      });
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
    <div className="page-container animate-fade-in">
      <header className="flex justify-between items-center mb-8">
        <div>
          <h2 className="text-2xl font-semibold mb-1 text-[var(--text-primary)]">Scene Management</h2>
          <p className="text-sm text-[var(--text-secondary)]">Quản lý {Object.keys(scenes).length} kịch bản tự động</p>
        </div>
        <div>
          <button className="btn-primary" onClick={openAddWizard}>
            + Add Scene Wizard
          </button>
        </div>
      </header>

      {loading ? (
        <div className="empty-state">
          <div className="skeleton w-32 h-8 mb-4"></div>
          <div>Loading scenes...</div>
        </div>
      ) : Object.keys(scenes).length === 0 ? (
        <div className="empty-state glass-panel">
          <h3 className="text-xl mb-2 text-[var(--text-primary)]">No Scenes Found</h3>
          <p className="text-[var(--text-secondary)]">Create your first automated scene to get started.</p>
        </div>
      ) : (
        <div className="glass-panel overflow-hidden">
          <div className="overflow-x-auto max-h-[60vh] custom-scrollbar">
            <table className="w-full text-left text-sm whitespace-nowrap">
              <thead className="bg-black/20 sticky top-0 z-10">
                <tr>
                  <th className="p-4 font-medium uppercase tracking-wider text-[var(--text-secondary)]">Scene ID</th>
                  <th className="p-4 font-medium uppercase tracking-wider text-[var(--text-secondary)]">Name</th>
                  <th className="p-4 font-medium uppercase tracking-wider text-[var(--text-secondary)]">Description</th>
                  <th className="p-4 font-medium uppercase tracking-wider text-[var(--text-secondary)]">Actions Count</th>
                  <th className="p-4 font-medium uppercase tracking-wider text-[var(--text-secondary)]">Actions</th>
                </tr>
            </thead>
            <tbody className="divide-y divide-[var(--border)]">
              {Object.entries(scenes).map(([key, scene]) => (
                <tr key={key} className="hover:bg-[var(--bg-hover)] transition-colors">
                  <td className="p-4 font-medium text-[var(--text-primary)]">{key}</td>
                  <td className="p-4 text-[var(--text-primary)]">{scene.name}</td>
                  <td className="p-4 text-xs text-[var(--text-secondary)] truncate max-w-xs">
                    {scene.description || 'N/A'}
                  </td>
                  <td className="p-4">
                    <span className="badge badge-online">
                      {scene.actions?.length || 0} steps
                    </span>
                  </td>
                  <td className="p-4 text-right">
                    <div className="relative inline-block group">
                      <button className="btn-secondary px-2 py-1">⋮</button>
                      <div className="absolute right-0 mt-2 w-36 bg-[var(--bg-elevated)] border border-[var(--border)] rounded-lg shadow-xl opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all z-50 flex flex-col py-1 text-left">
                        <button className="px-4 py-2 text-sm hover:bg-[var(--bg-hover)] text-white text-left" onClick={() => handleAction('activate', key)}>▶ Preview</button>
                        <button className="px-4 py-2 text-sm hover:bg-[var(--bg-hover)] text-white text-left" onClick={() => openEditWizard(key, scene)}>✏️ Edit</button>
                        <button className="px-4 py-2 text-sm hover:bg-[var(--bg-hover)] text-white text-left" onClick={() => duplicateScene(key, scene)}>📋 Duplicate</button>
                        <div className="border-t border-[var(--border)] my-1"></div>
                        <button className="px-4 py-2 text-sm hover:bg-[var(--bg-hover)] text-[var(--danger)] text-left" onClick={() => handleAction('delete', key)}>🗑️ Delete</button>
                      </div>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          </div>
        </div>
      )}

      {showWizard && (
        <div className="dialog-overlay">
          <div className="dialog-content" style={{ width: '1200px', maxWidth: '95%', maxHeight: '90vh', padding: '0', display: 'flex', flexDirection: 'column' }}>
            
            <div className="px-6 py-4 border-b border-[var(--border)] flex justify-between items-center">
                <h3 className="text-xl font-semibold text-[var(--accent)]">
                {wizardMode === 'create' ? '✨ Create New Scene' : '✏️ Edit Scene'}
                </h3>
                <div className="flex gap-4">
                    {wizardMode === 'update' && versions.length > 0 && (
                        <button onClick={() => setShowVersions(!showVersions)} className="btn-secondary">
                            🕒 History ({versions.length})
                        </button>
                    )}
                    <button onClick={runDryRun} className="btn-primary">
                        ▶️ Dry Run
                    </button>
                </div>
            </div>
            
            <div className="p-6 overflow-y-auto custom-scrollbar flex-1">
                {showVersions && (
                    <div className="bg-[var(--bg-elevated)] border border-[var(--border)] rounded-xl p-4 mb-6">
                        <h4 className="font-semibold text-white mb-3">Version History</h4>
                        <ul className="max-h-[150px] overflow-y-auto custom-scrollbar space-y-2">
                            {versions.map((v, i) => (
                                <li key={v.id} className="flex justify-between items-center p-2 border-b border-[var(--border)]">
                                    <span className="text-sm text-[var(--text-secondary)]">Version {versions.length - i} ({new Date(v.updated_at * 1000).toLocaleString()}) - {v.actions.length} actions</span>
                                    <button onClick={() => restoreVersion(v)} className="btn-secondary text-xs py-1 px-3">Restore</button>
                                </li>
                            ))}
                        </ul>
                    </div>
                )}

                {showDryRun && (
                    <div className="bg-[var(--bg-hover)] border border-[var(--accent)] rounded-xl p-4 mb-6">
                        <div className="flex justify-between items-center mb-3">
                            <h4 className="font-semibold text-[var(--accent)]">Dry Run Output</h4>
                            <button onClick={() => setShowDryRun(false)} className="text-[var(--text-secondary)] hover:text-white text-sm">Close</button>
                        </div>
                        <pre className="text-xs text-indigo-200 whitespace-pre-wrap max-h-[200px] overflow-y-auto">
                            {dryRunLog.map((l, i) => (
                                <div key={i}><span className="text-slate-500">[{l.time.toFixed(1)}s]</span> {l.msg}</div>
                            ))}
                        </pre>
                    </div>
                )}
                
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
                    <div className="md:col-span-1">
                        <label className="block text-base text-[#a1a1aa] mb-2">Scene ID</label>
                        <input 
                            placeholder="e.g. relax_mode" 
                            value={currentScene.id} 
                            onChange={e => setCurrentScene({...currentScene, id: e.target.value})}
                            className="w-full bg-black/40 border border-white/10 text-white rounded-xl px-5 py-3 text-lg focus:outline-none focus:border-emerald-500 transition-colors"
                            disabled={wizardMode === 'update'}
                        />
                    </div>
                    <div className="md:col-span-2">
                        <label className="block text-base text-[#a1a1aa] mb-2">Display Name</label>
                        <input 
                            placeholder="e.g. Relax Mode" 
                            value={currentScene.name} 
                            onChange={e => setCurrentScene({...currentScene, name: e.target.value})}
                            className="w-full bg-black/40 border border-white/10 text-white rounded-xl px-5 py-3 text-lg focus:outline-none focus:border-emerald-500 transition-colors"
                        />
                    </div>
                </div>
                
                <div className="mb-8">
                    <label className="block text-base text-[#a1a1aa] mb-2">Description</label>
                    <textarea 
                        placeholder="What does this scene do?" 
                        value={currentScene.description} 
                        onChange={e => setCurrentScene({...currentScene, description: e.target.value})}
                        className="w-full bg-black/40 border border-white/10 text-white rounded-xl px-5 py-3 text-lg focus:outline-none focus:border-emerald-500 transition-colors min-h-[100px]"
                    />
                </div>

                <div className="flex justify-between items-center mb-6 bg-white/5 p-6 rounded-2xl border border-white/5">
                    <div>
                        <h4 className="text-xl font-semibold text-white">Actions Sequence</h4>
                        <p className="text-base text-[#a1a1aa] mt-1">Estimated Runtime: <strong className="text-amber-400">{estimatedTime.toFixed(1)}s</strong></p>
                    </div>
                    <button onClick={addAction} className="bg-emerald-600 hover:bg-emerald-500 text-white px-5 py-3 rounded-xl text-base font-medium transition-colors">
                        + Add Step
                    </button>
                </div>
                
                <div className="space-y-6">
                    {currentScene.actions.map((act, idx) => (
                        <div key={idx} className={`relative border border-white/10 p-6 rounded-2xl transition-all ${act.enabled ? 'bg-white/5' : 'bg-black/20 opacity-60'}`}>
                            
                            {/* Step Header */}
                            <div className="flex gap-4 items-center mb-6">
                                <div className="w-8 h-8 rounded-full bg-white/10 flex items-center justify-center font-bold text-slate-300 text-base">
                                    {idx + 1}
                                </div>
                                
                                <div className="flex flex-col gap-0 leading-none">
                                    <button onClick={() => moveAction(idx, -1)} disabled={idx === 0} className={`text-slate-400 hover:text-white ${idx === 0 ? 'opacity-0' : ''}`}>▲</button>
                                    <button onClick={() => moveAction(idx, 1)} disabled={idx === currentScene.actions.length - 1} className={`text-slate-400 hover:text-white ${idx === currentScene.actions.length - 1 ? 'opacity-0' : ''}`}>▼</button>
                                </div>

                                <input 
                                    type="text"
                                    placeholder="Add comment (e.g. Turn on living room lights)"
                                    value={act.comment || ''}
                                    onChange={(e) => updateAction(idx, 'comment', e.target.value)}
                                    className="flex-1 bg-transparent border-none text-slate-400 italic text-base focus:outline-none focus:text-white"
                                />

                                <label className="flex items-center gap-2 text-base text-slate-300 cursor-pointer">
                                    <input type="checkbox" checked={act.enabled} onChange={(e) => updateAction(idx, 'enabled', e.target.checked)} className="rounded w-4 h-4 bg-black/50 border-white/20 text-emerald-500" />
                                    Enabled
                                </label>

                                <button onClick={() => removeAction(idx)} className="text-red-400 hover:text-red-300 text-3xl ml-4">&times;</button>
                            </div>

                            {/* Step Body */}
                            <div className="grid grid-cols-1 md:grid-cols-12 gap-4">
                                <div className="md:col-span-4">
                                    <select value={act.device} onChange={(e) => updateAction(idx, 'device', e.target.value)} className="w-full bg-slate-800 border border-slate-700 text-white rounded-xl px-4 py-3 text-base focus:outline-none focus:border-emerald-500">
                                        <option value="">— Select Target Device —</option>
                                        <option value="system">💻 System Event / Notify</option>
                                        {Object.entries(devices).map(([dId, d]) => (
                                            <option key={dId} value={dId}>{d.name} ({dId})</option>
                                        ))}
                                    </select>
                                </div>

                                <div className="md:col-span-3">
                                    <select value={act.action} onChange={(e) => updateAction(idx, 'action', e.target.value)} className="w-full bg-slate-800 border border-slate-700 text-white rounded-xl px-4 py-3 text-base focus:outline-none focus:border-emerald-500">
                                        <option value="on">Turn ON</option>
                                        <option value="off">Turn OFF</option>
                                        <option value="set">Set Value</option>
                                        <option value="toggle">Toggle</option>
                                        <option value="notify">Notify</option>
                                    </select>
                                </div>

                                <div className="md:col-span-3">
                                    <input type="text" placeholder="Value" value={act.value || ''} onChange={(e) => updateAction(idx, 'value', e.target.value)} className="w-full bg-slate-800 border border-slate-700 text-white rounded-xl px-4 py-3 text-base focus:outline-none focus:border-emerald-500" />
                                </div>
                                
                                <div className="md:col-span-2 flex items-center bg-slate-800 border border-slate-700 rounded-xl px-4">
                                    <span className="text-slate-400 text-sm">⏱</span>
                                    <input type="number" min="0" step="0.1" value={act.delay_seconds} onChange={(e) => updateAction(idx, 'delay_seconds', e.target.value)} className="w-full bg-transparent border-none text-amber-400 text-right focus:outline-none text-base" />
                                    <span className="text-slate-400 text-sm ml-2">s</span>
                                </div>
                            </div>

                            {/* Step Advanced */}
                            <div className="mt-5 grid grid-cols-1 md:grid-cols-4 gap-4">
                                <div className="md:col-span-2">
                                    <label className="text-sm text-slate-500 block mb-2">Condition (JSON) - Optional</label>
                                    <input type="text" placeholder='{"type":"device_state", "device_id":"sensor1", "state":"ON"}' value={act.condition_json || ''} onChange={(e) => updateAction(idx, 'condition_json', e.target.value)} className="w-full bg-black/30 border border-dashed border-slate-700 text-emerald-200 rounded-lg px-3 py-2 text-sm font-mono focus:outline-none focus:border-emerald-500" />
                                </div>
                                <div>
                                    <label className="text-sm text-slate-500 block mb-2">Retry Count</label>
                                    <input type="number" min="0" value={act.retry_count || 0} onChange={(e) => updateAction(idx, 'retry_count', e.target.value)} className="w-full bg-black/30 border border-dashed border-slate-700 text-white rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-emerald-500" />
                                </div>
                                <div>
                                    <label className="text-sm text-slate-500 block mb-2">Timeout (s)</label>
                                    <input type="number" min="1" value={act.timeout_seconds || 30} onChange={(e) => updateAction(idx, 'timeout_seconds', e.target.value)} className="w-full bg-black/30 border border-dashed border-slate-700 text-white rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-emerald-500" />
                                </div>
                            </div>
                        </div>
                    ))}
                    {currentScene.actions.length === 0 && (
                        <div className="text-center text-slate-500 p-10 border-2 border-dashed border-white/10 rounded-xl">
                            No actions added yet. Click {'"'}+ Add Step{'"'} to begin building your scene.
                        </div>
                    )}
                </div>
            </div>

            <div className="px-8 py-6 border-t border-white/10 flex justify-end gap-4 bg-white/5">
              <button onClick={() => setShowWizard(false)} className="px-8 py-3 rounded-xl text-base font-medium border border-white/10 text-[#a1a1aa] hover:text-white hover:bg-white/5 transition-colors">Cancel</button>
              <button onClick={saveWizard} className="px-8 py-3 rounded-xl text-base font-medium bg-emerald-600 hover:bg-emerald-500 text-white transition-colors flex items-center gap-2">💾 Save Scene</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
