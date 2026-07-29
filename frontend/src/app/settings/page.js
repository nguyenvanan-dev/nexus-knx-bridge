'use client';
import { useState, useEffect } from 'react';
import { showDialog, showToast } from '../../utils/ui';

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

  // Tab State
  const [activeTab, setActiveTab] = useState('system'); // 'system', 'users', 'config'

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
        if (String(data.role || '').toLowerCase() === 'admin') {
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
      if (!newUser.username || !newUser.password) {
          showDialog("Validation Error", "Please fill username and password", "warning");
          return;
      }
      try {
          const res = await fetch('/api/users', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify(newUser)
          });
          const data = await res.json();
          if (res.ok) {
              showToast("User created successfully", "success");
              setNewUser({ username: '', password: '', role: 'Member' });
              fetchUsers();
          } else {
              showDialog("Error", data.error || data.detail || "Failed to create user", "danger");
          }
      } catch (e) {
          showDialog("Error", "Error creating user: " + e.message, "danger");
      }
  };

  const handleDeleteUser = async (id) => {
      showDialog("Delete User", "Are you sure you want to delete this user?", "danger", async () => {
          try {
              const res = await fetch(`/api/users?id=${id}`, { method: 'DELETE' });
              if (res.ok) {
                  showToast("User deleted successfully", "success");
                  fetchUsers();
              } else {
                  const data = await res.json();
                  showDialog("Error", data.error || data.detail || "Failed to delete user", "danger");
              }
          } catch (e) {
              showDialog("Error", "Error deleting user: " + e.message, "danger");
          }
      });
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
              showToast(data.message || "Configuration updated", "success");
          } else {
              showDialog("Error", data.error || data.detail || "Failed to update configuration", "danger");
          }
      } catch (e) {
          showDialog("Error", "Error saving config: " + e.message, "danger");
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
      if (!file.name.endsWith('.zip')) {
          showDialog("Invalid File", "Please upload a .zip file", "warning");
          return;
      }

      showDialog(
          "Restore System",
          "This will overwrite the current database and configuration. The system will restart. Proceed?",
          "danger",
          async () => {
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
                      showToast(data.message || 'System restored. Restarting...', "success");
                      setTimeout(() => window.location.reload(), 3000);
                  } else {
                      showDialog("Restore Failed", data.error || data.detail || 'Failed to restore system', "danger");
                  }
              } catch (e) {
                  showDialog("Restore Error", 'Error restoring system: ' + e.message, "danger");
              } finally {
                  setRestoring(false);
                  e.target.value = ''; // Reset file input
              }
          }
      );
  };

  useEffect(() => {
    fetchLogs();
    fetchUser();
  }, [logService]);

  const handleRestart = async (serviceName) => {
    showDialog(
        "Restart Service",
        `Are you sure you want to restart ${serviceName}?`,
        "warning",
        async () => {
            setRestarting(true);
            try {
              const res = await fetch('/api/system/restart', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ service: serviceName })
              });
              const data = await res.json();
              showToast(data.message || 'Restart command sent', "success");
              if (serviceName === logService) {
                setTimeout(fetchLogs, 2000);
              }
            } catch (e) {
              showDialog("Error", `Error restarting: ${e.message}`, "danger");
            } finally {
              setRestarting(false);
            }
        }
    );
  };

  const handleDownloadBackup = () => {
    // The backend endpoint serves the file directly without auth for simplicity here
    window.open('http://127.0.0.1:5055/api/system/backup', '_blank');
  };

  return (
    <div className="page-container animate-fade-in flex flex-col h-full max-h-full">
      <header className="shrink-0" style={{ marginBottom: '16px' }}>
        <h2 className="text-[26px] font-bold text-[var(--text-primary)]">System Settings & Administration</h2>
      </header>

      {/* Tabs Navigation (Standalone Boxes) */}
      <div className="shrink-0 overflow-x-auto custom-scrollbar pb-1" style={{ marginBottom: '8px' }}>
        <div className="flex gap-3" style={{ minWidth: 'max-content' }}>
          <button
              className={`px-[18px] py-[10px] rounded-[9px] text-[15px] font-semibold transition-all whitespace-nowrap border ${
                activeTab === 'system'
                  ? 'bg-[var(--accent)] border-[var(--accent)] text-white shadow-sm'
                  : 'bg-white/[0.02] border-white/[0.08] text-white/60 hover:bg-white/[0.06] hover:text-white'
              }`}
              onClick={() => setActiveTab('system')}
          >
              General System
          </button>
          {String(currentUser?.role || '').toLowerCase() === 'admin' && (
              <>
                  <button
                      className={`px-[18px] py-[10px] rounded-[9px] text-[15px] font-semibold transition-all whitespace-nowrap border ${
                        activeTab === 'users'
                          ? 'bg-[var(--accent)] border-[var(--accent)] text-white shadow-sm'
                          : 'bg-white/[0.02] border-white/[0.08] text-white/60 hover:bg-white/[0.06] hover:text-white'
                      }`}
                      onClick={() => setActiveTab('users')}
                  >
                      User Management
                  </button>
                  <button
                      className={`px-[18px] py-[10px] rounded-[9px] text-[15px] font-semibold transition-all whitespace-nowrap border ${
                        activeTab === 'config'
                          ? 'bg-[var(--accent)] border-[var(--accent)] text-white shadow-sm'
                          : 'bg-white/[0.02] border-white/[0.08] text-white/60 hover:bg-white/[0.06] hover:text-white'
                      }`}
                      onClick={() => setActiveTab('config')}
                  >
                      System Config
                  </button>
                  <button
                      className={`px-[18px] py-[10px] rounded-[9px] text-[15px] font-semibold transition-all whitespace-nowrap border ${
                        activeTab === 'integrations'
                          ? 'bg-[var(--accent)] border-[var(--accent)] text-white shadow-sm'
                          : 'bg-white/[0.02] border-white/[0.08] text-white/60 hover:bg-white/[0.06] hover:text-white'
                      }`}
                      onClick={() => setActiveTab('integrations')}
                  >
                      Integration Setup
                  </button>
              </>
          )}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto custom-scrollbar pb-6 flex flex-col">
        {/* TAB 1: System */}
        {activeTab === 'system' && (
            <div className="flex flex-col gap-6 shrink-0">
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                    {/* Backup & Restore Panel */}
                    <div className="glass-panel p-6">
          <h3 style={{ fontSize: '1.1rem', marginBottom: '16px', color: 'var(--text-primary)', fontWeight: '600' }}>Backup & Restore</h3>
          <p style={{ color: 'var(--text-secondary)', marginBottom: '16px', fontSize: '0.9rem' }}>
            Tải về bản sao lưu an toàn bao gồm database (smarthome.db), cấu hình thiết bị và các biến môi trường (.env).
          </p>
          <div style={{ display: 'flex', gap: '12px' }}>
            <button
              onClick={handleDownloadBackup}
              style={{ background: 'var(--accent)', color: '#fff', border: 'none', padding: '8px 16px', borderRadius: '6px', cursor: 'pointer', fontWeight: '500' }}>
              📥 Download System Backup (.zip)
            </button>
            <label style={{ background: '#dc2626', color: '#fff', border: 'none', padding: '8px 16px', borderRadius: '6px', cursor: 'pointer', fontWeight: '500', opacity: restoring ? 0.5 : 1 }}>
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
          <h3 style={{ fontSize: '1.1rem', marginBottom: '16px', color: 'var(--text-primary)', fontWeight: '600' }}>Service Management</h3>
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
                className="px-4 py-1.5 rounded text-sm font-medium transition-all"
                style={{
                  background: 'rgba(255,255,255,0.05)',
                  border: '1px solid rgba(255,255,255,0.1)',
                  color: 'rgba(255,255,255,0.8)',
                  cursor: 'pointer'
                }}
                onMouseEnter={e => {
                  e.currentTarget.style.background = '#dc2626';
                  e.currentTarget.style.borderColor = '#dc2626';
                  e.currentTarget.style.color = '#ffffff';
                }}
                onMouseLeave={e => {
                  e.currentTarget.style.background = 'rgba(255,255,255,0.05)';
                  e.currentTarget.style.borderColor = 'rgba(255,255,255,0.1)';
                  e.currentTarget.style.color = 'rgba(255,255,255,0.8)';
                }}
              >
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
                className="px-4 py-1.5 rounded text-sm font-medium transition-all"
                style={{
                  background: 'rgba(255,255,255,0.05)',
                  border: '1px solid rgba(255,255,255,0.1)',
                  color: 'rgba(255,255,255,0.8)',
                  cursor: 'pointer'
                }}
                onMouseEnter={e => {
                  e.currentTarget.style.background = '#dc2626';
                  e.currentTarget.style.borderColor = '#dc2626';
                  e.currentTarget.style.color = '#ffffff';
                }}
                onMouseLeave={e => {
                  e.currentTarget.style.background = 'rgba(255,255,255,0.05)';
                  e.currentTarget.style.borderColor = 'rgba(255,255,255,0.1)';
                  e.currentTarget.style.color = 'rgba(255,255,255,0.8)';
                }}
              >
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
                className="px-4 py-1.5 rounded text-sm font-medium transition-all"
                style={{
                  background: 'rgba(255,255,255,0.05)',
                  border: '1px solid rgba(255,255,255,0.1)',
                  color: 'rgba(255,255,255,0.8)',
                  cursor: 'pointer'
                }}
                onMouseEnter={e => {
                  e.currentTarget.style.background = '#dc2626';
                  e.currentTarget.style.borderColor = '#dc2626';
                  e.currentTarget.style.color = '#ffffff';
                }}
                onMouseLeave={e => {
                  e.currentTarget.style.background = 'rgba(255,255,255,0.05)';
                  e.currentTarget.style.borderColor = 'rgba(255,255,255,0.1)';
                  e.currentTarget.style.color = 'rgba(255,255,255,0.8)';
                }}
              >
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
                className="px-4 py-1.5 rounded text-sm font-medium transition-all"
                style={{
                  background: 'rgba(255,255,255,0.05)',
                  border: '1px solid rgba(255,255,255,0.1)',
                  color: 'rgba(255,255,255,0.8)',
                  cursor: 'pointer'
                }}
                onMouseEnter={e => {
                  e.currentTarget.style.background = '#dc2626';
                  e.currentTarget.style.borderColor = '#dc2626';
                  e.currentTarget.style.color = '#ffffff';
                }}
                onMouseLeave={e => {
                  e.currentTarget.style.background = 'rgba(255,255,255,0.05)';
                  e.currentTarget.style.borderColor = 'rgba(255,255,255,0.1)';
                  e.currentTarget.style.color = 'rgba(255,255,255,0.8)';
                }}
              >
                Restart
              </button>
            </div>
          </div>
        </div>
          </div>
        </div>
        )}

        {/* TAB 2: Users */}
        {activeTab === 'users' && String(currentUser?.role || '').toLowerCase() === 'admin' && (
        <div className="glass-panel shrink-0" style={{ padding: '20px', marginBottom: '24px' }}>
          <h3 style={{ fontSize: '1.1rem', marginBottom: '16px', color: 'var(--text-primary)', fontWeight: '600' }}>User Management</h3>
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
                                              background: 'rgba(255,255,255,0.08)',
                                              color: 'rgba(255,255,255,0.8)',
                                              padding: '2px 8px', borderRadius: '12px', fontSize: '0.8rem',
                                              border: '1px solid rgba(255,255,255,0.15)'
                                          }}>
                                              {u.role}
                                          </span>
                                      </td>
                                      <td style={{ padding: '12px 0' }}>
                                          {currentUser.id !== u.id && (
                                              <button onClick={() => handleDeleteUser(u.id)} style={{ background: 'transparent', color: '#dc2626', border: '1px solid #dc2626', padding: '4px 8px', borderRadius: '4px', cursor: 'pointer', fontSize: '0.8rem' }}>Delete</button>
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
                      <button type="submit" style={{ background: 'var(--accent)', color: 'white', border: 'none', padding: '10px', borderRadius: '6px', cursor: 'pointer', fontWeight: 'bold' }}>Add User</button>
                  </form>
              </div>
          </div>
        </div>
        )}
        {/* TAB 3: System Config */}
        {activeTab === 'config' && String(currentUser?.role || '').toLowerCase() === 'admin' && (
        <div className="glass-panel shrink-0" style={{ padding: '20px', marginBottom: '24px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
            <div>
              <h3 style={{ fontSize: '1.1rem', color: 'var(--text-primary)', fontWeight: '600' }}>System Configuration (.env)</h3>
              <p style={{ color: 'var(--text-secondary)', marginTop: '4px', fontSize: '0.9rem' }}>
                Cập nhật các biến môi trường trực tiếp. Lưu ý: một số thay đổi yêu cầu khởi động lại Service để áp dụng.
              </p>
            </div>
            <button
              onClick={handleUpdateConfig}
              disabled={savingConfig}
              style={{ background: 'var(--accent)', color: 'white', border: 'none', padding: '8px 16px', borderRadius: '6px', cursor: 'pointer', fontWeight: 'bold' }}>
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
        {/* TAB 4: Guided integration setup */}
        {activeTab === 'integrations' && String(currentUser?.role || '').toLowerCase() === 'admin' && (
          <div className="glass-panel shrink-0" style={{ padding: '24px', marginBottom: '24px' }}>
            <h3 style={{ fontSize: '1.2rem', color: 'var(--text-primary)', fontWeight: '600', marginBottom: '8px' }}>
              Guided Integration Setup
            </h3>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.95rem', lineHeight: 1.6, marginBottom: '20px', maxWidth: '820px' }}>
              Cấu hình KNX Gateway, AI provider, OpenClaw, Telegram, Zalo và Tailscale bằng quy trình có kiểm tra an toàn. Secret đã lưu chỉ hiển thị trạng thái, không hiển thị lại giá trị.
            </p>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3" style={{ marginBottom: '20px' }}>
              {['KNX & System', 'AI & OpenClaw', 'Telegram, Zalo & Tailscale'].map(label => (
                <div key={label} style={{ padding: '14px 16px', border: '1px solid rgba(255,255,255,0.08)', borderRadius: '7px', background: 'rgba(255,255,255,0.025)', color: 'var(--text-primary)', fontWeight: 600 }}>
                  {label}
                </div>
              ))}
            </div>
            <button
              type="button"
              onClick={() => { window.location.href = '/setup'; }}
              style={{ background: 'var(--accent)', color: '#fff', border: 'none', padding: '10px 18px', borderRadius: '6px', cursor: 'pointer', fontWeight: 600 }}
            >
              Open Setup Wizard
            </button>
          </div>
        )}
        {/* Live Logs Panel (Always visible across tabs for debug, or only on System Tab?)
            Since it was global, let's keep it visible at the bottom or only in System tab.
            Let's put it outside the tabs, but within the scrollable container.
        */}
        {activeTab === 'system' && (
        <div className="glass-panel flex-1" style={{ padding: '20px', display: 'flex', flexDirection: 'column', marginTop: '24px', minHeight: '300px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
          <h3 style={{ fontSize: '1.1rem', color: 'var(--text-primary)', fontWeight: '600' }}>System Logs (journalctl)</h3>

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
        )}

      </div> {/* End scrollable area */}
    </div>
  );
}
