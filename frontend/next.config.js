/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  transpilePackages: ['three'],
  images: {
    domains: ['localhost', 'supabase.co'],
  },
}

module.exports = nextConfig
