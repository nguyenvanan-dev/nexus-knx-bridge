import { fetchApi } from './client';

export const controlDevice = async ({ deviceId, action, value = null, signal }) => {
  const payload = {
    device: deviceId,
    action: action
  };
  if (value !== null && value !== undefined) {
    payload.value = value;
  }
  
  return fetchApi('/api/devices/control', {
    method: 'POST',
    signal: signal,
    body: JSON.stringify(payload)
  });
};
