import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react-swc';
import { visualizer } from 'rollup-plugin-visualizer';

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    react(),
    // Bundle analyzer - generates stats.html after build
    visualizer({
      filename: 'bundle-stats.html',
      open: false,
      gzipSize: true,
      brotliSize: true,
    }),
  ],
  build: {
    // Enable minification and treeshaking
    minify: 'esbuild',
    // Enable CSS code splitting for per-route optimization
    cssCodeSplit: true,
    target: 'esnext',
    modulePreload: {
      polyfill: false,
    },
    rollupOptions: {
      output: {
        // Aggressive manual chunks for optimal lazy loading and caching
        manualChunks(id) {
          if (id.includes('node_modules')) {
            // Core React - separate and cacheable
            if (id.includes('react') || id.includes('react-dom') || id.includes('scheduler')) {
              return 'vendor-react';
            }
            // Sentry - HEAVY, isolate for observability chunk
            if (id.includes('@sentry')) {
              return 'vendor-sentry';
            }
            // Maps - HEAVY, lazy loaded manually but just in case
            if (id.includes('leaflet') || id.includes('react-leaflet')) {
              return 'vendor-maps';
            }
            // Axios and utils
            if (id.includes('axios') || id.includes('clsx') || id.includes('tailwind-merge')) {
              return 'vendor-core';
            }
            // Lucide Icons - Tree-shaking should handle most, but isolate just in case
            if (id.includes('lucide-react')) {
              return 'vendor-icons';
            }
            // Fallback for other node_modules
            return 'vendor-others';
          }
        },
      },
    },
  },
});
