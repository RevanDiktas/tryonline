/** @type {import('next').NextConfig} */
// Use 127.0.0.1 (not localhost) to avoid IPv6 ::1 ECONNREFUSED on macOS
// Strip trailing slashes so rewrite destination is never ...origin//api/...
const API_BASE = (process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000')
  .replace(/\/+$/, '')
  .replace('localhost', '127.0.0.1');

const nextConfig = {
  reactStrictMode: true,
  transpilePackages: ['three'],
  images: {
    domains: ['localhost', 'supabase.co'],
  },
  async rewrites() {
    return [
      { source: '/api/:path*', destination: `${API_BASE}/api/:path*` },
      { source: '/health', destination: `${API_BASE}/health` },
    ];
  },
  async headers() {
    return [
      {
        source: '/test-viewer.html',
        headers: [{ key: 'Content-Security-Policy', value: 'frame-ancestors *' }],
      },
    ];
  },
};

module.exports = nextConfig;
