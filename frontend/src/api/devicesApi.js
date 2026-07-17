import { fetchApi } from './client';

export const getDevices = () => {
  return fetchApi('/api/devices');
};
