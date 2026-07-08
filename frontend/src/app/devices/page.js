'use client';
import { useState, useEffect } from 'react';

export default function DevicesPage() {
  const [devices, setDevices] = useState({});
  const [loading, setLoading] = useState(true);
  
  // Wizard State
  const [showWizard, setShowWizard] = useState(false);
  const [wizardStep, setWizardStep] = useState(1); // 1: Info, 2: GA, 3: Review, 4: Test
  const [wizardMode, setWizardMode] = useState('add'); // 'add', 'edit'
  
  const [currentDevice, setCurrentDevice] = useState({
    device_id: '', type: 'light', onoff_ga: '', status_ga: '', brightness_ga: '', brightness_status_ga: ''
  });
  
  const [gaWarnings, setGaWarnings] = useState([]);
  const [isSaving, setIsSaving] = useState(false);

  const fetchDevices = async () => {
    try {
      const res = await fetch('/api/devices');
      const data = await res.json();
      setDevices(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDevices();
  }, []);

  const handleAction = async (action, payload) => {
    if (action === 'delete' && !confirm(`Are you sure you want to delete ${payload.device_id}?`)) return;
    
    try {
      const res = await fetch('/api/devices', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action, payload: { ...payload, confirmed: true } })
      });
      if (res.ok) {
        if (action === 'delete') {
          const newDevices = { ...devices };
          delete newDevices[payload.device_id];
          setDevices(newDevices);
        } else {
          fetchDevices();
        }
      } else {
        const err = await res.json();
        alert('Error: ' + JSON.stringify(err));
      }
    } catch (e) {
      alert('Error performing action');
    }
  };

  // ---------------- WIZARD LOGIC ----------------

  const openAddWizard = () => {
    setWizardMode('add');
    setCurrentDevice({ device_id: '', type: 'light', onoff_ga: '', status_ga: '', brightness_ga: '', brightness_status_ga: '' });
    setWizardStep(1);
    setGaWarnings([]);
    setShowWizard(true);
  };

  const openEditWizard = (key, dev) => {
    setWizardMode('update');
    setCurrentDevice({
      device_id: key,
      type: dev.type || 'light',
      onoff_ga: dev.onoff_ga || '',
      status_ga: dev.status_ga || '',
      brightness_ga: dev.brightness_ga || '',
      brightness_status_ga: dev.brightness_status_ga || ''
    });
    setWizardStep(1);
    setGaWarnings([]);
    setShowWizard(true);
  };

  const clear_group_addresses = (device) => {
    const copy = { ...device };
    for (const key of Object.keys(copy)) {
      if (key.endsWith('_ga')) {
        copy[key] = '';
      }
    }
    return copy;
  };

  const duplicateDevice = (key, dev) => {
    setWizardMode('add');
    const newDevice = clear_group_addresses(dev);
    newDevice.device_id = `${key}_copy`;
    setCurrentDevice(newDevice);
    setWizardStep(1);
    setGaWarnings([]);
    setShowWizard(true);
  };

  const validateGAs = () => {
    const warnings = [];
    const checkGa = (gaField, label) => {
        const ga = currentDevice[gaField];
        if (!ga) return;
        // Check format x/y/z
        if (!/^\d+\/\d+\/\d+$/.test(ga)) {
            warnings.push(`${label} (${ga}) does not look like a valid KNX format (e.g., 1/1/1).`);
        }
        // Check duplicates in other devices
        for (const [key, dev] of Object.entries(devices)) {
            if (key === currentDevice.device_id) continue; // skip self
            if (dev.onoff_ga === ga || dev.status_ga === ga || dev.brightness_ga === ga || dev.brightness_status_ga === ga) {
                warnings.push(`Warning: ${ga} is already used by device '${key}'.`);
            }
        }
    };
    
    checkGa('onoff_ga', 'ON/OFF GA');
    checkGa('status_ga', 'Status GA');
    checkGa('brightness_ga', 'Brightness GA');
    checkGa('brightness_status_ga', 'Brightness Status GA');
    
    setGaWarnings(warnings);
    return warnings.length === 0;
  };

  const nextStep = () => {
      if (wizardStep === 1) {
          if (!currentDevice.device_id.trim()) return alert("Device ID is required");
          setWizardStep(2);
      } else if (wizardStep === 2) {
          validateGAs();
          setWizardStep(3);
      }
  };

  const saveAndDeploy = async () => {
      setIsSaving(true);
      try {
          // Save Device
          const res = await fetch('/api/devices', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ action: wizardMode, payload: { ...currentDevice, confirmed: true } })
          });
          
          if (!res.ok) throw new Error(JSON.stringify(await res.json()));
          
          await fetchDevices();
          
          // Reload Backend KNX Cache to apply immediately
          await fetch('/api/system/restart', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ service: 'knx-bridge' })
          });
          
          // Go to Test Step
          setWizardStep(4);
      } catch (e) {
          alert('Error saving device: ' + e.message);
      } finally {
          setIsSaving(false);
      }
  };

  const testDeviceControl = async (action) => {
      try {
          const res = await fetch('/api/devices/control', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ device_id: currentDevice.device_id, action })
          });
          if (!res.ok) throw new Error("Control failed");
          alert("Command sent successfully!");
      } catch (e) {
          alert("Error: " + e.message);
      }
  };

  const exportDevices = async () => {
    try {
        const res = await fetch('/api/devices/export');
        const data = await res.json();
        const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'devices_export.json';
        a.click();
        URL.revokeObjectURL(url);
    } catch (e) {
        alert("Export failed: " + e.message);
    }
  };

  const [importReview, setImportReview] = useState(null);

  const importDevices = async (e) => {
      const file = e.target.files[0];
      if (!file) return;
      const reader = new FileReader();
      reader.onload = async (event) => {
          try {
              const text = event.target.result;
              let parsedDevices = [];
              const expectedHeaders = ['device_id', 'name', 'room', 'type', 'onoff_ga', 'status_ga', 'brightness_ga', 'brightness_status_ga'];
              
              if (file.name.endsWith('.csv')) {
                  const lines = text.split('\n');
                  const headers = lines[0].split(',').map(h => h.trim().toLowerCase());
                  
                  if (!headers.includes('device_id')) {
                      throw new Error("CSV must have a 'device_id' column");
                  }
                  
                  for (let i = 1; i < lines.length; i++) {
                      if (!lines[i].trim()) continue;
                      // Simple split by comma, assuming no complex quotes in CSV for this simple format
                      const cols = lines[i].split(',').map(c => c.trim());
                      let dev = {};
                      headers.forEach((h, idx) => {
                          if (expectedHeaders.includes(h) && cols[idx]) {
                              dev[h] = cols[idx];
                          }
                      });
                      if (dev.device_id) {
                          parsedDevices.push(dev);
                      }
                  }
              } else {
                  // JSON format fallback
                  const payload = JSON.parse(text);
                  if (!Array.isArray(payload)) {
                      parsedDevices = Object.keys(payload).map(k => ({ device_id: k, ...payload[k] }));
                  } else {
                      parsedDevices = payload;
                  }
              }
              
              // Validate and check conflicts
              const conflicts = [];
              const allUsedGAs = new Set();
              Object.values(devices).forEach(d => {
                  if (d.onoff_ga) allUsedGAs.add(d.onoff_ga);
                  if (d.status_ga) allUsedGAs.add(d.status_ga);
                  if (d.brightness_ga) allUsedGAs.add(d.brightness_ga);
                  if (d.brightness_status_ga) allUsedGAs.add(d.brightness_status_ga);
              });

              parsedDevices.forEach(d => {
                  if (devices[d.device_id]) {
                      conflicts.push(`Device ID '${d.device_id}' already exists.`);
                  }
                  const checkGa = (gaField, label) => {
                      const ga = d[gaField];
                      if (!ga) return;
                      if (!/^\d+\/\d+\/\d+$/.test(ga)) {
                          conflicts.push(`Device '${d.device_id}': ${label} (${ga}) has invalid KNX format.`);
                      } else if (allUsedGAs.has(ga)) {
                          conflicts.push(`Device '${d.device_id}': ${label} (${ga}) is already used by an existing device.`);
                      }
                      allUsedGAs.add(ga); // track within import batch as well
                  };
                  checkGa('onoff_ga', 'ON/OFF GA');
                  checkGa('status_ga', 'Status GA');
                  checkGa('brightness_ga', 'Brightness GA');
                  checkGa('brightness_status_ga', 'Brightness Status GA');
              });
              
              setImportReview({ devices: parsedDevices, conflicts });
              
          } catch (err) {
              alert("Import Parse Error: " + err.message);
          }
      };
      reader.readAsText(file);
      e.target.value = null; // reset input
  };
  
  const confirmImport = async (mode) => {
      if (!importReview) return;
      try {
          setIsSaving(true);
          const payload = {
              mode: mode, // 'merge' or 'overwrite'
              devices: importReview.devices
          };
          const res = await fetch('/api/devices/import', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify(payload)
          });
          if (res.ok) {
              alert("Import successful! Reloading...");
              // Reload platform to ensure new devices are in memory
              await fetch('/api/platform/reload', { method: 'POST' });
              await fetchDevices();
              setImportReview(null);
          } else {
              throw new Error(await res.text());
          }
      } catch (err) {
          alert("Import failed: " + err.message);
      } finally {
          setIsSaving(false);
      }
  };

  return (
    <>
      <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
        <div>
          <h2 style={{ fontSize: '1.5rem', fontWeight: '600' }}>Device Management</h2>
          <p style={{ color: 'var(--text-secondary)', marginTop: '4px' }}>Quản lý {Object.keys(devices).length} thiết bị KNX</p>
        </div>
        <div style={{ display: 'flex', gap: '8px' }}>
          <input type="file" id="import-file" style={{ display: 'none' }} accept=".json,.csv" onChange={importDevices} />
          <button style={{ background: 'rgba(255,255,255,0.1)', color: '#fff', border: '1px solid rgba(255,255,255,0.2)', padding: '8px 16px', borderRadius: '8px', cursor: 'pointer' }} onClick={() => document.getElementById('import-file').click()}>
            📥 Import
          </button>
          <button style={{ background: 'rgba(255,255,255,0.1)', color: '#fff', border: '1px solid rgba(255,255,255,0.2)', padding: '8px 16px', borderRadius: '8px', cursor: 'pointer' }} onClick={exportDevices}>
            📤 Export
          </button>
          <button className="nav-item active" style={{ background: '#3b82f6', color: '#fff', border: 'none', padding: '8px 16px', borderRadius: '8px', cursor: 'pointer' }} onClick={openAddWizard}>
            + Add Device Wizard
          </button>
        </div>
      </header>

      {loading ? (
        <div style={{ textAlign: 'center', color: 'var(--text-secondary)' }}>Loading devices...</div>
      ) : (
        <div className="glass-panel" style={{ padding: '20px', overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.1)' }}>
                <th style={{ padding: '12px' }}>Device ID</th>
                <th style={{ padding: '12px' }}>Type</th>
                <th style={{ padding: '12px' }}>Group Addresses</th>
                <th style={{ padding: '12px' }}>Status</th>
                <th style={{ padding: '12px' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(devices).map(([key, dev]) => (
                <tr key={key} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                  <td style={{ padding: '12px', fontWeight: '500' }}>{key}</td>
                  <td style={{ padding: '12px' }}>
                    <span style={{ padding: '4px 8px', background: 'rgba(255,255,255,0.1)', borderRadius: '12px', fontSize: '0.8rem' }}>
                      {dev.type || 'light'}
                    </span>
                  </td>
                  <td style={{ padding: '12px', fontSize: '0.9rem', color: 'var(--text-secondary)' }}>
                    ON/OFF: {dev.onoff_ga || 'N/A'}<br/>
                    Status: {dev.status_ga || 'N/A'}
                  </td>
                  <td style={{ padding: '12px' }}>
                    {dev.disabled ? (
                      <span style={{ color: '#ef4444', fontSize: '0.9rem' }}>Disabled</span>
                    ) : (
                      <span style={{ color: '#10b981', fontSize: '0.9rem' }}>Active</span>
                    )}
                  </td>
                  <td style={{ padding: '12px', display: 'flex', gap: '8px' }}>
                    <a href={`/devices/${key}`} style={{ background: '#3b82f6', border: 'none', color: '#fff', borderRadius: '4px', padding: '4px 8px', cursor: 'pointer', textDecoration: 'none', fontSize: '0.9rem' }}>🔍 Details</a>
                    <button style={{ background: 'transparent', border: '1px solid rgba(255,255,255,0.2)', color: '#fff', borderRadius: '4px', padding: '4px 8px', cursor: 'pointer' }} onClick={() => openEditWizard(key, dev)}>Edit</button>
                    <button style={{ background: 'transparent', border: '1px solid rgba(255,255,255,0.2)', color: '#fff', borderRadius: '4px', padding: '4px 8px', cursor: 'pointer' }} onClick={() => duplicateDevice(key, dev)}>Duplicate</button>
                    <button style={{ background: 'transparent', border: '1px solid #ef4444', color: '#ef4444', borderRadius: '4px', padding: '4px 8px', cursor: 'pointer' }} onClick={() => handleAction('delete', { device_id: key })}>Delete</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

            {/* IMPORT REVIEW MODAL */}
      {importReview && (
          <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: 'rgba(0,0,0,0.85)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }}>
             <div className="glass-panel" style={{ padding: '24px', width: '600px', maxWidth: '90%', maxHeight: '80vh', overflowY: 'auto' }}>
                 <h3 style={{ marginBottom: '16px', color: '#10b981' }}>Review Import ({importReview.devices.length} devices)</h3>
                 
                 {importReview.conflicts.length > 0 && (
                     <div style={{ background: 'rgba(239, 68, 68, 0.1)', border: '1px solid #ef4444', padding: '12px', borderRadius: '6px', marginBottom: '16px' }}>
                         <strong style={{ color: '#ef4444', fontSize: '0.9rem' }}>⚠️ Conflicts Detected:</strong>
                         <ul style={{ margin: '8px 0 0 16px', padding: 0, fontSize: '0.85rem', color: '#fca5a5' }}>
                             {importReview.conflicts.slice(0, 5).map((c, i) => <li key={i}>{c}</li>)}
                             {importReview.conflicts.length > 5 && <li>... and {importReview.conflicts.length - 5} more</li>}
                         </ul>
                     </div>
                 )}
                 
                 <div style={{ maxHeight: '300px', overflowY: 'auto', background: 'rgba(0,0,0,0.3)', padding: '12px', borderRadius: '6px', marginBottom: '16px' }}>
                    <table style={{ width: '100%', fontSize: '0.85rem', textAlign: 'left' }}>
                        <thead>
                            <tr style={{ color: 'var(--text-secondary)' }}>
                                <th>Device ID</th>
                                <th>Type</th>
                                <th>ON/OFF GA</th>
                            </tr>
                        </thead>
                        <tbody>
                            {importReview.devices.map((d, i) => (
                                <tr key={i}>
                                    <td style={{ color: devices[d.device_id] ? '#ef4444' : '#10b981' }}>{d.device_id}</td>
                                    <td>{d.type || 'light'}</td>
                                    <td>{d.onoff_ga}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                 </div>
                 
                 <div style={{ display: 'flex', justifyContent: 'space-between', gap: '12px' }}>
                     <button onClick={() => setImportReview(null)} style={{ background: 'transparent', border: '1px solid rgba(255,255,255,0.2)', color: '#fff', borderRadius: '6px', padding: '10px 16px', cursor: 'pointer' }}>Cancel</button>
                     <div style={{ display: 'flex', gap: '12px' }}>
                         <button onClick={() => confirmImport('skip')} disabled={isSaving} style={{ background: '#64748b', border: 'none', color: '#fff', borderRadius: '6px', padding: '10px 16px', cursor: 'pointer' }}>Skip</button>
                         <button onClick={() => confirmImport('overwrite')} disabled={isSaving} style={{ background: '#ef4444', border: 'none', color: '#fff', borderRadius: '6px', padding: '10px 16px', cursor: 'pointer' }}>Overwrite</button>
                         <button onClick={() => confirmImport('rename')} disabled={isSaving} style={{ background: '#10b981', border: 'none', color: '#fff', borderRadius: '6px', padding: '10px 16px', cursor: 'pointer' }}>Rename</button>
                     </div>
                 </div>
             </div>
          </div>
      )}

      {/* WIZARD MODAL */}
      {showWizard && (
        <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: 'rgba(0,0,0,0.85)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }}>
          <div className="glass-panel" style={{ padding: '0', width: '500px', maxWidth: '90%', display: 'flex', flexDirection: 'column' }}>
            
            {/* Header */}
            <div style={{ padding: '20px 24px', borderBottom: '1px solid rgba(255,255,255,0.1)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <h3 style={{ fontSize: '1.2rem', margin: 0 }}>
                    {wizardMode === 'add' ? '✨ Device Wizard' : '✏️ Edit Device Wizard'}
                </h3>
                {wizardStep !== 4 && (
                    <button onClick={() => setShowWizard(false)} style={{ background: 'transparent', border: 'none', color: '#fff', fontSize: '1.5rem', cursor: 'pointer', lineHeight: 1 }}>&times;</button>
                )}
            </div>

            {/* Stepper */}
            <div style={{ padding: '16px 24px', background: 'rgba(0,0,0,0.2)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                {[1,2,3,4].map(step => (
                    <div key={step} style={{ display: 'flex', alignItems: 'center', gap: '8px', opacity: wizardStep >= step ? 1 : 0.4 }}>
                        <div style={{ width: '24px', height: '24px', borderRadius: '12px', background: wizardStep === step ? '#3b82f6' : (wizardStep > step ? '#10b981' : '#444'), display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '0.8rem', fontWeight: 'bold' }}>
                            {step}
                        </div>
                        <span style={{ fontSize: '0.8rem', display: step === 4 ? 'none' : 'block' }}>&mdash;</span>
                    </div>
                ))}
            </div>

            {/* Body */}
            <div style={{ padding: '24px', minHeight: '250px' }}>
                
                {wizardStep === 1 && (
                    <div className="wizard-step" style={{ animation: 'fadeIn 0.3s' }}>
                        <h4 style={{ marginBottom: '16px', color: '#3b82f6' }}>Step 1: Basic Information</h4>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                            <div>
                                <label style={{ display: 'block', marginBottom: '6px', fontSize: '0.9rem', color: 'var(--text-secondary)' }}>Device ID</label>
                                <input 
                                    placeholder="e.g. living_light_1" 
                                    value={currentDevice.device_id} 
                                    onChange={e => setCurrentDevice({...currentDevice, device_id: e.target.value})}
                                    style={{ width: '100%', padding: '10px', background: 'rgba(0,0,0,0.3)', border: '1px solid rgba(255,255,255,0.2)', color: '#fff', borderRadius: '6px' }}
                                    disabled={wizardMode === 'update'}
                                />
                                {wizardMode === 'update' && <small style={{ color: '#ef4444', marginTop: '4px', display: 'block' }}>Cannot change ID of existing device.</small>}
                            </div>
                            <div>
                                <label style={{ display: 'block', marginBottom: '6px', fontSize: '0.9rem', color: 'var(--text-secondary)' }}>Device Type</label>
                                <select 
                                    value={currentDevice.type}
                                    onChange={e => setCurrentDevice({...currentDevice, type: e.target.value})}
                                    style={{ width: '100%', padding: '10px', background: '#252525', border: '1px solid rgba(255,255,255,0.2)', color: '#fff', borderRadius: '6px' }}>
                                    <option value="light">Light (Switchable)</option>
                                    <option value="dimmer">Dimmer (Light + Brightness)</option>
                                    <option value="switch">Switch / Relay</option>
                                    <option value="blind">Window Blind</option>
                                </select>
                            </div>
                        </div>
                    </div>
                )}

                {wizardStep === 2 && (
                    <div className="wizard-step" style={{ animation: 'fadeIn 0.3s' }}>
                        <h4 style={{ marginBottom: '16px', color: '#3b82f6' }}>Step 2: Group Addresses</h4>
                        <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '16px' }}>Enter the physical KNX Group Addresses (Format: x/y/z).</p>
                        
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                            <div>
                                <label style={{ display: 'block', marginBottom: '4px', fontSize: '0.85rem' }}>ON/OFF Address *</label>
                                <input placeholder="1/1/1" value={currentDevice.onoff_ga} onChange={e => setCurrentDevice({...currentDevice, onoff_ga: e.target.value})} style={{ width: '100%', padding: '8px', background: 'rgba(0,0,0,0.3)', border: '1px solid rgba(255,255,255,0.2)', color: '#fff', borderRadius: '4px' }} />
                            </div>
                            <div>
                                <label style={{ display: 'block', marginBottom: '4px', fontSize: '0.85rem' }}>State/Status Address (Optional)</label>
                                <input placeholder="1/1/2" value={currentDevice.status_ga} onChange={e => setCurrentDevice({...currentDevice, status_ga: e.target.value})} style={{ width: '100%', padding: '8px', background: 'rgba(0,0,0,0.3)', border: '1px solid rgba(255,255,255,0.2)', color: '#fff', borderRadius: '4px' }} />
                            </div>
                            
                            {currentDevice.type === 'dimmer' && (
                                <>
                                    <div>
                                        <label style={{ display: 'block', marginBottom: '4px', fontSize: '0.85rem' }}>Brightness Set Address</label>
                                        <input placeholder="1/1/3" value={currentDevice.brightness_ga} onChange={e => setCurrentDevice({...currentDevice, brightness_ga: e.target.value})} style={{ width: '100%', padding: '8px', background: 'rgba(0,0,0,0.3)', border: '1px solid rgba(255,255,255,0.2)', color: '#fff', borderRadius: '4px' }} />
                                    </div>
                                    <div>
                                        <label style={{ display: 'block', marginBottom: '4px', fontSize: '0.85rem' }}>Brightness Status Address</label>
                                        <input placeholder="1/1/4" value={currentDevice.brightness_status_ga} onChange={e => setCurrentDevice({...currentDevice, brightness_status_ga: e.target.value})} style={{ width: '100%', padding: '8px', background: 'rgba(0,0,0,0.3)', border: '1px solid rgba(255,255,255,0.2)', color: '#fff', borderRadius: '4px' }} />
                                    </div>
                                </>
                            )}
                        </div>
                    </div>
                )}

                {wizardStep === 3 && (
                    <div className="wizard-step" style={{ animation: 'fadeIn 0.3s' }}>
                        <h4 style={{ marginBottom: '16px', color: '#10b981' }}>Step 3: Review & Save</h4>
                        
                        {gaWarnings.length > 0 && (
                            <div style={{ background: 'rgba(239, 68, 68, 0.1)', border: '1px solid #ef4444', padding: '12px', borderRadius: '6px', marginBottom: '16px' }}>
                                <strong style={{ color: '#ef4444', fontSize: '0.9rem' }}>⚠️ Validation Warnings:</strong>
                                <ul style={{ margin: '8px 0 0 16px', padding: 0, fontSize: '0.85rem', color: '#fca5a5' }}>
                                    {gaWarnings.map((w, i) => <li key={i}>{w}</li>)}
                                </ul>
                                <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '8px' }}>You can still proceed if this is intentional.</p>
                            </div>
                        )}

                        <div style={{ background: 'rgba(255,255,255,0.05)', padding: '16px', borderRadius: '8px', fontSize: '0.9rem' }}>
                            <p><strong>Device ID:</strong> {currentDevice.device_id}</p>
                            <p><strong>Type:</strong> {currentDevice.type}</p>
                            <p><strong>ON/OFF GA:</strong> <span style={{ color: '#3b82f6' }}>{currentDevice.onoff_ga}</span></p>
                            <p><strong>Status GA:</strong> <span style={{ color: '#3b82f6' }}>{currentDevice.status_ga || 'None'}</span></p>
                        </div>
                        <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginTop: '16px', textAlign: 'center' }}>
                            Clicking Save will record the device and automatically reload the backend cache.
                        </p>
                    </div>
                )}

                {wizardStep === 4 && (
                    <div className="wizard-step" style={{ animation: 'fadeIn 0.3s', textAlign: 'center' }}>
                        <div style={{ fontSize: '3rem', marginBottom: '16px' }}>🎉</div>
                        <h4 style={{ marginBottom: '8px', color: '#10b981', fontSize: '1.2rem' }}>Device Deployed!</h4>
                        <p style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', marginBottom: '24px' }}>
                            The backend cache has been reloaded. You can now physically test the device below.
                        </p>
                        
                        <div style={{ background: 'rgba(255,255,255,0.05)', padding: '24px', borderRadius: '8px', display: 'flex', justifyContent: 'center', gap: '16px' }}>
                            <button 
                                onClick={() => testDeviceControl('on')}
                                style={{ background: '#10b981', color: '#fff', border: 'none', padding: '12px 32px', borderRadius: '8px', fontSize: '1.1rem', cursor: 'pointer', fontWeight: 'bold' }}>
                                TURN ON
                            </button>
                            <button 
                                onClick={() => testDeviceControl('off')}
                                style={{ background: '#ef4444', color: '#fff', border: 'none', padding: '12px 32px', borderRadius: '8px', fontSize: '1.1rem', cursor: 'pointer', fontWeight: 'bold' }}>
                                TURN OFF
                            </button>
                        </div>
                    </div>
                )}

            </div>

            {/* Footer Buttons */}
            <div style={{ padding: '16px 24px', borderTop: '1px solid rgba(255,255,255,0.1)', display: 'flex', justifyContent: 'space-between', background: 'rgba(0,0,0,0.3)' }}>
                {wizardStep === 4 ? (
                    <button onClick={() => setShowWizard(false)} style={{ width: '100%', background: '#3b82f6', border: 'none', color: '#fff', borderRadius: '6px', padding: '10px 16px', cursor: 'pointer', fontWeight: 'bold' }}>Finish & Close</button>
                ) : (
                    <>
                        {wizardStep > 1 ? (
                            <button onClick={() => setWizardStep(wizardStep - 1)} style={{ background: 'transparent', border: '1px solid rgba(255,255,255,0.2)', color: '#fff', borderRadius: '6px', padding: '8px 24px', cursor: 'pointer' }}>Back</button>
                        ) : <div></div>}

                        {wizardStep === 3 ? (
                            <button onClick={saveAndDeploy} disabled={isSaving} style={{ background: '#10b981', border: 'none', color: '#fff', borderRadius: '6px', padding: '8px 24px', cursor: 'pointer', fontWeight: 'bold', opacity: isSaving ? 0.7 : 1 }}>
                                {isSaving ? 'Deploying...' : 'Save & Deploy'}
                            </button>
                        ) : (
                            <button onClick={nextStep} style={{ background: '#3b82f6', border: 'none', color: '#fff', borderRadius: '6px', padding: '8px 24px', cursor: 'pointer', fontWeight: 'bold' }}>Next</button>
                        )}
                    </>
                )}
            </div>

          </div>
        </div>
      )}
    </>
  );
}
