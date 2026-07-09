'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { 
  Activity, Server, Database, Clock, Terminal, 
  Wifi, WifiOff, RefreshCw, AlertTriangle, Cpu, HardDrive
} from 'lucide-react';

export default function DiagnosticsHub() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [reconnecting, setReconnecting] = useState(false);

  const fetchHealth = async () => {
    try {
      const res = await fetch('/api/health/detail');
      if (!res.ok) throw new Error('Failed to fetch health data');
      const json = await res.json();
      setData(json);
      setError(null);
    } catch (err) {
      console.error(err);
      setError('Could not connect to backend service.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHealth();
    const interval = setInterval(fetchHealth, 5000); // 5s REST polling as requested
    return () => clearInterval(interval);
  }, []);

  const handleReconnect = async () => {
    if (!window.confirm('Reconnect KNX Interface?')) return;
    setReconnecting(true);
    try {
      await fetch('/api/system/restart', { method: 'POST' });
      // Might take a few seconds
      setTimeout(fetchHealth, 3000);
    } catch (e) {
      console.error(e);
    } finally {
      setTimeout(() => setReconnecting(false), 3000);
    }
  };

  if (loading && !data) {
    return <div className="flex h-screen items-center justify-center"><RefreshCw className="animate-spin w-8 h-8 text-blue-500" /></div>;
  }

  // Helper formatting functions
  const formatUptime = (seconds) => {
    if (!seconds) return '0s';
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = Math.floor(seconds % 60);
    if (h > 0) return `${h}h ${m}m`;
    if (m > 0) return `${m}m ${s}s`;
    return `${s}s`;
  };

  const getStatusColor = (status) => {
    if (status === 'HEALTHY') return 'text-green-400 bg-green-500/10 border-green-500/20';
    if (status === 'WARNING') return 'text-yellow-400 bg-yellow-500/10 border-yellow-500/20';
    return 'text-red-400 bg-red-500/10 border-red-500/20';
  };

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      <header className="mb-8 flex justify-between items-start">
        <div>
          <div className="flex items-center gap-3">
            <h2 className="text-3xl font-bold bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent">
              Diagnostics Hub
            </h2>
            {data?.overall_status && (
              <span className={`px-3 py-1 text-sm font-bold border rounded-full ${getStatusColor(data.overall_status)}`}>
                {data.overall_status}
              </span>
            )}
          </div>
          <p className="text-gray-400 mt-2">
            System health, network status, event bus monitoring, and logs. Auto-refreshing every 5 seconds.
          </p>
        </div>
        {data?.version && (
          <div className="text-right text-xs text-gray-500">
            <p className="font-mono text-gray-400">Version: {data.version.version}</p>
            <p>Commit: {data.version.git_commit}</p>
            <p>Build: {data.version.build_time}</p>
          </div>
        )}
      </header>

      {error && (
        <div className="bg-red-900/20 border border-red-500/50 text-red-200 p-4 rounded-lg flex items-center gap-3">
          <AlertTriangle className="w-5 h-5" />
          <p>{error}</p>
        </div>
      )}

      {/* TOP ROW: Health & Network */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        
        {/* System Health Card */}
        <div className="glass-panel p-6 rounded-xl border border-white/5 bg-gray-900/50">
          <div className="flex items-center gap-3 mb-4">
            <div className="p-2 bg-blue-500/10 rounded-lg text-blue-400"><Server className="w-6 h-6" /></div>
            <h3 className="text-xl font-semibold">System Health</h3>
          </div>
          
          <div className="grid grid-cols-2 gap-4">
            <div className="bg-gray-800/50 p-4 rounded-lg">
              <p className="text-gray-400 text-sm flex items-center gap-2"><Cpu className="w-4 h-4"/> CPU Load</p>
              <p className="text-2xl font-bold mt-1">{data?.system?.cpu_percent ?? 0}%</p>
            </div>
            <div className="bg-gray-800/50 p-4 rounded-lg">
              <p className="text-gray-400 text-sm flex items-center gap-2"><HardDrive className="w-4 h-4"/> Memory</p>
              <p className="text-2xl font-bold mt-1">{data?.system?.mem_used_mb ?? 0} <span className="text-lg font-normal text-gray-500">/ {data?.system?.mem_total_mb ?? 0} MB</span></p>
            </div>
            <div className="bg-gray-800/50 p-4 rounded-lg">
              <p className="text-gray-400 text-sm flex items-center gap-2"><Activity className="w-4 h-4"/> Python Process</p>
              <p className="text-2xl font-bold mt-1">{data?.system?.process_mem_mb ?? 0} MB</p>
            </div>
            <div className="bg-gray-800/50 p-4 rounded-lg">
              <p className="text-gray-400 text-sm flex items-center gap-2"><Clock className="w-4 h-4"/> Uptime</p>
              <p className="text-2xl font-bold mt-1">{formatUptime(data?.system?.uptime_seconds)}</p>
            </div>
          </div>
        </div>

        {/* KNX Network Card */}
        <div className="glass-panel p-6 rounded-xl border border-white/5 bg-gray-900/50 flex flex-col">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3">
              <div className={`p-2 rounded-lg ${data?.knx?.connected ? 'bg-green-500/10 text-green-400' : 'bg-red-500/10 text-red-400'}`}>
                {data?.knx?.connected ? <Wifi className="w-6 h-6" /> : <WifiOff className="w-6 h-6" />}
              </div>
              <h3 className="text-xl font-semibold">KNX Connection</h3>
            </div>
            <span className={`px-3 py-1 rounded-full text-sm font-medium ${data?.knx?.connected ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'}`}>
              {data?.knx?.connected ? 'Connected' : 'Disconnected'}
            </span>
          </div>
          
          <div className="grid grid-cols-2 gap-4 flex-1">
            <div className="bg-gray-800/50 p-3 rounded-lg flex flex-col justify-center">
              <p className="text-gray-400 text-xs uppercase tracking-wider">Tunnel State</p>
              <p className="text-lg font-medium mt-1 truncate">{data?.knx?.tunnel_state || 'Unknown'}</p>
            </div>
            <div className="bg-gray-800/50 p-3 rounded-lg flex flex-col justify-center">
              <p className="text-gray-400 text-xs uppercase tracking-wider">Interface</p>
              <p className="text-sm font-medium mt-1 truncate">{data?.knx?.interface_ip || '?'}:{data?.knx?.interface_port || '?'}</p>
            </div>
            <div className="bg-gray-800/50 p-3 rounded-lg flex flex-col justify-center">
              <p className="text-gray-400 text-xs uppercase tracking-wider">Last Telegram</p>
              <p className="text-lg font-medium mt-1">
                {data?.knx?.last_telegram_age_s !== undefined && data?.knx?.last_telegram_age_s !== null 
                  ? `${data.knx.last_telegram_age_s}s ago` 
                  : 'Never'}
              </p>
            </div>
            <div className="bg-gray-800/50 p-3 rounded-lg flex flex-col justify-center">
              <p className="text-gray-400 text-xs uppercase tracking-wider">Conn Time / Reconnects</p>
              <p className="text-sm font-medium mt-1">
                {data?.knx?.connection_time ? formatUptime(Date.now()/1000 - data.knx.connection_time) : '0s'} / {data?.knx?.reconnect_count ?? 0}
              </p>
            </div>
          </div>

          <div className="mt-4 pt-4 border-t border-white/5 flex items-center justify-end">
            <button 
              onClick={handleReconnect}
              disabled={reconnecting}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-800 text-white rounded-lg text-sm font-medium transition-colors flex items-center gap-2"
            >
              {reconnecting ? <RefreshCw className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />}
              {reconnecting ? 'Reconnect đang thực hiện...' : 'Force Reconnect'}
            </button>
          </div>
        </div>
      </div>

      {/* MIDDLE ROW: EventBus & Offline Devices */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        
        {/* EventBus Card */}
        <div className="glass-panel p-6 rounded-xl border border-white/5 bg-gray-900/50">
          <div className="flex items-center gap-3 mb-4">
            <div className="p-2 bg-purple-500/10 rounded-lg text-purple-400"><Database className="w-6 h-6" /></div>
            <h3 className="text-xl font-semibold">EventBus Status</h3>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="bg-gray-800/50 p-3 rounded-lg flex justify-between items-center">
              <span className="text-gray-400 text-sm">Published</span>
              <span className="font-bold">{data?.event_bus?.published_total ?? 0}</span>
            </div>
            <div className="bg-gray-800/50 p-3 rounded-lg flex justify-between items-center">
              <span className="text-gray-400 text-sm">Subscribers</span>
              <span className="font-bold">{data?.event_bus?.subscriber_count ?? 0}</span>
            </div>
            <div className="bg-gray-800/50 p-3 rounded-lg flex justify-between items-center">
              <span className="text-gray-400 text-sm">Pending Queue</span>
              <span className="font-bold text-yellow-400">{data?.queues?.device_event_queue_size ?? 0}</span>
            </div>
            <div className="bg-gray-800/50 p-3 rounded-lg flex justify-between items-center">
              <span className="text-gray-400 text-sm">Errors</span>
              <span className="font-bold text-red-400">{data?.event_bus?.error_total ?? 0}</span>
            </div>
            <div className="col-span-2 bg-gray-800/50 p-3 rounded-lg flex justify-between items-center">
              <span className="text-gray-400 text-sm">Last Event</span>
              <span className="font-mono text-xs text-blue-400 truncate max-w-[200px]">{data?.event_bus?.last_event?.type || 'None'}</span>
            </div>
          </div>
        </div>

        {/* Offline Devices Card */}
        <div className="glass-panel p-6 rounded-xl border border-white/5 bg-gray-900/50 flex flex-col">
          <div className="flex items-center gap-3 mb-4">
            <div className="p-2 bg-orange-500/10 rounded-lg text-orange-400"><AlertTriangle className="w-6 h-6" /></div>
            <h3 className="text-xl font-semibold flex items-center gap-2">
              Offline Devices 
              {data?.offline_devices?.length > 0 && (
                <span className="bg-orange-500/20 text-orange-400 text-xs px-2 py-0.5 rounded-full">
                  {data.offline_devices.length}
                </span>
              )}
            </h3>
          </div>
          
          <div className="flex-1 bg-gray-800/30 rounded-lg border border-white/5 overflow-y-auto max-h-[150px] p-2">
            {!data?.offline_devices || data.offline_devices.length === 0 ? (
              <div className="h-full flex items-center justify-center text-gray-500 text-sm">
                All devices have reported recently.
              </div>
            ) : (
              <ul className="space-y-2">
                {data.offline_devices.map(d => (
                  <li key={d.id} className="text-sm p-3 bg-gray-800/50 rounded flex justify-between items-center border border-white/5">
                    <div className="flex flex-col">
                      <span className="font-medium text-gray-200">{d.name}</span>
                      <span className="text-xs text-gray-500">{d.room}</span>
                    </div>
                    <div className="flex flex-col items-end text-xs">
                      {d.status === 'No Data' ? (
                        <span className="text-orange-400 shrink-0 bg-orange-500/10 px-2 py-1 rounded">Never updated</span>
                      ) : (
                        <>
                          <span className="text-gray-400">Offline</span>
                          <span className="text-orange-400 shrink-0 bg-orange-500/10 px-2 py-1 rounded mt-1">
                            {formatUptime(d.last_update_age_s)}
                          </span>
                        </>
                      )}
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      </div>

      {/* BOTTOM ROW: Recent Logs & Tools */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Recent Logs (Takes up 2 columns) */}
        <div className="lg:col-span-2 glass-panel p-6 rounded-xl border border-white/5 bg-gray-900/50">
          <div className="flex items-center gap-3 mb-4">
            <div className="p-2 bg-gray-500/10 rounded-lg text-gray-400"><Terminal className="w-6 h-6" /></div>
            <h3 className="text-xl font-semibold">Recent Logs</h3>
          </div>
          <div className="bg-black/50 p-4 rounded-lg border border-white/5 overflow-x-auto h-[150px] overflow-y-auto">
            <pre className="text-xs text-green-400 font-mono whitespace-pre-wrap">
              {data?.recent_logs && data.recent_logs.length > 0 
                ? data.recent_logs.join('\n') 
                : 'No recent logs found.'}
            </pre>
          </div>
        </div>

        {/* Tools (Takes up 1 column) */}
        <div className="glass-panel p-6 rounded-xl border border-white/5 bg-gray-900/50">
          <h3 className="text-xl font-semibold mb-4">Diagnostic Tools</h3>
          <div className="space-y-3">
            <Link href="/diagnostics/ga-tester" className="block p-4 rounded-lg bg-gray-800/50 hover:bg-gray-700/50 transition-colors border border-white/5">
              <div className="flex items-center justify-between">
                <div>
                  <h4 className="font-medium text-blue-400">GA Tester</h4>
                  <p className="text-xs text-gray-400 mt-1">Read/Write raw KNX telegrams</p>
                </div>
                <span className="text-xl">🧪</span>
              </div>
            </Link>
            <Link href="/diagnostics/bus-monitor" className="block p-4 rounded-lg bg-gray-800/50 hover:bg-gray-700/50 transition-colors border border-white/5">
              <div className="flex items-center justify-between">
                <div>
                  <h4 className="font-medium text-purple-400">Bus Monitor</h4>
                  <p className="text-xs text-gray-400 mt-1">Real-time KNX traffic</p>
                </div>
                <span className="text-xl">📡</span>
              </div>
            </Link>
          </div>
        </div>

      </div>
    </div>
  );
}
