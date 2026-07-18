/** @type {import('next').NextConfig} */
const nextConfig = {
  allowedDevOrigins: ['10.1.10.116', '*'],
  experimental: {
    proxyClientMaxBodySize: '100mb',
  },
};
export default nextConfig;
