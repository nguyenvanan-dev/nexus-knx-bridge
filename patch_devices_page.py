import re

with open("frontend/src/app/devices/page.js", "r") as f:
    code = f.read()

import_logic_old = """  const importDevices = async (e) => {
      const file = e.target.files[0];
      if (!file) return;
      const reader = new FileReader();
      reader.onload = async (event) => {
          try {
              const payload = JSON.parse(event.target.result);
              const res = await fetch('/api/devices/import', {
                  method: 'POST',
                  headers: { 'Content-Type': 'application/json' },
                  body: JSON.stringify(payload)
              });
              if (res.ok) {
                  alert("Import successful! Reloading...");
                  fetchDevices();
              } else {
                  throw new Error(await res.text());
              }
          } catch (err) {
              alert("Import failed: " + err.message);
          }
      };
      reader.readAsText(file);
  };"""

import_logic_new = """  const [importReview, setImportReview] = useState(null);

  const importDevices = async (e) => {
      const file = e.target.files[0];
      if (!file) return;
      const reader = new FileReader();
      reader.onload = async (event) => {
          try {
              const text = event.target.result;
              let parsedDevices = [];
              
              if (file.name.endsWith('.csv')) {
                  const lines = text.split('\\n');
                  const headers = lines[0].split(',').map(h => h.trim().toLowerCase());
                  
                  if (!headers.includes('device_id')) {
                      throw new Error("CSV must have a 'device_id' column");
                  }
                  
                  for (let i = 1; i < lines.length; i++) {
                      if (!lines[i].trim()) continue;
                      const cols = lines[i].split(',').map(c => c.trim());
                      let dev = {};
                      headers.forEach((h, idx) => {
                          dev[h] = cols[idx];
                      });
                      parsedDevices.push(dev);
                  }
              } else {
                  // JSON format
                  const payload = JSON.parse(text);
                  // Convert dict to array if necessary
                  if (!Array.isArray(payload)) {
                      parsedDevices = Object.keys(payload).map(k => ({ device_id: k, ...payload[k] }));
                  } else {
                      parsedDevices = payload;
                  }
              }
              
              // Validate and check conflicts
              const conflicts = [];
              parsedDevices.forEach(d => {
                  if (devices[d.device_id]) {
                      conflicts.push(`Device ID '${d.device_id}' already exists.`);
                  }
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
  };"""

code = code.replace(import_logic_old, import_logic_new)

# Add Import Review UI Modal
import_review_ui = """      {/* IMPORT REVIEW MODAL */}
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
                         <button onClick={() => confirmImport('merge')} disabled={isSaving} style={{ background: '#3b82f6', border: 'none', color: '#fff', borderRadius: '6px', padding: '10px 16px', cursor: 'pointer' }}>Import (Skip Existing)</button>
                         <button onClick={() => confirmImport('overwrite')} disabled={isSaving} style={{ background: '#10b981', border: 'none', color: '#fff', borderRadius: '6px', padding: '10px 16px', cursor: 'pointer' }}>Import (Overwrite Existing)</button>
                     </div>
                 </div>
             </div>
          </div>
      )}"""

# Insert the UI before {/* WIZARD MODAL */}
code = code.replace("{/* WIZARD MODAL */}", import_review_ui + "\n\n      {/* WIZARD MODAL */}")

# Update input accept to allow .csv
code = code.replace('accept=".json"', 'accept=".json,.csv"')

with open("frontend/src/app/devices/page.js", "w") as f:
    f.write(code)
