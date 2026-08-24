import { defineConfig } from './frontend/node_modules/vitest/dist/config.js'
import react from './frontend/node_modules/@vitejs/plugin-react/dist/index.js'
import { fileURLToPath } from 'node:url'

export default defineConfig({
  root: fileURLToPath(new URL('.', import.meta.url)),
  plugins: [react()],
  resolve: {
    alias: {
      react: fileURLToPath(new URL('./frontend/node_modules/react', import.meta.url)),
      'react-dom': fileURLToPath(new URL('./frontend/node_modules/react-dom', import.meta.url)),
      '@testing-library/react': fileURLToPath(new URL('./frontend/node_modules/@testing-library/react', import.meta.url)),
      '@testing-library/jest-dom': fileURLToPath(new URL('./frontend/node_modules/@testing-library/jest-dom', import.meta.url)),
      '@testing-library/user-event': fileURLToPath(new URL('./frontend/node_modules/@testing-library/user-event', import.meta.url)),
      'react-router-dom': fileURLToPath(new URL('./frontend/node_modules/react-router-dom', import.meta.url)),
    },
  },
  test: {
    environment: 'jsdom',
    include: [
      'tests/01_decentralized_uploading/**/*.test.tsx',
      'tests/02_identity_governance/**/*.test.tsx',
    ],
  },
})
