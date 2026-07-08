import Link from 'next/link';

export default function DiagnosticsHub() {
  const tools = [
    {
      title: 'Group Address Tester',
      description: 'Read and write raw KNX telegrams to any Group Address. Now supports ETS CSV Import, advanced DPTs, and action history.',
      icon: '🧪',
      href: '/diagnostics/ga-tester',
      status: 'Active',
      color: 'blue'
    },
    {
      title: 'Bus Monitor',
      description: 'Real-time monitoring of all KNX bus traffic. Watch telegrams, filtering by address, payload, or type.',
      icon: '📡',
      href: '/diagnostics/bus-monitor',
      status: 'Active',
      color: 'purple'
    },
    {
      title: 'Device Tester',
      description: 'Simulate and test device states directly from the registry without going through UI or Automation.',
      icon: '📱',
      href: '#',
      status: 'Coming Soon',
      color: 'gray'
    },
    {
      title: 'Telegram Inspector',
      description: 'Deep dive into raw hexadecimal telegrams for protocol debugging and troubleshooting connection issues.',
      icon: '🔍',
      href: '#',
      status: 'Coming Soon',
      color: 'gray'
    },
    {
      title: 'Network Diagnostics',
      description: 'Ping KNX IP Interfaces, trace routes, and check port availability (UDP 3671).',
      icon: '🌐',
      href: '#',
      status: 'Coming Soon',
      color: 'gray'
    },
    {
      title: 'Performance Profiler',
      description: 'Analyze system memory, CPU usage, Event Bus latency, and queue depths.',
      icon: '⚡',
      href: '#',
      status: 'Coming Soon',
      color: 'gray'
    }
  ];

  return (
    <div style={{ padding: '24px', maxWidth: '1200px', margin: '0 auto' }}>
      <header style={{ marginBottom: '32px' }}>
        <h2 style={{ fontSize: '2rem', fontWeight: 'bold', background: 'linear-gradient(90deg, #60a5fa, #c084fc)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
          Diagnostics Hub
        </h2>
        <p style={{ color: 'var(--text-secondary)', marginTop: '8px', fontSize: '1.1rem' }}>
          Centralized command center for system troubleshooting, protocol testing, and performance analysis.
        </p>
      </header>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(350px, 1fr))', gap: '24px' }}>
        {tools.map((tool, idx) => (
          <Link href={tool.href} key={idx} style={{ textDecoration: 'none' }}>
            <div 
              className="glass-panel hover:bg-gray-800/50 transition-all duration-200" 
              style={{ 
                padding: '24px', 
                height: '100%', 
                display: 'flex', 
                flexDirection: 'column',
                border: '1px solid rgba(255,255,255,0.05)',
                cursor: tool.href !== '#' ? 'pointer' : 'default',
                opacity: tool.href !== '#' ? 1 : 0.6
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '16px' }}>
                <div style={{ fontSize: '2.5rem', background: 'rgba(255,255,255,0.05)', width: '60px', height: '60px', display: 'flex', alignItems: 'center', justifyContent: 'center', borderRadius: '12px' }}>
                  {tool.icon}
                </div>
                <span style={{ 
                  fontSize: '0.75rem', 
                  fontWeight: 'bold', 
                  padding: '4px 10px', 
                  borderRadius: '12px',
                  background: tool.status === 'Active' ? 'rgba(16, 185, 129, 0.2)' : 'rgba(255, 255, 255, 0.1)',
                  color: tool.status === 'Active' ? '#10b981' : '#94a3b8'
                }}>
                  {tool.status}
                </span>
              </div>
              
              <h3 style={{ fontSize: '1.3rem', fontWeight: 'bold', color: '#fff', marginBottom: '8px' }}>
                {tool.title}
              </h3>
              
              <p style={{ color: '#94a3b8', fontSize: '0.95rem', lineHeight: '1.5', flex: 1 }}>
                {tool.description}
              </p>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
