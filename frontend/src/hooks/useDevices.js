import { useState, useEffect } from 'react';
import { getDevices } from '../api/devicesApi';
import { Lightbulb, Thermometer, Blinds, Wind, Activity } from 'lucide-react';

export function useDevices() {
  const [devices, setDevices] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let mounted = true;

    async function loadDevices() {
      try {
        setIsLoading(true);
        const data = await getDevices();
        if (mounted) {
          const rawDevices = Object.values(data).filter(d => 
            (d.onoff_ga || d.type === 'sensor') && 
            !d.device_id.startsWith('bulk_light_') && 
            !d.device_id.startsWith('test_light') &&
            d.device_id !== 'room_all_on' && 
            d.device_id !== 'room_all_off'
          );

          const roomLabels = {
            phong_rd: 'Phòng R&D',
            living_room: 'Phòng khách',
            bedroom: 'Phòng ngủ'
          };

          // Normalize the backend dict payload into an array for the UI
          const normalized = rawDevices.map(d => {
            // Pick an icon based on type (default Lightbulb)
            let IconComponent = Lightbulb;
            if (d.type === 'ac' || d.type === 'hvac') IconComponent = Thermometer;
            else if (d.type === 'curtain') IconComponent = Blinds;
            else if (d.type === 'appliance') IconComponent = Wind;
            else if (d.type === 'sensor') IconComponent = Activity;

            return {
              id: d.device_id,
              name: d.name,
              room: roomLabels[d.room] || d.room || 'Chưa phân phòng',
              type: d.type,
              icon: IconComponent,
              isOn: d.state === 'on', // Assuming the backend starts providing state or it defaults to off for now
              value: d.value || (d.state === 'on' ? '100%' : 'Off'),
              capabilities: [
                ...(d.onoff_ga ? ['on_off', 'switch'] : []),
                ...(d.brightness_ga ? ['brightness', 'dim'] : [])
              ]
            };
          });

          setDevices(normalized);
          setError(null);
        }
      } catch (err) {
        if (mounted) {
          setError(err.message);
        }
      } finally {
        if (mounted) {
          setIsLoading(false);
        }
      }
    }

    loadDevices();
    
    return () => { mounted = false; };
  }, []);

  return { devices, isLoading, error, setDevices };
}
