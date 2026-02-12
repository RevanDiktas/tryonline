/** @type {import('next').NextConfig} */
// Use 127.0.0.1 (not localhost) to avoid IPv6 ::1 ECONNREFUSED on macOS
const API_BASE = (process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000').replace('localhost', '127.0.0.1');

const nextConfig = {
  reactStrictMode: true,
  transpilePackages: ['three'],
  images: {
    // Add your Supabase project host (e.g. 'xxxxx.supabase.co') for storage images in production
    domains: ['localhost', 'supabase.co'],
  },
  async rewrites() {
    return [
      { source: '/api/:path*', destination: `${API_BASE}/api/:path*` },
      { source: '/health', destination: `${API_BASE}/health` },
    ];
  },
};

module.exports = nextConfig;
