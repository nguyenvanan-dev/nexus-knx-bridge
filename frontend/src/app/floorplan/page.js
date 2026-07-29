'use client';
import { useState, useRef, useEffect, useCallback } from 'react';
import Link from 'next/link';

// ── Icon Components ────────────────────────────────────────────
const ICONS = {
  light: ({ on, brightness }) => (
    <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" className="w-full h-full">
      <circle cx="12" cy="12" r="5" fill={on ? `hsl(45,100%,${40 + (brightness || 80) * 0.4}%)` : '#374151'} />
      {on && [...Array(8)].map((_, i) => (
        <line key={i}
          x1="12" y1="12"
          x2={12 + 9 * Math.cos((i * 45 * Math.PI) / 180)}
          y2={12 + 9 * Math.sin((i * 45 * Math.PI) / 180)}
          stroke="hsl(45,100%,70%)" strokeWidth="1.5" strokeLinecap="round"
          opacity={0.6 + (brightness || 80) * 0.004}
        />
      ))}
      {!on && <circle cx="12" cy="12" r="5" stroke="#6B7280" strokeWidth="1.5" fill="none" />}
    </svg>
  ),
  switch: ({ on }) => (
    <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" className="w-full h-full">
      <rect x="4" y="7" width="16" height="10" rx="5" fill={on ? '#10B981' : '#374151'} />
      <circle cx={on ? 15 : 9} cy="12" r="3.5" fill="white" />
    </svg>
  ),
  curtain: ({ position }) => {
    const pos = position ?? 50;
    return (
      <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" className="w-full h-full">
        <line x1="2" y1="3" x2="22" y2="3" stroke="#9CA3AF" strokeWidth="1.5" strokeLinecap="round" />
        <rect x="3" y="3" width={8 - pos * 0.06} height="17" rx="1" fill="#6366F1" opacity="0.8" />
        <rect x={21 - (8 - pos * 0.06)} y="3" width={8 - pos * 0.06} height="17" rx="1" fill="#6366F1" opacity="0.8" />
      </svg>
    );
  },
  ac: ({ on, temperature }) => (
    <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" className="w-full h-full">
      <rect x="2" y="6" width="20" height="12" rx="3" fill={on ? '#0EA5E9' : '#374151'} />
      <rect x="4" y="10" width="12" height="4" rx="1" fill={on ? '#7DD3FC' : '#4B5563'} />
      {on && <text x="18" y="14" fontSize="5" fill="white" textAnchor="middle">{temperature || '24'}°</text>}
      {[...Array(3)].map((_, i) => (
        <line key={i} x1={6 + i * 3} y1="16" x2={6 + i * 3} y2="20" stroke={on ? '#7DD3FC' : '#4B5563'} strokeWidth="1" strokeLinecap="round" />
      ))}
    </svg>
  ),
  sensor: ({ state }) => (
    <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" className="w-full h-full">
      <circle cx="12" cy="12" r="8" stroke="#8B5CF6" strokeWidth="1.5" fill="#1F2937" />
      <circle cx="12" cy="12" r="3" fill="#8B5CF6" />
      <text x="12" y="21" fontSize="4" fill="#8B5CF6" textAnchor="middle">{state || '?'}</text>
    </svg>
  ),
  speaker: ({ on }) => (
    <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" className="w-full h-full">
      <rect x="3" y="8" width="8" height="8" rx="1" fill={on ? '#EC4899' : '#374151'} />
      {on && <>
        <path d="M15 8 Q19 12 15 16" stroke="#EC4899" strokeWidth="1.5" fill="none" strokeLinecap="round" />
        <path d="M17 5 Q23 12 17 19" stroke="#EC4899" strokeWidth="1" fill="none" strokeLinecap="round" opacity="0.6" />
      </>}
      <polygon points="11,8 16,5 16,19 11,16" fill={on ? '#F472B6' : '#4B5563'} />
    </svg>
  ),
};

