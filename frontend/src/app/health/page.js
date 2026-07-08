'use client';
import { useState, useEffect } from 'react';
import Link from 'next/link';

function MetricCard({ title, value, status = 'neutral', icon, sub }) {
  const bg = {
    ok: 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400',
    warn: 'bg-amber-500/10 border-amber-500/20 text-amber-400',
    error: 'bg-red-500/10 border-red-500/20 text-red-400',
    neutral: 'bg-gray-800/50 border-gray-700/50 text-gray-300',
  }[status];

  return (
    <div className={`p-4 rounded-xl border ${bg} flex flex-col`}>
      <div className="flex items-center gap-2 mb-2">
        <span>{icon}</span>
        <h3 className="text-sm font-semibold text-gray-300">{title}</h3>
      </div>
      <div className="text-2xl font-bold mt-auto">{value}</div>
      {sub && <div className="text-xs text-gray-500 mt-1">{sub}</div>}
    </div>
  );
}

function Section({ title, children }) {
  return (
    <div className="bg-gray-900/40 border border-gray-800 rounded-2xl p-5">
      <h2 className="text-sm font-bold text-gray-400 uppercase tracking-wider mb-4">{title}</h2>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {children}
      </div>
    </div>
  );
}

export default function HealthPage() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchHealth = () => {
    fetch('/api/health/detail')
      .then(res => res.json())
      .then(d => {
        if (d.error) setError(d.error);
        else { setData(d); setError(null); }
        setLoading(false);
      })
      .catch(e => {
        setError(e.message);
        setLoading(false);
      });
  };

  useEffect(() => {
    fetchHealth();
    const interval = setInterval(fetchHealth, 3000); // Poll every 3s
    return () => clearInterval(interval);
  }, []);

  if (loading && !data) {
    return <div className="min-h-screen bg-gray-950 flex items-center justify-center text-gray-400">Loading metrics...</div>;
  }
  
  if (error && !data) {
    return <div className="min-h-screen bg-gray-950 flex items-center justify-center text-red-400">Error: {error}</div>;
  }

  const {
    knx, queues, sse, state_manager, device_registry,
    event_bus, command_pipeline, automation_engine, system
  } = data || {};

  const formatUptime = (secs) => {
    if (!secs) return '0s';
    const h = Math.floor(secs / 3600);
    const m = Math.floor((secs % 3600) / 60);
    const s = secs % 60;
    return `${h > 0 ? h + 'h ' : ''}${m > 0 ? m + 'm ' : ''}${s}s`;
  };

  const getMemStatus = (used, total) => {
    if (!used || !total) return 'neutral';
    const pct = used / total;
    if (pct > 0.9) return 'error';
    if (pct > 0.7) return 'warn';
    return 'ok';
  };

  return (
    <div className="min-h-screen bg-gray-950 text-white p-6">
      <div className="max-w-6xl mx-auto space-y-6">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-2xl font-bold bg-gradient-to-r from-teal-400 to-blue-400 bg-clip-text text-transparent">
              System Observability
            </h1>
            <p className="text-sm text-gray-400">Live Health Monitor & Metrics</p>
          </div>
          <div className="flex items-center gap-3">
            <div className={`w-3 h-3 rounded-full ${knx?.knx_connected ? 'bg-emerald-500 animate-pulse' : 'bg-red-500'}`} />
            <span className="text-sm font-medium text-gray-300">
              {knx?.knx_connected ? 'System Online' : 'KNX Disconnected'}
            </span>
          </div>
        </div>

        {/* System & Hardware */}
        <Section title="Hardware & Platform">
          <MetricCard title="Uptime" value={formatUptime(system?.uptime_seconds)} icon="⏱️" />
          <MetricCard 
            title="CPU Usage" 
            value={system?.cpu_percent >= 0 ? `${system?.cpu_percent}%` : 'N/A'} 
            status={system?.cpu_percent > 80 ? 'warn' : 'ok'}
            icon="🧠" 
          />
          <MetricCard 
            title="Memory" 
            value={system?.mem_used_mb >= 0 ? `${system?.mem_used_mb} MB` : 'N/A'}
            sub={`of ${system?.mem_total_mb} MB`}
            status={getMemStatus(system?.mem_used_mb, system?.mem_total_mb)}
            icon="💽" 
          />
          <MetricCard title="Active SSE Clients" value={(sse?.event_clients || 0) + (sse?.bus_clients || 0)} icon="🔌" />
        </Section>

        {/* KNX Bus */}
        <Section title="KNX Bus Connectivity">
          <MetricCard 
            title="Connection Status" 
            value={knx?.knx_connected ? 'CONNECTED' : 'DISCONNECTED'} 
            status={knx?.knx_connected ? 'ok' : 'error'}
            icon="📡" 
            sub={knx?.knx_gateway_ip ? `${knx.knx_gateway_ip}:${knx.knx_gateway_port}` : ''}
          />
          <MetricCard 
            title="Last Telegram" 
            value={knx?.last_telegram_age_s !== null && knx?.last_telegram_age_s !== undefined ? `${knx.last_telegram_age_s}s ago` : 'Never'}
            status={(knx?.last_telegram_age_s || 0) > 300 ? 'warn' : 'neutral'}
            icon="✉️" 
          />
          <MetricCard title="Raw Queue" value={queues?.raw_telegram_queue_size} icon="📥" status={queues?.raw_telegram_queue_size > 100 ? 'warn' : 'neutral'} />
          <MetricCard title="Event Queue" value={queues?.device_event_queue_size} icon="📥" status={queues?.device_event_queue_size > 100 ? 'warn' : 'neutral'} />
        </Section>

        {/* Domain Layer */}
        <Section title="Domain Layer Stats">
          <MetricCard title="Registered Devices" value={device_registry?.total_devices} icon="🔌" />
          <MetricCard title="States in RAM" value={state_manager?.total_devices} icon="💾" />
          <MetricCard title="Commands Executed" value={command_pipeline?.executed} icon="⚡" status="neutral" />
          <MetricCard 
            title="Commands Blocked/Failed" 
            value={(command_pipeline?.rejected || 0) + (command_pipeline?.failed || 0)} 
            icon="🚫" 
            status={(command_pipeline?.rejected > 0 || command_pipeline?.failed > 0) ? 'warn' : 'neutral'}
          />
        </Section>

        {/* Automation & Events */}
        <Section title="Automation & Events">
          <MetricCard title="Active Rules" value={automation_engine?.active_rules} icon="🤖" />
          <MetricCard title="Running Actions" value={automation_engine?.running_actions} icon="🏃" />
          <MetricCard title="Events Published" value={event_bus?.published_events} icon="📢" />
          <MetricCard title="Active Subscribers" value={event_bus?.total_subscribers} icon="👂" />
        </Section>
      </div>
    </div>
  );
}
