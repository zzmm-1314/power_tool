import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    host: '127.0.0.1', // 强制使用 IPv4，避免 [::1] 的诡异问题
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:5000',
        changeOrigin: true,
        configure: (proxy, options) => {
          proxy.on('error', (err, req, res) => {
            console.log('代理发生错误', err);
            // 关键：代理失败必须给浏览器回一个响应，
            // 否则请求永远悬着，界面会一直卡在"上传中..."
            if (res && !res.headersSent) {
              res.writeHead(502, { 'Content-Type': 'application/json; charset=utf-8' });
              res.end(
                JSON.stringify({
                  code: 502,
                  msg: '后端服务不可达（http://127.0.0.1:5000 未启动），请重启后端后重试',
                  data: null,
                }),
              );
            }
          });
          proxy.on('proxyReq', (proxyReq, req, res) => {
            console.log('正在转发请求:', req.method, req.url || '', '->', (options.target || '') + (req.url || ''));
          });
        }
      },
    },
  },
  build: {
    outDir: 'dist',
    assetsDir: 'assets',
  },
})