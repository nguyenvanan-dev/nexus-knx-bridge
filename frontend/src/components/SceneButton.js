import React from 'react';

export default function SceneButton({ name, icon: Icon, color }) {
  return (
    <button 
      className="scene-button glass-panel" 
      style={{ 
        display: 'flex', 
        alignItems: 'center', 
        justifyContent: 'center',
        padding: '16px',
        borderLeft: `2px solid ${color}`
      }}
    >
      <span style={{ fontSize: '0.85rem', fontWeight: '500', letterSpacing: '0.05em', textTransform: 'uppercase' }}>{name}</span>
    </button>
  );
}
