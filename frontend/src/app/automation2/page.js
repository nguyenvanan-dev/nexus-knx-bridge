'use client';
import { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';

// ── Constants ─────────────────────────────────────────────────
const TRIGGER_TYPES = [
  { value: 'device_state', label: '🔌 Device State Change', desc: 'Fires when a device changes state' },
  { value: 'time',         label: '🕐 Scheduled Time',     desc: 'Fires at a specific time each day' },
  { value: 'sun',          label: '🌅 Sunrise / Sunset',   desc: 'Fires relative to sunrise or sunset' },
  { value: 'weather',      label: '🌤️ Weather',           desc: 'Fires on weather changes (temp, rain)' },
  { value: 'system',       label: '⚙️ System Event',       desc: 'Fires on startup, reconnect, etc.' },
];

const CONDITION_TYPES = [
  { value: 'device_state', label: '🔌 Device State' },
  { value: 'time_range',   label: '🕐 Time Range' },
  { value: 'day_of_week',  label: '📅 Day of Week' },
  { value: 'weather',      label: '🌤️ Weather' },
  { value: 'variable',     label: '🔢 Variable' },
];

const ACTION_TYPES = [
  { value: 'control',        label: '🔌 Control Device', color: 'blue' },
  { value: 'activate_scene', label: '🎬 Activate Scene', color: 'purple' },
  { value: 'delay',          label: '⏱️ Wait / Delay',   color: 'gray' },
  { value: 'wait_for',       label: '⏳ Wait for State', color: 'gray' },
  { value: 'set_var',        label: '🔢 Set Variable',   color: 'gray' },
  { value: 'notify',         label: '📢 Send Notification', color: 'green' },
  { value: 'repeat',         label: '🔁 Repeat Block',   color: 'orange' },
  { value: 'if_action',      label: '🔀 Conditional (IF)', color: 'yellow' },
];

const DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
const DAY_VALUES = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun'];
const OPS = ['==', '!=', '>', '<', '>=', '<='];

const emptyRule = () => ({
  name: '',
  description: '',
  enabled: true,
  priority: 50,
  trigger: { type: 'device_state', device_id: '', state: 'ON', op: '==' },
  conditions: null,
  actions: [],
  time_filter: null,
  cooldown_seconds: 5,
  max_runs_per_day: 0,
});

// ── Sub-components ────────────────────────────────────────────
function SectionCard({ title, icon, children, extra }) {
  return (
    <div className="bg-gray-900/60 border border-gray-800 rounded-2xl overflow-hidden">
      <div className="flex items-center justify-between px-5 py-3 border-b border-gray-800 bg-gray-900/40">
        <div className="flex items-center gap-2 text-sm font-semibold text-gray-200">
          <span>{icon}</span><span>{title}</span>
        </div>
        {extra}
      </div>
      <div className="p-5">{children}</div>
    </div>
  );
}

function TriggerEditor({ trigger, onChange, devices }) {
  const ttype = trigger.type;
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
        {TRIGGER_TYPES.map(t => (
          <button
            key={t.value}
            onClick={() => onChange({ type: t.value })}
            className={`p-3 rounded-xl border text-left transition-all ${ttype === t.value
              ? 'border-blue-500 bg-blue-500/10 text-blue-300'
              : 'border-gray-700 bg-gray-800/40 text-gray-400 hover:border-gray-600'}`}
          >
            <div className="text-base mb-1">{t.label.split(' ')[0]}</div>
            <div className="text-xs font-medium">{t.label.slice(t.label.indexOf(' ') + 1)}</div>
          </button>
        ))}
      </div>

      {ttype === 'device_state' && (
        <div className="grid grid-cols-3 gap-3">
          <div className="col-span-2">
            <label className="text-xs text-gray-400 mb-1 block">Device</label>
            <select className="w-full bg-gray-800 border border-gray-700 rounded-xl px-3 py-2.5 text-white text-sm outline-none focus:border-blue-500"
              value={trigger.device_id || ''} onChange={e => onChange({ ...trigger, device_id: e.target.value })}>
              <option value="">— Select device —</option>
              {devices.map(d => <option key={d.device_id} value={d.device_id}>{d.name} ({d.device_id})</option>)}
            </select>
          </div>
          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="text-xs text-gray-400 mb-1 block">Op</label>
              <select className="w-full bg-gray-800 border border-gray-700 rounded-xl px-3 py-2.5 text-white text-sm outline-none focus:border-blue-500"
                value={trigger.op || '=='} onChange={e => onChange({ ...trigger, op: e.target.value })}>
                {OPS.map(o => <option key={o}>{o}</option>)}
              </select>
            </div>
            <div>
              <label className="text-xs text-gray-400 mb-1 block">State/Value</label>
              <input className="w-full bg-gray-800 border border-gray-700 rounded-xl px-3 py-2.5 text-white text-sm outline-none focus:border-blue-500"
                value={trigger.state || ''} placeholder="ON / 25.0"
                onChange={e => onChange({ ...trigger, state: e.target.value })} />
            </div>
          </div>
        </div>
      )}

      {ttype === 'time' && (
        <div className="space-y-3">
          <div className="flex items-center gap-4">
            <div>
              <label className="text-xs text-gray-400 mb-1 block">Fire at</label>
              <input type="time" className="bg-gray-800 border border-gray-700 rounded-xl px-3 py-2.5 text-white text-sm outline-none focus:border-blue-500"
                value={trigger.at || '07:00'} onChange={e => onChange({ ...trigger, at: e.target.value })} />
            </div>
          </div>
          <div>
            <label className="text-xs text-gray-400 mb-1 block">Days (leave empty = every day)</label>
            <div className="flex gap-2 flex-wrap">
              {DAYS.map((d, i) => {
                const val = DAY_VALUES[i];
                const active = (trigger.days || []).includes(val);
                return (
                  <button key={val}
                    onClick={() => {
                      const days = trigger.days || [];
                      onChange({ ...trigger, days: active ? days.filter(x => x !== val) : [...days, val] });
                    }}
                    className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${active ? 'bg-blue-600 text-white' : 'bg-gray-800 text-gray-400 hover:bg-gray-700'}`}
                  >{d}</button>
                );
              })}
            </div>
          </div>
        </div>
      )}

      {ttype === 'sun' && (
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-xs text-gray-400 mb-1 block">Event</label>
            <select className="w-full bg-gray-800 border border-gray-700 rounded-xl px-3 py-2.5 text-white text-sm outline-none focus:border-blue-500"
              value={trigger.event || 'sunset'} onChange={e => onChange({ ...trigger, event: e.target.value })}>
              <option value="sunrise">🌅 Sunrise</option>
              <option value="sunset">🌇 Sunset</option>
            </select>
          </div>
          <div>
            <label className="text-xs text-gray-400 mb-1 block">Offset (minutes, can be negative)</label>
            <input type="number" className="w-full bg-gray-800 border border-gray-700 rounded-xl px-3 py-2.5 text-white text-sm outline-none focus:border-blue-500"
              value={trigger.offset_minutes || 0} placeholder="-30 = 30min before"
              onChange={e => onChange({ ...trigger, offset_minutes: Number(e.target.value) })} />
          </div>
        </div>
      )}

      {ttype === 'weather' && (
        <div className="grid grid-cols-3 gap-3">
          <div>
            <label className="text-xs text-gray-400 mb-1 block">Metric</label>
            <select className="w-full bg-gray-800 border border-gray-700 rounded-xl px-3 py-2.5 text-white text-sm outline-none focus:border-blue-500"
              value={trigger.metric || 'temperature'} onChange={e => onChange({ ...trigger, metric: e.target.value })}>
              <option value="temperature">Temperature (°C)</option>
              <option value="humidity">Humidity (%)</option>
              <option value="condition">Condition (Rain, Clear)</option>
            </select>
          </div>
          <div>
            <label className="text-xs text-gray-400 mb-1 block">Op</label>
            <select className="w-full bg-gray-800 border border-gray-700 rounded-xl px-3 py-2.5 text-white text-sm outline-none focus:border-blue-500"
              value={trigger.op || '=='} onChange={e => onChange({ ...trigger, op: e.target.value })}>
              {OPS.map(o => <option key={o}>{o}</option>)}
            </select>
          </div>
          <div>
            <label className="text-xs text-gray-400 mb-1 block">Value</label>
            <input className="w-full bg-gray-800 border border-gray-700 rounded-xl px-3 py-2.5 text-white text-sm outline-none focus:border-blue-500"
              value={trigger.value || ''} placeholder="e.g. 30 or Rain"
              onChange={e => onChange({ ...trigger, value: e.target.value })} />
          </div>
        </div>
      )}
    </div>
  );
}

function ConditionEditor({ conditions, onChange, devices }) {
  if (!conditions) {
    return (
      <div className="text-center py-6 text-gray-500">
        <p className="text-sm mb-3">No conditions — rule fires on every trigger</p>
        <button onClick={() => onChange({ op: 'AND', items: [] })}
          className="px-4 py-2 bg-gray-800 text-gray-300 rounded-xl text-sm hover:bg-gray-700 transition-colors">
          + Add Conditions (Optional)
        </button>
      </div>
    );
  }

  const addItem = () => {
    onChange({
      ...conditions,
      items: [...(conditions.items || []), { type: 'device_state', device_id: '', state: 'ON', op: '==' }]
    });
  };

  const updateItem = (i, updated) => {
    const items = [...(conditions.items || [])];
    items[i] = updated;
    onChange({ ...conditions, items });
  };

  const removeItem = (i) => {
    const items = (conditions.items || []).filter((_, j) => j !== i);
    onChange(items.length > 0 ? { ...conditions, items } : null);
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-3">
        <span className="text-xs text-gray-400">Logic:</span>
        {['AND', 'OR'].map(op => (
          <button key={op}
            onClick={() => onChange({ ...conditions, op })}
            className={`px-3 py-1 rounded-lg text-xs font-bold transition-all ${conditions.op === op ? 'bg-blue-600 text-white' : 'bg-gray-800 text-gray-400 hover:bg-gray-700'}`}
          >{op}</button>
        ))}
        <button onClick={() => onChange(null)} className="ml-auto text-xs text-red-400 hover:text-red-300">Remove All</button>
      </div>

      {(conditions.items || []).map((item, i) => (
        <div key={i} className="flex items-start gap-2 bg-gray-800/50 rounded-xl p-3">
          <div className="flex-1 grid grid-cols-3 gap-2">
            <div>
              <label className="text-[10px] text-gray-500 mb-1 block">Type</label>
              <select className="w-full bg-gray-700/80 border border-gray-600 rounded-lg px-2 py-1.5 text-white text-xs outline-none"
                value={item.type || 'device_state'} onChange={e => updateItem(i, { ...item, type: e.target.value })}>
                {CONDITION_TYPES.map(c => <option key={c.value} value={c.value}>{c.label}</option>)}
              </select>
            </div>

            {item.type === 'device_state' && (<>
              <div>
                <label className="text-[10px] text-gray-500 mb-1 block">Device</label>
                <select className="w-full bg-gray-700/80 border border-gray-600 rounded-lg px-2 py-1.5 text-white text-xs outline-none"
                  value={item.device_id || ''} onChange={e => updateItem(i, { ...item, device_id: e.target.value })}>
                  <option value="">—</option>
                  {devices.map(d => <option key={d.device_id} value={d.device_id}>{d.name}</option>)}
                </select>
              </div>
              <div className="flex gap-1">
                <select className="flex-1 bg-gray-700/80 border border-gray-600 rounded-lg px-1 py-1.5 text-white text-xs outline-none"
                  value={item.op || '=='} onChange={e => updateItem(i, { ...item, op: e.target.value })}>
                  {OPS.map(o => <option key={o}>{o}</option>)}
                </select>
                <input className="flex-1 bg-gray-700/80 border border-gray-600 rounded-lg px-2 py-1.5 text-white text-xs outline-none"
                  value={item.state || ''} placeholder="ON"
                  onChange={e => updateItem(i, { ...item, state: e.target.value })} />
              </div>
            </>)}

            {item.type === 'time_range' && (<>
              <div>
                <label className="text-[10px] text-gray-500 mb-1 block">From</label>
                <input type="time" className="w-full bg-gray-700/80 border border-gray-600 rounded-lg px-2 py-1.5 text-white text-xs outline-none"
                  value={item.from || '00:00'} onChange={e => updateItem(i, { ...item, from: e.target.value })} />
              </div>
              <div>
                <label className="text-[10px] text-gray-500 mb-1 block">To</label>
                <input type="time" className="w-full bg-gray-700/80 border border-gray-600 rounded-lg px-2 py-1.5 text-white text-xs outline-none"
                  value={item.to || '23:59'} onChange={e => updateItem(i, { ...item, to: e.target.value })} />
              </div>
            </>)}

            {item.type === 'day_of_week' && (
              <div className="col-span-2 flex gap-1 flex-wrap">
                {DAYS.map((d, j) => {
                  const val = DAY_VALUES[j];
                  const active = (item.days || []).includes(val);
                  return (
                    <button key={val}
                      onClick={() => updateItem(i, { ...item, days: active ? (item.days || []).filter(x => x !== val) : [...(item.days || []), val] })}
                      className={`px-2 py-1 rounded text-[10px] font-medium transition-all ${active ? 'bg-blue-600 text-white' : 'bg-gray-700 text-gray-400'}`}
                    >{d}</button>
                  );
                })}
              </div>
            )}

            {item.type === 'weather' && (<>
              <div>
                <label className="text-[10px] text-gray-500 mb-1 block">Metric</label>
                <select className="w-full bg-gray-700/80 border border-gray-600 rounded-lg px-2 py-1.5 text-white text-xs outline-none"
                  value={item.metric || 'temperature'} onChange={e => updateItem(i, { ...item, metric: e.target.value })}>
                  <option value="temperature">Temperature (°C)</option>
                  <option value="humidity">Humidity (%)</option>
                  <option value="condition">Condition</option>
                </select>
              </div>
              <div className="flex gap-1">
                <select className="flex-1 bg-gray-700/80 border border-gray-600 rounded-lg px-1 py-1.5 text-white text-xs outline-none"
                  value={item.op || '=='} onChange={e => updateItem(i, { ...item, op: e.target.value })}>
                  {OPS.map(o => <option key={o}>{o}</option>)}
                </select>
                <input className="flex-1 bg-gray-700/80 border border-gray-600 rounded-lg px-2 py-1.5 text-white text-xs outline-none"
                  value={item.value || ''} placeholder="30 or Rain"
                  onChange={e => updateItem(i, { ...item, value: e.target.value })} />
              </div>
            </>)}

            {item.type === 'variable' && (<>
              <div>
                <label className="text-[10px] text-gray-500 mb-1 block">Var Name</label>
                <input className="w-full bg-gray-700/80 border border-gray-600 rounded-lg px-2 py-1.5 text-white text-xs outline-none"
                  value={item.var_name || ''} placeholder="e.g. guest_mode"
                  onChange={e => updateItem(i, { ...item, var_name: e.target.value })} />
              </div>
              <div className="flex gap-1">
                <select className="flex-1 bg-gray-700/80 border border-gray-600 rounded-lg px-1 py-1.5 text-white text-xs outline-none"
                  value={item.op || '=='} onChange={e => updateItem(i, { ...item, op: e.target.value })}>
                  {OPS.map(o => <option key={o}>{o}</option>)}
                </select>
                <input className="flex-1 bg-gray-700/80 border border-gray-600 rounded-lg px-2 py-1.5 text-white text-xs outline-none"
                  value={item.value || ''} placeholder="1"
                  onChange={e => updateItem(i, { ...item, value: e.target.value })} />
              </div>
            </>)}
          </div>
          <button onClick={() => removeItem(i)} className="text-red-500 hover:text-red-400 text-sm mt-5 px-1">✕</button>
        </div>
      ))}

      <button onClick={addItem} className="text-sm text-blue-400 hover:text-blue-300 transition-colors">
        + Add Condition
      </button>
    </div>
  );
}

function ActionEditor({ actions, onChange, devices, scenes }) {
  const addAction = (type) => {
    const defaults = {
      control: { type: 'control', device_id: '', action: 'on', value: null },
      activate_scene: { type: 'activate_scene', scene_id: '' },
      delay: { type: 'delay', seconds: 5 },
      wait_for: { type: 'wait_for', condition: { type: 'device_state', device_id: '', state: 'ON', op: '==' }, timeout_seconds: 60 },
      set_var: { type: 'set_var', var_name: '', value: '' },
      notify: { type: 'notify', channel: 'telegram', title: 'Smart Home', message: '' },
      repeat: { type: 'repeat', count: 3, interval_seconds: 1, actions: [] },
      if_action: { type: 'if_action', condition: { type: 'device_state', device_id: '', state: 'ON', op: '==' }, then: [], else: [] },
    };
    onChange([...actions, defaults[type] || { type }]);
  };

  const updateAction = (i, updated) => {
    const a = [...actions];
    a[i] = updated;
    onChange(a);
  };

  const removeAction = (i) => onChange(actions.filter((_, j) => j !== i));
  const moveAction = (i, dir) => {
    const a = [...actions];
    const j = i + dir;
    if (j < 0 || j >= a.length) return;
    [a[i], a[j]] = [a[j], a[i]];
    onChange(a);
  };

  const colorMap = { control: 'blue', activate_scene: 'purple', delay: 'gray', notify: 'green', repeat: 'orange', if_action: 'yellow' };
  const bgMap = { blue: 'bg-blue-500/10 border-blue-500/30', purple: 'bg-purple-500/10 border-purple-500/30', gray: 'bg-gray-700/30 border-gray-600/30', green: 'bg-green-500/10 border-green-500/30', orange: 'bg-orange-500/10 border-orange-500/30', yellow: 'bg-yellow-500/10 border-yellow-500/30' };

  return (
    <div className="space-y-3">
      {actions.map((action, i) => {
        const color = colorMap[action.type] || 'gray';
        const atype = ACTION_TYPES.find(t => t.value === action.type) || { label: action.type };
        return (
          <div key={i} className={`relative rounded-xl border p-4 ${bgMap[color]}`}>
            <div className="flex items-start gap-3">
              {/* Step number */}
              <div className="flex-shrink-0 w-7 h-7 rounded-full bg-gray-700 flex items-center justify-center text-xs font-bold text-gray-300">
                {i + 1}
              </div>
              <div className="flex-1 space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium text-gray-200">{atype.label}</span>
                  <div className="flex items-center gap-1">
                    <button onClick={() => moveAction(i, -1)} className="text-gray-500 hover:text-gray-300 text-xs px-1" title="Move up">↑</button>
                    <button onClick={() => moveAction(i, 1)} className="text-gray-500 hover:text-gray-300 text-xs px-1" title="Move down">↓</button>
                    <button onClick={() => removeAction(i)} className="text-red-500 hover:text-red-400 text-xs px-1">✕</button>
                  </div>
                </div>

                {/* Action-specific fields */}
                {action.type === 'control' && (
                  <div className="grid grid-cols-3 gap-2">
                    <div className="col-span-2">
                      <label className="text-[10px] text-gray-500 mb-1 block">Device</label>
                      <select className="w-full bg-gray-800/80 border border-gray-700 rounded-lg px-2 py-1.5 text-white text-xs outline-none focus:border-blue-500"
                        value={action.device_id || ''} onChange={e => updateAction(i, { ...action, device_id: e.target.value })}>
                        <option value="">— Select device —</option>
                        {devices.map(d => <option key={d.device_id} value={d.device_id}>{d.name}</option>)}
                      </select>
                    </div>
                    <div className="grid grid-cols-2 gap-1">
                      <div>
                        <label className="text-[10px] text-gray-500 mb-1 block">Action</label>
                        <select className="w-full bg-gray-800/80 border border-gray-700 rounded-lg px-2 py-1.5 text-white text-xs outline-none"
                          value={action.action || 'on'} onChange={e => updateAction(i, { ...action, action: e.target.value })}>
                          <option value="on">ON</option>
                          <option value="off">OFF</option>
                          <option value="toggle">Toggle</option>
                          <option value="brightness">Brightness</option>
                          <option value="position">Position%</option>
                        </select>
                      </div>
                      <div>
                        <label className="text-[10px] text-gray-500 mb-1 block">Value</label>
                        <input className="w-full bg-gray-800/80 border border-gray-700 rounded-lg px-2 py-1.5 text-white text-xs outline-none"
                          value={action.value ?? ''} placeholder="e.g. 75"
                          onChange={e => updateAction(i, { ...action, value: e.target.value ? Number(e.target.value) : null })} />
                      </div>
                    </div>
                  </div>
                )}

                {action.type === 'activate_scene' && (
                  <select className="w-full bg-gray-800/80 border border-gray-700 rounded-lg px-2 py-1.5 text-white text-xs outline-none focus:border-purple-500"
                    value={action.scene_id || ''} onChange={e => updateAction(i, { ...action, scene_id: e.target.value })}>
                    <option value="">— Select scene —</option>
                    {(scenes || []).map(s => <option key={s.scene_id} value={s.scene_id}>{s.name}</option>)}
                  </select>
                )}

                {action.type === 'delay' && (
                  <div className="flex items-center gap-3">
                    <input type="number" min="1" max="300" className="w-24 bg-gray-800/80 border border-gray-700 rounded-lg px-2 py-1.5 text-white text-xs outline-none"
                      value={action.seconds || 5} onChange={e => updateAction(i, { ...action, seconds: Number(e.target.value) })} />
                    <span className="text-xs text-gray-400">seconds</span>
                  </div>
                )}

                {action.type === 'notify' && (
                  <div className="space-y-2">
                    <div className="grid grid-cols-3 gap-2">
                      <div>
                        <label className="text-[10px] text-gray-500 mb-1 block">Channel</label>
                        <select className="w-full bg-gray-800/80 border border-gray-700 rounded-lg px-2 py-1.5 text-white text-xs outline-none"
                          value={action.channel || 'telegram'} onChange={e => updateAction(i, { ...action, channel: e.target.value })}>
                          <option value="telegram">Telegram</option>
                          <option value="zalo">Zalo</option>
                          <option value="email">Email</option>
                        </select>
                      </div>
                      <div className="col-span-2">
                        <label className="text-[10px] text-gray-500 mb-1 block">Title</label>
                        <input className="w-full bg-gray-800/80 border border-gray-700 rounded-lg px-2 py-1.5 text-white text-xs outline-none"
                          value={action.title || ''} placeholder="Smart Home Alert"
                          onChange={e => updateAction(i, { ...action, title: e.target.value })} />
                      </div>
                    </div>
                    <div>
                      <label className="text-[10px] text-gray-500 mb-1 block">Message</label>
                      <input className="w-full bg-gray-800/80 border border-gray-700 rounded-lg px-2 py-1.5 text-white text-xs outline-none"
                        value={action.message || ''} placeholder="Đèn hành lang đã bật"
                        onChange={e => updateAction(i, { ...action, message: e.target.value })} />
                    </div>
                  </div>
                )}

                {action.type === 'repeat' && (
                  <div className="flex items-center gap-3">
                    <input type="number" min="1" max="20" className="w-20 bg-gray-800/80 border border-gray-700 rounded-lg px-2 py-1.5 text-white text-xs outline-none"
                      value={action.count || 3} onChange={e => updateAction(i, { ...action, count: Number(e.target.value) })} />
                    <span className="text-xs text-gray-400">times, every</span>
                    <input type="number" min="1" max="60" className="w-20 bg-gray-800/80 border border-gray-700 rounded-lg px-2 py-1.5 text-white text-xs outline-none"
                      value={action.interval_seconds || 1} onChange={e => updateAction(i, { ...action, interval_seconds: Number(e.target.value) })} />
                    <span className="text-xs text-gray-400">seconds</span>
                  </div>
                )}

                {action.type === 'wait_for' && (
                  <div className="grid grid-cols-4 gap-2">
                    <div className="col-span-2">
                      <label className="text-[10px] text-gray-500 mb-1 block">Device</label>
                      <select className="w-full bg-gray-800/80 border border-gray-700 rounded-lg px-2 py-1.5 text-white text-xs outline-none focus:border-blue-500"
                        value={action.condition?.device_id || ''} onChange={e => updateAction(i, { ...action, condition: { ...action.condition, device_id: e.target.value } })}>
                        <option value="">— Select device —</option>
                        {devices.map(d => <option key={d.device_id} value={d.device_id}>{d.name}</option>)}
                      </select>
                    </div>
                    <div>
                      <label className="text-[10px] text-gray-500 mb-1 block">State</label>
                      <input className="w-full bg-gray-800/80 border border-gray-700 rounded-lg px-2 py-1.5 text-white text-xs outline-none"
                        value={action.condition?.state || ''} placeholder="ON"
                        onChange={e => updateAction(i, { ...action, condition: { ...action.condition, state: e.target.value } })} />
                    </div>
                    <div>
                      <label className="text-[10px] text-gray-500 mb-1 block">Timeout(s)</label>
                      <input type="number" className="w-full bg-gray-800/80 border border-gray-700 rounded-lg px-2 py-1.5 text-white text-xs outline-none"
                        value={action.timeout_seconds || 60} onChange={e => updateAction(i, { ...action, timeout_seconds: Number(e.target.value) })} />
                    </div>
                  </div>
                )}

                {action.type === 'set_var' && (
                  <div className="flex gap-2">
                    <div className="flex-1">
                      <label className="text-[10px] text-gray-500 mb-1 block">Var Name</label>
                      <input className="w-full bg-gray-800/80 border border-gray-700 rounded-lg px-2 py-1.5 text-white text-xs outline-none"
                        value={action.var_name || ''} placeholder="guest_mode"
                        onChange={e => updateAction(i, { ...action, var_name: e.target.value })} />
                    </div>
                    <div className="flex-1">
                      <label className="text-[10px] text-gray-500 mb-1 block">Value</label>
                      <input className="w-full bg-gray-800/80 border border-gray-700 rounded-lg px-2 py-1.5 text-white text-xs outline-none"
                        value={action.value || ''} placeholder="1 or ON"
                        onChange={e => updateAction(i, { ...action, value: e.target.value })} />
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        );
      })}

      {/* Add Action buttons */}
      <div className="flex flex-wrap gap-2 pt-2">
        {ACTION_TYPES.map(t => (
          <button key={t.value} onClick={() => addAction(t.value)}
            className="px-3 py-1.5 bg-gray-800 text-gray-300 border border-gray-700 rounded-lg text-xs hover:bg-gray-700 transition-colors">
            + {t.label}
          </button>
        ))}
      </div>
    </div>
  );
}

// ── Rule Card ─────────────────────────────────────────────────
function RuleCard({ rule, onEdit, onDelete, onToggle, onTest, testLoading }) {
  const ttype = rule.trigger?.type || 'device_state';
  const triggerIcon = { device_state: '🔌', time: '🕐', sun: '🌅', system: '⚙️' }[ttype] || '⚡';

  return (
    <div className={`bg-gray-900/60 border rounded-2xl p-5 transition-all ${rule.enabled ? 'border-gray-800 hover:border-gray-700' : 'border-gray-800/40 opacity-60'}`}>
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-start gap-3 flex-1 min-w-0">
          <div className="text-2xl mt-0.5">{triggerIcon}</div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <h3 className="text-white font-semibold truncate">{rule.name}</h3>
              <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${rule.enabled ? 'bg-green-500/20 text-green-400' : 'bg-gray-700 text-gray-500'}`}>
                {rule.enabled ? 'Active' : 'Disabled'}
              </span>
              {rule.priority > 75 && <span className="text-[10px] px-2 py-0.5 rounded-full bg-red-500/20 text-red-400">High Priority</span>}
            </div>
            {rule.description && <p className="text-gray-500 text-xs mt-0.5 truncate">{rule.description}</p>}

            <div className="flex items-center flex-wrap gap-x-4 gap-y-1 mt-2 text-xs text-gray-500">
              <span>Trigger: <span className="text-gray-300">{ttype === 'device_state' ? `${rule.trigger?.device_id} ${rule.trigger?.op} ${rule.trigger?.state}` : ttype === 'time' ? `${rule.trigger?.at || ''}` : ttype === 'sun' ? `${rule.trigger?.event} ${rule.trigger?.offset_minutes > 0 ? '+' : ''}${rule.trigger?.offset_minutes || 0}min` : rule.trigger?.event || ''}</span></span>
              {rule.conditions && <span>Conditions: <span className="text-yellow-400">{rule.conditions?.op} ({(rule.conditions?.items || []).length})</span></span>}
              <span>Actions: <span className="text-blue-400">{(rule.actions || []).length}</span></span>
              <span>Cooldown: <span className="text-gray-300">{rule.cooldown_seconds}s</span></span>
              {rule.run_count > 0 && <span>Runs: <span className="text-green-400">{rule.run_count}</span></span>}
              {rule.last_error && <span className="text-red-400">⚠ Error: {rule.last_error.slice(0, 40)}</span>}
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2 flex-shrink-0">
          <button onClick={() => onTest(rule.rule_id)} disabled={testLoading === rule.rule_id}
            className="px-3 py-1.5 text-xs bg-gray-800 text-gray-300 border border-gray-700 rounded-lg hover:bg-gray-700 transition-colors disabled:opacity-50">
            {testLoading === rule.rule_id ? '⏳' : '▶ Test'}
          </button>
          <button onClick={() => onToggle(rule.rule_id)}
            className={`px-3 py-1.5 text-xs rounded-lg border transition-colors ${rule.enabled ? 'bg-gray-800 text-yellow-400 border-yellow-500/30 hover:bg-yellow-500/10' : 'bg-gray-800 text-green-400 border-green-500/30 hover:bg-green-500/10'}`}>
            {rule.enabled ? 'Disable' : 'Enable'}
          </button>
          <button onClick={() => onEdit(rule)} className="px-3 py-1.5 text-xs bg-blue-600/20 text-blue-400 border border-blue-500/30 rounded-lg hover:bg-blue-600/30 transition-colors">Edit</button>
          <button onClick={() => onDelete(rule.rule_id)} className="px-3 py-1.5 text-xs bg-red-500/10 text-red-400 border border-red-500/20 rounded-lg hover:bg-red-500/20 transition-colors">Delete</button>
        </div>
      </div>
    </div>
  );
}

// ── Main Page ─────────────────────────────────────────────────
export default function AutomationPage() {
  const [rules, setRules] = useState([]);
  const [devices, setDevices] = useState([]);
  const [scenes, setScenes] = useState([]);
  const [editing, setEditing] = useState(null);      // null | rule object
  const [isCreating, setIsCreating] = useState(false);
  const [saving, setSaving] = useState(false);
  const [testLoading, setTestLoading] = useState(null);
  const [toast, setToast] = useState(null);
  const [filter, setFilter] = useState('all');

  const showToast = (msg, type = 'success') => {
    setToast({ msg, type });
    setTimeout(() => setToast(null), 3000);
  };

  const loadRules = useCallback(async () => {
    const res = await fetch('/api/automation2');
    const data = await res.json();
    setRules(data.rules || []);
  }, []);

  useEffect(() => {
    loadRules();
    fetch('/api/devices').then(r => r.json()).then(d => setDevices(d.devices || []));
    fetch('/api/scenes').then(r => r.json()).then(d => setScenes(d.scenes || [])).catch(() => {});
  }, [loadRules]);

  const handleSave = async () => {
    if (!editing) return;
    if (!editing.name.trim()) { showToast('Rule name is required', 'error'); return; }
    if (!editing.actions?.length) { showToast('At least one action is required', 'error'); return; }
    setSaving(true);
    try {
      const url = editing.rule_id ? `/api/automation2/${editing.rule_id}` : '/api/automation2';
      const method = editing.rule_id ? 'PUT' : 'POST';
      const res = await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(editing),
      });
      if (!res.ok) throw new Error(await res.text());
      showToast(editing.rule_id ? 'Rule updated ✓' : 'Rule created ✓');
      setEditing(null);
      setIsCreating(false);
      await loadRules();
    } catch (e) {
      showToast(`Error: ${e.message}`, 'error');
    }
    setSaving(false);
  };

  const handleDelete = async (ruleId) => {
    if (!confirm('Delete this rule?')) return;
    await fetch(`/api/automation2/${ruleId}`, { method: 'DELETE' });
    showToast('Rule deleted');
    loadRules();
  };

  const handleToggle = async (ruleId) => {
    await fetch(`/api/automation2/${ruleId}/toggle`, { method: 'PUT' });
    loadRules();
  };

  const handleTest = async (ruleId) => {
    setTestLoading(ruleId);
    const res = await fetch(`/api/automation2/${ruleId}/test`, { method: 'POST' });
    const data = await res.json();
    showToast(data.ok ? '✓ Rule fired successfully' : `Error: ${data.detail}`, data.ok ? 'success' : 'error');
    setTestLoading(null);
    setTimeout(loadRules, 1000);
  };

  const filteredRules = rules.filter(r =>
    filter === 'all' ? true : filter === 'active' ? r.enabled : !r.enabled
  );

  // Editor panel
  if (editing !== null) {
    return (
      <div className="min-h-screen bg-gray-950 text-white">
        {/* Editor Header */}
        <div className="sticky top-0 z-20 flex items-center justify-between px-6 py-4 bg-gray-900/95 border-b border-gray-800 backdrop-blur-sm">
          <div className="flex items-center gap-3">
            <button onClick={() => { setEditing(null); setIsCreating(false); }} className="text-gray-400 hover:text-white transition-colors">← Back</button>
            <h1 className="text-xl font-bold text-white">{editing.rule_id ? 'Edit Rule' : 'New Rule'}</h1>
          </div>
          <div className="flex items-center gap-3">
            <button onClick={() => { setEditing(null); setIsCreating(false); }} className="px-4 py-2 bg-gray-800 text-gray-300 rounded-xl text-sm hover:bg-gray-700 transition-colors">Cancel</button>
            <button onClick={handleSave} disabled={saving}
              className="px-5 py-2 bg-blue-600 text-white rounded-xl text-sm font-semibold hover:bg-blue-500 transition-colors disabled:opacity-50">
              {saving ? 'Saving…' : editing.rule_id ? 'Update Rule' : 'Create Rule'}
            </button>
          </div>
        </div>

        <div className="max-w-4xl mx-auto p-6 space-y-6">
          {/* Name & Settings */}
          <SectionCard title="Rule Settings" icon="⚙️">
            <div className="grid grid-cols-2 gap-4">
              <div className="col-span-2">
                <label className="text-xs text-gray-400 mb-1 block">Rule Name *</label>
                <input className="w-full bg-gray-800 border border-gray-700 rounded-xl px-4 py-3 text-white outline-none focus:border-blue-500 text-sm"
                  value={editing.name} placeholder="e.g. Auto Turn Off Hall Light"
                  onChange={e => setEditing({ ...editing, name: e.target.value })} autoFocus />
              </div>
              <div>
                <label className="text-xs text-gray-400 mb-1 block">Description</label>
                <input className="w-full bg-gray-800 border border-gray-700 rounded-xl px-4 py-3 text-white outline-none focus:border-blue-500 text-sm"
                  value={editing.description || ''} placeholder="Optional description"
                  onChange={e => setEditing({ ...editing, description: e.target.value })} />
              </div>
              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="text-xs text-gray-400 mb-1 block">Priority (0-100)</label>
                  <input type="number" min="0" max="100" className="w-full bg-gray-800 border border-gray-700 rounded-xl px-3 py-3 text-white text-sm outline-none focus:border-blue-500"
                    value={editing.priority} onChange={e => setEditing({ ...editing, priority: Number(e.target.value) })} />
                </div>
                <div>
                  <label className="text-xs text-gray-400 mb-1 block">Cooldown (s)</label>
                  <input type="number" min="0" className="w-full bg-gray-800 border border-gray-700 rounded-xl px-3 py-3 text-white text-sm outline-none focus:border-blue-500"
                    value={editing.cooldown_seconds} onChange={e => setEditing({ ...editing, cooldown_seconds: Number(e.target.value) })} />
                </div>
                <div>
                  <label className="text-xs text-gray-400 mb-1 block">Max runs/day (0=∞)</label>
                  <input type="number" min="0" className="w-full bg-gray-800 border border-gray-700 rounded-xl px-3 py-3 text-white text-sm outline-none focus:border-blue-500"
                    value={editing.max_runs_per_day} onChange={e => setEditing({ ...editing, max_runs_per_day: Number(e.target.value) })} />
                </div>
              </div>
            </div>
          </SectionCard>

          {/* WHEN */}
          <SectionCard title="WHEN — Trigger" icon="⚡" extra={<span className="text-xs text-gray-500">Required</span>}>
            <TriggerEditor trigger={editing.trigger || {}} onChange={t => setEditing({ ...editing, trigger: t })} devices={devices} />
          </SectionCard>

          {/* IF — Conditions */}
          <SectionCard title="IF — Conditions" icon="🔀" extra={<span className="text-xs text-gray-500">Optional</span>}>
            <ConditionEditor conditions={editing.conditions} onChange={c => setEditing({ ...editing, conditions: c })} devices={devices} />
          </SectionCard>

          {/* Time Filter */}
          <SectionCard title="TIME FILTER — Only run during" icon="📅" extra={<span className="text-xs text-gray-500">Optional</span>}>
            {editing.time_filter ? (
              <div className="space-y-3">
                <div className="flex gap-4 items-center">
                  <div>
                    <label className="text-xs text-gray-400 mb-1 block">From</label>
                    <input type="time" className="bg-gray-800 border border-gray-700 rounded-xl px-3 py-2 text-white text-sm outline-none focus:border-blue-500"
                      value={editing.time_filter?.from || ''} onChange={e => setEditing({ ...editing, time_filter: { ...editing.time_filter, from: e.target.value } })} />
                  </div>
                  <div>
                    <label className="text-xs text-gray-400 mb-1 block">To</label>
                    <input type="time" className="bg-gray-800 border border-gray-700 rounded-xl px-3 py-2 text-white text-sm outline-none focus:border-blue-500"
                      value={editing.time_filter?.to || ''} onChange={e => setEditing({ ...editing, time_filter: { ...editing.time_filter, to: e.target.value } })} />
                  </div>
                  <button onClick={() => setEditing({ ...editing, time_filter: null })} className="text-red-400 hover:text-red-300 text-sm mt-5">Remove</button>
                </div>
                <div className="flex gap-2 flex-wrap">
                  {DAYS.map((d, i) => {
                    const val = DAY_VALUES[i];
                    const active = (editing.time_filter?.days || []).includes(val);
                    return (
                      <button key={val}
                        onClick={() => { const days = editing.time_filter?.days || []; setEditing({ ...editing, time_filter: { ...editing.time_filter, days: active ? days.filter(x => x !== val) : [...days, val] } }); }}
                        className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${active ? 'bg-blue-600 text-white' : 'bg-gray-800 text-gray-400 hover:bg-gray-700'}`}
                      >{d}</button>
                    );
                  })}
                </div>
              </div>
            ) : (
              <button onClick={() => setEditing({ ...editing, time_filter: { from: '07:00', to: '22:00', days: [] } })}
                className="text-sm text-gray-500 hover:text-gray-300 transition-colors">+ Add Time Filter</button>
            )}
          </SectionCard>

          {/* THEN — Actions */}
          <SectionCard title="THEN — Actions" icon="🎯" extra={<span className="text-xs text-gray-500">Required — runs in order</span>}>
            <ActionEditor actions={editing.actions || []} onChange={a => setEditing({ ...editing, actions: a })} devices={devices} scenes={scenes} />
          </SectionCard>
        </div>
      </div>
    );
  }

  // List view
  return (
    <div className="min-h-screen bg-gray-950 text-white">
      {/* Header */}
      <div className="sticky top-0 z-20 flex items-center justify-between px-6 py-4 bg-gray-900/95 border-b border-gray-800 backdrop-blur-sm">
        <div className="flex items-center gap-4">
          <Link href="/" className="text-gray-400 hover:text-white transition-colors">← Back</Link>
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-violet-500 to-purple-400 flex items-center justify-center text-sm">⚡</div>
            <h1 className="text-xl font-bold bg-gradient-to-r from-violet-400 to-purple-300 bg-clip-text text-transparent">
              Automation Engine
            </h1>
          </div>
        </div>
        <button onClick={() => { setEditing(emptyRule()); setIsCreating(true); }}
          className="px-5 py-2.5 bg-gradient-to-r from-violet-600 to-purple-600 text-white rounded-xl text-sm font-semibold hover:from-violet-500 hover:to-purple-500 transition-all shadow-lg shadow-purple-500/20">
          + New Rule
        </button>
      </div>

      <div className="max-w-5xl mx-auto p-6">
        {/* Stats */}
        <div className="grid grid-cols-4 gap-4 mb-6">
          {[
            { label: 'Total Rules', value: rules.length, color: 'text-white' },
            { label: 'Active', value: rules.filter(r => r.enabled).length, color: 'text-green-400' },
            { label: 'Total Runs', value: rules.reduce((s, r) => s + (r.run_count || 0), 0), color: 'text-blue-400' },
            { label: 'With Errors', value: rules.filter(r => r.last_error).length, color: 'text-red-400' },
          ].map(stat => (
            <div key={stat.label} className="bg-gray-900/60 border border-gray-800 rounded-2xl p-4">
              <div className={`text-2xl font-bold ${stat.color}`}>{stat.value}</div>
              <div className="text-xs text-gray-500 mt-1">{stat.label}</div>
            </div>
          ))}
        </div>

        {/* Filter */}
        <div className="flex gap-2 mb-5">
          {['all', 'active', 'disabled'].map(f => (
            <button key={f} onClick={() => setFilter(f)}
              className={`px-4 py-1.5 rounded-lg text-sm font-medium transition-all ${filter === f ? 'bg-violet-600 text-white' : 'bg-gray-800 text-gray-400 hover:bg-gray-700'}`}>
              {f.charAt(0).toUpperCase() + f.slice(1)}
            </button>
          ))}
        </div>

        {/* Rules List */}
        {filteredRules.length === 0 ? (
          <div className="text-center py-20 text-gray-500">
            <div className="text-6xl mb-4">⚡</div>
            <p className="text-xl font-medium mb-2">No automation rules yet</p>
            <p className="text-sm mb-6">Create your first rule to automate your home</p>
            <button onClick={() => { setEditing(emptyRule()); setIsCreating(true); }}
              className="px-6 py-3 bg-violet-600 text-white rounded-xl font-semibold hover:bg-violet-500 transition-colors">
              + Create First Rule
            </button>
          </div>
        ) : (
          <div className="space-y-3">
            {filteredRules.map(rule => (
              <RuleCard key={rule.rule_id} rule={rule}
                onEdit={r => setEditing({ ...r })}
                onDelete={handleDelete}
                onToggle={handleToggle}
                onTest={handleTest}
                testLoading={testLoading}
              />
            ))}
          </div>
        )}
      </div>

      {/* Toast */}
      {toast && (
        <div className={`fixed bottom-6 right-6 z-50 px-5 py-3 rounded-xl shadow-2xl text-sm font-medium transition-all ${toast.type === 'error' ? 'bg-red-600 text-white' : 'bg-green-600 text-white'}`}>
          {toast.msg}
        </div>
      )}
    </div>
  );
}
