import React from 'react';

export default function StatusBadge({ label, status, customText }) {
  const getStatusColor = () => {
    switch(status) {
      case 'online': return 'var(--success)';
      case 'offline': return 'var(--danger)';
      case 'warning': return 'var(--warning)';
      default: return 'var(--text-muted)';
    }
  };

  return (
    <div className="status-badge glass-panel">
      <span className="status-dot" style={{ backgroundColor: getStatusColor() }}></span>
      <span className="status-label">{label}{customText ? ` · ${customText}` : ''}</span>
    </div>
  );
}
