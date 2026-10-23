/// <reference types="vitest/config" />
import path from 'node:path'
import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

const apiProxyTarget = process.env.VITE_API_PROXY_TARGET ?? 'http://localhost:8000'

const vendorChunks: Record<string, string[]> = {
  'vendor-react': ['react', 'react-dom', 'scheduler', 'react-router', 'react-router-dom'],
  'vendor-radix': ['radix-ui', '@radix-ui'],
  'vendor-i18n': ['i18next', 'react-i18next'],
  'vendor-forms': ['zod', 'react-hook-form', '@hookform/resolvers'],
}

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks(moduleId) {
          if (!moduleId.includes('node_modules')) return undefined
          for (const [chunkName, packageNames] of Object.entries(vendorChunks)) {
            if (packageNames.some((packageName) => moduleId.includes(`/node_modules/${packageName}/`))) {
              return chunkName
            }
          }
          return undefined
        },
      },
    },
  },
  server: {
    port: 5173,
    proxy: {
      '/api': { target: apiProxyTarget },
    },
  },
  test: {
    environment: 'jsdom',
    include: ['src/**/*.test.{ts,tsx}'],
    restoreMocks: true,
    unstubGlobals: true,
  },
})
