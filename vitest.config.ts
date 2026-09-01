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
      // 测试需在项目主题下测量字号字重（MUI 默认 body2 是 14px，主题覆盖为 13px）
      '@mui/material': fileURLToPath(new URL('./frontend/node_modules/@mui/material', import.meta.url)),
    },
  },
  test: {
    environment: 'jsdom',
    // 逐目录白名单而非 'tests/**'：tests/ 下同时存在 pytest 用的 .py 与前端 .test.tsx，
    // 且部分目录只有 Python 测试。新增含 .test.tsx 的目录时必须同步加到这里，
    // 否则该目录的用例会被静默跳过——不报错、不计数，看不出漏了。
    include: [
      'tests/01_decentralized_uploading/**/*.test.tsx',
      'tests/02_identity_governance/**/*.test.tsx',
      'tests/03_data_search_and_database_discovery/**/*.test.tsx',
      'tests/08_news/**/*.test.tsx',
    ],
  },
})
