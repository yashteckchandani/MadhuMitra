import type { NextConfig } from 'next';

const nextConfig: NextConfig = {
  // Development and production builds must not overwrite each other's artifacts.
  distDir: process.env.NODE_ENV === 'development' ? '.next-dev' : '.next',
};

export default nextConfig;
