'use client';
import { useState, useEffect } from 'react';

export default function Home() {
  const [health, setHealth] = useState(null);
  const [loading, setLoading] = useState(true);

  const fetchHealth = async () => {
    try {
      const res = await fetch('/api/health');
      const data = await res.json();
      setHealth(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHealth();
    const interval = setInterval(fetchHealth, 5000);
    return () => clearInterval(interval);
  }, []);

  return (
    <>
      <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2 style={{ fontSize: '1.5rem', fontWeight: '600' }}>Dashboard Overview</h2>
          <p style={{ color: 'var(--text-secondary)', marginTop: '4px' }}>Hệ sinh thái KNX AI Smart Home</p>
        </div>
        {health && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.9rem' }}>
            <span style={{ 
              display: 'inline-block', 
              width: '10px', 
              height: '10px', 
              borderRadius: '50%', 
              backgroundColor: health.ok ? '#10b981' : '#ef4444' 
            }}></span>
            {health.ok ? 'System Online' : 'System Offline'}
          </div>
        )}
      </header>

      {loading ? (
        <div style={{ marginTop: '40px', textAlign: 'center', color: 'var(--text-secondary)' }}>Đang tải dữ liệu hệ thống...</div>
      ) : health ? (
        <>
          <div className='grid-3' style={{marginTop: '24px'}}>
            <div className='glass-panel stat-card'>
              <div className='stat-label'>Tổng số thiết bị KNX</div>
              <div className='stat-value gradient-text'>{health.devices}</div>
            </div>
            <div className='glass-panel stat-card'>
              <div className='stat-label'>KNX Gateway</div>
              <div className='stat-value' style={{ color: health.knx_connected ? '#10b981' : '#ef4444' }}>
                {health.knx_connected ? 'Connected' : 'Disconnected'}
              </div>
              <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '8px' }}>
                {health.knx_gateway_ip}:{health.knx_gateway_port}
              </div>
            </div>
            <div className='glass-panel stat-card'>
              <div className='stat-label'>AI OpenClaw Proposals</div>
              <div className='stat-value'>{health.pending_proposals} <span style={{fontSize: '1rem', color: 'var(--text-secondary)'}}>pending</span></div>
            </div>
          </div>

          <h3 style={{ fontSize: '1.2rem', fontWeight: '500', marginTop: '32px', marginBottom: '16px' }}>Hardware Metrics (Raspberry Pi)</h3>
          <div className='grid-4' style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '16px' }}>
            <div className='glass-panel' style={{ padding: '20px', textAlign: 'center' }}>
              <div style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', marginBottom: '8px' }}>CPU Usage</div>
              <div style={{ fontSize: '1.5rem', fontWeight: 'bold', color: health.hardware?.cpu_percent > 80 ? '#ef4444' : 'var(--text-primary)' }}>
                {health.hardware?.cpu_percent}%
              </div>
            </div>
            <div className='glass-panel' style={{ padding: '20px', textAlign: 'center' }}>
              <div style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', marginBottom: '8px' }}>RAM Usage</div>
              <div style={{ fontSize: '1.5rem', fontWeight: 'bold', color: health.hardware?.ram_percent > 80 ? '#ef4444' : 'var(--text-primary)' }}>
                {health.hardware?.ram_percent}%
              </div>
            </div>
            <div className='glass-panel' style={{ padding: '20px', textAlign: 'center' }}>
              <div style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', marginBottom: '8px' }}>Disk Usage</div>
              <div style={{ fontSize: '1.5rem', fontWeight: 'bold' }}>
                {health.hardware?.disk_percent}%
              </div>
            </div>
            <div className='glass-panel' style={{ padding: '20px', textAlign: 'center' }}>
              <div style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', marginBottom: '8px' }}>Temperature</div>
              <div style={{ fontSize: '1.5rem', fontWeight: 'bold', color: health.hardware?.temperature > 70 ? '#ef4444' : 'var(--text-primary)' }}>
                {health.hardware?.temperature ? `${health.hardware.temperature}°C` : 'N/A'}
              </div>
            </div>
          </div>
          
          <div style={{ marginTop: '32px', fontSize: '0.9rem', color: 'var(--text-secondary)', textAlign: 'center' }}>
            FastAPI Version: {health.version} • OS: {health.hardware?.os} • Local IP: {health.knx_local_ip}
          </div>
        </>
      ) : (
        <div style={{ marginTop: '40px', textAlign: 'center', color: '#ef4444' }}>Không thể kết nối đến Backend API!</div>
      )}
    </>
  );
}
