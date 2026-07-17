import React from 'react';

export default function RoomChip({ name, isActive, onClick }) {
  return (
    <button 
      className={`room-chip ${isActive ? 'active' : ''}`}
      onClick={onClick}
    >
      {name}
    </button>
  );
}
