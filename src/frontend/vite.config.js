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
    // Enable minification and treeshaking (default, but explicit)
    minify: 'esbuild',
    // Enable CSS code splitting for per-route optimization
    cssCodeSplit: true,
    rollupOptions: {
      output: {
        // Aggressive manual chunks for optimal lazy loading and caching
        manualChunks: {
          // Core React - always needed, tiny and cached well
          'vendor-react': ['react', 'react-dom'],

          // Map stack - HEAVY, lazy load only when needed (~240KB)
          'vendor-maps': ['leaflet', 'react-leaflet', '@mapbox/togeojson'],

          // Icons - separate chunk for dynamic loading
          'vendor-icons': ['lucide-react'],

          // UI utilities - lightweight, can be in main or separate
          'vendor-utils': ['clsx', 'tailwind-merge'],

          // HTTP client - used by services, separate from main
          'vendor-http': ['axios'],
        },
      },
    },
  },
});
