import React from 'react';

export default function DeviceCard({ id, name, type, icon: Icon, isOn, value, capabilities = [], onToggle, onControl, onOpenControl }) {
  // Determine if it's a special device (has dimming or color)
  const isSpecial = onOpenControl !== null && onOpenControl !== undefined;

  return (
    <div 
      className={`relative p-4 rounded-2xl cursor-pointer transition-all duration-300 border flex flex-col justify-between aspect-square group overflow-hidden ${
        isOn 
          ? 'bg-amber-500/10 border-amber-500/20 shadow-lg' 
          : 'bg-white/5 border-white/10 hover:bg-white/10'
      }`}
      onClick={() => onOpenControl && onOpenControl()}
    >
      {/* Centered Large Dimmed Icon used as toggle button */}
      {type === 'sensor' ? (
        <div className="absolute inset-0 m-auto flex items-center justify-center transition-all duration-300 text-blue-400 opacity-20 scale-100 group-hover:scale-105">
          {Icon ? <Icon size={80} strokeWidth={1} /> : (
            <svg width="80" height="80" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/>
            </svg>
          )}
        </div>
      ) : (
        <button 
          className={`absolute inset-0 m-auto flex items-center justify-center transition-all duration-300 ${
            isOn ? 'text-amber-400 opacity-30 drop-shadow-[0_0_15px_rgba(251,191,36,0.8)] scale-110' : 'text-slate-500 opacity-10 group-hover:opacity-20 scale-100 group-hover:scale-105'
          }`}
          onClick={(e) => {
            e.stopPropagation();
            onToggle && onToggle(id, !isOn);
          }}
          aria-label={isOn ? "Turn Off" : "Turn On"}
        >
          {Icon ? <Icon size={80} strokeWidth={1} /> : (
            <svg width="80" height="80" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1" strokeLinecap="round" strokeLinejoin="round">
              <path d="M15 14c.2-1 .7-1.7 1.5-2.5 1-.9 1.5-2.2 1.5-3.5A6 6 0 0 0 6 8c0 1 .2 2.2 1.5 3.5.7.9 1.3 1.5 1.5 2.5"/>
              <path d="M9 18h6"/><path d="M10 22h4"/>
            </svg>
          )}
        </button>
      )}
      
      {/* Empty div to push the bottom text down in the flex container */}
      <div></div>
      
      <div className="mt-auto relative z-10 pointer-events-none flex flex-col items-center text-center">
        <h4 className={`text-[15px] font-semibold mb-0.5 leading-tight tracking-tight line-clamp-2 ${
          isOn ? 'text-white' : 'text-slate-300'
        }`}>{name}</h4>
        <div className={`flex items-center justify-center gap-1.5 ${capabilities?.includes('dim') ? 'mb-2' : ''}`}>
          {type === 'sensor' ? (
             <span className="text-[14px] font-semibold text-blue-400/90">{value || 'N/A'}</span>
          ) : (
            <>
              <span className={`text-[13px] font-medium transition-colors ${
                isOn ? 'text-amber-400' : 'text-slate-500'
              }`}>{
                type === 'curtain' ? (isOn ? 'Đang Mở' : 'Đang Đóng') : (isOn ? 'Đang Bật' : 'Đã Tắt')
              }</span>
              {isOn && value && value !== '100%' && value !== 'Off' && value !== 'ON' && !capabilities?.includes('dim') && (
                <span className="text-[13px] font-semibold text-amber-400/80">· {value}</span>
              )}
            </>
          )}
        </div>

        {/* Dimmer Slider */}
        {capabilities?.includes('dim') && (
          <div className="w-full px-2 pointer-events-auto h-6 flex items-center justify-center" onClick={e => e.stopPropagation()}>
            <input
              type="range"
              min="0"
              max="100"
              value={isOn && value && value !== 'Off' && value !== 'ON' ? parseInt(value) || 0 : (isOn ? 100 : 0)}
              onChange={(e) => {
                  const val = parseInt(e.target.value);
                  if (val === 0) {
                      onToggle && onToggle(id, false);
                  } else {
                      onControl && onControl(id, 'brightness', val);
                  }
              }}
              className="w-full h-1.5 bg-white/10 rounded-lg appearance-none cursor-pointer accent-amber-500 hover:bg-white/20 transition-colors focus:outline-none"
            />
          </div>
        )}
      </div>
    </div>
  );
}
