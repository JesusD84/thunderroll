const path = require('path');

const isDev = process.env.NODE_ENV !== 'production';

/**
 * Content-Security-Policy compatible con Next.js.
 *
 * - `script-src` necesita 'unsafe-inline': Next.js inyecta scripts de
 *   arranque para la hidratación y no hay forma de añadirles un nonce sin
 *   reescribir cada etiqueta. En desarrollo además hace falta
 *   'unsafe-eval' (React en modo desarrollo y el source map del bundler).
 * - `style-src` necesita 'unsafe-inline' por los estilos que inyectan
 *   Radix/Tailwind en tiempo de ejecución.
 * - `connect-src` es solo 'self': desde que las llamadas al backend pasan
 *   por el proxy de este mismo origen, el navegador no habla con ningún
 *   otro origen (y por eso ya no necesita CORS).
 */
const contentSecurityPolicy = [
  "default-src 'self'",
  `script-src 'self' 'unsafe-inline'${isDev ? " 'unsafe-eval'" : ''}`,
  "style-src 'self' 'unsafe-inline'",
  "img-src 'self' data: blob:",
  "font-src 'self' data:",
  `connect-src 'self'${isDev ? ' ws:' : ''}`,
  "object-src 'none'",
  "base-uri 'self'",
  "form-action 'self'",
  "frame-ancestors 'none'",
  ...(isDev ? [] : ['upgrade-insecure-requests']),
].join('; ');

/** @type {import('next').NextConfig} */
const nextConfig = {
  distDir: process.env.NEXT_DIST_DIR || '.next',
  output: process.env.NEXT_OUTPUT_MODE,
  experimental: {
    outputFileTracingRoot: path.join(__dirname, '../'),
  },
  eslint: {
    ignoreDuringBuilds: true,
  },
  typescript: {
    ignoreBuildErrors: false,
  },
  images: { unoptimized: true },
  async headers() {
    return [
      {
        source: '/:path*',
        headers: [
          { key: 'Content-Security-Policy', value: contentSecurityPolicy },
          { key: 'X-Frame-Options', value: 'DENY' },
          { key: 'Referrer-Policy', value: 'strict-origin-when-cross-origin' },
          { key: 'X-Content-Type-Options', value: 'nosniff' },
          {
            key: 'Permissions-Policy',
            value:
              'camera=(), microphone=(), geolocation=(), payment=(), usb=(), interest-cohort=()',
          },
        ],
      },
    ];
  },
};

module.exports = nextConfig;
