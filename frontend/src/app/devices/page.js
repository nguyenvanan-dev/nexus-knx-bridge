'use client';
import { useState, useEffect } from 'react';
import { showDialog, showToast } from '../../utils/ui';

export default function DevicesPage() {
  const [devices, setDevices] = useState({});
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');

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

  /* eslint-disable react-hooks/set-state-in-effect */
  useEffect(() => {
    fetchDevices();
  }, []);
  /* eslint-enable react-hooks/set-state-in-effect */

  const handleAction = async (action, payload) => {
    if (action === 'delete') {
        showDialog("Delete Device", `Are you sure you want to delete ${payload.device_id}?`, "danger", async () => {
            await performAction(action, payload);
        });
        return;
    }
    await performAction(action, payload);
  };

  const performAction = async (action, payload) => {
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
          showToast("Device deleted successfully", "success");
        } else {
          fetchDevices();
        }
      } else {
        const err = await res.json();
        showDialog("Error", JSON.stringify(err), "danger");
      }
    } catch (e) {
      showDialog("Error", "Error performing action", "danger");
    }
  };

  // ---------------- WIZARD LOGIC ----------------

  // ---------------- WIZARD LOGIC ----------------

  const openAddWizard = () => {
    setWizardMode('add');
    setCurrentDevice({
      device_id: '',
      name: '',
      room: 'phong_rd',
      type: 'light',
      onoff_ga: '',
      status_ga: '',
      supports_brightness: false,
      brightness_ga: '',
      brightness_status_ga: '',
      color_rgb_ga: '',
      color_temp_ga: '',
      color_temp_status_ga: '',
      color_temp_min: '',
      color_temp_max: '',
      temperature_set_ga: '',
      temperature_status_ga: '',
      fan_speed_ga: '',
      mode_ga: '',
      stop_ga: '',
      position_set_ga: '',
      position_status_ga: '',
      role: '',
      aliases: [],
      safety_level: 'safe_demo',
      require_confirm: false,
      enabled: true
    });
    setWizardStep(1);
    setGaWarnings([]);
    setShowWizard(true);
  };

  const openEditWizard = (key, dev) => {
    setWizardMode('update');
    const caps = dev.capabilities || {};
    setCurrentDevice({
      device_id: key,
      name: dev.name || '',
      room: dev.room || 'phong_rd',
      type: dev.type || 'light',
      onoff_ga: dev.onoff_ga || '',
      status_ga: dev.status_ga || '',
      supports_brightness: dev.supports_brightness || false,
      brightness_ga: dev.brightness_ga || '',
      brightness_status_ga: dev.brightness_status_ga || '',

      color_rgb_ga: caps.rgb?.write_ga || dev.color_rgb_ga || '',
      color_temp_ga: caps.color_temperature?.write_ga || dev.color_temp_ga || '',
      color_temp_status_ga: caps.color_temperature?.status_ga || dev.color_temp_status_ga || '',
      color_temp_min: caps.color_temperature?.min || dev.color_temp_min || '',
      color_temp_max: caps.color_temperature?.max || dev.color_temp_max || '',
      temperature_set_ga: caps.temperature_setpoint?.write_ga || dev.temperature_set_ga || '',
      temperature_status_ga: caps.temperature_setpoint?.status_ga || dev.temperature_status_ga || '',
      fan_speed_ga: caps.fan_speed?.write_ga || dev.fan_speed_ga || '',
      mode_ga: caps.mode?.write_ga || dev.mode_ga || '',
      stop_ga: caps.stop?.write_ga || dev.stop_ga || '',
      position_set_ga: caps.position?.write_ga || dev.position_set_ga || '',
      position_status_ga: caps.position?.status_ga || dev.position_status_ga || '',

      role: dev.role || '',
      aliases: dev.aliases || [],
      safety_level: dev.safety_level || 'safe_demo',
      require_confirm: dev.require_confirm || false,
      enabled: dev.enabled !== false
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
    if (copy.capabilities) {
      copy.capabilities = {};
    }
    if (copy.knx_config_payload) {
      copy.knx_config_payload = '';
    }
    return copy;
  };

  const duplicateDevice = (key, dev) => {
    setWizardMode('add');
    const caps = dev.capabilities || {};
    const fullDev = {
      device_id: key,
      name: dev.name || '',
      room: dev.room || 'phong_rd',
      type: dev.type || 'light',
      onoff_ga: dev.onoff_ga || '',
      status_ga: dev.status_ga || '',
      supports_brightness: dev.supports_brightness || false,
      brightness_ga: dev.brightness_ga || '',
      brightness_status_ga: dev.brightness_status_ga || '',
      color_rgb_ga: caps.rgb?.write_ga || dev.color_rgb_ga || '',
      color_temp_ga: caps.color_temperature?.write_ga || dev.color_temp_ga || '',
      color_temp_status_ga: caps.color_temperature?.status_ga || dev.color_temp_status_ga || '',
      color_temp_min: caps.color_temperature?.min || dev.color_temp_min || '',
      color_temp_max: caps.color_temperature?.max || dev.color_temp_max || '',
      temperature_set_ga: caps.temperature_setpoint?.write_ga || dev.temperature_set_ga || '',
      temperature_status_ga: caps.temperature_setpoint?.status_ga || dev.temperature_status_ga || '',
      fan_speed_ga: caps.fan_speed?.write_ga || dev.fan_speed_ga || '',
      mode_ga: caps.mode?.write_ga || dev.mode_ga || '',
      stop_ga: caps.stop?.write_ga || dev.stop_ga || '',
      position_set_ga: caps.position?.write_ga || dev.position_set_ga || '',
      position_status_ga: caps.position?.status_ga || dev.position_status_ga || '',
      role: dev.role || '',
      aliases: dev.aliases || [],
      safety_level: dev.safety_level || 'safe_demo',
      require_confirm: dev.require_confirm || false,
      enabled: dev.enabled !== false
    };
    const newDevice = clear_group_addresses(fullDev);
    newDevice.device_id = `${key}_copy`;
    setCurrentDevice(newDevice);
    setWizardStep(1);
    setGaWarnings([]);
    setShowWizard(true);
  };

  // Helper to build knx_config_payload on frontend
  const buildKnxConfigPayload = (device) => {
    const capabilities = {};
    if (device.onoff_ga) {
      capabilities.switch = {
        write_ga: device.onoff_ga,
        status_ga: device.status_ga || ''
      };
    }
    if (device.supports_brightness || device.brightness_ga) {
      capabilities.brightness = {
        write_ga: device.brightness_ga || '',
        status_ga: device.brightness_status_ga || '',
        dpt: '5.001',
        min: 0,
        max: 100
      };
    }
    if (device.color_temp_ga) {
      capabilities.color_temperature = {
        write_ga: device.color_temp_ga,
        status_ga: device.color_temp_status_ga || '',
        dpt: '7.600',
        min: device.color_temp_min ? parseInt(device.color_temp_min) : 1000,
        max: device.color_temp_max ? parseInt(device.color_temp_max) : 10000
      };
    }
    if (device.color_rgb_ga) {
      capabilities.rgb = {
        write_ga: device.color_rgb_ga,
        status_ga: device.color_status_ga || '',
        dpt: '232.600'
      };
    }
    if (device.temperature_set_ga) {
      capabilities.temperature_setpoint = {
        write_ga: device.temperature_set_ga,
        status_ga: device.temperature_status_ga || '',
        dpt: '9.001',
        min: 16,
        max: 30
      };
    }
    if (device.fan_speed_ga) {
      capabilities.fan_speed = {
        write_ga: device.fan_speed_ga,
        dpt: '5.001',
        min: 0,
        max: 100
      };
    }
    if (device.mode_ga) {
      capabilities.mode = {
        write_ga: device.mode_ga,
        dpt: '20.105'
      };
    }
    if (device.stop_ga) {
      capabilities.stop = {
        write_ga: device.stop_ga,
        dpt: '1.010'
      };
    }
    if (device.position_set_ga) {
      capabilities.position = {
        write_ga: device.position_set_ga,
        status_ga: device.position_status_ga || '',
        dpt: '5.001',
        min: 0,
        max: 100
      };
    }
    if (device.type === 'sensor' && device.status_ga) {
      capabilities.sensor_value = {
        status_ga: device.status_ga
      };
    }
    return { capabilities };
  };

  // Helper to extract GAs dynamically from a device object (including capabilities)
  const collectGasFromDevice = (device) => {
    const gas = [];
    for (const key of Object.keys(device)) {
      if (key.endsWith('_ga') && device[key]) {
        gas.push(device[key]);
      }
    }
    const extractInnerGAs = (obj) => {
      if (typeof obj === 'object' && obj !== null) {
        for (const [k, v] of Object.entries(obj)) {
          if (typeof k === 'string' && (k.endsWith('_ga') || k === 'write_ga' || k === 'status_ga')) {
            if (v && typeof v === 'string') {
              gas.push(v);
            }
          } else if (typeof v === 'object') {
            extractInnerGAs(v);
          }
        }
      }
    };

    let caps = device.capabilities;
    if (!caps && device.knx_config_payload) {
      try {
        const parsed = typeof device.knx_config_payload === 'string'
          ? JSON.parse(device.knx_config_payload)
          : device.knx_config_payload;
        caps = parsed.capabilities || parsed;
      } catch (e) {}
    }
    if (caps) {
      extractInnerGAs(caps);
    }
    return Array.from(new Set(gas.filter(g => typeof g === 'string' && /^\d+\/\d+\/\d+$/.test(g))));
  };

  const validateGAs = () => {
    const warnings = [];
    const currentDeviceGAs = collectGasFromDevice(currentDevice);

    // Check format of all entered GAs on currentDevice
    for (const key of Object.keys(currentDevice)) {
      if (key.endsWith('_ga') && currentDevice[key]) {
        const val = currentDevice[key];
        if (!/^\d+\/\d+\/\d+$/.test(val)) {
            warnings.push(`${key.replace(/_/g, ' ').toUpperCase()} (${val}) does not look like a valid KNX format (e.g., 1/1/1).`);
        }
      }
    }

    // Check duplicates against all existing devices in workspace
    for (const [key, dev] of Object.entries(devices)) {
      if (key === currentDevice.device_id) continue;
      const existingGAs = collectGasFromDevice(dev);
      for (const ga of currentDeviceGAs) {
        if (existingGAs.includes(ga)) {
          warnings.push(`Warning: GA ${ga} is already used by device '${key}'.`);
        }
      }
    }

    setGaWarnings(warnings);
    return warnings.length === 0;
  };

  const nextStep = () => {
      if (wizardStep === 1) {
          if (!currentDevice.device_id.trim()) {
              showDialog("Validation Error", "Device ID is required", "warning");
              return;
          }
          setWizardStep(2);
      } else if (wizardStep === 2) {
          validateGAs();
          setWizardStep(3);
      }
  };

  const saveAndDeploy = async () => {
      setIsSaving(true);
      try {
          const payloadToSend = { ...currentDevice };

          // Build capability payload
          const capsRes = buildKnxConfigPayload(currentDevice);
          payloadToSend.knx_config_payload = capsRes;

          const res = await fetch('/api/devices', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ action: wizardMode, payload: { ...payloadToSend, confirmed: true } })
          });

          if (!res.ok) throw new Error(JSON.stringify(await res.json()));

          await fetchDevices();

          // Reload platform registry instead of restarting service
          await fetch('/api/platform/reload', { method: 'POST' });

          showToast("Device saved & platforms reloaded successfully", "success");
          setWizardStep(4);
      } catch (e) {
          showDialog("Save Error", "Error saving device: " + e.message, "danger");
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
          showToast("Command sent successfully!", "success");
      } catch (e) {
          showDialog("Control Error", e.message, "danger");
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
        showToast("Devices exported successfully", "success");
    } catch (e) {
        showDialog("Export Error", "Export failed: " + e.message, "danger");
    }
  };

  const [importReview, setImportReview] = useState(null);

  const importDevices = async (e) => {
      const file = e.target.files[0];
      if (!file) return;

      if (file.name.endsWith('.knxproj')) {
          const password = prompt("Nhập mật khẩu file ETS .knxproj (để trống nếu không có):") || "";
          try {
              setIsSaving(true);
              const formData = new FormData();
              formData.append("file", file);
              if (password) {
                  formData.append("password", password);
              }
              const res = await fetch('/api/knxproj/parse', {
                  method: 'POST',
                  body: formData
              });
              const result = await res.json();

              if (!res.ok) {
                  throw new Error(result.message || result.error || `HTTP ${res.status}`);
              }

              if (result.status === 'error' || result.ok === false) {
                  throw new Error(result.message || result.error || 'KNXProj parse failed');
              }

              const proposedDevices = Array.isArray(result.proposed_devices) ? result.proposed_devices : [];
              const duplicates = Array.isArray(result.duplicates) ? result.duplicates : [];
              const unmapped = Array.isArray(result.unmapped_group_addresses) ? result.unmapped_group_addresses : [];

              const summary = result.summary || {
                  total_devices: proposedDevices.length,
                  ready: proposedDevices.filter(d => d.status === 'ready').length,
                  needs_review: proposedDevices.filter(d => d.status === 'needs_review').length,
                  missing_info: proposedDevices.filter(d => d.status === 'missing_info').length,
                  by_type: {}
              };

              if (proposedDevices.length === 0) {
                  if (unmapped.length > 0) {
                      setImportReview({
                          isKnxProj: true,
                          proposal_path: result.proposal_path,
                          summary: summary,
                          devices: proposedDevices,
                          duplicates: duplicates,
                          unmapped: unmapped,
                          conflicts: duplicates.map(d => {
                              const devices = Array.isArray(d.devices) ? d.devices.join(', ') : 'unknown devices';
                              return `GA '${d.group_address || 'unknown'}' is shared between devices ${devices}`;
                          })
                      });
                  } else {
                      showDialog(
                          "KNXProj Parse Result",
                          "Parser chạy xong nhưng chưa ánh xạ được thiết bị logic nào. Có thể file ETS chỉ chứa group addresses hoặc schema chưa được hỗ trợ đầy đủ.",
                          "warning"
                      );
                  }
              } else {
                  setImportReview({
                      isKnxProj: true,
                      proposal_path: result.proposal_path,
                      summary: summary,
                      devices: proposedDevices,
                      duplicates: duplicates,
                      unmapped: unmapped,
                      conflicts: duplicates.map(d => {
                          const devices = Array.isArray(d.devices) ? d.devices.join(', ') : 'unknown devices';
                          return `GA '${d.group_address || 'unknown'}' is shared between devices ${devices}`;
                      })
                  });
              }
          } catch (err) {
              showDialog("KNXProj Parse Error", err.message, "danger");
          } finally {
              setIsSaving(false);
              e.target.value = null; // reset input
          }
          return;
      }

      const reader = new FileReader();
      reader.onload = async (event) => {
          try {
              const text = event.target.result;
              let parsedDevices = [];
              const expectedHeaders = [
                  'device_id', 'name', 'room', 'type',
                  'onoff_ga', 'status_ga', 'brightness_ga', 'brightness_status_ga',
                  'color_ga', 'color_status_ga', 'color_rgb_ga', 'color_temp_ga',
                  'color_temp_status_ga', 'color_temp_min', 'color_temp_max',
                  'temperature_set_ga', 'temperature_status_ga', 'fan_speed_ga',
                  'mode_ga', 'stop_ga', 'position_set_ga', 'position_status_ga',
                  'knx_config_payload', 'aliases', 'role', 'safety_level', 'require_confirm', 'enabled'
              ];

              if (file.name.endsWith('.csv')) {
                  const lines = text.split('\n');
                  const headers = lines[0].split(',').map(h => h.trim().toLowerCase());

                  if (!headers.includes('device_id')) {
                      throw new Error("CSV must have a 'device_id' column");
                  }

                  for (let i = 1; i < lines.length; i++) {
                      if (!lines[i].trim()) continue;
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
                  // JSON format
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
                  collectGasFromDevice(d).forEach(ga => allUsedGAs.add(ga));
              });

              parsedDevices.forEach(d => {
                  if (devices[d.device_id]) {
                      conflicts.push(`Device ID '${d.device_id}' already exists.`);
                  }

                  const deviceGAs = collectGasFromDevice(d);
                  deviceGAs.forEach(ga => {
                      if (!/^\d+\/\d+\/\d+$/.test(ga)) {
                          conflicts.push(`Device '${d.device_id}': GA (${ga}) has invalid KNX format.`);
                      } else if (allUsedGAs.has(ga)) {
                          conflicts.push(`Device '${d.device_id}': GA (${ga}) is already used by an existing device.`);
                      }
                      allUsedGAs.add(ga);
                  });
              });

              setImportReview({ devices: parsedDevices, conflicts });

          } catch (err) {
              showDialog("Import Parse Error", err.message, "danger");
          }
      };
      reader.readAsText(file);
      e.target.value = null; // reset input
  };

  const confirmImport = async (mode) => {
      if (!importReview) return;
      try {
          setIsSaving(true);

          // Ensure each imported device has correct knx_config_payload built from discrete fields
          const devicesToSend = importReview.devices.map(d => {
              const copy = { ...d };
              if (!copy.knx_config_payload || copy.knx_config_payload === '{}') {
                  const caps = buildKnxConfigPayload(copy);
                  copy.knx_config_payload = caps;
              }
              return copy;
          });

          const payload = {
              mode: mode,
              devices: devicesToSend
          };
          const res = await fetch('/api/devices/import', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify(payload)
          });
          if (res.ok) {
              showToast("Import successful! Reloading...", "success");
              await fetch('/api/platform/reload', { method: 'POST' });
              await fetchDevices();
              setImportReview(null);
          } else {
              throw new Error(await res.text());
          }
      } catch (err) {
          showDialog("Import Error", "Import failed: " + err.message, "danger");
      } finally {
          setIsSaving(false);
      }
  };

  return (
    <div className="page-container animate-fade-in flex flex-col h-full max-h-full">
      <header className="flex justify-between items-center mb-8">
        <div>
          <h2 className="text-2xl font-semibold mb-1 text-[var(--text-primary)]">Device Management</h2>
          <p className="text-sm text-[var(--text-secondary)]">Quản lý {Object.keys(devices).length} thiết bị KNX</p>
        </div>
        <div className="flex gap-4">
          <input type="file" id="import-file" className="hidden" accept=".json,.csv,.knxproj" onChange={importDevices} />
          <button className="btn-secondary" onClick={() => document.getElementById('import-file').click()}>
            📥 Import
          </button>
          <button className="btn-secondary" onClick={exportDevices}>
            📤 Export
          </button>
          <button className="btn-primary" onClick={openAddWizard}>
            + Add Device Wizard
          </button>
        </div>
      </header>

      {loading ? (
        <div className="empty-state">
          <div className="skeleton w-32 h-8 mb-4"></div>
          <div>Loading devices...</div>
        </div>
      ) : Object.keys(devices).length === 0 ? (
        <div className="empty-state glass-panel">
          <h3 className="text-xl mb-2 text-white">No Devices Found</h3>
          <p className="text-[var(--text-secondary)]">Import an ETS project or add a device manually to get started.</p>
        </div>
      ) : (
        <div className="flex flex-col gap-4 flex-1 overflow-hidden" style={{ display: 'flex', flexDirection: 'column', flex: 1, minHeight: 0 }}>
          {/* Filters */}
          <div className="flex gap-4 mb-2">
            <input
              type="text"
              placeholder="Search devices..."
              className="input-primary"
              style={{ maxWidth: '300px' }}
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
            />
          </div>

          <div className="glass-panel overflow-hidden flex-1 flex flex-col" style={{ padding: '0', borderRadius: '16px', display: 'flex', flexDirection: 'column', flex: 1, minHeight: 0 }}>
            <div className="overflow-x-auto overflow-y-auto flex-1 custom-scrollbar" style={{ flex: 1 }}>
              <table className="w-full text-left whitespace-nowrap" style={{ fontSize: '15px' }}>
                <thead className="sticky top-0 z-10 shadow-sm" style={{ backgroundColor: '#13151a' }}>
                  <tr>
                    <th className="font-medium uppercase tracking-wider text-[var(--text-secondary)]" style={{ padding: '16px', fontSize: '13px' }}>Device ID</th>
                    <th className="font-medium uppercase tracking-wider text-[var(--text-secondary)]" style={{ padding: '16px', fontSize: '13px' }}>Type</th>
                    <th className="font-medium uppercase tracking-wider text-[var(--text-secondary)]" style={{ padding: '16px', fontSize: '13px' }}>Group Addresses</th>
                    <th className="font-medium uppercase tracking-wider text-[var(--text-secondary)]" style={{ padding: '16px', fontSize: '13px' }}>Status</th>
                    <th className="font-medium uppercase tracking-wider text-[var(--text-secondary)]" style={{ padding: '16px', fontSize: '13px' }}>Source</th>
                    <th className="font-medium uppercase tracking-wider text-[var(--text-secondary)] text-right" style={{ padding: '16px', fontSize: '13px' }}>Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[var(--border)]">
                  {Object.entries(devices).filter(([key]) => key.toLowerCase().includes(searchQuery.toLowerCase())).map(([key, dev]) => (
                    <tr key={key} className="hover:bg-[var(--bg-hover)] transition-colors">
                    <td className="font-medium text-[var(--text-primary)]" style={{ padding: '16px' }}>{key}</td>
                    <td style={{ padding: '16px' }}>
                      <span className="badge badge-online" style={{ padding: '4px 10px', fontSize: '13px' }}>
                        {dev.type || 'light'}
                      </span>
                    </td>
                    <td className="text-[var(--text-secondary)]" style={{ padding: '16px', fontSize: '14px', lineHeight: '1.5' }}>
                      ON/OFF: <span className="text-white font-medium">{dev.onoff_ga || 'N/A'}</span><br/>
                      Status: <span className="text-white font-medium">{dev.status_ga || 'N/A'}</span>
                    </td>
                    <td style={{ padding: '16px' }}>
                      {dev.disabled ? (
                        <span className="badge badge-offline">Disabled</span>
                      ) : (
                        <span className="badge badge-online">Active</span>
                      )}
                    </td>
                    <td style={{ padding: '16px' }}>
                      {dev.knx_config_payload ? (
                        <span className="badge" style={{ background: 'var(--accent-soft)', color: 'var(--accent)', padding: '4px 10px', fontSize: '13px' }}>ETS6</span>
                      ) : (
                        <span className="badge" style={{ background: 'var(--bg-hover)', color: 'var(--text-secondary)', padding: '4px 10px', fontSize: '13px' }}>Manual</span>
                      )}
                    </td>
                    <td className="text-right" style={{ padding: '16px' }}>
                      <div className="relative inline-block group">
                        <button className="btn-secondary px-2 py-1">⋮</button>
                        <div className="absolute right-0 mt-2 w-32 bg-[var(--bg-elevated)] border border-[var(--border)] rounded-lg shadow-xl opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all z-50 flex flex-col py-1">
                          <a href={`/devices/${key}`} className="px-4 py-2 text-sm text-left hover:bg-[var(--bg-hover)] text-white text-decoration-none">🔍 Details</a>
                          <button className="px-4 py-2 text-sm text-left hover:bg-[var(--bg-hover)] text-white" onClick={() => openEditWizard(key, dev)}>✏️ Edit</button>
                          <button className="px-4 py-2 text-sm text-left hover:bg-[var(--bg-hover)] text-white" onClick={() => duplicateDevice(key, dev)}>📋 Duplicate</button>
                          <div className="border-t border-[var(--border)] my-1"></div>
                          <button className="px-4 py-2 text-sm text-left hover:bg-[var(--bg-hover)] text-[var(--danger)]" onClick={() => handleAction('delete', { device_id: key })}>🗑️ Delete</button>
                        </div>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
        </div>
      )}

      {/* IMPORT REVIEW MODAL */}
      {importReview && !importReview.isKnxProj && (
          <div className="dialog-overlay">
             <div className="dialog-content" style={{ width: '600px', maxWidth: '90%', maxHeight: '80vh', overflowY: 'auto' }}>
                 <h3 className="text-xl mb-4 text-[var(--success)]">Review Import ({importReview.devices.length} devices)</h3>

                 {importReview.conflicts.length > 0 && (
                     <div style={{ background: 'rgba(231, 101, 107, 0.1)', border: '1px solid var(--danger)', padding: '12px', borderRadius: 'var(--radius-sm)', marginBottom: '16px' }}>
                         <strong className="text-[var(--danger)] text-sm">⚠️ Conflicts Detected:</strong>
                         <ul className="mt-2 pl-4 text-xs text-[var(--danger)]">
                             {importReview.conflicts.slice(0, 5).map((c, i) => <li key={i}>{c}</li>)}
                             {importReview.conflicts.length > 5 && <li>... and {importReview.conflicts.length - 5} more</li>}
                         </ul>
                     </div>
                 )}

                 <div className="custom-scrollbar" style={{ maxHeight: '300px', overflowY: 'auto', background: 'rgba(0,0,0,0.3)', padding: '12px', borderRadius: 'var(--radius-sm)', marginBottom: '16px' }}>
                    <table className="w-full text-sm text-left">
                        <thead>
                            <tr className="text-[var(--text-secondary)]">
                                <th className="pb-2">Device ID</th>
                                <th className="pb-2">Type</th>
                                <th className="pb-2">ON/OFF GA</th>
                            </tr>
                        </thead>
                        <tbody>
                            {importReview.devices.map((d, i) => (
                                <tr key={i} className="border-t border-[var(--border)]">
                                    <td className="py-2" style={{ color: devices[d.device_id] ? 'var(--danger)' : 'var(--success)' }}>{d.device_id}</td>
                                    <td className="py-2">{d.type || 'light'}</td>
                                    <td className="py-2">{d.onoff_ga}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                 </div>

                 <div className="flex justify-between gap-3 mt-4">
                     <button onClick={() => setImportReview(null)} className="btn-secondary">Cancel</button>
                     <div className="flex gap-3">
                         <button onClick={() => confirmImport('skip')} disabled={isSaving} className="btn-secondary">Skip</button>
                         <button onClick={() => confirmImport('overwrite')} disabled={isSaving} className="btn-secondary" style={{ color: 'var(--danger)', borderColor: 'var(--danger)' }}>Overwrite</button>
                         <button onClick={() => confirmImport('rename')} disabled={isSaving} className="btn-primary">Rename</button>
                     </div>
                 </div>
             </div>
          </div>
      )}

      {/* KNXPROJ IMPORT REVIEW MODAL */}
      {importReview && importReview.isKnxProj && (
          <div className="dialog-overlay">
             <div className="dialog-content" style={{ width: '800px', maxWidth: '95%', maxHeight: '90vh', display: 'flex', flexDirection: 'column' }}>

                 <div style={{ padding: '16px 0' }} className="border-b border-[var(--border)] flex justify-between items-center">
                     <h3 className="text-xl m-0 text-[var(--success)] font-semibold flex items-center gap-2">
                         <span>📥 Review ETS Import:</span>
                         <span className="text-sm font-normal text-[var(--text-secondary)]">({importReview.summary.total_devices} devices parsed)</span>
                     </h3>
                     <button onClick={() => setImportReview(null)} className="text-2xl text-[var(--text-secondary)] hover:text-white leading-none">&times;</button>
                 </div>

                 <div className="flex-1 custom-scrollbar" style={{ overflowY: 'auto', padding: '16px 0' }}>

                     <div className="grid grid-cols-4 gap-4 mb-6">
                         <div style={{ background: 'rgba(255,255,255,0.05)', padding: '12px', borderRadius: 'var(--radius-sm)' }}>
                             <span className="text-xs text-[var(--text-secondary)] block">Total Devices</span>
                             <strong className="text-xl">{importReview.summary.total_devices}</strong>
                         </div>
                         <div style={{ background: 'rgba(16, 185, 129, 0.1)', padding: '12px', borderRadius: 'var(--radius-sm)', border: '1px solid rgba(16, 185, 129, 0.2)' }}>
                             <span className="text-xs text-[var(--text-secondary)] block">Ready to Import</span>
                             <strong className="text-xl text-[var(--success)]">{importReview.summary.ready}</strong>
                         </div>
                         <div style={{ background: 'rgba(245, 158, 11, 0.1)', padding: '12px', borderRadius: 'var(--radius-sm)', border: '1px solid rgba(245, 158, 11, 0.2)' }}>
                             <span className="text-xs text-[var(--text-secondary)] block">Needs Review</span>
                             <strong className="text-xl text-[var(--warning)]">{importReview.summary.needs_review}</strong>
                         </div>
                         <div style={{ background: 'rgba(239, 68, 68, 0.1)', padding: '12px', borderRadius: 'var(--radius-sm)', border: '1px solid rgba(239, 68, 68, 0.2)' }}>
                             <span className="text-xs text-[var(--text-secondary)] block">Missing Info</span>
                             <strong className="text-xl text-[var(--danger)]">{importReview.summary.missing_info}</strong>
                         </div>
                     </div>

                     {importReview.conflicts.length > 0 && (
                         <div style={{ background: 'rgba(231, 101, 107, 0.1)', border: '1px solid var(--danger)', padding: '12px', borderRadius: 'var(--radius-sm)', marginBottom: '16px' }}>
                             <strong className="text-[var(--danger)] text-sm">⚠️ Group Address Collisions Detected:</strong>
                             <ul className="mt-2 pl-4 text-xs text-[var(--danger)] list-disc">
                                 {importReview.conflicts.slice(0, 5).map((c, i) => <li key={i}>{c}</li>)}
                                 {importReview.conflicts.length > 5 && <li>... and {importReview.conflicts.length - 5} more</li>}
                             </ul>
                         </div>
                     )}

                     <div className="flex gap-6 mb-6 p-4 rounded bg-[rgba(255,255,255,0.02)] border border-[var(--border)]">
                         <label className="flex items-center gap-2 text-sm cursor-pointer select-none">
                             <input
                                 type="checkbox"
                                 checked={importReview.includeNeedsReview || false}
                                 onChange={(e) => setImportReview({ ...importReview, includeNeedsReview: e.target.checked })}
                                 className="cursor-pointer"
                             />
                             <span>Include devices needing review (<code>needs_review</code>)</span>
                         </label>

                         <label className="flex items-center gap-2 text-sm cursor-pointer select-none">
                             <input
                                 type="checkbox"
                                 checked={importReview.allowDuplicates || false}
                                 onChange={(e) => setImportReview({ ...importReview, allowDuplicates: e.target.checked })}
                                 className="cursor-pointer"
                             />
                             <span className="text-[var(--warning)]">Allow duplicate group addresses (force import)</span>
                         </label>
                     </div>

                     <h4 className="text-sm font-semibold mb-2">Proposed Devices Preview</h4>
                     <div style={{ background: 'rgba(0,0,0,0.3)', padding: '12px', borderRadius: 'var(--radius-sm)', marginBottom: '16px' }}>
                        <table className="w-full text-sm text-left">
                            <thead>
                                <tr className="text-[var(--text-secondary)] border-b border-[var(--border)]">
                                    <th className="pb-2">Physical Addr</th>
                                    <th className="pb-2">Logical Name</th>
                                    <th className="pb-2">Room</th>
                                    <th className="pb-2">Type</th>
                                    <th className="pb-2">Status</th>
                                    <th className="pb-2">Confidence</th>
                                </tr>
                            </thead>
                            <tbody>
                                 {importReview.devices.length === 0 ? (
                                     <tr>
                                         <td colSpan="6" className="py-4 text-center text-[var(--text-secondary)]">
                                             Không có thiết bị logic nào được đề xuất bóc tách.
                                         </td>
                                     </tr>
                                 ) : (
                                     importReview.devices.map((d, i) => (
                                         <tr key={i} className="border-b border-[var(--border)] hover:bg-[rgba(255,255,255,0.02)]">
                                             <td className="py-2 text-[var(--accent)] font-mono">{d.source.physical_address}</td>
                                             <td className="py-2 font-medium">{d.name}</td>
                                             <td className="py-2">{d.room}</td>
                                             <td className="py-2"><span className="px-2 py-0.5 rounded text-xs" style={{ background: 'rgba(255,255,255,0.08)' }}>{d.type}</span></td>
                                             <td className="py-2">
                                                 <span className="px-2 py-0.5 rounded text-xs font-semibold" style={{
                                                     background: d.status === 'ready' ? 'rgba(16, 185, 129, 0.2)' : (d.status === 'needs_review' ? 'rgba(245, 158, 11, 0.2)' : 'rgba(239, 68, 68, 0.2)'),
                                                     color: d.status === 'ready' ? 'var(--success)' : (d.status === 'needs_review' ? 'var(--warning)' : 'var(--danger)')
                                                 }}>
                                                     {d.status}
                                                 </span>
                                             </td>
                                             <td className="py-2 font-mono">{(d.confidence * 100).toFixed(0)}%</td>
                                         </tr>
                                     ))
                                 )}
                             </tbody>
                        </table>
                     </div>

                     {importReview.consoleOutput && (
                         <div className="mb-4">
                             <h4 className="text-sm font-semibold mb-2">Dry-run Output Console</h4>
                             <pre className="p-4 rounded text-xs font-mono text-[var(--success)] bg-black overflow-x-auto" style={{ maxHeight: '200px', overflowY: 'auto' }}>
                                 {importReview.consoleOutput}
                             </pre>
                         </div>
                     )}

                 </div>

                 <div className="flex justify-between gap-3 border-t border-[var(--border)] pt-4" style={{ paddingBottom: '16px' }}>
                     <button onClick={() => setImportReview(null)} className="btn-secondary">Cancel</button>
                     <div className="flex gap-3">
                         <button onClick={async () => {
                             try {
                                 const res = await fetch('/api/device-proposals/apply', {
                                     method: 'POST',
                                     headers: { 'Content-Type': 'application/json' },
                                     body: JSON.stringify({
                                         proposal_path: importReview.proposal_path,
                                         confirm: false,
                                         include_needs_review: importReview.includeNeedsReview || false,
                                         allow_duplicates: importReview.allowDuplicates || false
                                     })
                                 });
                                 const output = await res.json();
                                 setImportReview({
                                     ...importReview,
                                     consoleOutput: `STDOUT:\n${output.stdout || ''}\n\nSTDERR:\n${output.stderr || ''}`
                                 });
                             } catch (err) {
                                 showDialog("Dry-run Error", err.message, "danger");
                             }
                         }} className="btn-secondary">Test (Dry-run)</button>

                         <button onClick={async () => {
                             if (!confirm("Xác nhận nạp thiết bị vào hệ thống? Thao tác này sẽ ghi đè và cập nhật DB.")) return;
                             try {
                                 setIsSaving(true);
                                 const res = await fetch('/api/device-proposals/apply', {
                                     method: 'POST',
                                     headers: { 'Content-Type': 'application/json' },
                                     body: JSON.stringify({
                                         proposal_path: importReview.proposal_path,
                                         confirm: true,
                                         include_needs_review: importReview.includeNeedsReview || false,
                                         allow_duplicates: importReview.allowDuplicates || false
                                     })
                                 });
                                 const result = await res.json();
                                 if (result.status === 'success') {
                                     showToast("Import successful! Reloading devices...", "success");
                                     await fetchDevices();
                                     setImportReview(null);
                                 } else {
                                     showDialog("Import Error", `Apply failed: ${result.stderr || result.message}`, "danger");
                                 }
                             } catch (err) {
                                 showDialog("Import Error", err.message, "danger");
                             } finally {
                                 setIsSaving(false);
                             }
                         }} className="btn-primary">Apply (Confirm)</button>
                     </div>
                 </div>
             </div>
          </div>
      )}

      {/* WIZARD MODAL */}
      {showWizard && (
        <div className="dialog-overlay">
          <div className="dialog-content" style={{ padding: '0', width: '500px', maxWidth: '90%', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>

            {/* Header */}
            <div style={{ padding: '16px 24px' }} className="border-b border-[var(--border)] flex justify-between items-center">
                <h3 className="text-xl m-0 text-[var(--accent)] font-semibold">
                    {wizardMode === 'add' ? 'Device Wizard' : 'Edit Device Wizard'}
                </h3>
                {wizardStep !== 4 && (
                    <button onClick={() => setShowWizard(false)} className="text-2xl text-[var(--text-secondary)] hover:text-white leading-none">&times;</button>
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
                    <div className="animate-fade-in">
                        <h4 className="mb-4 text-[var(--accent)] font-medium">Step 1: Basic Information</h4>
                        <div className="flex flex-col gap-4">
                            <div>
                                <label className="block mb-2 text-sm text-[var(--text-secondary)]">Device ID</label>
                                <input
                                    className="input-primary"
                                    placeholder="e.g. living_light_1"
                                    value={currentDevice.device_id}
                                    onChange={e => setCurrentDevice({...currentDevice, device_id: e.target.value})}
                                    disabled={wizardMode === 'update'}
                                />
                                {wizardMode === 'update' && <small className="text-[var(--danger)] mt-1 block">Cannot change ID of existing device.</small>}
                            </div>
                            <div>
                                <label style={{ display: 'block', marginBottom: '6px', fontSize: '0.9rem', color: 'var(--text-secondary)' }}>Device Type</label>
                                <select
                                    className="input-primary"
                                    value={currentDevice.type}
                                    onChange={e => setCurrentDevice({...currentDevice, type: e.target.value})}
                                >
                                    <option value="light">Light (Switchable)</option>
                                    <option value="dimmer">Dimmer (Light + Brightness)</option>
                                    <option value="color_light">RGB/Color Light</option>
                                    <option value="ac">HVAC / Air Conditioner</option>
                                    <option value="curtain">Curtain / Window Blind</option>
                                    <option value="appliance">Smart Plug / Appliance</option>
                                    <option value="sensor">Sensor</option>
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
                            {currentDevice.type !== 'sensor' && (
                                <div>
                                    <label style={{ display: 'block', marginBottom: '4px', fontSize: '0.85rem' }}>ON/OFF Address *</label>
                                    <input className="input-primary" placeholder="1/1/1" value={currentDevice.onoff_ga} onChange={e => setCurrentDevice({...currentDevice, onoff_ga: e.target.value})} />
                                </div>
                            )}
                            <div>
                                <label style={{ display: 'block', marginBottom: '4px', fontSize: '0.85rem' }}>{currentDevice.type === 'sensor' ? 'Sensor Value Address *' : 'State/Status Address'}</label>
                                <input className="input-primary" placeholder="1/1/2" value={currentDevice.status_ga} onChange={e => setCurrentDevice({...currentDevice, status_ga: e.target.value})} />
                            </div>

                            {(currentDevice.type === 'dimmer' || currentDevice.type === 'color_light') && (
                                <>
                                    <div>
                                        <label style={{ display: 'block', marginBottom: '4px', fontSize: '0.85rem' }}>Brightness Set Address</label>
                                        <input className="input-primary" placeholder="1/1/3" value={currentDevice.brightness_ga} onChange={e => setCurrentDevice({...currentDevice, brightness_ga: e.target.value})} />
                                    </div>
                                    <div>
                                        <label style={{ display: 'block', marginBottom: '4px', fontSize: '0.85rem' }}>Brightness Status Address</label>
                                        <input className="input-primary" placeholder="1/1/4" value={currentDevice.brightness_status_ga} onChange={e => setCurrentDevice({...currentDevice, brightness_status_ga: e.target.value})} />
                                    </div>
                                </>
                            )}

                            {currentDevice.type === 'color_light' && (
                                <>
                                    <div>
                                        <label style={{ display: 'block', marginBottom: '4px', fontSize: '0.85rem' }}>RGB/HSV Color Address</label>
                                        <input className="input-primary" placeholder="1/1/5" value={currentDevice.color_rgb_ga} onChange={e => setCurrentDevice({...currentDevice, color_rgb_ga: e.target.value})} />
                                    </div>
                                    <div>
                                        <label style={{ display: 'block', marginBottom: '4px', fontSize: '0.85rem' }}>Color Temperature (White) Address</label>
                                        <input className="input-primary" placeholder="1/1/6" value={currentDevice.color_temp_ga} onChange={e => setCurrentDevice({...currentDevice, color_temp_ga: e.target.value})} />
                                    </div>
                                </>
                            )}

                            {currentDevice.type === 'ac' && (
                                <>
                                    <div>
                                        <label style={{ display: 'block', marginBottom: '4px', fontSize: '0.85rem' }}>Temperature Setpoint Address</label>
                                        <input className="input-primary" placeholder="2/1/1" value={currentDevice.temperature_set_ga} onChange={e => setCurrentDevice({...currentDevice, temperature_set_ga: e.target.value})} />
                                    </div>
                                    <div>
                                        <label style={{ display: 'block', marginBottom: '4px', fontSize: '0.85rem' }}>Current Temperature (Sensor) Address</label>
                                        <input className="input-primary" placeholder="2/1/2" value={currentDevice.temperature_status_ga} onChange={e => setCurrentDevice({...currentDevice, temperature_status_ga: e.target.value})} />
                                    </div>
                                    <div style={{ display: 'flex', gap: '12px' }}>
                                        <div style={{ flex: 1 }}>
                                            <label style={{ display: 'block', marginBottom: '4px', fontSize: '0.85rem' }}>Fan Speed Address</label>
                                            <input className="input-primary" placeholder="2/1/3" value={currentDevice.fan_speed_ga} onChange={e => setCurrentDevice({...currentDevice, fan_speed_ga: e.target.value})} />
                                        </div>
                                        <div style={{ flex: 1 }}>
                                            <label style={{ display: 'block', marginBottom: '4px', fontSize: '0.85rem' }}>HVAC Mode Address</label>
                                            <input className="input-primary" placeholder="2/1/4" value={currentDevice.mode_ga} onChange={e => setCurrentDevice({...currentDevice, mode_ga: e.target.value})} />
                                        </div>
                                    </div>
                                </>
                            )}

                            {currentDevice.type === 'curtain' && (
                                <>
                                    <div>
                                        <label style={{ display: 'block', marginBottom: '4px', fontSize: '0.85rem' }}>Stop / Step Address (Crucial)</label>
                                        <input className="input-primary" placeholder="3/1/1" value={currentDevice.stop_ga} onChange={e => setCurrentDevice({...currentDevice, stop_ga: e.target.value})} />
                                    </div>
                                    <div style={{ display: 'flex', gap: '12px' }}>
                                        <div style={{ flex: 1 }}>
                                            <label style={{ display: 'block', marginBottom: '4px', fontSize: '0.85rem' }}>Position Set Address (%)</label>
                                            <input className="input-primary" placeholder="3/1/2" value={currentDevice.position_set_ga} onChange={e => setCurrentDevice({...currentDevice, position_set_ga: e.target.value})} />
                                        </div>
                                        <div style={{ flex: 1 }}>
                                            <label style={{ display: 'block', marginBottom: '4px', fontSize: '0.85rem' }}>Position Status Address</label>
                                            <input className="input-primary" placeholder="3/1/3" value={currentDevice.position_status_ga} onChange={e => setCurrentDevice({...currentDevice, position_status_ga: e.target.value})} />
                                        </div>
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
                            <button onClick={() => setWizardStep(wizardStep - 1)} className="btn-secondary">Back</button>
                        ) : <div></div>}

                        {wizardStep === 3 ? (
                            <button onClick={saveAndDeploy} disabled={isSaving} className="btn-primary" style={{ background: '#10b981', color: 'white' }}>
                                {isSaving ? 'Deploying...' : 'Save & Deploy'}
                            </button>
                        ) : (
                            <button onClick={nextStep} className="btn-primary">Next</button>
                        )}
                    </>
                )}
            </div>

          </div>
        </div>
      )}
    </div>
  );
}