// ── Device Icon Overlay ────────────────────────────────────────
function DeviceIcon({ device, onControl, editMode, onDragEnd, containerRef }) {
  const state = device.current_state || {};
  const isOn = state.state === 'ON' || Number(state.brightness) > 0;
  const brightness = state.brightness || (isOn ? 80 : 0);
  const Icon = ICONS[device.icon_type] || ICONS.light;

  const handleMouseDown = useCallback((e) => {
    if (!editMode) return;
    e.preventDefault();
    const container = containerRef.current;
    if (!container) return;
    const rect = container.getBoundingClientRect();

    const onMove = (me) => {
      const x = ((me.clientX - rect.left) / rect.width) * 100;
      const y = ((me.clientY - rect.top) / rect.height) * 100;
      onDragEnd?.(device.device_id, Math.max(2, Math.min(98, x)), Math.max(2, Math.min(98, y)));
    };
    const onUp = () => {
      document.removeEventListener('mousemove', onMove);
      document.removeEventListener('mouseup', onUp);
    };
    document.addEventListener('mousemove', onMove);
    document.addEventListener('mouseup', onUp);
  }, [editMode, device.device_id, containerRef, onDragEnd]);

  return (
    <div
      className={`absolute flex flex-col items-center group transition-transform ${editMode ? 'cursor-move' : 'cursor-pointer'}`}
      style={{
        left: `${device.x_percent}%`,
        top: `${device.y_percent}%`,
        transform: 'translate(-50%, -50%)',
        zIndex: 10,
      }}
      onMouseDown={handleMouseDown}
      onClick={() => !editMode && onControl?.(device)}
    >
      {/* Glow effect when ON */}
      {isOn && (
        <div className="absolute inset-0 rounded-full animate-pulse"
          style={{
            width: 52, height: 52, top: -2, left: -2,
            background: 'radial-gradient(circle, rgba(251,191,36,0.35) 0%, transparent 70%)',
            pointerEvents: 'none',
          }}
        />
      )}

      {/* Icon */}
      <div
        className={`w-10 h-10 rounded-full border-2 p-1.5 shadow-lg backdrop-blur-sm transition-all duration-300
          ${isOn
            ? 'border-amber-400/70 bg-gray-900/80 shadow-amber-500/30'
            : 'border-gray-600/50 bg-gray-900/70'
          }
          ${editMode ? 'border-blue-400 ring-2 ring-blue-400/30' : 'group-hover:scale-110 group-hover:border-amber-400/50'}
        `}
      >
        <Icon on={isOn} brightness={brightness} position={state.position} temperature={state.temperature} state={state.state} />
      </div>

      {/* Label */}
      <div className={`mt-1 text-xs font-medium px-1.5 py-0.5 rounded backdrop-blur-sm whitespace-nowrap
        ${isOn ? 'text-amber-300 bg-gray-900/80' : 'text-gray-400 bg-gray-900/60'}`}>
        {device.label || device.device_name}
      </div>

      {/* State badge */}
      {!editMode && (
        <div className={`absolute -top-1 -right-1 text-[9px] font-bold px-1 py-0.5 rounded-full
          ${isOn ? 'bg-green-500 text-white' : 'bg-gray-700 text-gray-400'}`}>
          {state.state || '?'}
        </div>
      )}
    </div>
  );
}

