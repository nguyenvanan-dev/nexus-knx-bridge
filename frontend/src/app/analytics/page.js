'use client';
import { useState, useEffect } from 'react';
import Link from 'next/link';

function StatCard({ title, value, sub }) {
  return (
    <div className="relative p-6 rounded-2xl cursor-pointer transition-all duration-300 backdrop-blur-xl border bg-white/5 border-white/5 hover:bg-emerald-900/10 hover:border-emerald-500/50 hover:shadow-[0_0_20px_rgba(16,185,129,0.15)] flex flex-col justify-between group" style={{ padding: '24px' }}>
      <div className="mb-4" style={{ marginBottom: '16px' }}>
        <div className="text-[2rem] font-light text-white leading-none drop-shadow-[0_0_8px_rgba(255,255,255,0.4)] group-hover:text-emerald-400 group-hover:drop-shadow-[0_0_12px_rgba(16,185,129,0.8)] transition-all duration-300">{value}</div>
      </div>
      <div>
        <div className="text-xs font-medium text-slate-400 uppercase tracking-widest">{title}</div>
        {sub && <div className="text-[10px] text-emerald-400 font-semibold mt-1 uppercase tracking-wide opacity-80">{sub}</div>}
      </div>
    </div>
  );
}

function HourHeatmap({ data }) {
  const maxVal = Math.max(...data.map(d => d.cnt), 1);
  const hours = Array.from({ length: 24 }, (_, i) => {
    const found = data.find(d => d.hour === i);
    return { hour: i, cnt: found?.cnt || 0 };
  });
  return (
    <div>
      <h3 className="text-sm font-semibold text-slate-300 mb-6 tracking-wide" style={{ marginBottom: '24px' }}>Activity by Hour (last 7 days)</h3>
      <div className="flex gap-1 items-end h-48 md:h-64 w-full" style={{ gap: '4px', marginBottom: '24px' }}>
        {hours.map(({ hour, cnt }) => (
          <div key={hour} className="flex-1 group relative h-full">
            <div
              className="absolute bottom-0 w-full transition-all duration-300 group-hover:opacity-100 opacity-70 group-hover:drop-shadow-[0_0_12px_rgba(6,182,212,0.8)]"
              style={{
                height: cnt === 0 ? '4px' : `${Math.max(2, (cnt / maxVal) * 100)}%`,
                borderTopLeftRadius: '3px',
                borderTopRightRadius: '3px',
                background: cnt === 0 ? 'rgba(255, 255, 255, 0.05)' : `linear-gradient(to top, rgba(6, 182, 212, ${0.4 + (cnt / maxVal) * 0.6}), rgba(16, 185, 129, ${0.6 + (cnt / maxVal) * 0.4}))`,
              }}
            />
            {hour % 4 === 0 && (
              <div className="absolute top-[calc(100%+8px)] left-1/2 -translate-x-1/2 text-[10px] font-medium text-slate-400">
                {hour}h
              </div>
            )}
            {/* Tooltip */}
            <div className="absolute bottom-full mb-2 left-1/2 -translate-x-1/2 bg-slate-800 border border-white/10 text-[var(--accent)] font-bold text-xs px-3 py-1.5 rounded shadow-xl whitespace-nowrap opacity-0 group-hover:opacity-100 pointer-events-none z-10 transition-all duration-200">
              {hour}:00 — {cnt} events
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function BarChart({ data, label = 'cnt', nameKey = 'who', title, maxItems = 10, color = 'linear-gradient(90deg, #06b6d4, #10b981)' }) {
  const items = data.slice(0, maxItems);
  const maxVal = Math.max(...items.map(d => d[label]), 1);
  return (
    <div>
      <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-widest mb-4" style={{ marginBottom: '16px' }}>{title}</h3>
      <div className="space-y-4" style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
        {items.map((item, i) => (
          <div key={i} className="flex items-center gap-3 group" style={{ gap: '12px' }}>
            <div className="w-32 text-xs text-slate-400 truncate flex-shrink-0 transition-colors group-hover:text-emerald-400" title={item[nameKey]}>{item[nameKey]}</div>
            <div className="flex-1 h-2 bg-white/5 rounded-full overflow-hidden border border-white/5 shadow-inner">
              <div className="h-full rounded-full transition-all duration-700 group-hover:drop-shadow-[0_0_5px_rgba(16,185,129,0.5)]"
                style={{ width: `${(item[label] / maxVal) * 100}%`, background: color }} />
            </div>
            <div className="text-xs text-slate-300 font-medium w-12 text-right group-hover:text-white transition-colors">{item[label]}</div>
          </div>
        ))}
        {items.length === 0 && <p className="text-slate-500 text-sm text-center py-4">No data yet</p>}
      </div>
    </div>
  );
}

export default function AnalyticsPage() {
  const [data, setData] = useState(null);
  const [days, setDays] = useState(30);
  const [loading, setLoading] = useState(true);

  /* eslint-disable react-hooks/set-state-in-effect */
  useEffect(() => {
    setLoading(true);
    fetch(`/api/analytics/summary?days=${days}`)
      .then(r => r.json())
      .then(d => { setData(d); setLoading(false); })
      .catch(() => setLoading(false));
  }, [days]);
  /* eslint-enable react-hooks/set-state-in-effect */

  const total = data?.commands?.total || 0;
  const success = data?.commands?.success || 0;
  const successRate = total ? Math.round((success / total) * 100) : 0;
  const autoTotal = data?.automation_commands || 0;
  const manualTotal = total - autoTotal;

  return (
    <div className="page-container animate-fade-in flex flex-col h-full max-h-full">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between mb-8 gap-4 shrink-0" style={{ marginBottom: '32px', gap: '16px' }}>
        <div className="flex flex-col">
          <div className="flex items-center gap-2 text-[var(--accent)] mb-1" style={{ gap: '8px', marginBottom: '4px' }}>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M3 3v18h18"/><path d="m19 9-5 5-4-4-3 3"/></svg>
            <span className="text-sm font-semibold tracking-wider uppercase">Command Telemetry</span>
          </div>
          <h2 className="text-2xl font-bold text-[var(--text-primary)]">System Analytics</h2>
          <p className="text-sm text-[var(--text-secondary)] mt-1" style={{ marginTop: '4px' }}>Hộp đen giám sát luồng lệnh điều khiển hệ thống KNX</p>
        </div>
        <div className="flex items-center gap-2 bg-[var(--bg-elevated)] p-1.5 rounded-xl border border-[var(--border)] shadow-lg overflow-x-auto" style={{ gap: '8px', padding: '6px' }}>
          {[7, 14, 30, 90].map(d => (
            <button key={d} onClick={() => setDays(d)}
              className={`px-5 py-2 rounded-lg text-sm font-semibold transition-all duration-300 whitespace-nowrap ${days === d ? 'bg-[var(--accent)]/20 text-[var(--accent)] drop-shadow-[0_0_8px_rgba(16,185,129,0.8)]' : 'text-[var(--text-secondary)] hover:text-white hover:bg-[var(--bg-hover)]'}`}>
              {d} ngày
            </button>
          ))}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto custom-scrollbar space-y-6 pb-6" style={{ paddingBottom: '24px', display: 'flex', flexDirection: 'column', gap: '24px' }}>
        {loading ? (
          <div className="flex items-center justify-center py-20" style={{ padding: '80px 0' }}>
            <div className="text-gray-400">Loading analytics…</div>
          </div>
        ) : (
          <>
            {/* Top Stats */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4" style={{ gap: '16px' }}>
              <StatCard title="Total Commands" value={total.toLocaleString()} sub={`Last ${days} days`} />
              <StatCard title="Success Rate" value={`${successRate}%`} sub={`${success} succeeded`} />
              <StatCard title="Automation" value={autoTotal.toLocaleString()} sub={total ? `${Math.round((autoTotal / total) * 100)}% of all` : '—'} />
              <StatCard title="Manual" value={manualTotal.toLocaleString()} sub={total ? `${Math.round((manualTotal / total) * 100)}% of all` : '—'} />
            </div>

            {/* Charts row */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6" style={{ gap: '24px' }}>
              <div className="bg-white/5 border border-white/5 backdrop-blur-xl rounded-2xl p-6 transition-all duration-300 hover:border-white/20 hover:shadow-[0_0_15px_rgba(255,255,255,0.05)]" style={{ padding: '24px' }}>
                <HourHeatmap data={data?.by_hour || []} />
              </div>
              <div className="bg-white/5 border border-white/5 backdrop-blur-xl rounded-2xl p-6 transition-all duration-300 hover:border-white/20 hover:shadow-[0_0_15px_rgba(255,255,255,0.05)]" style={{ padding: '24px' }}>
                <BarChart
                  data={data?.top_devices || []}
                  label="cnt" nameKey="device_id"
                  title="Most Active Devices"
                  color="linear-gradient(90deg, #06b6d4, #10b981)"
                />
              </div>
            </div>

            {/* Commands by source */}
            <div className="bg-white/5 border border-white/5 backdrop-blur-xl rounded-2xl p-6 transition-all duration-300 hover:border-white/20 hover:shadow-[0_0_15px_rgba(255,255,255,0.05)]" style={{ padding: '24px' }}>
              <BarChart
                data={data?.by_source || []}
                label="cnt" nameKey="who"
                title="Commands by Source"
                maxItems={10}
                color="linear-gradient(90deg, #3b82f6, #06b6d4)"
              />
            </div>

            {/* Breakdown */}
            <div className="bg-white/5 border border-white/5 backdrop-blur-xl rounded-2xl p-6 transition-all duration-300 hover:border-white/20 hover:shadow-[0_0_15px_rgba(255,255,255,0.05)]" style={{ padding: '24px' }}>
              <h3 className="text-sm font-semibold text-slate-300 mb-6 tracking-wide" style={{ marginBottom: '24px' }}>Command Pipeline Breakdown</h3>
              <div className="flex gap-8 flex-wrap" style={{ gap: '32px' }}>
                {[
                  { label: 'API / Dashboard', value: (data?.by_source || []).filter(s => s.who === 'api').reduce((a, b) => a + b.cnt, 0), color: 'bg-cyan-500' },
                  { label: 'Automation', value: autoTotal, color: 'bg-purple-500' },
                  { label: 'AI Agent', value: (data?.by_source || []).filter(s => s.who?.includes('ai') || s.who?.includes('agent')).reduce((a, b) => a + b.cnt, 0), color: 'bg-emerald-500' },
                ].map(item => (
                  <div key={item.label} className="flex items-center gap-3" style={{ gap: '12px' }}>
                    <div className={`w-3 h-3 rounded-full ${item.color} shadow-[0_0_8px_currentColor]`} />
                    <span className="text-sm text-slate-400 font-medium">{item.label}:</span>
                    <span className="text-sm text-white font-bold">{item.value}</span>
                  </div>
                ))}
              </div>

              {/* Progress bar */}
              {total > 0 && (
                <div className="mt-6 h-4 rounded-full overflow-hidden flex bg-white/5 border border-white/10 shadow-inner" style={{ marginTop: '24px' }}>
                  {[
                    { pct: (data?.by_source || []).filter(s => s.who === 'api').reduce((a, b) => a + b.cnt, 0) / total, color: 'bg-cyan-500' },
                    { pct: autoTotal / total, color: 'bg-purple-500' },
                    { pct: (data?.by_source || []).filter(s => s.who?.includes('ai') || s.who?.includes('agent')).reduce((a, b) => a + b.cnt, 0) / total, color: 'bg-emerald-500' },
                  ].map((seg, i) => (
                    <div key={i} className={`h-full transition-all duration-1000 ${seg.color} shadow-[0_0_10px_currentColor]`} style={{ width: `${seg.pct * 100}%` }} />
                  ))}
                </div>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
