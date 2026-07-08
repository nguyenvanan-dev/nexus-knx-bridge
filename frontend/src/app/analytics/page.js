'use client';
import { useState, useEffect } from 'react';
import Link from 'next/link';

function StatCard({ title, value, sub, icon, color = 'blue' }) {
  const colors = {
    blue: 'from-blue-500/20 to-blue-600/5 border-blue-500/20 text-blue-400',
    green: 'from-green-500/20 to-green-600/5 border-green-500/20 text-green-400',
    purple: 'from-purple-500/20 to-purple-600/5 border-purple-500/20 text-purple-400',
    amber: 'from-amber-500/20 to-amber-600/5 border-amber-500/20 text-amber-400',
    red: 'from-red-500/20 to-red-600/5 border-red-500/20 text-red-400',
  };
  return (
    <div className={`bg-gradient-to-br ${colors[color]} border rounded-2xl p-5`}>
      <div className="flex items-start justify-between mb-3">
        <div className="text-2xl">{icon}</div>
        <div className={`text-3xl font-bold ${colors[color].split(' ').pop()}`}>{value}</div>
      </div>
      <div className="text-sm font-medium text-gray-200">{title}</div>
      {sub && <div className="text-xs text-gray-500 mt-0.5">{sub}</div>}
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
      <h3 className="text-sm font-semibold text-gray-300 mb-3">Activity by Hour (last 7 days)</h3>
      <div className="flex gap-0.5 items-end h-20">
        {hours.map(({ hour, cnt }) => (
          <div key={hour} className="flex-1 flex flex-col items-center gap-1 group relative">
            <div
              className="w-full rounded-t transition-all duration-300 group-hover:opacity-80"
              style={{
                height: `${Math.max(4, (cnt / maxVal) * 72)}px`,
                background: cnt === 0 ? '#1F2937' : `hsl(${240 - (cnt / maxVal) * 60}, 80%, ${30 + (cnt / maxVal) * 30}%)`,
              }}
            />
            {hour % 6 === 0 && <div className="text-[9px] text-gray-600">{hour}h</div>}
            {/* Tooltip */}
            <div className="absolute bottom-full mb-1 left-1/2 -translate-x-1/2 bg-gray-800 text-white text-[10px] px-2 py-1 rounded whitespace-nowrap opacity-0 group-hover:opacity-100 pointer-events-none z-10">
              {hour}:00 — {cnt} events
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function BarChart({ data, label = 'cnt', nameKey = 'who', title, maxItems = 10, color = '#6366F1' }) {
  const items = data.slice(0, maxItems);
  const maxVal = Math.max(...items.map(d => d[label]), 1);
  return (
    <div>
      <h3 className="text-sm font-semibold text-gray-300 mb-3">{title}</h3>
      <div className="space-y-2">
        {items.map((item, i) => (
          <div key={i} className="flex items-center gap-3">
            <div className="w-32 text-xs text-gray-400 truncate flex-shrink-0" title={item[nameKey]}>{item[nameKey]}</div>
            <div className="flex-1 h-5 bg-gray-800 rounded overflow-hidden">
              <div className="h-full rounded transition-all duration-500"
                style={{ width: `${(item[label] / maxVal) * 100}%`, background: color }} />
            </div>
            <div className="text-xs text-white font-medium w-12 text-right">{item[label]}</div>
          </div>
        ))}
        {items.length === 0 && <p className="text-gray-500 text-sm text-center py-4">No data yet</p>}
      </div>
    </div>
  );
}

export default function AnalyticsPage() {
  const [data, setData] = useState(null);
  const [days, setDays] = useState(30);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    fetch(`/api/analytics/summary?days=${days}`)
      .then(r => r.json())
      .then(d => { setData(d); setLoading(false); })
      .catch(() => setLoading(false));
  }, [days]);

  const total = data?.commands?.total || 0;
  const success = data?.commands?.success || 0;
  const successRate = total ? Math.round((success / total) * 100) : 0;
  const autoTotal = data?.automation_commands || 0;
  const manualTotal = total - autoTotal;

  return (
    <div className="min-h-screen bg-gray-950 text-white">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-gray-800 bg-gray-900/80 backdrop-blur-sm">
        <div className="flex items-center gap-4">
          <Link href="/" className="text-gray-400 hover:text-white transition-colors">← Back</Link>
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-emerald-500 to-teal-400 flex items-center justify-center text-sm">📊</div>
            <h1 className="text-xl font-bold bg-gradient-to-r from-emerald-400 to-teal-300 bg-clip-text text-transparent">Analytics</h1>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {[7, 14, 30, 90].map(d => (
            <button key={d} onClick={() => setDays(d)}
              className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-all ${days === d ? 'bg-emerald-600 text-white' : 'bg-gray-800 text-gray-400 hover:bg-gray-700'}`}>
              {d}d
            </button>
          ))}
        </div>
      </div>

      <div className="max-w-6xl mx-auto p-6 space-y-6">
        {loading ? (
          <div className="flex items-center justify-center py-20">
            <div className="text-gray-400">Loading analytics…</div>
          </div>
        ) : (
          <>
            {/* Top Stats */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <StatCard icon="⚡" title="Total Commands" value={total.toLocaleString()} sub={`Last ${days} days`} color="blue" />
              <StatCard icon="✅" title="Success Rate" value={`${successRate}%`} sub={`${success} succeeded`} color="green" />
              <StatCard icon="🤖" title="Automation" value={autoTotal.toLocaleString()} sub={total ? `${Math.round((autoTotal / total) * 100)}% of all` : '—'} color="purple" />
              <StatCard icon="👤" title="Manual" value={manualTotal.toLocaleString()} sub={total ? `${Math.round((manualTotal / total) * 100)}% of all` : '—'} color="amber" />
            </div>

            {/* Charts row */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="bg-gray-900/60 border border-gray-800 rounded-2xl p-5">
                <HourHeatmap data={data?.by_hour || []} />
              </div>
              <div className="bg-gray-900/60 border border-gray-800 rounded-2xl p-5">
                <BarChart
                  data={data?.top_devices || []}
                  label="cnt" nameKey="device_id"
                  title="Most Active Devices"
                  color="#6366F1"
                />
              </div>
            </div>

            {/* Commands by source */}
            <div className="bg-gray-900/60 border border-gray-800 rounded-2xl p-5">
              <BarChart
                data={data?.by_source || []}
                label="cnt" nameKey="who"
                title="Commands by Source"
                maxItems={10}
                color="#10B981"
              />
            </div>

            {/* Breakdown */}
            <div className="bg-gray-900/60 border border-gray-800 rounded-2xl p-5">
              <h3 className="text-sm font-semibold text-gray-300 mb-4">Command Pipeline Breakdown</h3>
              <div className="flex gap-6 flex-wrap">
                {[
                  { label: 'API / Dashboard', value: (data?.by_source || []).filter(s => s.who === 'api').reduce((a, b) => a + b.cnt, 0), color: 'bg-blue-500' },
                  { label: 'Automation', value: autoTotal, color: 'bg-purple-500' },
                  { label: 'AI Agent', value: (data?.by_source || []).filter(s => s.who?.includes('ai') || s.who?.includes('agent')).reduce((a, b) => a + b.cnt, 0), color: 'bg-amber-500' },
                ].map(item => (
                  <div key={item.label} className="flex items-center gap-2">
                    <div className={`w-3 h-3 rounded-full ${item.color}`} />
                    <span className="text-sm text-gray-400">{item.label}:</span>
                    <span className="text-sm text-white font-medium">{item.value}</span>
                  </div>
                ))}
              </div>

              {/* Progress bar */}
              {total > 0 && (
                <div className="mt-4 h-3 rounded-full overflow-hidden flex bg-gray-800">
                  {[
                    { pct: (data?.by_source || []).filter(s => s.who === 'api').reduce((a, b) => a + b.cnt, 0) / total, color: 'bg-blue-500' },
                    { pct: autoTotal / total, color: 'bg-purple-500' },
                    { pct: (data?.by_source || []).filter(s => s.who?.includes('ai') || s.who?.includes('agent')).reduce((a, b) => a + b.cnt, 0) / total, color: 'bg-amber-500' },
                  ].map((seg, i) => (
                    <div key={i} className={`h-full transition-all duration-700 ${seg.color}`} style={{ width: `${seg.pct * 100}%` }} />
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
