'use client';
import { useState, useEffect } from 'react';

export default function SettingsPage() {
  const [logs, setLogs] = useState('');
  const [logService, setLogService] = useState('knx-bridge');
  const [loadingLogs, setLoadingLogs] = useState(false);
  const [restarting, setRestarting] = useState(false);
  const [currentUser, setCurrentUser] = useState(null);
  
  // User Management state
  const [users, setUsers] = useState([]);
  const [newUser, setNewUser] = useState({ username: '', password: '', role: 'Member' });
  const [loadingUsers, setLoadingUsers] = useState(false);
  
  // Config Manager state
  const [configs, setConfigs] = useState([]);
  const [loadingConfigs, setLoadingConfigs] = useState(false);
  const [savingConfig, setSavingConfig] = useState(false);
  
  // Restore state
  const [restoring, setRestoring] = useState(false);
  
  const fetchLogs = async () => {
    setLoadingLogs(true);
    try {
      const res = await fetch(`/api/system/logs?service=${logService}&lines=50`);
      const data = await res.json();
      if (data.logs) {
        setLogs(data.logs);
      } else {
        setLogs('No logs found or error fetching logs.');
      }
    } catch (e) {
      setLogs(`Error fetching logs: ${e.message}`);
    } finally {
      setLoadingLogs(false);
    }
  };

  const fetchUser = async () => {
    try {
      const res = await fetch('/api/auth/me');
      if (res.ok) {
        const data = await res.json();
        setCurrentUser(data);
        if (data.role === 'Admin') {
            fetchUsers();
            fetchConfigs();
        }
      }
    } catch (e) {
      console.error('Error fetching user', e);
    }
  };

  const fetchUsers = async () => {
      setLoadingUsers(true);
      try {
          const res = await fetch('/api/users');
          if (res.ok) {
              const data = await res.json();
              setUsers(data);
          }
      } catch (e) {
          console.error("Failed to fetch users", e);
      } finally {
          setLoadingUsers(false);
      }
  };

  const handleCreateUser = async (e) => {
      e.preventDefault();
      if (!newUser.username || !newUser.password) return alert("Please fill username and password");
      try {
          const res = await fetch('/api/users', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify(newUser)
          });
          const data = await res.json();
          if (res.ok) {
              alert("User created successfully");
              setNewUser({ username: '', password: '', role: 'Member' });
              fetchUsers();
          } else {
              alert(data.error || data.detail || "Failed to create user");
          }
      } catch (e) {
          alert("Error creating user: " + e.message);
      }
  };

  const handleDeleteUser = async (id) => {
      if (!confirm("Are you sure you want to delete this user?")) return;
      try {
          const res = await fetch(`/api/users?id=${id}`, { method: 'DELETE' });
          if (res.ok) {
              fetchUsers();
          } else {
              const data = await res.json();
              alert(data.error || data.detail || "Failed to delete user");
          }
      } catch (e) {
          alert("Error deleting user: " + e.message);
      }
  };

  const fetchConfigs = async () => {
      setLoadingConfigs(true);
      try {
          const res = await fetch('/api/system/config');
          if (res.ok) {
              const data = await res.json();
              if (data.configs) {
                  setConfigs(data.configs);
              }
          }
      } catch (e) {
          console.error("Failed to fetch configs", e);
      } finally {
          setLoadingConfigs(false);
      }
  };

  const handleUpdateConfig = async (e) => {
      e.preventDefault();
      setSavingConfig(true);
      const payload = {};
      configs.forEach(c => {
          payload[c.key] = c.value;
      });
      try {
          const res = await fetch('/api/system/config', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify(payload)
          });
          const data = await res.json();
          if (res.ok) {
              alert(data.message || "Configuration updated");
          } else {
              alert(data.error || data.detail || "Failed to update configuration");
          }
      } catch (e) {
          alert("Error saving config: " + e.message);
      } finally {
          setSavingConfig(false);
      }
  };

  const handleConfigChange = (index, value) => {
      const newConfigs = [...configs];
      newConfigs[index].value = value;
      setConfigs(newConfigs);
  };

  const handleRestore = async (e) => {
      const file = e.target.files[0];
      if (!file) return;
      if (!file.name.endsWith('.zip')) return alert('Please upload a .zip file');
      if (!confirm('This will overwrite the current database and configuration. The system will restart. Proceed?')) return;
      
      setRestoring(true);
      const formData = new FormData();
      formData.append('file', file);
      
      try {
          const res = await fetch('/api/system/restore', {
              method: 'POST',
              body: formData
          });
          const data = await res.json();
          if (res.ok) {
              alert(data.message || 'System restored. Restarting...');
              setTimeout(() => window.location.reload(), 3000);
          } else {
              alert(data.error || data.detail || 'Failed to restore system');
          }
      } catch (e) {
          alert('Error restoring system: ' + e.message);
      } finally {
          setRestoring(false);
          e.target.value = ''; // Reset file input
      }
  };

  useEffect(() => {
    fetchLogs();
    fetchUser();
  }, [logService]);

  const handleRestart = async (serviceName) => {
    if (!confirm(`Are you sure you want to restart ${serviceName}?`)) return;
    setRestarting(true);
    try {
      const res = await fetch('/api/system/restart', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ service: serviceName })
      });
      const data = await res.json();
      alert(data.message || 'Restart command sent');
      if (serviceName === logService) {
        setTimeout(fetchLogs, 2000);
      }
    } catch (e) {
      alert(`Error restarting: ${e.message}`);
    } finally {
      setRestarting(false);
    }
  };

  const handleDownloadBackup = () => {
    // The backend endpoint serves the file directly without auth for simplicity here
    window.open('http://127.0.0.1:5055/api/system/backup', '_blank');
  };

  return (
    <>
      <header style={{ marginBottom: '24px' }}>
        <h2 style={{ fontSize: '1.5rem', fontWeight: '600' }}>System Settings & Administration</h2>
        <p style={{ color: 'var(--text-secondary)', marginTop: '4px' }}>Quản lý tiến trình, Backup dữ liệu và xem Logs</p>
      </header>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px', marginBottom: '24px' }}>
        
        {/* Backup & Restore Panel */}
        <div className="glass-panel" style={{ padding: '20px' }}>
          <h3 style={{ fontSize: '1.1rem', marginBottom: '16px', color: '#10b981' }}>Backup & Restore</h3>
          <p style={{ color: 'var(--text-secondary)', marginBottom: '16px', fontSize: '0.9rem' }}>
            Tải về bản sao lưu an toàn bao gồm database (smarthome.db), cấu hình thiết bị và các biến môi trường (.env).
          </p>
          <div style={{ display: 'flex', gap: '12px' }}>
            <button 
              onClick={handleDownloadBackup}
              style={{ background: '#3b82f6', color: '#fff', border: 'none', padding: '8px 16px', borderRadius: '6px', cursor: 'pointer', fontWeight: '500' }}>
              📥 Download System Backup (.zip)
            </button>
            <label style={{ background: '#ef4444', color: '#fff', border: 'none', padding: '8px 16px', borderRadius: '6px', cursor: 'pointer', fontWeight: '500', opacity: restoring ? 0.5 : 1 }}>
              {restoring ? '⏳ Restoring...' : '📤 Upload Restore (.zip)'}
              <input type="file" accept=".zip" onChange={handleRestore} style={{ display: 'none' }} disabled={restoring} />
            </label>
          </div>
          <div style={{ marginTop: '16px', borderTop: '1px solid rgba(255,255,255,0.1)', paddingTop: '16px' }}>
             <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>* Cảnh báo: Restore sẽ ghi đè database hiện tại.</p>
          </div>
        </div>

        {/* Service Management Panel */}
        <div className="glass-panel" style={{ padding: '20px' }}>
          <h3 style={{ fontSize: '1.1rem', marginBottom: '16px', color: '#ef4444' }}>Service Management</h3>
          <p style={{ color: 'var(--text-secondary)', marginBottom: '16px', fontSize: '0.9rem' }}>
            Khởi động lại các tiến trình ngầm (systemctl services) khi gặp sự cố mà không cần dùng SSH.
          </p>
          
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: 'rgba(255,255,255,0.05)', padding: '12px', borderRadius: '6px' }}>
              <div>
                <strong>knx-bridge</strong>
                <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>FastAPI Backend Service (Port 5055)</div>
              </div>
              <button 
                disabled={restarting}
                onClick={() => handleRestart('knx-bridge')}
                style={{ background: '#ef4444', color: '#fff', border: 'none', padding: '6px 16px', borderRadius: '4px', cursor: 'pointer' }}>
                Restart
              </button>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: 'rgba(255,255,255,0.05)', padding: '12px', borderRadius: '6px' }}>
              <div>
                <strong>knx-frontend</strong>
                <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Next.js Dashboard Service (Port 3000)</div>
              </div>
              <button 
                disabled={restarting}
                onClick={() => handleRestart('knx-frontend')}
                style={{ background: '#ef4444', color: '#fff', border: 'none', padding: '6px 16px', borderRadius: '4px', cursor: 'pointer' }}>
                Restart
              </button>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: 'rgba(255,255,255,0.05)', padding: '12px', borderRadius: '6px' }}>
              <div>
                <strong>ngrok / localtunnel</strong>
                <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Public Tunnel Service</div>
              </div>
              <button 
                disabled={restarting}
                onClick={() => handleRestart('ngrok')}
                style={{ background: '#ef4444', color: '#fff', border: 'none', padding: '6px 16px', borderRadius: '4px', cursor: 'pointer' }}>
                Restart
              </button>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: 'rgba(255,255,255,0.05)', padding: '12px', borderRadius: '6px' }}>
              <div>
                <strong>openclaw</strong>
                <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>AI Agent Background Worker</div>
              </div>
              <button 
                disabled={restarting}
                onClick={() => handleRestart('openclaw')}
                style={{ background: '#ef4444', color: '#fff', border: 'none', padding: '6px 16px', borderRadius: '4px', cursor: 'pointer' }}>
                Restart
              </button>
            </div>
          </div>
        </div>
      </div>

      {currentUser?.role === 'Admin' && (
        <div className="glass-panel" style={{ padding: '20px', marginBottom: '24px' }}>
          <h3 style={{ fontSize: '1.1rem', marginBottom: '16px', color: '#a855f7' }}>User Management</h3>
          <p style={{ color: 'var(--text-secondary)', marginBottom: '16px', fontSize: '0.9rem' }}>
            Quản lý tài khoản truy cập hệ thống.
          </p>
          <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '24px' }}>
              <div style={{ background: 'rgba(255,255,255,0.05)', padding: '16px', borderRadius: '8px' }}>
                  <h4 style={{ marginBottom: '12px', fontSize: '1rem' }}>User List</h4>
                  {loadingUsers ? <p>Loading users...</p> : (
                      <table style={{ width: '100%', textAlign: 'left', borderCollapse: 'collapse' }}>
                          <thead>
                              <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.1)' }}>
                                  <th style={{ padding: '8px 0', color: 'var(--text-secondary)', fontWeight: 'normal' }}>Username</th>
                                  <th style={{ padding: '8px 0', color: 'var(--text-secondary)', fontWeight: 'normal' }}>Role</th>
                                  <th style={{ padding: '8px 0', color: 'var(--text-secondary)', fontWeight: 'normal' }}>Action</th>
                              </tr>
                          </thead>
                          <tbody>
                              {users.map(u => (
                                  <tr key={u.id} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                                      <td style={{ padding: '12px 0' }}>{u.username}</td>
                                      <td style={{ padding: '12px 0' }}>
                                          <span style={{ 
                                              background: u.role === 'Admin' ? 'rgba(168, 85, 247, 0.2)' : 'rgba(59, 130, 246, 0.2)',
                                              color: u.role === 'Admin' ? '#c084fc' : '#60a5fa',
                                              padding: '2px 8px', borderRadius: '12px', fontSize: '0.8rem'
                                          }}>
                                              {u.role}
                                          </span>
                                      </td>
                                      <td style={{ padding: '12px 0' }}>
                                          {currentUser.id !== u.id && (
                                              <button onClick={() => handleDeleteUser(u.id)} style={{ background: 'transparent', color: '#ef4444', border: '1px solid #ef4444', padding: '4px 8px', borderRadius: '4px', cursor: 'pointer', fontSize: '0.8rem' }}>Delete</button>
                                          )}
                                      </td>
                                  </tr>
                              ))}
                          </tbody>
                      </table>
                  )}
              </div>
              <div style={{ background: 'rgba(255,255,255,0.05)', padding: '16px', borderRadius: '8px' }}>
                  <h4 style={{ marginBottom: '12px', fontSize: '1rem' }}>Create User</h4>
                  <form onSubmit={handleCreateUser} style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                      <input type="text" placeholder="Username" value={newUser.username} onChange={e => setNewUser({...newUser, username: e.target.value})} style={{ padding: '10px', borderRadius: '6px', border: '1px solid rgba(255,255,255,0.1)', background: 'rgba(0,0,0,0.2)', color: 'white' }} required />
                      <input type="password" placeholder="Password" value={newUser.password} onChange={e => setNewUser({...newUser, password: e.target.value})} style={{ padding: '10px', borderRadius: '6px', border: '1px solid rgba(255,255,255,0.1)', background: 'rgba(0,0,0,0.2)', color: 'white' }} required />
                      <select value={newUser.role} onChange={e => setNewUser({...newUser, role: e.target.value})} style={{ padding: '10px', borderRadius: '6px', border: '1px solid rgba(255,255,255,0.1)', background: 'rgba(0,0,0,0.2)', color: 'white' }}>
                          <option value="Member">Member</option>
                          <option value="Admin">Admin</option>
                      </select>
                      <button type="submit" style={{ background: '#a855f7', color: 'white', border: 'none', padding: '10px', borderRadius: '6px', cursor: 'pointer', fontWeight: 'bold' }}>Add User</button>
                  </form>
              </div>
          </div>
        </div>
      )}

      {/* Config Manager Panel */}
      {currentUser?.role === 'Admin' && (
        <div className="glass-panel" style={{ padding: '20px', marginBottom: '24px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
            <div>
              <h3 style={{ fontSize: '1.1rem', color: '#10b981' }}>System Configuration (.env)</h3>
              <p style={{ color: 'var(--text-secondary)', marginTop: '4px', fontSize: '0.9rem' }}>
                Cập nhật các biến môi trường trực tiếp. Lưu ý: một số thay đổi yêu cầu khởi động lại Service để áp dụng.
              </p>
            </div>
            <button 
              onClick={handleUpdateConfig}
              disabled={savingConfig}
              style={{ background: '#10b981', color: 'white', border: 'none', padding: '8px 16px', borderRadius: '6px', cursor: 'pointer', fontWeight: 'bold' }}>
              {savingConfig ? 'Saving...' : 'Save Configuration'}
            </button>
          </div>
          
          <div style={{ background: 'rgba(255,255,255,0.05)', padding: '16px', borderRadius: '8px' }}>
              {loadingConfigs ? <p>Loading configuration...</p> : (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                      {configs.map((c, idx) => (
                          <div key={c.key} style={{ display: 'grid', gridTemplateColumns: '1fr 3fr', alignItems: 'center', gap: '16px', borderBottom: '1px solid rgba(255,255,255,0.05)', paddingBottom: '12px' }}>
                              <label style={{ color: '#e2e8f0', fontFamily: 'monospace', fontSize: '0.9rem' }}>{c.key}</label>
                              <input 
                                type="text" 
                                value={c.value} 
                                onChange={(e) => handleConfigChange(idx, e.target.value)}
                                style={{ width: '100%', padding: '8px 12px', borderRadius: '6px', border: '1px solid rgba(255,255,255,0.1)', background: 'rgba(0,0,0,0.2)', color: 'white', fontFamily: 'monospace' }} 
                              />
                          </div>
                      ))}
                      {configs.length === 0 && <p style={{ color: 'var(--text-secondary)' }}>No configuration variables found.</p>}
                  </div>
              )}
          </div>
        </div>
      )}

      {/* Live Logs Panel */}
      <div className="glass-panel" style={{ padding: '20px', display: 'flex', flexDirection: 'column', height: '400px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
          <h3 style={{ fontSize: '1.1rem', color: '#f59e0b' }}>System Logs (journalctl)</h3>
          
          <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
            <select 
              value={logService} 
              onChange={e => setLogService(e.target.value)}
              style={{ background: '#2d2d2d', color: '#fff', border: '1px solid rgba(255,255,255,0.2)', padding: '4px 8px', borderRadius: '4px' }}>
              <option value="knx-bridge">knx-bridge (Backend)</option>
              <option value="knx-frontend">knx-frontend (UI)</option>
              <option value="ngrok">ngrok (Tunnel)</option>
              <option value="openclaw">openclaw (AI Agent)</option>
            </select>
            
            <button 
              onClick={fetchLogs}
              disabled={loadingLogs}
              style={{ background: 'rgba(255,255,255,0.1)', color: '#fff', border: 'none', padding: '4px 12px', borderRadius: '4px', cursor: 'pointer' }}>
              {loadingLogs ? 'Loading...' : 'Refresh'}
            </button>
          </div>
        </div>

        <textarea 
          readOnly
          value={logs}
          style={{ 
            flex: 1, background: '#1e1e1e', color: '#d4d4d4', border: '1px solid rgba(255,255,255,0.1)', 
            borderRadius: '6px', padding: '12px', fontFamily: 'monospace', fontSize: '0.85rem', resize: 'none'
          }}
        />
      </div>
    </>
  );
}