// ── Quick Control Popup ────────────────────────────────────────
function ControlPopup({ device, onClose, onAction }) {
  if (!device) return null;
  const state = device.current_state || {};
  const isOn = state.state === 'ON';

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center" onClick={onClose}>
      <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" />
      <div
        className="relative z-10 w-80 bg-gray-900 border border-gray-700 rounded-2xl p-5 shadow-2xl"
        onClick={e => e.stopPropagation()}
      >
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-white font-semibold text-lg">{device.label || device.device_name}</h3>
            <p className="text-gray-400 text-xs mt-0.5">{device.device_id} • {device.icon_type}</p>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-white p-1">✕</button>
        </div>

        {/* ON/OFF */}
        <div className="flex gap-3 mb-4">
          <button
            onClick={() => onAction(device.device_id, 'on')}
            className={`flex-1 py-3 rounded-xl font-semibold transition-all ${isOn ? 'bg-amber-500 text-white shadow-lg shadow-amber-500/30' : 'bg-gray-800 text-gray-400 hover:bg-gray-700'}`}
          >
            ☀️ ON
          </button>
          <button
            onClick={() => onAction(device.device_id, 'off')}
            className={`flex-1 py-3 rounded-xl font-semibold transition-all ${!isOn ? 'bg-gray-600 text-white' : 'bg-gray-800 text-gray-400 hover:bg-gray-700'}`}
          >
            🌙 OFF
          </button>
        </div>

        {/* Brightness slider if applicable */}
        {(device.icon_type === 'light' || device.device_type === 'light') && (
          <div className="space-y-2">
            <label className="text-gray-400 text-xs">Brightness</label>
            <input
              type="range" min="0" max="100"
              defaultValue={state.brightness || 80}
              className="w-full accent-amber-400"
              onChange={e => onAction(device.device_id, 'brightness', Number(e.target.value))}
            />
          </div>
        )}

        {/* Status */}
        <div className="mt-4 p-3 bg-gray-800/60 rounded-xl text-xs text-gray-400">
          <div className="flex justify-between"><span>State</span><span className={isOn ? 'text-green-400' : 'text-gray-500'}>{state.state || 'UNKNOWN'}</span></div>
          {state.source && <div className="flex justify-between mt-1"><span>Source</span><span>{state.source}</span></div>}
          {state.last_update && <div className="flex justify-between mt-1"><span>Updated</span><span>{Math.round(state.age_seconds || 0)}s ago</span></div>}
        </div>
      </div>
    </div>
  );
}

