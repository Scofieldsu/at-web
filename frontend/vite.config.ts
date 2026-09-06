import { defineApplicationConfig } from '@vben/vite-config';

export default defineApplicationConfig({
  overrides: {
    optimizeDeps: {
      include: [
        'echarts/core',
        'echarts/charts',
        'echarts/components',
        'echarts/renderers',
        'qrcode',
        '@iconify/iconify',
        'ant-design-vue/es/locale/zh_CN',
        'ant-design-vue/es/locale/en_US',
      ],
    },
    server: {
      proxy: {
        // 改造：/api 代理到 Flask 后端，保留 /api 前缀（Flask 蓝图以 /api 挂载）
        '/api': {
          target: 'http://127.0.0.1:6001',
          changeOrigin: false,
          ws: true,
        },
        // 外链占位页 /ext/* 代理到 Flask（演示用，替代源工程内网外链）
        '/ext': {
          target: 'http://127.0.0.1:6001',
          changeOrigin: false,
        },
      },
      open: true, // 项目启动后，自动打开
      warmup: {
        clientFiles: ['./index.html', './src/{views,components}/*'],
      },
    },
  },
});
