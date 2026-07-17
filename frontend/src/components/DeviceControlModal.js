import React, { useState, useEffect } from 'react';

export default function DeviceControlModal({ device, onClose, onControl }) {
  const [brightness, setBrightness] = useState(0);

  // Parse initial brightness from device value
  /* eslint-disable react-hooks/set-state-in-effect */
  useEffect(() => {
    if (device && device.value) {
      if (device.value === 'Off') {
        setBrightness(0);
      } else if (device.value === '100%' || device.value === 'ON') {
        setBrightness(100);
      } else {
        const val = parseInt(device.value.replace('%', ''), 10);
        if (!isNaN(val)) setBrightness(val);
      }
    } else {
      setBrightness(device?.isOn ? 100 : 0);
    }
  }, [device]);
  /* eslint-enable react-hooks/set-state-in-effect */

  const handleBrightnessChange = (e) => {
    const val = parseInt(e.target.value, 10);
    setBrightness(val);
  };

  const handleBrightnessRelease = () => {
    if (onControl) {
      if (brightness === 0) {
        onControl(device.id, 'off');
      } else {
        onControl(device.id, 'brightness', brightness);
      }
    }
  };

  if (!device) return null;

  const isDimmable = device.capabilities?.includes('brightness') || device.capabilities?.includes('dimmer');
  
  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-[9999] flex items-center justify-center p-4 animate-fade-in" onClick={onClose}>
      <div 
        className="bg-[#1c1c1e] border border-white/10 rounded-[2.5rem] p-8 w-full max-w-md shadow-2xl relative"
        onClick={(e) => e.stopPropagation()} // Prevent closing when clicking inside
      >
        {/* Header */}
        <div className="flex justify-between items-start mb-8">
          <div>
            <h2 className="text-2xl font-semibold text-white mb-1">{device.name}</h2>
            <p className="text-slate-400 font-medium">
              {brightness > 0 ? `Đang bật · ${brightness}%` : 'Đã tắt'}
            </p>
          </div>
          <button 
            onClick={onClose}
            className="w-10 h-10 rounded-full bg-white/10 hover:bg-white/20 text-white flex items-center justify-center transition-colors"
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="18" y1="6" x2="6" y2="18"></line>
              <line x1="6" y1="6" x2="18" y2="18"></line>
            </svg>
          </button>
        </div>

        {/* Content */}
        <div className="space-y-8">
          {/* Dimmer / Brightness Slider */}
          {isDimmable ? (
            <div className="space-y-4">
              <div className="flex justify-between text-sm font-medium text-slate-400">
                <span>0%</span>
                <span>Độ sáng</span>
                <span>100%</span>
              </div>
              <input 
                type="range" 
                min="0" 
                max="100" 
                value={brightness}
                onChange={handleBrightnessChange}
                onMouseUp={handleBrightnessRelease}
                onTouchEnd={handleBrightnessRelease}
                className="w-full h-12 bg-white/10 rounded-2xl appearance-none cursor-pointer outline-none focus:ring-2 focus:ring-emerald-500 transition-all slider-apple"
                style={{
                  background: `linear-gradient(to right, white ${brightness}%, rgba(255,255,255,0.1) ${brightness}%)`
                }}
              />
            </div>
          ) : (
            <div className="flex justify-center py-4">
              <button 
                className={`w-32 h-32 rounded-full flex flex-col items-center justify-center transition-all duration-300 shadow-xl ${
                  brightness > 0 
                    ? 'bg-white text-amber-500 shadow-[0_0_40px_rgba(255,255,255,0.2)]' 
                    : 'bg-white/5 text-slate-400 border border-white/10'
                }`}
                onClick={() => {
                  const newVal = brightness > 0 ? 0 : 100;
                  setBrightness(newVal);
                  onControl && onControl(device.id, newVal > 0 ? 'on' : 'off');
                }}
              >
                {device.icon ? <device.icon size={48} className="mb-2" /> : (
                  <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="mb-2">
                    <path d="M15 14c.2-1 .7-1.7 1.5-2.5 1-.9 1.5-2.2 1.5-3.5A6 6 0 0 0 6 8c0 1 .2 2.2 1.5 3.5.7.9 1.3 1.5 1.5 2.5"/>
                    <path d="M9 18h6"/><path d="M10 22h4"/>
                  </svg>
                )}
                <span className={`font-semibold ${brightness > 0 ? 'text-slate-900' : 'text-slate-400'}`}>
                  {brightness > 0 ? 'TẮT' : 'BẬT'}
                </span>
              </button>
            </div>
          )}
          
          {/* Add a specific Apple style CSS for slider thumb */}
          <style dangerouslySetInnerHTML={{__html: `
            .slider-apple::-webkit-slider-thumb {
              appearance: none;
              width: 32px;
              height: 48px;
              border-radius: 12px;
              background: white;
              box-shadow: 0 2px 10px rgba(0,0,0,0.3);
              cursor: grab;
            }
            .slider-apple::-webkit-slider-thumb:active {
              cursor: grabbing;
              transform: scale(1.1);
            }
          `}} />
        </div>
      </div>
    </div>
  );
}
