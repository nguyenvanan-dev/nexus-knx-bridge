'use client';

import { useState, useEffect } from 'react';
import StatusBadge from '../components/StatusBadge';
import RoomChip from '../components/RoomChip';
import SceneButton from '../components/SceneButton';
import DeviceCard from '../components/DeviceCard';
import DeviceControlModal from '../components/DeviceControlModal';

import { useDevices } from '../hooks/useDevices';
import { mockRooms } from '../mock/rooms';
import { mockScenes } from '../mock/scenes';

import { controlDevice } from '../api/controlApi';

export default function Dashboard() {
  const [activeRoom, setActiveRoom] = useState('all');
  const [selectedDevice, setSelectedDevice] = useState(null);
  const { devices, isLoading, error, setDevices } = useDevices();
  const [commandState, setCommandState] = useState({ status: 'idle', message: '' });
  const [knxStatus, setKnxStatus] = useState('CHECKING');

  useEffect(() => {
    const fetchHealth = async () => {
      try {
        const res = await fetch('/api/health/detail');
        if (res.ok) {
          const data = await res.json();
          setKnxStatus(data.knx_bus === 'connected' ? 'LIVE KNX' : 'DISCONNECTED');
        } else {
          setKnxStatus('DISCONNECTED');
        }
      } catch (err) {
        setKnxStatus('DISCONNECTED');
      }
    };
    fetchHealth();
    // Refresh health status every 30 seconds
    const interval = setInterval(fetchHealth, 30000);
    return () => clearInterval(interval);
  }, []);

  const handleControl = async (id, action, value = null) => {
    const device = devices.find(d => d.id === id);
    if (!device) return;

    const previousDevices = [...devices];
    
    // Optimistic Update
    setDevices(devices.map(d => {
      if (d.id === id) {
          if (action === 'on' || action === 'off') {
              return { ...d, isOn: action === 'on', value: action === 'on' ? '100%' : 'Off' };
          } else if (action === 'brightness') {
              return { ...d, isOn: value > 0, value: value > 0 ? `${value}%` : 'Off' };
          }
      }
      return d;
    }));
    setCommandState({ status: 'sending', message: 'Sending command...' });

    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 5000);
      
      const payload = { device: id, action: action };
      if (value !== null) payload.value = value;
      
      // We use controlDevice which has been updated to accept an object
      await controlDevice({ deviceId: id, action, value, signal: controller.signal });
      clearTimeout(timeoutId);
      
      setCommandState({ status: 'success', message: 'Device updated' });
      setTimeout(() => setCommandState({ status: 'idle', message: '' }), 2000);
    } catch (err) {
      console.error('Control failed:', err);
      // Rollback
      setDevices(previousDevices);
      setCommandState({ status: 'error', message: err.name === 'AbortError' ? 'Command timed out' : 'Command failed' });
      setTimeout(() => setCommandState({ status: 'idle', message: '' }), 3000);
    }
  };

  // Adapter for old onToggle
  const handleToggle = (id, newState) => {
      handleControl(id, newState ? 'on' : 'off');
  };

  const filteredDevices = activeRoom === 'all' 
    ? devices 
    : devices.filter(d => d.room === activeRoom);

  return (
    <div className="page-container animate-fade-in">
      {/* Top Status */}
      <div style={{ display: 'flex', gap: '16px', marginBottom: '24px', alignItems: 'center' }}>
        <StatusBadge 
          label="KNX Gateway" 
          status={knxStatus === 'LIVE KNX' ? 'online' : knxStatus === 'CHECKING' ? 'warning' : 'offline'} 
          customText={knxStatus}
        />
        {commandState.status !== 'idle' && (
          <span style={{ 
            fontSize: '0.875rem', 
            padding: '4px 12px', 
            borderRadius: '16px',
            backgroundColor: commandState.status === 'error' ? 'rgba(239, 68, 68, 0.1)' : 
                             commandState.status === 'success' ? 'rgba(34, 197, 94, 0.1)' : 'rgba(59, 130, 246, 0.1)',
            color: commandState.status === 'error' ? '#ef4444' : 
                   commandState.status === 'success' ? '#22c55e' : '#3b82f6'
          }}>
            {commandState.message}
          </span>
        )}
      </div>

      {/* Rooms Filter */}
      <div style={{ display: 'flex', gap: '12px', overflowX: 'auto', paddingBottom: '8px', marginBottom: '32px' }} className="no-scrollbar">
        <RoomChip 
          key="all"
          name="Tất Cả (All)"
          isActive={activeRoom === 'all'}
          onClick={() => setActiveRoom('all')}
        />
        {Array.from(new Set(devices.map(d => d.room).filter(Boolean))).map(room => (
          <RoomChip 
            key={room}
            name={room}
            isActive={activeRoom === room}
            onClick={() => setActiveRoom(room)}
          />
        ))}
      </div>

      {/* Control & Test */}
      <h2 style={{ fontSize: '1.25rem', fontWeight: 'bold', marginBottom: '16px' }}>Control & Test</h2>
      {isLoading ? (
        <div style={{ color: 'var(--text-muted)' }}>Loading devices...</div>
      ) : error ? (
        <div style={{ color: 'red' }}>Error loading devices: {error}</div>
      ) : (
        <div className="grid-4">
          {filteredDevices.map(device => (
            <DeviceCard
              key={device.id}
              id={device.id}
              name={device.name}
              type={device.type}
              icon={device.icon}
              isOn={device.isOn}
              value={device.value}
              capabilities={device.capabilities}
              onToggle={handleToggle}
              onControl={handleControl}
              onOpenControl={() => setSelectedDevice(device)}
            />
          ))}
        </div>
      )}

      {/* Recent Events (Placeholder) */}
      <h2 style={{ fontSize: '1.25rem', fontWeight: 'bold', margin: '32px 0 16px' }}>Recent Events</h2>
      <div className="glass-panel" style={{ padding: '24px', textAlign: 'center', color: 'var(--text-muted)' }}>
        No recent events recorded.
      </div>

      {selectedDevice && (
        <DeviceControlModal 
          device={selectedDevice} 
          onClose={() => setSelectedDevice(null)} 
          onControl={handleControl}
        />
      )}
    </div>
  );
}
