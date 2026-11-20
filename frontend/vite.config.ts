import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'

export default defineConfig({
  // 部署子路径：https://zidovpp.com/zjPowerTool/
  // 后端直接托管（static 目录）时用 VITE_BASE=/ 构建，产物按根路径引用资源
  base: process.env.VITE_BASE || '/zjPowerTool/',
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    host: '127.0.0.1',
    port: 5173,
    proxy: {
      // 开发环境下前端请求 /zjPowerTool/api/*，rewrite 成 /api/* 转发到后端
      '/zjPowerTool/api': {
        target: 'http://127.0.0.1:5000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/zjPowerTool/, ''),
        configure: (proxy, options) => {
          proxy.on('error', (err, req, res) => {
            console.log('代理发生错误', err)
            if (res && !res.headersSent) {
              res.writeHead(502, { 'Content-Type': 'application/json; charset=utf-8' })
              res.end(JSON.stringify({
                code: 502,
                msg: '后端服务不可达（http://127.0.0.1:5000 未启动），请重启后端后重试',
                data: null,
              }))
            }
          })
          proxy.on('proxyReq', (proxyReq, req, res) => {
            console.log('正在转发请求:', req.method, req.url || '', '->', (options.target || '') + (req.url || ''))
          })
        },
      },
      // 兼容仍写死 /api 的旧调用
      '/api': {
        target: 'http://127.0.0.1:5000',
        changeOrigin: true,
        configure: (proxy, options) => {
          proxy.on('error', (err, req, res) => {
            console.log('代理发生错误', err)
            if (res && !res.headersSent) {
              res.writeHead(502, { 'Content-Type': 'application/json; charset=utf-8' })
              res.end(JSON.stringify({
                code: 502,
                msg: '后端服务不可达（http://127.0.0.1:5000 未启动），请重启后端后重试',
                data: null,
              }))
            }
          })
          proxy.on('proxyReq', (proxyReq, req, res) => {
            console.log('正在转发请求:', req.method, req.url || '', '->', (options.target || '') + (req.url || ''))
          })
        },
      },
    },
  },
  build: {
    outDir: 'dist',
    assetsDir: 'assets',
  },
})