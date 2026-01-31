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
    reporters: ['default', 'junit'],
    outputFile: {
      junit: process.env.VITEST_JUNIT_OUTPUT_FILE || defaultJunitPath,
    },
  },
});
