import { defineConfig } from 'vite'
import { resolve } from 'path'

export default defineConfig({
  root: '.',
  server: {
    port: 5173,
    host: true,
  },
  build: {
    rollupOptions: {
      input: {
        main: resolve(__dirname, 'index.html'),
        login: resolve(__dirname, 'login.html'),
        upload: resolve(__dirname, 'upload.html'),
        privacy: resolve(__dirname, 'privacy-check.html'),
        scan: resolve(__dirname, 'scan-in-progress.html'),
        findings: resolve(__dirname, 'findings.html'),
        viewer: resolve(__dirname, 'viewer.html'),
        signoff: resolve(__dirname, 'sign-off.html'),
        worklist: resolve(__dirname, 'worklist.html'),
        analytics: resolve(__dirname, 'analytics.html'),
        audit: resolve(__dirname, 'audit-log.html'),
        howitworks: resolve(__dirname, 'how-it-works.html'),
        about: resolve(__dirname, 'about.html'),
      }
    }
  }
})