// ── Main Floor Plan Page ───────────────────────────────────────
export default function FloorPlanPage() {
  const [plans, setPlans] = useState([]);
  const [activePlan, setActivePlan] = useState(null);
  const [planData, setPlanData] = useState(null);
  const [editMode, setEditMode] = useState(false);
  const [selectedDevice, setSelectedDevice] = useState(null);
  const [availableDevices, setAvailableDevices] = useState([]);
  const [showAddDevice, setShowAddDevice] = useState(false);
  const [showNewPlan, setShowNewPlan] = useState(false);
  const [newPlanName, setNewPlanName] = useState('');
  const [dragging, setDragging] = useState(null);
  const [saving, setSaving] = useState(false);
  const [uploading, setUploading] = useState(false);
  const containerRef = useRef(null);
  const fileRef = useRef(null);
  const planFileRef = useRef(null);

  // Load plans
  useEffect(() => {
    fetch('/api/floorplan/plans').then(r => r.json()).then(d => {
      setPlans(d.plans || []);
      if (d.plans?.length > 0 && !activePlan) setActivePlan(d.plans[0].plan_id);
    });
    fetch('/api/devices').then(r => r.json()).then(d => setAvailableDevices(d.devices || []));
  }, []);

  // Load plan details + SSE for realtime state
  useEffect(() => {
    if (!activePlan) return;
    const load = () => fetch(`/api/floorplan/plans/${activePlan}`).then(r => r.json()).then(setPlanData);
    load();

    // SSE for realtime state updates
    const es = new EventSource('/api/events/stream');
    es.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data);
        if (data.device_id && data.state !== undefined) {
          setPlanData(prev => {
            if (!prev) return prev;
            return {
              ...prev,
              devices: prev.devices.map(d =>
                d.device_id === data.device_id
                  ? { ...d, current_state: { ...d.current_state, state: data.state, source: data.source } }
                  : d
              )
            };
          });
        }
      } catch (err) { /* ignore */ }
    };
    return () => es.close();
  }, [activePlan]);

  const handleDragEnd = useCallback((deviceId, x, y) => {
    setPlanData(prev => {
      if (!prev) return prev;
      return {
        ...prev,
        devices: prev.devices.map(d => d.device_id === deviceId ? { ...d, x_percent: x, y_percent: y } : d)
      };
    });
  }, []);

  const handleControl = async (device) => {
    setSelectedDevice(device);
  };

  const handleAction = async (deviceId, action, value) => {
    await fetch('/api/devices/control', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ device_id: deviceId, action, value }),
    });
  };

  const handleSaveLayout = async () => {
    if (!planData) return;
    setSaving(true);
    await fetch(`/api/floorplan/plans/${activePlan}/devices`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ devices: planData.devices.map(d => ({ device_id: d.device_id, x_percent: d.x_percent, y_percent: d.y_percent, icon_type: d.icon_type, label: d.label })) }),
    });
    setSaving(false);
    setEditMode(false);
  };

  const handleUploadImage = async (e) => {
    const file = e.target.files?.[0];
    if (!file || !activePlan) return;
    setUploading(true);
    const fd = new FormData();
    fd.append('file', file);
    const res = await fetch(`/api/floorplan/upload/${activePlan}`, { method: 'POST', body: fd });
    const data = await res.json();
    if (data.ok) {
      setPlanData(prev => prev ? { ...prev, plan: { ...prev.plan, image_path: data.image_path } } : prev);
    }
    setUploading(false);
  };

  const handleAddDeviceToMap = async (deviceId, iconType) => {
    if (!planData) return;
    const reg = availableDevices.find(d => d.device_id === deviceId);
    const newDevice = {
      device_id: deviceId,
      x_percent: 50,
      y_percent: 50,
      icon_type: iconType || reg?.type || 'light',
      label: reg?.name || deviceId,
      device_name: reg?.name || deviceId,
      device_type: reg?.type || 'light',
      current_state: { state: 'UNKNOWN' },
    };
    setPlanData(prev => ({ ...prev, devices: [...(prev?.devices || []), newDevice] }));
    setShowAddDevice(false);
  };

  const handleRemoveDevice = (deviceId) => {
    setPlanData(prev => ({ ...prev, devices: prev.devices.filter(d => d.device_id !== deviceId) }));
  };

  const handleCreatePlan = async () => {
    if (!newPlanName.trim()) return;
    const res = await fetch('/api/floorplan/plans', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: newPlanName }),
    });
    const data = await res.json();
    if (data.ok) {
      setPlans(prev => [...prev, { plan_id: data.plan_id, name: newPlanName }]);
      setActivePlan(data.plan_id);
      setNewPlanName('');
      setShowNewPlan(false);
    }
  };

  const imageSrc = planData?.plan?.image_path;

  return (
    <div className="min-h-screen bg-gray-950 text-white flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-gray-800 bg-gray-900/80 backdrop-blur-sm">
        <div className="flex items-center gap-4">
          <Link href="/" className="text-gray-400 hover:text-white transition-colors">← Back</Link>
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-cyan-400 flex items-center justify-center text-sm">🏠</div>
            <h1 className="text-xl font-bold bg-gradient-to-r from-blue-400 to-cyan-300 bg-clip-text text-transparent">
              Digital Twin
            </h1>
          </div>

          {/* Plan tabs */}
          <div className="flex items-center gap-1 ml-4">
            {plans.map(p => (
              <button
                key={p.plan_id}
                onClick={() => { setActivePlan(p.plan_id); setEditMode(false); }}
                className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-all ${activePlan === p.plan_id ? 'bg-blue-600 text-white' : 'bg-gray-800 text-gray-400 hover:bg-gray-700'}`}
              >
                {p.name}
              </button>
            ))}
            <button onClick={() => setShowNewPlan(true)} className="px-3 py-1.5 rounded-lg text-sm text-gray-400 hover:bg-gray-800 transition-colors">+ Plan</button>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {editMode && (
            <>
              <button onClick={() => setShowAddDevice(true)} className="px-4 py-2 bg-green-600/20 text-green-400 border border-green-600/30 rounded-lg text-sm hover:bg-green-600/30 transition-colors">
                + Add Device
              </button>
              <button onClick={() => fileRef.current?.click()} className="px-4 py-2 bg-blue-600/20 text-blue-400 border border-blue-600/30 rounded-lg text-sm hover:bg-blue-600/30 transition-colors">
                {uploading ? '...' : '📷 Upload Image'}
              </button>
              <button onClick={handleSaveLayout} disabled={saving} className="px-4 py-2 bg-green-600 text-white rounded-lg text-sm font-semibold hover:bg-green-500 transition-colors disabled:opacity-50">
                {saving ? 'Saving...' : '💾 Save'}
              </button>
              <button onClick={() => setEditMode(false)} className="px-4 py-2 bg-gray-700 text-gray-300 rounded-lg text-sm hover:bg-gray-600 transition-colors">
                Cancel
              </button>
            </>
          )}
          {!editMode && (
            <button onClick={() => setEditMode(true)} className="px-4 py-2 bg-gray-800 text-gray-300 border border-gray-700 rounded-lg text-sm hover:bg-gray-700 transition-colors">
              ✏️ Edit Layout
            </button>
          )}
          <input ref={fileRef} type="file" accept="image/*" className="hidden" onChange={handleUploadImage} />
        </div>
      </div>

      {/* Stats bar */}
      {planData && !editMode && (
        <div className="flex items-center gap-6 px-6 py-2 bg-gray-900/50 border-b border-gray-800/50 text-xs">
          {['ON', 'OFF', 'UNKNOWN'].map(s => {
            const cnt = (planData.devices || []).filter(d => (d.current_state?.state || 'UNKNOWN') === s).length;
            return (
              <div key={s} className="flex items-center gap-1.5">
                <div className={`w-2 h-2 rounded-full ${s === 'ON' ? 'bg-green-400' : s === 'OFF' ? 'bg-gray-600' : 'bg-yellow-600'}`} />
                <span className="text-gray-400">{s}: <span className="text-white font-medium">{cnt}</span></span>
              </div>
            );
          })}
          <div className="ml-auto text-gray-500">🔴 Live</div>
        </div>
      )}

      {/* Main canvas */}
      <div className="flex-1 relative overflow-hidden p-4">
        {/* Edit mode: device sidebar */}
        {editMode && planData && (
          <div className="absolute left-4 top-4 bottom-4 w-52 bg-gray-900/90 border border-gray-700 rounded-xl z-20 overflow-y-auto">
            <div className="p-3 border-b border-gray-700">
              <p className="text-xs text-gray-400 font-medium">PLACED DEVICES</p>
            </div>
            {(planData.devices || []).map(d => (
              <div key={d.device_id} className="flex items-center gap-2 p-2 hover:bg-gray-800/50 transition-colors">
                <div className="w-5 h-5 flex-shrink-0">
                  {(() => { const I = ICONS[d.icon_type] || ICONS.light; return <I on={d.current_state?.state === 'ON'} />; })()}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="text-xs text-white truncate">{d.label || d.device_name}</div>
                  <div className="text-[10px] text-gray-500">{d.icon_type}</div>
                </div>
                <button onClick={() => handleRemoveDevice(d.device_id)} className="text-red-500 hover:text-red-400 text-xs px-1">✕</button>
              </div>
            ))}
          </div>
        )}

        {/* Floor plan image + device overlays */}
        <div
          ref={containerRef}
          className={`relative h-full rounded-2xl overflow-hidden border ${editMode ? 'border-blue-500/40 ml-56' : 'border-gray-800/50'}`}
          style={{ background: imageSrc ? 'transparent' : 'radial-gradient(ellipse at center, #1a2035 0%, #0d1117 100%)' }}
        >
          {imageSrc ? (
            <img src={imageSrc} alt="Floor Plan" className="w-full h-full object-contain" draggable={false} />
          ) : (
            <div className="absolute inset-0 flex flex-col items-center justify-center">
              {/* Grid background when no image */}
              <div className="absolute inset-0 opacity-10"
                style={{ backgroundImage: 'linear-gradient(#334155 1px, transparent 1px), linear-gradient(90deg, #334155 1px, transparent 1px)', backgroundSize: '40px 40px' }} />
              <div className="text-center z-10">
                <div className="text-6xl mb-4">🏠</div>
                <p className="text-gray-400 text-lg font-medium mb-2">No floor plan image</p>
                <p className="text-gray-500 text-sm mb-6">Click <strong>Edit Layout</strong> then <strong>Upload Image</strong> to add your floor plan</p>
                <button onClick={() => { setEditMode(true); setTimeout(() => fileRef.current?.click(), 100); }}
                  className="px-6 py-3 bg-blue-600 text-white rounded-xl font-semibold hover:bg-blue-500 transition-colors">
                  📷 Upload Floor Plan
                </button>
              </div>
            </div>
          )}

          {/* Device overlays */}
          {(planData?.devices || []).map(device => (
            <DeviceIcon
              key={device.device_id}
              device={device}
              editMode={editMode}
              onControl={handleControl}
              onDragEnd={handleDragEnd}
              containerRef={containerRef}
            />
          ))}

          {/* Edit mode hint */}
          {editMode && (
            <div className="absolute bottom-4 left-1/2 -translate-x-1/2 bg-blue-600/90 text-white text-xs px-4 py-2 rounded-full backdrop-blur-sm">
              Drag device icons to reposition • Click &quot;+&quot; to add devices
            </div>
          )}
        </div>
      </div>

      {/* Control Popup */}
      {selectedDevice && (
        <ControlPopup device={selectedDevice} onClose={() => setSelectedDevice(null)} onAction={handleAction} />
      )}

      {/* Add Device Modal */}
      {showAddDevice && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm" onClick={() => setShowAddDevice(false)}>
          <div className="bg-gray-900 border border-gray-700 rounded-2xl p-5 w-96 max-h-[70vh] flex flex-col" onClick={e => e.stopPropagation()}>
            <h3 className="text-white font-semibold mb-4 flex items-center justify-between">
              Add Device to Map
              <button onClick={() => setShowAddDevice(false)} className="text-gray-400 hover:text-white">✕</button>
            </h3>
            <div className="overflow-y-auto flex-1 space-y-1">
              {availableDevices
                .filter(d => !(planData?.devices || []).some(pd => pd.device_id === d.device_id))
                .map(d => (
                  <button
                    key={d.device_id}
                    onClick={() => handleAddDeviceToMap(d.device_id, d.type)}
                    className="w-full flex items-center gap-3 p-3 rounded-xl hover:bg-gray-800 transition-colors text-left"
                  >
                    <div className="w-8 h-8 flex-shrink-0">
                      {(() => { const I = ICONS[d.type] || ICONS.light; return <I on={false} />; })()}
                    </div>
                    <div>
                      <div className="text-sm text-white font-medium">{d.name}</div>
                      <div className="text-xs text-gray-500">{d.device_id} • {d.room || 'No room'}</div>
                    </div>
                  </button>
                ))
              }
            </div>
          </div>
        </div>
      )}

      {/* New Plan Modal */}
      {showNewPlan && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm" onClick={() => setShowNewPlan(false)}>
          <div className="bg-gray-900 border border-gray-700 rounded-2xl p-5 w-80" onClick={e => e.stopPropagation()}>
            <h3 className="text-white font-semibold mb-4">New Floor Plan</h3>
            <input value={newPlanName} onChange={e => setNewPlanName(e.target.value)}
              placeholder="e.g. Ground Floor, Bedroom..."
              className="w-full bg-gray-800 border border-gray-700 rounded-xl px-4 py-3 text-white text-sm mb-4 outline-none focus:border-blue-500"
              onKeyDown={e => e.key === 'Enter' && handleCreatePlan()}
              autoFocus
            />
            <div className="flex gap-3">
              <button onClick={handleCreatePlan} className="flex-1 py-2.5 bg-blue-600 text-white rounded-xl text-sm font-semibold hover:bg-blue-500">Create</button>
              <button onClick={() => setShowNewPlan(false)} className="flex-1 py-2.5 bg-gray-800 text-gray-400 rounded-xl text-sm hover:bg-gray-700">Cancel</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
