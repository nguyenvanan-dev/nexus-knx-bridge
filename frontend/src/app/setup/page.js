'use client';
import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { showToast } from '../../utils/ui';

export default function SetupWizardPage() {
  const router = useRouter();
  const [step, setStep] = useState(1);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState(null);
  const [bootstrapToken, setBootstrapToken] = useState('');

  // Password / Secret toggles
  const [showSecrets, setShowSecrets] = useState({});

  // Setup state
  const [status, setStatus] = useState(null);
  const [integrations, setIntegrations] = useState(null);

  // Form states
  const [systemForm, setSystemForm] = useState({
    installation_name: 'KNX Smart Home',
    timezone: 'Asia/Ho_Chi_Minh',
    language: 'vi'
  });

  const [adminForm, setAdminForm] = useState({
    username: 'admin',
    password: '',
    confirm_password: ''
  });

  const [knxForm, setKnxForm] = useState({
    gateway_host: '127.0.0.1',
    gateway_port: 3671,
    connection_type: 'TUNNELING',
    individual_address: '1.1.250'
  });

  const [aiForm, setAiForm] = useState({
    provider: 'openai',
    model: 'gpt-4o-mini',
    base_url: 'https://api.openai.com/v1',
    api_key: ''
  });
  const [providerEditor, setProviderEditor] = useState({
    id: 'openai',
    display_name: 'OpenAI',
    api_type: 'openai_compatible',
    base_url: 'https://api.openai.com/v1',
    models_text: 'gpt-4o-mini',
    default_model: 'gpt-4o-mini',
    timeout_seconds: 60,
    api_key: '',
    configured: false,
    active: false
  });

  const [openclawForm, setOpenclawForm] = useState({
    enabled: false,
    runtime_path: '',
    workspace_path: '',
    provider: '',
    model: '',
    base_url: ''
  });
  const [skillCredential, setSkillCredential] = useState({
    skill_id: '',
    key: 'apiKey',
    value: ''
  });

  const [telegramForm, setTelegramForm] = useState({
    enabled: false,
    bot_token: '',
    chat_id: '',
    allow_from: []
  });

  const [zaloForm, setZaloForm] = useState({
    enabled: false,
    bot_token: '',
    webhook_url: '',
    webhook_secret: '',
    integration_mode: 'webhook',
    allow_from: []
  });
  const [zaloUserStatus, setZaloUserStatus] = useState(null);
  const [zaloUserGroups, setZaloUserGroups] = useState([]);
  const [zaloUserBusy, setZaloUserBusy] = useState(false);
  const [zaloUserForm, setZaloUserForm] = useState({
    enabled: false,
    group_policy: 'allowlist',
    group_ids: [],
    history_limit: 50,
    require_mention: true
  });
  const [remoteForm, setRemoteForm] = useState({
    tailscale_enabled: false,
    tailscale_hostname: ''
  });

  useEffect(() => {
    loadSetupStatus();
  }, []);

  useEffect(() => {
    if (step >= 4) refreshIntegrations();
  }, [step]);

  useEffect(() => {
    if (step === 7) loadZaloUserStatus(false);
  }, [step]);

  useEffect(() => {
    const providers = integrations?.ai_provider_configs;
    if (step === 4 && Array.isArray(providers) && providers.length > 0) {
      const selected = providers.find(item => item.id === providerEditor.id);
      selectProvider(selected || providers.find(item => item.active) || providers[0]);
    }
  }, [integrations, step]);

  const loadSetupStatus = async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/setup/status');
      const data = await res.json();
      setStatus(data);
      if (data.config) {
        if (data.config.system) setSystemForm(prev => ({ ...prev, ...data.config.system }));
        if (data.config.knx) setKnxForm(prev => ({ ...prev, ...data.config.knx }));
        if (data.config.ai) setAiForm(prev => ({ ...prev, ...data.config.ai, api_key: '' }));
        if (data.config.telegram) setTelegramForm(prev => ({ ...prev, ...data.config.telegram, bot_token: '' }));
        if (data.config.zalo) setZaloForm(prev => ({
          ...prev,
          ...data.config.zalo,
          bot_token: '',
          webhook_url: '',
          webhook_secret: ''
        }));
        if (data.config.openclaw) setOpenclawForm(prev => ({ ...prev, ...data.config.openclaw }));
        if (data.config.remote_access) setRemoteForm(prev => ({ ...prev, ...data.config.remote_access }));
      }
    } catch (e) {
      showToast(`Không thể tải trạng thái setup: ${e.message}`, 'error');
    } finally {
      setLoading(false);
    }
  };

  const toggleSecret = (field) => {
    setShowSecrets(prev => ({ ...prev, [field]: !prev[field] }));
  };

  const setupHeaders = () => ({
    'Content-Type': 'application/json',
    ...(bootstrapToken ? { 'X-Setup-Token': bootstrapToken } : {})
  });

  const refreshIntegrations = async () => {
    try {
      const res = await fetch('/api/setup/integrations', { headers: setupHeaders() });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Không thể đọc trạng thái tích hợp');
      setIntegrations(data);
    } catch (error) {
      showToast(error.message, 'warning');
    }
  };

  const loadZaloUserStatus = async (probe = false) => {
    try {
      const res = await fetch(
        `/api/setup/zalouser/status${probe ? '?probe=true' : ''}`,
        { headers: setupHeaders() }
      );
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Không thể đọc trạng thái Zalo Personal');
      setZaloUserStatus(data);
      setZaloUserForm(prev => ({
        ...prev,
        enabled: Boolean(data.enabled),
        group_policy: data.group_policy || 'allowlist',
        group_ids: Array.isArray(data.groups) ? data.groups.map(item => item.id) : [],
        history_limit: Number(data.history_limit ?? 50),
        require_mention: Array.isArray(data.groups) && data.groups.length > 0
          ? data.groups.every(item => item.require_mention !== false)
          : prev.require_mention
      }));
      return data;
    } catch (error) {
      showToast(error.message, 'warning');
      return null;
    }
  };

  const loadZaloUserGroups = async () => {
    setZaloUserBusy(true);
    try {
      const res = await fetch('/api/setup/zalouser/groups?limit=200', {
        headers: setupHeaders()
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Không thể đọc danh sách group');
      setZaloUserGroups(Array.isArray(data.groups) ? data.groups : []);
      showToast(`Đã tải ${data.groups?.length || 0} group Zalo`, 'success');
    } catch (error) {
      showToast(error.message, 'error');
    } finally {
      setZaloUserBusy(false);
    }
  };

  const saveZaloUserConfig = async (showSuccess = true) => {
    const res = await fetch('/api/setup/zalouser/config', {
      method: 'POST',
      headers: setupHeaders(),
      body: JSON.stringify(zaloUserForm)
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Không thể lưu Zalo Personal');
    await loadZaloUserStatus(false);
    if (showSuccess) {
      showToast('Đã lưu cấu hình Zalo Personal. Cần restart OpenClaw để áp dụng.', 'success');
    }
    return data;
  };

  const startZaloUserLogin = async () => {
    setZaloUserBusy(true);
    try {
      const res = await fetch('/api/setup/zalouser/login/start', {
        method: 'POST',
        headers: setupHeaders(),
        body: '{}'
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Không thể bắt đầu đăng nhập');
      setZaloUserStatus(prev => ({ ...(prev || {}), login: data.login }));
      for (let attempt = 0; attempt < 90; attempt += 1) {
        await new Promise(resolve => setTimeout(resolve, 2000));
        const statusRes = await fetch('/api/setup/zalouser/login/status', {
          headers: setupHeaders()
        });
        const statusData = await statusRes.json();
        if (!statusRes.ok) throw new Error(statusData.detail || 'Mất phiên đăng nhập');
        setZaloUserStatus(prev => ({ ...(prev || {}), login: statusData.login }));
        if (['connected', 'error'].includes(statusData.login?.state)) {
          await loadZaloUserStatus(true);
          break;
        }
      }
    } catch (error) {
      showToast(error.message, 'error');
    } finally {
      setZaloUserBusy(false);
    }
  };

  const logoutZaloUser = async () => {
    if (!window.confirm('Đăng xuất tài khoản Zalo Personal hiện tại?')) return;
    setZaloUserBusy(true);
    try {
      const res = await fetch('/api/setup/zalouser/logout', {
        method: 'POST',
        headers: setupHeaders(),
        body: JSON.stringify({ confirm: true })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Không thể đăng xuất');
      await loadZaloUserStatus(true);
      showToast('Đã đăng xuất Zalo Personal', 'success');
    } catch (error) {
      showToast(error.message, 'error');
    } finally {
      setZaloUserBusy(false);
    }
  };

  const handleSaveZaloStep = async () => {
    setSaving(true);
    try {
      const botRes = await fetch('/api/setup/zalo', {
        method: 'POST',
        headers: setupHeaders(),
        body: JSON.stringify(zaloForm)
      });
      const botData = await botRes.json();
      if (!botRes.ok || !botData.ok) {
        throw new Error(botData.detail || 'Không thể lưu Zalo Bot');
      }
      await saveZaloUserConfig(false);
      showToast('Đã lưu cả Zalo Bot và Zalo Personal', 'success');
      setStep(prev => prev + 1);
    } catch (error) {
      showToast(error.message, 'error');
    } finally {
      setSaving(false);
    }
  };

  const selectProvider = (item) => {
    const models = Array.isArray(item.models) ? item.models : [];
    const normalizedModels = models.map(model => (
      typeof model === 'string' ? model : model.id
    )).filter(Boolean);
    const defaultModel = item.default_model || normalizedModels[0] || '';
    setProviderEditor({
      id: item.id || item.provider,
      display_name: item.display_name || item.provider || item.id,
      api_type: item.api_type || 'openai_compatible',
      base_url: item.base_url || '',
      models_text: normalizedModels.join('\n'),
      default_model: defaultModel,
      timeout_seconds: item.timeout_seconds || 60,
      api_key: '',
      configured: Boolean(item.configured),
      active: Boolean(item.active)
    });
  };

  const newProvider = () => {
    setProviderEditor({
      id: '',
      display_name: '',
      api_type: 'openai_compatible',
      base_url: '',
      models_text: '',
      default_model: '',
      timeout_seconds: 60,
      api_key: '',
      configured: false,
      active: false
    });
  };

  const saveProvider = async () => {
    const providerId = providerEditor.id.trim().toLowerCase();
    if (!providerId) {
      showToast('Vui lòng nhập Provider ID', 'warning');
      return;
    }
    const models = providerEditor.models_text
      .split(/\n|,/)
      .map(value => value.trim())
      .filter((value, index, values) => value && values.indexOf(value) === index)
      .map(id => ({ id, name: id }));
    setSaving(true);
    try {
      const res = await fetch(`/api/setup/ai/providers/${encodeURIComponent(providerId)}`, {
        method: 'PUT',
        headers: setupHeaders(),
        body: JSON.stringify({
          display_name: providerEditor.display_name || providerId,
          api_type: providerEditor.api_type,
          base_url: providerEditor.base_url,
          models,
          default_model: providerEditor.default_model,
          timeout_seconds: Number(providerEditor.timeout_seconds),
          api_key: providerEditor.api_key === '__CLEAR__' ? '' : providerEditor.api_key,
          clear_api_key: providerEditor.api_key === '__CLEAR__'
        })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Không thể lưu provider');
      setAiForm({
        provider: providerId === 'google' ? 'gemini' : providerId,
        model: providerEditor.default_model,
        base_url: providerEditor.base_url,
        api_key: ''
      });
      await handleSaveStep('ai', {
        provider: providerId === 'google' ? 'gemini' : providerId,
        model: providerEditor.default_model,
        base_url: providerEditor.base_url,
        api_key: ''
      }, false);
      await refreshIntegrations();
      selectProvider(data.provider);
      showToast('Đã lưu provider và danh sách model', 'success');
    } catch (error) {
      showToast(error.message, 'error');
    } finally {
      setSaving(false);
    }
  };

  const deleteProvider = async () => {
    if (!providerEditor.id || providerEditor.active) return;
    const confirmed = window.confirm(
      `Xóa cấu hình ${providerEditor.display_name || providerEditor.id}? API key của provider này cũng bị xóa khỏi OpenClaw.`
    );
    if (!confirmed) return;
    setSaving(true);
    try {
      const res = await fetch(`/api/setup/ai/providers/${encodeURIComponent(providerEditor.id)}`, {
        method: 'DELETE',
        headers: setupHeaders()
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Không thể xóa provider');
      newProvider();
      await refreshIntegrations();
      showToast('Đã xóa provider', 'success');
    } catch (error) {
      showToast(error.message, 'error');
    } finally {
      setSaving(false);
    }
  };

  const saveSkillCredential = async () => {
    if (!skillCredential.skill_id.trim() || !skillCredential.key.trim() || !skillCredential.value) {
      showToast('Nhập Skill ID, tên khóa và credential', 'warning');
      return;
    }
    setSaving(true);
    try {
      const path = `/api/setup/openclaw/skill-credentials/${encodeURIComponent(skillCredential.skill_id.trim().toLowerCase())}/${encodeURIComponent(skillCredential.key.trim())}`;
      const res = await fetch(path, {
        method: 'PUT',
        headers: setupHeaders(),
        body: JSON.stringify({ value: skillCredential.value })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Không thể lưu skill credential');
      setSkillCredential({ ...skillCredential, value: '' });
      await refreshIntegrations();
      showToast('Đã lưu credential cho skill', 'success');
    } catch (error) {
      showToast(error.message, 'error');
    } finally {
      setSaving(false);
    }
  };

  const handleSaveStep = async (category, payload, nextStep = true) => {
    setSaving(true);
    setTestResult(null);
    try {
      const res = await fetch(`/api/setup/${category}`, {
        method: 'POST',
        headers: setupHeaders(),
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      if (res.ok && data.ok) {
        showToast(`Đã lưu cấu hình ${category.toUpperCase()}`, 'success');
        if (nextStep) setStep(prev => prev + 1);
      } else {
        showToast(data.detail || data.error || 'Lưu thất bại', 'error');
      }
    } catch (e) {
      showToast(`Lỗi kết nối: ${e.message}`, 'error');
    } finally {
      setSaving(false);
    }
  };

  const handleCreateAdmin = async () => {
    if (!adminForm.username || !adminForm.password) {
      showToast('Vui lòng nhập đầy đủ Tên đăng nhập và Mật khẩu', 'warning');
      return;
    }
    if (adminForm.password !== adminForm.confirm_password) {
      showToast('Mật khẩu xác nhận không khớp', 'error');
      return;
    }
    setSaving(true);
    try {
      const res = await fetch('/api/setup/bootstrap-admin', {
        method: 'POST',
        headers: setupHeaders(),
        body: JSON.stringify({
          username: adminForm.username,
          password: adminForm.password
        })
      });
      const data = await res.json();
      if (res.ok) {
        showToast('Tạo tài khoản quản trị thành công', 'success');
        setStep(prev => prev + 1);
      } else {
        showToast(data.detail || 'Không thể tạo tài khoản', 'error');
      }
    } catch (e) {
      showToast(`Lỗi: ${e.message}`, 'error');
    } finally {
      setSaving(false);
    }
  };

  const handleRunTest = async (testCategory, payload) => {
    setTesting(true);
    setTestResult(null);
    try {
      const res = await fetch(`/api/setup/test/${testCategory}`, {
        method: 'POST',
        headers: setupHeaders(),
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      setTestResult(data);
      if (data.ok) {
        showToast('Kiểm tra cấu hình thành công', 'success');
      } else {
        showToast(data.detail || 'Kiểm tra thất bại', 'warning');
      }
    } catch (e) {
      setTestResult({ ok: false, detail: e.message });
    } finally {
      setTesting(false);
    }
  };

  const handleFinishSetup = async () => {
    setSaving(true);
    try {
      const res = await fetch('/api/setup/complete', {
        method: 'POST',
        headers: setupHeaders()
      });
      const data = await res.json();
      if (res.ok) {
        showToast(
          data.restart_required
            ? 'Đã lưu setup. Cần restart service để nạp cấu hình mới.'
            : 'Hoàn tất thiết lập hệ thống thành công!',
          'success'
        );
        router.push('/settings');
      } else {
        const detail = data.detail;
        const message = typeof detail === 'object'
          ? `${detail.message}: ${(detail.blockers || []).join('; ')}`
          : detail;
        showToast(message || 'Lỗi hoàn tất setup', 'error');
      }
    } catch (e) {
      showToast(`Lỗi: ${e.message}`, 'error');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '60vh', color: '#e2e8f0' }}>
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: '1.5rem', fontWeight: 600, marginBottom: '0.5rem' }}>KNX Bridge Setup Wizard</div>
          <div style={{ color: '#94a3b8' }}>Đang khởi tạo cấu hình...</div>
        </div>
      </div>
    );
  }

  const stepsList = [
    { num: 1, title: 'Hệ thống' },
    { num: 2, title: 'Tài khoản Admin' },
    { num: 3, title: 'KNX Gateway' },
    { num: 4, title: 'AI Provider' },
    { num: 5, title: 'OpenClaw' },
    { num: 6, title: 'Telegram' },
    { num: 7, title: 'Zalo' },
    { num: 8, title: 'Remote Access' },
    { num: 9, title: 'Xem lại' },
    { num: 10, title: 'Hoàn tất' }
  ];

  return (
    <div style={{ maxWidth: '900px', margin: '0 auto', padding: '1.5rem 1rem' }}>
      {/* Header */}
      <div style={{ marginBottom: '2rem', textAlign: 'center' }}>
        <h1 style={{ fontSize: '1.875rem', fontWeight: 700, color: '#f8fafc', marginBottom: '0.5rem' }}>
          Hướng Dẫn Thiết Lập KNX Bridge
        </h1>
        <p style={{ color: '#94a3b8', fontSize: '0.95rem' }}>
          Cấu hình nhanh các thành phần kết nối, tài khoản và tích hợp mở rộng
        </p>
      </div>

      {/* Stepper Navigation */}
      <div style={{ display: 'flex', overflowX: 'auto', gap: '0.5rem', marginBottom: '2rem', paddingBottom: '0.5rem', borderBottom: '1px solid #334155' }}>
        {stepsList.map((s) => (
          <button
            key={s.num}
            onClick={() => setStep(s.num)}
            style={{
              flex: '0 0 auto',
              padding: '0.5rem 0.85rem',
              borderRadius: '0.5rem',
              fontSize: '0.85rem',
              fontWeight: 500,
              cursor: 'pointer',
              border: 'none',
              background: step === s.num ? '#3b82f6' : (step > s.num ? '#1e293b' : 'transparent'),
              color: step === s.num ? '#ffffff' : (step > s.num ? '#60a5fa' : '#94a3b8')
            }}
          >
            {s.num}. {s.title}
          </button>
        ))}
      </div>

      {/* Main Content Box */}
      <div style={{ background: '#0f172a', border: '1px solid #1e293b', borderRadius: '0.75rem', padding: '1.75rem', marginBottom: '1.5rem' }}>

        {/* STEP 1: SYSTEM */}
        {step === 1 && (
          <div>
            <h2 style={{ fontSize: '1.25rem', fontWeight: 600, color: '#f1f5f9', marginBottom: '1rem' }}>Step 1: Cấu hình Hệ thống Baseline</h2>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              {!status?.setup_complete && (
                <div>
                  <label style={{ display: 'block', fontSize: '0.875rem', color: '#94a3b8', marginBottom: '0.25rem' }}>Setup Bootstrap Token:</label>
                  <input
                    type={showSecrets.bootstrap_token ? 'text' : 'password'}
                    value={bootstrapToken}
                    onChange={e => setBootstrapToken(e.target.value)}
                    autoComplete="off"
                    style={{ width: '100%', padding: '0.6rem 0.8rem', borderRadius: '0.375rem', background: '#1e293b', border: '1px solid #334155', color: '#f8fafc' }}
                  />
                  <button
                    type="button"
                    onClick={() => toggleSecret('bootstrap_token')}
                    style={{ marginTop: '0.4rem', background: 'transparent', border: 'none', color: '#60a5fa', fontSize: '0.85rem', cursor: 'pointer' }}
                  >
                    {showSecrets.bootstrap_token ? 'Ẩn token' : 'Hiển thị token'}
                  </button>
                </div>
              )}
              <div>
                <label style={{ display: 'block', fontSize: '0.875rem', color: '#94a3b8', marginBottom: '0.25rem' }}>Tên công trình / Hệ thống:</label>
                <input
                  type="text"
                  value={systemForm.installation_name}
                  onChange={e => setSystemForm({ ...systemForm, installation_name: e.target.value })}
                  style={{ width: '100%', padding: '0.6rem 0.8rem', borderRadius: '0.375rem', background: '#1e293b', border: '1px solid #334155', color: '#f8fafc' }}
                />
              </div>
              <div>
                <label style={{ display: 'block', fontSize: '0.875rem', color: '#94a3b8', marginBottom: '0.25rem' }}>Múi giờ (Timezone):</label>
                <input
                  type="text"
                  value={systemForm.timezone}
                  onChange={e => setSystemForm({ ...systemForm, timezone: e.target.value })}
                  style={{ width: '100%', padding: '0.6rem 0.8rem', borderRadius: '0.375rem', background: '#1e293b', border: '1px solid #334155', color: '#f8fafc' }}
                />
              </div>
              <div>
                <label style={{ display: 'block', fontSize: '0.875rem', color: '#94a3b8', marginBottom: '0.25rem' }}>Ngôn ngữ mặc định:</label>
                <select
                  value={systemForm.language}
                  onChange={e => setSystemForm({ ...systemForm, language: e.target.value })}
                  style={{ width: '100%', padding: '0.6rem 0.8rem', borderRadius: '0.375rem', background: '#1e293b', border: '1px solid #334155', color: '#f8fafc' }}
                >
                  <option value="vi">Tiếng Việt</option>
                  <option value="en">English</option>
                </select>
              </div>
            </div>
          </div>
        )}

        {/* STEP 2: ADMIN ACCOUNT */}
        {step === 2 && (
          <div>
            <h2 style={{ fontSize: '1.25rem', fontWeight: 600, color: '#f1f5f9', marginBottom: '1rem' }}>Step 2: Tài khoản Quản trị (Admin)</h2>
            {status?.admin_exists ? (
              <div style={{ padding: '1rem', background: '#064e3b', border: '1px solid #047857', borderRadius: '0.5rem', color: '#a7f3d0' }}>
                ✓ Hệ thống đã có tài khoản Quản trị. Bạn có thể tạo thêm hoặc bấm <strong>Tiếp tục</strong>.
              </div>
            ) : (
              <p style={{ color: '#94a3b8', fontSize: '0.9rem', marginBottom: '1rem' }}>Tạo tài khoản quản trị ban đầu để đăng nhập và điều khiển KNX Bridge.</p>
            )}

            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', marginTop: '1rem' }}>
              <div>
                <label style={{ display: 'block', fontSize: '0.875rem', color: '#94a3b8', marginBottom: '0.25rem' }}>Tên đăng nhập:</label>
                <input
                  type="text"
                  value={adminForm.username}
                  onChange={e => setAdminForm({ ...adminForm, username: e.target.value })}
                  style={{ width: '100%', padding: '0.6rem 0.8rem', borderRadius: '0.375rem', background: '#1e293b', border: '1px solid #334155', color: '#f8fafc' }}
                />
              </div>
              <div>
                <label style={{ display: 'block', fontSize: '0.875rem', color: '#94a3b8', marginBottom: '0.25rem' }}>Mật khẩu:</label>
                <input
                  type={showSecrets.admin_pwd ? 'text' : 'password'}
                  value={adminForm.password}
                  onChange={e => setAdminForm({ ...adminForm, password: e.target.value })}
                  style={{ width: '100%', padding: '0.6rem 0.8rem', borderRadius: '0.375rem', background: '#1e293b', border: '1px solid #334155', color: '#f8fafc' }}
                />
              </div>
              <div>
                <label style={{ display: 'block', fontSize: '0.875rem', color: '#94a3b8', marginBottom: '0.25rem' }}>Xác nhận mật khẩu:</label>
                <input
                  type={showSecrets.admin_pwd ? 'text' : 'password'}
                  value={adminForm.confirm_password}
                  onChange={e => setAdminForm({ ...adminForm, confirm_password: e.target.value })}
                  style={{ width: '100%', padding: '0.6rem 0.8rem', borderRadius: '0.375rem', background: '#1e293b', border: '1px solid #334155', color: '#f8fafc' }}
                />
              </div>
              <button
                type="button"
                onClick={() => toggleSecret('admin_pwd')}
                style={{ alignSelf: 'flex-start', background: 'transparent', border: 'none', color: '#60a5fa', fontSize: '0.85rem', cursor: 'pointer' }}
              >
                {showSecrets.admin_pwd ? '🔒 Ẩn mật khẩu' : '👁️ Hiển thị mật khẩu'}
              </button>
            </div>
          </div>
        )}

        {/* STEP 3: KNX GATEWAY */}
        {step === 3 && (
          <div>
            <h2 style={{ fontSize: '1.25rem', fontWeight: 600, color: '#f1f5f9', marginBottom: '1rem' }}>Step 3: Kết Nối KNX Gateway</h2>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              <div>
                <label style={{ display: 'block', fontSize: '0.875rem', color: '#94a3b8', marginBottom: '0.25rem' }}>Gateway Host / IP:</label>
                <input
                  type="text"
                  value={knxForm.gateway_host}
                  onChange={e => setKnxForm({ ...knxForm, gateway_host: e.target.value })}
                  style={{ width: '100%', padding: '0.6rem 0.8rem', borderRadius: '0.375rem', background: '#1e293b', border: '1px solid #334155', color: '#f8fafc' }}
                />
              </div>
              <div>
                <label style={{ display: 'block', fontSize: '0.875rem', color: '#94a3b8', marginBottom: '0.25rem' }}>Gateway Port (mặc định 3671):</label>
                <input
                  type="number"
                  value={knxForm.gateway_port}
                  onChange={e => setKnxForm({ ...knxForm, gateway_port: parseInt(e.target.value) || 3671 })}
                  style={{ width: '100%', padding: '0.6rem 0.8rem', borderRadius: '0.375rem', background: '#1e293b', border: '1px solid #334155', color: '#f8fafc' }}
                />
              </div>
              <div>
                <label style={{ display: 'block', fontSize: '0.875rem', color: '#94a3b8', marginBottom: '0.25rem' }}>Kiểu kết nối:</label>
                <select
                  value={knxForm.connection_type}
                  onChange={e => setKnxForm({ ...knxForm, connection_type: e.target.value })}
                  style={{ width: '100%', padding: '0.6rem 0.8rem', borderRadius: '0.375rem', background: '#1e293b', border: '1px solid #334155', color: '#f8fafc' }}
                >
                  <option value="TUNNELING">TUNNELING</option>
                  <option value="ROUTING">ROUTING</option>
                  <option value="AUTOMATIC">AUTOMATIC</option>
                </select>
              </div>
              <div>
                <label style={{ display: 'block', fontSize: '0.875rem', color: '#94a3b8', marginBottom: '0.25rem' }}>Địa chỉ cá nhân (Individual Address):</label>
                <input
                  type="text"
                  value={knxForm.individual_address}
                  onChange={e => setKnxForm({ ...knxForm, individual_address: e.target.value })}
                  style={{ width: '100%', padding: '0.6rem 0.8rem', borderRadius: '0.375rem', background: '#1e293b', border: '1px solid #334155', color: '#f8fafc' }}
                />
              </div>

              <div style={{ marginTop: '0.5rem' }}>
                <button
                  type="button"
                  onClick={() => handleRunTest('knx', knxForm)}
                  disabled={testing}
                  style={{ padding: '0.5rem 1rem', background: '#334155', color: '#f8fafc', border: 'none', borderRadius: '0.375rem', cursor: 'pointer', fontSize: '0.875rem' }}
                >
                  {testing ? 'Đang kiểm tra...' : '🔍 Validate Configuration (No KNX Telegram Write)'}
                </button>
              </div>
            </div>
          </div>
        )}

        {/* STEP 4: AI PROVIDER */}
        {step === 4 && (
          <div>
            <h2 style={{ fontSize: '1.25rem', fontWeight: 600, color: '#f1f5f9', marginBottom: '1rem' }}>Step 4: AI Provider / LLM API</h2>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '1rem' }}>
                <div style={{ color: '#94a3b8', fontSize: '0.875rem' }}>
                  Có thể khai báo nhiều provider và nhiều model. Provider có model mặc định sẽ được OpenClaw sử dụng.
                </div>
                <button type="button" onClick={newProvider} style={{ padding: '0.55rem 0.9rem', background: '#0e7490', color: '#fff', border: 0, borderRadius: '0.4rem', cursor: 'pointer', whiteSpace: 'nowrap' }}>
                  + Provider
                </button>
              </div>
              {integrations?.ai_provider_configs?.length > 0 && (
                <div>
                  <div style={{ color: '#94a3b8', fontSize: '0.875rem', marginBottom: '0.5rem' }}>Provider credentials đang có:</div>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '0.65rem' }}>
                    {integrations.ai_provider_configs.map(item => (
                      <button
                        type="button"
                        key={item.id}
                        onClick={() => selectProvider(item)}
                        style={{
                          padding: '0.8rem',
                          textAlign: 'left',
                          borderRadius: '0.45rem',
                          border: item.active ? '1px solid #22d3ee' : '1px solid #334155',
                          background: item.active ? 'rgba(34,211,238,0.08)' : '#172033',
                          color: '#e2e8f0',
                          cursor: 'pointer'
                        }}
                      >
                        <div style={{ display: 'flex', justifyContent: 'space-between', gap: '0.5rem', marginBottom: '0.45rem' }}>
                          <strong>{item.display_name}</strong>
                          <span style={{ color: item.configured ? '#34d399' : '#f59e0b', fontSize: '0.8rem' }}>
                            {item.active ? 'Active' : item.configured ? 'Configured' : 'Missing'}
                          </span>
                        </div>
                        <div style={{ fontFamily: 'monospace', fontSize: '0.82rem', color: '#cbd5e1' }}>
                          {item.masked || 'Chưa có API key'}
                        </div>
                        {item.fingerprint && (
                          <div style={{ fontSize: '0.75rem', color: '#64748b', marginTop: '0.3rem' }}>
                            SHA256: {item.fingerprint}
                          </div>
                        )}
                        <div style={{ fontSize: '0.75rem', color: '#64748b', marginTop: '0.3rem', overflowWrap: 'anywhere' }}>
                          {item.source}
                        </div>
                      </button>
                    ))}
                  </div>
                </div>
              )}
              <div style={{ display: 'grid', gridTemplateColumns: 'minmax(160px, 1fr) minmax(180px, 1fr)', gap: '0.75rem' }}>
                <div>
                  <label style={{ display: 'block', fontSize: '0.875rem', color: '#94a3b8', marginBottom: '0.25rem' }}>Provider ID:</label>
                  <input value={providerEditor.id} disabled={providerEditor.configured || providerEditor.active} onChange={e => setProviderEditor({ ...providerEditor, id: e.target.value.toLowerCase() })} placeholder="anthropic, ollama, company-ai" style={{ width: '100%', padding: '0.6rem 0.8rem', borderRadius: '0.375rem', background: '#1e293b', border: '1px solid #334155', color: '#f8fafc' }} />
                </div>
                <div>
                  <label style={{ display: 'block', fontSize: '0.875rem', color: '#94a3b8', marginBottom: '0.25rem' }}>Tên hiển thị:</label>
                  <input value={providerEditor.display_name} onChange={e => setProviderEditor({ ...providerEditor, display_name: e.target.value })} placeholder="Anthropic" style={{ width: '100%', padding: '0.6rem 0.8rem', borderRadius: '0.375rem', background: '#1e293b', border: '1px solid #334155', color: '#f8fafc' }} />
                </div>
              </div>
              <div>
                <label style={{ display: 'block', fontSize: '0.875rem', color: '#94a3b8', marginBottom: '0.25rem' }}>Kiểu API:</label>
                <select value={providerEditor.api_type} onChange={e => setProviderEditor({ ...providerEditor, api_type: e.target.value })} style={{ width: '100%', padding: '0.6rem 0.8rem', borderRadius: '0.375rem', background: '#1e293b', border: '1px solid #334155', color: '#f8fafc' }}>
                  <option value="openai_compatible">OpenAI-compatible</option>
                  <option value="anthropic">Anthropic Messages API</option>
                  <option value="google">Google Gemini API</option>
                  <option value="local">Local / Ollama</option>
                </select>
              </div>
              <div>
                <label style={{ display: 'block', fontSize: '0.875rem', color: '#94a3b8', marginBottom: '0.25rem' }}>Base URL:</label>
                <input
                  type="text"
                  value={providerEditor.base_url}
                  onChange={e => setProviderEditor({ ...providerEditor, base_url: e.target.value })}
                  style={{ width: '100%', padding: '0.6rem 0.8rem', borderRadius: '0.375rem', background: '#1e293b', border: '1px solid #334155', color: '#f8fafc' }}
                />
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '0.75rem' }}>
                <div>
                  <label style={{ display: 'block', fontSize: '0.875rem', color: '#94a3b8', marginBottom: '0.25rem' }}>Models (mỗi dòng một model):</label>
                  <textarea value={providerEditor.models_text} onChange={e => setProviderEditor({ ...providerEditor, models_text: e.target.value })} rows={4} placeholder={'model-a\nmodel-b'} style={{ width: '100%', padding: '0.6rem 0.8rem', borderRadius: '0.375rem', background: '#1e293b', border: '1px solid #334155', color: '#f8fafc', resize: 'vertical' }} />
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                  <div>
                    <label style={{ display: 'block', fontSize: '0.875rem', color: '#94a3b8', marginBottom: '0.25rem' }}>Model mặc định:</label>
                    <input value={providerEditor.default_model} onChange={e => setProviderEditor({ ...providerEditor, default_model: e.target.value })} style={{ width: '100%', padding: '0.6rem 0.8rem', borderRadius: '0.375rem', background: '#1e293b', border: '1px solid #334155', color: '#f8fafc' }} />
                  </div>
                  <div>
                    <label style={{ display: 'block', fontSize: '0.875rem', color: '#94a3b8', marginBottom: '0.25rem' }}>Timeout (giây):</label>
                    <input type="number" min="1" max="600" value={providerEditor.timeout_seconds} onChange={e => setProviderEditor({ ...providerEditor, timeout_seconds: e.target.value })} style={{ width: '100%', padding: '0.6rem 0.8rem', borderRadius: '0.375rem', background: '#1e293b', border: '1px solid #334155', color: '#f8fafc' }} />
                  </div>
                </div>
              </div>
              <div>
                <label style={{ display: 'block', fontSize: '0.875rem', color: '#94a3b8', marginBottom: '0.25rem' }}>API Key:</label>
                <div style={{ display: 'flex', gap: '0.5rem' }}>
                  <input
                    type={showSecrets.ai_key ? 'text' : 'password'}
                    placeholder={providerEditor.configured ? 'Đã cấu hình - để trống nếu giữ nguyên' : 'Nhập API Key mới'}
                    value={providerEditor.api_key}
                    onChange={e => setProviderEditor({ ...providerEditor, api_key: e.target.value })}
                    style={{ flex: 1, padding: '0.6rem 0.8rem', borderRadius: '0.375rem', background: '#1e293b', border: '1px solid #334155', color: '#f8fafc' }}
                  />
                  <button
                    type="button"
                    onClick={() => toggleSecret('ai_key')}
                    style={{ padding: '0.6rem', background: '#334155', border: 'none', borderRadius: '0.375rem', color: '#f8fafc', cursor: 'pointer' }}
                  >
                    {showSecrets.ai_key ? 'Ẩn' : 'Hiện'}
                  </button>
                  {providerEditor.configured && (
                    <button
                      type="button"
                      onClick={() => setProviderEditor({ ...providerEditor, api_key: '__CLEAR__' })}
                      style={{ padding: '0.6rem', background: '#991b1b', border: 'none', borderRadius: '0.375rem', color: '#f8fafc', cursor: 'pointer' }}
                    >
                      Clear
                    </button>
                  )}
                </div>
              </div>

              <div style={{ marginTop: '0.5rem', display: 'flex', gap: '0.65rem' }}>
                <button type="button" onClick={saveProvider} disabled={saving} style={{ padding: '0.6rem 1rem', background: '#0891b2', color: '#fff', border: 0, borderRadius: '0.375rem', cursor: 'pointer', fontWeight: 600 }}>
                  Lưu provider
                </button>
                <button
                  type="button"
                  onClick={() => handleRunTest('ai', { provider: providerEditor.id, base_url: providerEditor.base_url, api_key: providerEditor.api_key })}
                  disabled={testing}
                  style={{ padding: '0.5rem 1rem', background: '#334155', color: '#f8fafc', border: 'none', borderRadius: '0.375rem', cursor: 'pointer', fontSize: '0.875rem' }}
                >
                  {testing ? 'Đang kiểm tra...' : '🔍 Validate Configuration (No API Calls Made)'}
                </button>
                {providerEditor.configured && !providerEditor.active && (
                  <button type="button" onClick={deleteProvider} disabled={saving} style={{ padding: '0.6rem 1rem', background: '#7f1d1d', color: '#fff', border: 0, borderRadius: '0.375rem', cursor: 'pointer' }}>
                    Xóa provider
                  </button>
                )}
              </div>
            </div>
          </div>
        )}

        {/* STEP 5: OPENCLAW */}
        {step === 5 && (
          <div>
            <h2 style={{ fontSize: '1.25rem', fontWeight: 600, color: '#f1f5f9', marginBottom: '1rem' }}>Step 5: Tích Hợp OpenClaw Runtime</h2>
            {integrations?.openclaw && (
              <div style={{ background: '#1e293b', padding: '1rem', borderRadius: '0.5rem', marginBottom: '1rem', fontSize: '0.875rem' }}>
                <div><strong>Runtime Installed:</strong> {integrations.openclaw.runtime_installed ? '✓ Yes' : '✗ No'}</div>
                <div><strong>Executable:</strong> {integrations.openclaw.executable_path || 'None'}</div>
                <div><strong>9router Service:</strong> {integrations.openclaw.service_status}</div>
                <div><strong>Workspace:</strong> {integrations.openclaw.workspace_path}</div>
                <div><strong>Skill Symlink Valid:</strong> {integrations.openclaw.skills_symlink_valid ? '✓ Valid' : '⚠ Link Missing/Outdated'}</div>
              </div>
            )}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: '#f8fafc', cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  checked={openclawForm.enabled}
                  onChange={e => setOpenclawForm({ ...openclawForm, enabled: e.target.checked })}
                />
                Kích hoạt tích hợp OpenClaw
              </label>
              {[
                ['runtime_path', 'Đường dẫn runtime', '/usr/local/bin/openclaw'],
                ['workspace_path', 'Workspace', '/home/user/.openclaw/workspace'],
                ['provider', 'AI provider', '9router'],
                ['model', 'Model', '9router/model-name'],
                ['base_url', 'Provider base URL', 'http://127.0.0.1:20128/v1']
              ].map(([field, label, placeholder]) => (
                <div key={field}>
                  <label style={{ display: 'block', fontSize: '0.875rem', color: '#94a3b8', marginBottom: '0.25rem' }}>{label}</label>
                  <input
                    value={openclawForm[field] || ''}
                    placeholder={placeholder}
                    onChange={e => setOpenclawForm({ ...openclawForm, [field]: e.target.value })}
                    style={{ width: '100%', padding: '0.6rem 0.8rem', borderRadius: '0.375rem', background: '#1e293b', border: '1px solid #334155', color: '#f8fafc' }}
                  />
                </div>
              ))}
              <button type="button" onClick={refreshIntegrations} style={{ alignSelf: 'flex-start', padding: '0.55rem 1rem', background: '#334155', color: '#f8fafc', border: 0, borderRadius: '0.375rem', cursor: 'pointer' }}>
                Làm mới trạng thái runtime
              </button>
              <div style={{ borderTop: '1px solid #334155', paddingTop: '1rem' }}>
                <h3 style={{ color: '#f1f5f9', fontSize: '1rem', marginBottom: '0.65rem' }}>Credential cho Skill / Plugin</h3>
                {integrations?.skill_credentials?.length > 0 && (
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', marginBottom: '0.75rem' }}>
                    {integrations.skill_credentials.map(item => (
                      <button key={`${item.skill_id}:${item.key}`} type="button" onClick={() => setSkillCredential({ skill_id: item.skill_id, key: item.key, value: '' })} style={{ padding: '0.55rem 0.7rem', background: '#172033', border: '1px solid #334155', borderRadius: '0.4rem', color: '#e2e8f0', cursor: 'pointer', textAlign: 'left' }}>
                        <strong>{item.skill_id}</strong> · {item.key}
                        <span style={{ display: 'block', color: '#94a3b8', fontFamily: 'monospace', marginTop: '0.2rem' }}>{item.masked}</span>
                      </button>
                    ))}
                  </div>
                )}
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 2fr auto', gap: '0.6rem', alignItems: 'end' }}>
                  <div>
                    <label style={{ display: 'block', color: '#94a3b8', fontSize: '0.82rem', marginBottom: '0.25rem' }}>Skill ID</label>
                    <input value={skillCredential.skill_id} onChange={e => setSkillCredential({ ...skillCredential, skill_id: e.target.value })} placeholder="goplaces" style={{ width: '100%', padding: '0.6rem', background: '#1e293b', border: '1px solid #334155', borderRadius: '0.375rem', color: '#f8fafc' }} />
                  </div>
                  <div>
                    <label style={{ display: 'block', color: '#94a3b8', fontSize: '0.82rem', marginBottom: '0.25rem' }}>Tên khóa</label>
                    <select value={skillCredential.key} onChange={e => setSkillCredential({ ...skillCredential, key: e.target.value })} style={{ width: '100%', padding: '0.6rem', background: '#1e293b', border: '1px solid #334155', borderRadius: '0.375rem', color: '#f8fafc' }}>
                      <option value="apiKey">apiKey</option>
                      <option value="token">token</option>
                      <option value="access_token">access_token</option>
                      <option value="client_secret">client_secret</option>
                      <option value="webhook_secret">webhook_secret</option>
                    </select>
                  </div>
                  <div>
                    <label style={{ display: 'block', color: '#94a3b8', fontSize: '0.82rem', marginBottom: '0.25rem' }}>Credential mới</label>
                    <input type="password" value={skillCredential.value} onChange={e => setSkillCredential({ ...skillCredential, value: e.target.value })} placeholder="Để trống nếu không thay đổi" style={{ width: '100%', padding: '0.6rem', background: '#1e293b', border: '1px solid #334155', borderRadius: '0.375rem', color: '#f8fafc' }} />
                  </div>
                  <button type="button" onClick={saveSkillCredential} disabled={saving} style={{ padding: '0.62rem 0.9rem', background: '#0891b2', border: 0, borderRadius: '0.375rem', color: '#fff', cursor: 'pointer' }}>Lưu key</button>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* STEP 6: TELEGRAM */}
        {step === 6 && (
          <div>
            <h2 style={{ fontSize: '1.25rem', fontWeight: 600, color: '#f1f5f9', marginBottom: '1rem' }}>Step 6: Tích Hợp Telegram Notification</h2>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: '#f8fafc', cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  checked={telegramForm.enabled}
                  onChange={e => setTelegramForm({ ...telegramForm, enabled: e.target.checked })}
                />
                Kích hoạt Telegram Notification
              </label>
              <div>
                <label style={{ display: 'block', fontSize: '0.875rem', color: '#94a3b8', marginBottom: '0.25rem' }}>Bot Token:</label>
                <div style={{ display: 'flex', gap: '0.5rem' }}>
                  <input
                    type={showSecrets.tg_token ? 'text' : 'password'}
                    placeholder={status?.config?.telegram?.bot_token?.configured ? 'Đã cấu hình - để trống nếu giữ nguyên' : 'Nhập Bot Token (ví dụ: 123456:ABC...)'}
                    value={telegramForm.bot_token}
                    onChange={e => setTelegramForm({ ...telegramForm, bot_token: e.target.value })}
                    style={{ flex: 1, padding: '0.6rem 0.8rem', borderRadius: '0.375rem', background: '#1e293b', border: '1px solid #334155', color: '#f8fafc' }}
                  />
                  <button
                    type="button"
                    onClick={() => toggleSecret('tg_token')}
                    style={{ padding: '0.6rem', background: '#334155', border: 'none', borderRadius: '0.375rem', color: '#f8fafc', cursor: 'pointer' }}
                  >
                    {showSecrets.tg_token ? 'Ẩn' : 'Hiện'}
                  </button>
                  {status?.config?.telegram?.bot_token?.configured && (
                    <button
                      type="button"
                      onClick={() => setTelegramForm({ ...telegramForm, bot_token: '__CLEAR__' })}
                      style={{ padding: '0.6rem', background: '#991b1b', border: 'none', borderRadius: '0.375rem', color: '#f8fafc', cursor: 'pointer' }}
                    >
                      Clear
                    </button>
                  )}
                </div>
              </div>
              <div>
                <label style={{ display: 'block', fontSize: '0.875rem', color: '#94a3b8', marginBottom: '0.25rem' }}>Default Chat ID:</label>
                <input
                  type="text"
                  value={telegramForm.chat_id}
                  onChange={e => setTelegramForm({ ...telegramForm, chat_id: e.target.value })}
                  style={{ width: '100%', padding: '0.6rem 0.8rem', borderRadius: '0.375rem', background: '#1e293b', border: '1px solid #334155', color: '#f8fafc' }}
                />
              </div>
              <div>
                <label style={{ display: 'block', fontSize: '0.875rem', color: '#94a3b8', marginBottom: '0.25rem' }}>Allow-list (ID, cách nhau bằng dấu phẩy):</label>
                <input
                  type="text"
                  value={Array.isArray(telegramForm.allow_from) ? telegramForm.allow_from.join(', ') : telegramForm.allow_from}
                  onChange={e => setTelegramForm({ ...telegramForm, allow_from: e.target.value })}
                  style={{ width: '100%', padding: '0.6rem 0.8rem', borderRadius: '0.375rem', background: '#1e293b', border: '1px solid #334155', color: '#f8fafc' }}
                />
                {integrations?.openclaw?.telegram_pairing && (
                  <div style={{ color: '#94a3b8', marginTop: '0.4rem' }}>
                    Pairing requests: {integrations.openclaw.telegram_pairing.pending_pairing_requests} · Allowed: {integrations.openclaw.telegram_pairing.allow_count}
                  </div>
                )}
              </div>

              <div style={{ marginTop: '0.5rem' }}>
                <button
                  type="button"
                  onClick={() => handleRunTest('telegram', telegramForm)}
                  disabled={testing}
                  style={{ padding: '0.5rem 1rem', background: '#334155', color: '#f8fafc', border: 'none', borderRadius: '0.375rem', cursor: 'pointer', fontSize: '0.875rem' }}
                >
                  {testing ? 'Đang kiểm tra...' : '🔍 Validate Configuration (No Messages Sent)'}
                </button>
              </div>
            </div>
          </div>
        )}

        {/* STEP 7: ZALO */}
        {step === 7 && (
          <div>
            <h2 style={{ fontSize: '1.25rem', fontWeight: 600, color: '#f1f5f9', marginBottom: '1rem' }}>Step 7: Tích Hợp Zalo Notification / Webhook</h2>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: '#f8fafc', cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  checked={zaloForm.enabled}
                  onChange={e => setZaloForm({ ...zaloForm, enabled: e.target.checked })}
                />
                Kích hoạt Zalo Webhook / Integration
              </label>
              <div>
                <label style={{ display: 'block', fontSize: '0.875rem', color: '#94a3b8', marginBottom: '0.25rem' }}>Zalo Bot Token:</label>
                <input
                  type={showSecrets.zalo_token ? 'text' : 'password'}
                  placeholder={status?.config?.zalo?.bot_token?.configured ? 'Đã cấu hình - để trống nếu giữ nguyên' : 'Nhập Bot Token'}
                  value={zaloForm.bot_token}
                  onChange={e => setZaloForm({ ...zaloForm, bot_token: e.target.value })}
                  style={{ width: '100%', padding: '0.6rem 0.8rem', borderRadius: '0.375rem', background: '#1e293b', border: '1px solid #334155', color: '#f8fafc' }}
                />
              </div>
              <div>
                <label style={{ display: 'block', fontSize: '0.875rem', color: '#94a3b8', marginBottom: '0.25rem' }}>Zalo Webhook URL:</label>
                <div style={{ display: 'flex', gap: '0.5rem' }}>
                  <input
                    type={showSecrets.zalo_url ? 'text' : 'password'}
                    placeholder={status?.config?.zalo?.webhook_url?.configured ? 'Đã cấu hình - để trống nếu giữ nguyên' : 'Nhập Webhook URL'}
                    value={zaloForm.webhook_url}
                    onChange={e => setZaloForm({ ...zaloForm, webhook_url: e.target.value })}
                    style={{ flex: 1, padding: '0.6rem 0.8rem', borderRadius: '0.375rem', background: '#1e293b', border: '1px solid #334155', color: '#f8fafc' }}
                  />
                  <button
                    type="button"
                    onClick={() => toggleSecret('zalo_url')}
                    style={{ padding: '0.6rem', background: '#334155', border: 'none', borderRadius: '0.375rem', color: '#f8fafc', cursor: 'pointer' }}
                  >
                    {showSecrets.zalo_url ? 'Ẩn' : 'Hiện'}
                  </button>
                  {status?.config?.zalo?.webhook_url?.configured && (
                    <button
                      type="button"
                      onClick={() => setZaloForm({ ...zaloForm, webhook_url: '__CLEAR__' })}
                      style={{ padding: '0.6rem', background: '#991b1b', border: 'none', borderRadius: '0.375rem', color: '#f8fafc', cursor: 'pointer' }}
                    >
                      Clear
                    </button>
                  )}
                </div>
              </div>
              <div>
                <label style={{ display: 'block', fontSize: '0.875rem', color: '#94a3b8', marginBottom: '0.25rem' }}>Webhook Secret:</label>
                <input
                  type={showSecrets.zalo_secret ? 'text' : 'password'}
                  placeholder={status?.config?.zalo?.webhook_secret?.configured ? 'Đã cấu hình - để trống nếu giữ nguyên' : 'Nhập webhook secret nếu Zalo cung cấp'}
                  value={zaloForm.webhook_secret}
                  onChange={e => setZaloForm({ ...zaloForm, webhook_secret: e.target.value })}
                  style={{ width: '100%', padding: '0.6rem 0.8rem', borderRadius: '0.375rem', background: '#1e293b', border: '1px solid #334155', color: '#f8fafc' }}
                />
              </div>
              <div>
                <label style={{ display: 'block', fontSize: '0.875rem', color: '#94a3b8', marginBottom: '0.25rem' }}>Allow-list (ID, cách nhau bằng dấu phẩy):</label>
                <input
                  type="text"
                  value={Array.isArray(zaloForm.allow_from) ? zaloForm.allow_from.join(', ') : zaloForm.allow_from}
                  onChange={e => setZaloForm({ ...zaloForm, allow_from: e.target.value })}
                  style={{ width: '100%', padding: '0.6rem 0.8rem', borderRadius: '0.375rem', background: '#1e293b', border: '1px solid #334155', color: '#f8fafc' }}
                />
                {integrations?.openclaw?.zalo_pairing && (
                  <div style={{ color: '#94a3b8', marginTop: '0.4rem' }}>
                    Pairing requests: {integrations.openclaw.zalo_pairing.pending_pairing_requests} · Allowed: {integrations.openclaw.zalo_pairing.allow_count}
                  </div>
                )}
              </div>

              <div style={{ marginTop: '0.5rem' }}>
                <button
                  type="button"
                  onClick={() => handleRunTest('zalo', zaloForm)}
                  disabled={testing}
                  style={{ padding: '0.5rem 1rem', background: '#334155', color: '#f8fafc', border: 'none', borderRadius: '0.375rem', cursor: 'pointer', fontSize: '0.875rem' }}
                >
                  {testing ? 'Đang kiểm tra...' : '🔍 Validate Configuration (No Real Webhook Sent)'}
                </button>
              </div>
            </div>

            <div style={{
              marginTop: '1.5rem',
              padding: '1.25rem',
              border: '1px solid #334155',
              borderRadius: '0.75rem',
              background: '#111827'
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: '1rem', alignItems: 'flex-start', flexWrap: 'wrap' }}>
                <div>
                  <h3 style={{ fontSize: '1.1rem', fontWeight: 650, color: '#f8fafc', margin: 0 }}>
                    Zalo Personal Group Reader
                  </h3>
                  <p style={{ color: '#94a3b8', margin: '0.35rem 0 0', lineHeight: 1.5 }}>
                    Tài khoản Zalo cá nhân dùng để đọc lịch sử, tóm tắt và phản hồi trong các group được chọn.
                  </p>
                </div>
                <div style={{ display: 'flex', gap: '0.65rem', alignItems: 'center', flexWrap: 'wrap' }}>
                  <span style={{
                    color: zaloUserStatus?.credential_present ? '#34d399' : '#f87171',
                    fontWeight: 600
                  }}>
                    ● {zaloUserStatus?.credential_present ? 'Đã đăng nhập' : 'Chưa đăng nhập'}
                  </span>
                  <span style={{
                    color: zaloUserStatus?.probe?.running ? '#34d399' : '#94a3b8',
                    fontWeight: 600
                  }}>
                    ● {zaloUserStatus?.probe?.running ? 'Đang chạy' : 'Chưa kiểm tra runtime'}
                  </span>
                </div>
              </div>

              <div style={{
                marginTop: '1rem',
                padding: '0.85rem 1rem',
                borderRadius: '0.5rem',
                border: '1px solid #713f12',
                background: 'rgba(120, 53, 15, 0.18)',
                color: '#fbbf24',
                lineHeight: 1.5
              }}>
                Zalo Personal dùng cơ chế đăng nhập không chính thức. Chỉ dùng tài khoản phụ và giới hạn group để giảm nguy cơ tài khoản bị hạn chế.
              </div>

              <div style={{ display: 'flex', gap: '0.75rem', marginTop: '1rem', flexWrap: 'wrap' }}>
                <button
                  type="button"
                  onClick={() => loadZaloUserStatus(true)}
                  disabled={zaloUserBusy}
                  style={{ padding: '0.65rem 1rem', background: '#334155', color: '#f8fafc', border: 'none', borderRadius: '0.45rem', cursor: 'pointer' }}
                >
                  Kiểm tra trạng thái
                </button>
                <button
                  type="button"
                  onClick={startZaloUserLogin}
                  disabled={zaloUserBusy}
                  style={{ padding: '0.65rem 1rem', background: '#0891b2', color: '#ffffff', border: 'none', borderRadius: '0.45rem', cursor: 'pointer', fontWeight: 600 }}
                >
                  {zaloUserBusy ? 'Đang xử lý...' : 'Đăng nhập / Đổi tài khoản bằng QR'}
                </button>
                <button
                  type="button"
                  onClick={logoutZaloUser}
                  disabled={zaloUserBusy || !zaloUserStatus?.credential_present}
                  style={{ padding: '0.65rem 1rem', background: '#7f1d1d', color: '#ffffff', border: 'none', borderRadius: '0.45rem', cursor: 'pointer' }}
                >
                  Đăng xuất
                </button>
              </div>

              {zaloUserStatus?.login?.qr_data_url && (
                <div style={{ marginTop: '1rem', display: 'flex', gap: '1rem', alignItems: 'center', flexWrap: 'wrap' }}>
                  <img
                    src={zaloUserStatus.login.qr_data_url}
                    alt="QR đăng nhập Zalo Personal"
                    width={240}
                    height={240}
                    style={{ width: '240px', height: '240px', background: '#ffffff', padding: '0.5rem', borderRadius: '0.5rem' }}
                  />
                  <div style={{ color: '#cbd5e1', maxWidth: '360px', lineHeight: 1.6 }}>
                    Mở ứng dụng Zalo trên điện thoại và quét mã này. Không đóng trang cho đến khi trạng thái chuyển sang đã kết nối.
                  </div>
                </div>
              )}
              {zaloUserStatus?.login?.message && (
                <div style={{ color: '#cbd5e1', marginTop: '0.75rem' }}>
                  {zaloUserStatus.login.message}
                </div>
              )}

              <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(210px, 1fr))',
                gap: '1rem',
                marginTop: '1.25rem'
              }}>
                <label style={{ color: '#e2e8f0' }}>
                  <span style={{ display: 'block', marginBottom: '0.45rem' }}>Hoạt động</span>
                  <input
                    type="checkbox"
                    checked={zaloUserForm.enabled}
                    onChange={event => setZaloUserForm({ ...zaloUserForm, enabled: event.target.checked })}
                  />{' '}
                  Bật Zalo Personal
                </label>
                <label style={{ color: '#e2e8f0' }}>
                  <span style={{ display: 'block', marginBottom: '0.45rem' }}>Quyền truy cập group</span>
                  <select
                    value={zaloUserForm.group_policy}
                    onChange={event => setZaloUserForm({ ...zaloUserForm, group_policy: event.target.value })}
                    style={{ width: '100%', padding: '0.65rem', background: '#1e293b', color: '#f8fafc', border: '1px solid #334155', borderRadius: '0.4rem' }}
                  >
                    <option value="allowlist">Chỉ group được chọn</option>
                    <option value="open">Tất cả group</option>
                    <option value="disabled">Không nhận tin group</option>
                  </select>
                </label>
                <label style={{ color: '#e2e8f0' }}>
                  <span style={{ display: 'block', marginBottom: '0.45rem' }}>Số tin lịch sử mỗi group</span>
                  <input
                    type="number"
                    min="0"
                    max="500"
                    value={zaloUserForm.history_limit}
                    onChange={event => setZaloUserForm({ ...zaloUserForm, history_limit: Number(event.target.value) })}
                    style={{ width: '100%', padding: '0.65rem', background: '#1e293b', color: '#f8fafc', border: '1px solid #334155', borderRadius: '0.4rem' }}
                  />
                </label>
              </div>

              <label style={{ display: 'flex', gap: '0.55rem', alignItems: 'center', color: '#e2e8f0', marginTop: '1rem' }}>
                <input
                  type="checkbox"
                  checked={zaloUserForm.require_mention}
                  onChange={event => setZaloUserForm({ ...zaloUserForm, require_mention: event.target.checked })}
                />
                Chỉ phản hồi khi bot được nhắc tên trong group
              </label>

              <div style={{ marginTop: '1.25rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '1rem', flexWrap: 'wrap' }}>
                  <div>
                    <strong style={{ color: '#f8fafc' }}>Group được phép</strong>
                    <div style={{ color: '#94a3b8', marginTop: '0.2rem' }}>
                      {zaloUserStatus?.group_count || 0} group có lịch sử · {zaloUserStatus?.message_count || 0} tin đã lưu
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={loadZaloUserGroups}
                    disabled={zaloUserBusy || !zaloUserStatus?.credential_present}
                    style={{ padding: '0.6rem 0.9rem', background: '#334155', color: '#f8fafc', border: 'none', borderRadius: '0.4rem', cursor: 'pointer' }}
                  >
                    Tải danh sách group
                  </button>
                </div>
                {zaloUserGroups.length > 0 && (
                  <div style={{ marginTop: '0.75rem', maxHeight: '240px', overflowY: 'auto', border: '1px solid #334155', borderRadius: '0.5rem' }}>
                    {zaloUserGroups.map(group => (
                      <label
                        key={group.id}
                        style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', padding: '0.75rem 0.9rem', borderBottom: '1px solid #243244', color: '#e2e8f0' }}
                      >
                        <input
                          type="checkbox"
                          checked={zaloUserForm.group_ids.includes(group.id)}
                          onChange={event => setZaloUserForm({
                            ...zaloUserForm,
                            group_ids: event.target.checked
                              ? [...new Set([...zaloUserForm.group_ids, group.id])]
                              : zaloUserForm.group_ids.filter(id => id !== group.id)
                          })}
                        />
                        <span style={{ flex: 1 }}>{group.name}</span>
                        <code style={{ color: '#94a3b8' }}>{group.id}</code>
                      </label>
                    ))}
                  </div>
                )}
              </div>

              <button
                type="button"
                onClick={() => saveZaloUserConfig(true)}
                disabled={saving || zaloUserBusy}
                style={{ marginTop: '1.25rem', padding: '0.7rem 1.1rem', background: '#2563eb', color: '#ffffff', border: 'none', borderRadius: '0.45rem', cursor: 'pointer', fontWeight: 600 }}
              >
                Lưu cấu hình Zalo Personal
              </button>
            </div>
          </div>
        )}

        {/* STEP 8: REMOTE ACCESS */}
        {step === 8 && (
          <div>
            <h2 style={{ fontSize: '1.25rem', fontWeight: 600, color: '#f1f5f9', marginBottom: '1rem' }}>Step 8: Remote Access (Tailscale Status)</h2>
            {integrations?.tailscale && (
              <div style={{ background: '#1e293b', padding: '1.25rem', borderRadius: '0.5rem', color: '#f8fafc' }}>
                <div style={{ fontSize: '1rem', fontWeight: 600, marginBottom: '0.5rem' }}>Tailscale VPN Status (Read-Only)</div>
                <div style={{ fontSize: '0.875rem', display: 'flex', flexDirection: 'column', gap: '0.4rem', color: '#cbd5e1' }}>
                  <div>Installed: <strong>{integrations.tailscale.installed ? '✓ Yes' : '✗ No'}</strong></div>
                  <div>Running: <strong>{integrations.tailscale.running ? '✓ Active' : 'Inactive'}</strong></div>
                  <div>Tailscale IP: <strong style={{ color: '#60a5fa' }}>{integrations.tailscale.ip || 'N/A'}</strong></div>
                </div>
              </div>
            )}
            <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: '#f8fafc', marginTop: '1rem' }}>
              <input
                type="checkbox"
                checked={remoteForm.tailscale_enabled}
                onChange={e => setRemoteForm({ ...remoteForm, tailscale_enabled: e.target.checked })}
              />
              Dùng Tailscale làm phương thức truy cập từ xa
            </label>
            <button type="button" onClick={refreshIntegrations} style={{ marginTop: '1rem', padding: '0.55rem 1rem', background: '#334155', color: '#f8fafc', border: 0, borderRadius: '0.375rem', cursor: 'pointer' }}>
              Kiểm tra lại Tailscale
            </button>
          </div>
        )}

        {/* STEP 9: REVIEW */}
        {step === 9 && (
          <div>
            <h2 style={{ fontSize: '1.25rem', fontWeight: 600, color: '#f1f5f9', marginBottom: '1rem' }}>Step 9: Xem Lại Toàn Bộ Cấu Hình</h2>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', fontSize: '0.875rem', color: '#cbd5e1' }}>
              <div style={{ background: '#1e293b', padding: '0.8rem', borderRadius: '0.375rem' }}>
                <strong>Hệ thống:</strong> {systemForm.installation_name} ({systemForm.timezone})
              </div>
              <div style={{ background: '#1e293b', padding: '0.8rem', borderRadius: '0.375rem' }}>
                <strong>KNX Gateway:</strong> {knxForm.gateway_host}:{knxForm.gateway_port} ({knxForm.connection_type})
              </div>
              <div style={{ background: '#1e293b', padding: '0.8rem', borderRadius: '0.375rem' }}>
                <strong>AI Provider:</strong> {aiForm.provider} - {aiForm.model} ({status?.config?.ai?.api_key?.configured || aiForm.api_key ? '✓ Key Configured' : 'No Key'})
              </div>
              <div style={{ background: '#1e293b', padding: '0.8rem', borderRadius: '0.375rem' }}>
                <strong>OpenClaw:</strong> {openclawForm.enabled ? '✓ Enabled' : 'Disabled'}
              </div>
              <div style={{ background: '#1e293b', padding: '0.8rem', borderRadius: '0.375rem' }}>
                <strong>Telegram:</strong> {telegramForm.enabled ? '✓ Enabled' : 'Disabled'}
              </div>
              <div style={{ background: '#1e293b', padding: '0.8rem', borderRadius: '0.375rem' }}>
                <strong>Zalo:</strong> {zaloForm.enabled ? '✓ Enabled' : 'Disabled'}
              </div>
              <div style={{ background: '#1e293b', padding: '0.8rem', borderRadius: '0.375rem' }}>
                <strong>Remote access:</strong> {remoteForm.tailscale_enabled ? 'Tailscale' : 'Local network only'}
              </div>
              <div style={{ background: '#1e293b', padding: '0.8rem', borderRadius: '0.375rem' }}>
                <strong>Services:</strong>{' '}
                {Object.entries(integrations?.services || {}).map(([name, state]) => `${name}: ${state}`).join(' · ') || 'Chưa kiểm tra'}
              </div>
              <div style={{ background: '#1e293b', padding: '0.8rem', borderRadius: '0.375rem' }}>
                <strong>Backup:</strong> {integrations?.backup_available ? 'Sẵn sàng tải trong System Settings' : 'Chưa có database để backup'}
              </div>
            </div>
          </div>
        )}

        {/* STEP 10: COMPLETE */}
        {step === 10 && (
          <div style={{ textAlign: 'center', padding: '1rem 0' }}>
            <h2 style={{ fontSize: '1.5rem', fontWeight: 700, color: '#4ade80', marginBottom: '0.5rem' }}>
              🎉 Tất Cả Đã Sẵn Sàng!
            </h2>
            <p style={{ color: '#94a3b8', marginBottom: '1.5rem' }}>
              Bấm nút bên dưới để hoàn tất cài đặt và chuyển đến Bảng Quản Trị Hệ Thống.
            </p>
            <button
              type="button"
              onClick={handleFinishSetup}
              disabled={saving}
              style={{ padding: '0.75rem 2rem', background: '#16a34a', color: '#ffffff', border: 'none', borderRadius: '0.5rem', fontSize: '1rem', fontWeight: 600, cursor: 'pointer' }}
            >
              {saving ? 'Đang hoàn tất...' : 'Hoàn Tất & Khóa Setup Wizard'}
            </button>
          </div>
        )}

        {/* Test Result Display Box */}
        {testResult && (
          <div style={{ marginTop: '1rem', padding: '0.8rem', borderRadius: '0.375rem', background: testResult.ok ? '#064e3b' : '#7f1d1d', color: testResult.ok ? '#a7f3d0' : '#fecaca', fontSize: '0.875rem' }}>
            {testResult.ok ? '✓ Success: ' : '✗ Error: '} {testResult.detail}
          </div>
        )}
      </div>

      {/* Footer Stepper Controls */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <button
          type="button"
          disabled={step === 1 || saving}
          onClick={() => setStep(prev => Math.max(1, prev - 1))}
          style={{ padding: '0.6rem 1.25rem', background: '#1e293b', color: '#94a3b8', border: '1px solid #334155', borderRadius: '0.375rem', cursor: 'pointer' }}
        >
          ← Quay lại
        </button>

        {step < 10 && (
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            {step === 1 && (
              <button
                type="button"
                onClick={() => handleSaveStep('system', systemForm)}
                disabled={saving}
                style={{ padding: '0.6rem 1.5rem', background: '#2563eb', color: '#ffffff', border: 'none', borderRadius: '0.375rem', cursor: 'pointer', fontWeight: 600 }}
              >
                Lưu & Tiếp theo →
              </button>
            )}
            {step === 2 && (
              <button
                type="button"
                onClick={status?.admin_exists ? () => setStep(prev => prev + 1) : handleCreateAdmin}
                disabled={saving}
                style={{ padding: '0.6rem 1.5rem', background: '#2563eb', color: '#ffffff', border: 'none', borderRadius: '0.375rem', cursor: 'pointer', fontWeight: 600 }}
              >
                {status?.admin_exists ? 'Tiếp theo →' : 'Tạo Admin & Tiếp theo →'}
              </button>
            )}
            {step === 3 && (
              <button
                type="button"
                onClick={() => handleSaveStep('knx', knxForm)}
                disabled={saving}
                style={{ padding: '0.6rem 1.5rem', background: '#2563eb', color: '#ffffff', border: 'none', borderRadius: '0.375rem', cursor: 'pointer', fontWeight: 600 }}
              >
                Lưu & Tiếp theo →
              </button>
            )}
            {step === 4 && (
              <button
                type="button"
                onClick={() => setStep(prev => prev + 1)}
                disabled={saving}
                style={{ padding: '0.6rem 1.5rem', background: '#2563eb', color: '#ffffff', border: 'none', borderRadius: '0.375rem', cursor: 'pointer', fontWeight: 600 }}
              >
                Tiếp theo →
              </button>
            )}
            {step === 5 && (
              <button
                type="button"
                onClick={() => handleSaveStep('openclaw', openclawForm)}
                disabled={saving}
                style={{ padding: '0.6rem 1.5rem', background: '#2563eb', color: '#ffffff', border: 'none', borderRadius: '0.375rem', cursor: 'pointer', fontWeight: 600 }}
              >
                Lưu & Tiếp theo →
              </button>
            )}
            {step === 6 && (
              <button
                type="button"
                onClick={() => handleSaveStep('telegram', telegramForm)}
                disabled={saving}
                style={{ padding: '0.6rem 1.5rem', background: '#2563eb', color: '#ffffff', border: 'none', borderRadius: '0.375rem', cursor: 'pointer', fontWeight: 600 }}
              >
                Lưu & Tiếp theo →
              </button>
            )}
            {step === 7 && (
              <button
                type="button"
                onClick={handleSaveZaloStep}
                disabled={saving}
                style={{ padding: '0.6rem 1.5rem', background: '#2563eb', color: '#ffffff', border: 'none', borderRadius: '0.375rem', cursor: 'pointer', fontWeight: 600 }}
              >
                Lưu & Tiếp theo →
              </button>
            )}
            {step === 8 && (
              <button
                type="button"
                onClick={() => handleSaveStep('remote_access', remoteForm)}
                style={{ padding: '0.6rem 1.5rem', background: '#2563eb', color: '#ffffff', border: 'none', borderRadius: '0.375rem', cursor: 'pointer', fontWeight: 600 }}
              >
                Tiếp theo →
              </button>
            )}
            {step === 9 && (
              <button
                type="button"
                onClick={() => setStep(10)}
                style={{ padding: '0.6rem 1.5rem', background: '#2563eb', color: '#ffffff', border: 'none', borderRadius: '0.375rem', cursor: 'pointer', fontWeight: 600 }}
              >
                Xác nhận & Đi đến bước Hoàn tất →
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
