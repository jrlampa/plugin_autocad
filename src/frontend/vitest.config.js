import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react-swc';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = process.env.SISRUA_REPO_ROOT
  ? path.resolve(process.env.SISRUA_REPO_ROOT)
  : path.resolve(__dirname, '..', '..');
const defaultJunitPath = path.join(repoRoot, 'qa', 'out', 'unit', 'junit.xml');

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/setupTests.js'],
    css: true,
    globals: true,
    exclude: ['**/node_modules/**', '**/dist/**', '**/e2e/**'],
    reporters: ['default', 'junit'],
    outputFile: {
      junit: process.env.VITEST_JUNIT_OUTPUT_FILE || defaultJunitPath,
    },
    coverage: {
      provider: 'v8',
      reporter: ['text', 'lcov'],
      reportsDirectory: path.join(repoRoot, 'qa', 'out', 'coverage', 'frontend'),
      // Exclude files that cannot be unit-tested in a jsdom environment
      exclude: [
        '**/node_modules/**',
        '**/dist/**',
        '**/e2e/**',
        // Build/config files (not application logic)
        'tailwind.config.*',
        'postcss.config.*',
        // Service worker (runs in separate thread — not testable in jsdom)
        'public/sw.js',
        // App bootstrap (requires real DOM mount)
        'src/main.jsx',
        // Sentry error-monitoring initialisation (requires real network/DSN)
        'src/sentry.js',
        'src/utils/dynamicSentry.js',
        // TypeScript type-only declarations (no runtime statements)
        'src/sdk/types.ts',
      ],
    },
  },
});
