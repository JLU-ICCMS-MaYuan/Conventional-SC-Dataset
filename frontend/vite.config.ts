import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// 移除大库的 modulepreload，由 React.lazy() 按需加载，避免首页预取
function removeHeavyPreloads() {
  return {
    name: 'remove-heavy-preloads',
    enforce: 'post' as const,
    transformIndexHtml(html: string) {
      return html.replace(
        /<link rel="modulepreload"[^>]*\/(recharts|react-markdown|vis-network|vis-data|3dmol)[^>]*\.js">\s*/g,
        '',
      )
    },
  }
}

export default defineConfig({
  plugins: [react(), removeHeavyPreloads()],
  build: {
    outDir: 'static',
    emptyOutDir: true,
    rollupOptions: {
      output: {
        manualChunks(id: string) {
          if (id.includes('node_modules/vis-network') || id.includes('node_modules/vis-data')) return 'vis-network'
        },
      },
    },
  },
  server: {
    port: 5173,
    host: '0.0.0.0',
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8080',
        changeOrigin: true,
      },
    },
  },
})
