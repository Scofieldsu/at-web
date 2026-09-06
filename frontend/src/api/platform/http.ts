import axios from 'axios';

// 从旧前端 web/src/api.js 平移而来：cookie-session 简单请求实例。
// 业务页面与鉴权共用它，直接拿 res.data，不经 Vben 的 defHttp 信封处理。
// 同源部署到 Flask（:5000），cookie 自动携带；withCredentials 兼容 dev 代理。
const http = axios.create({
  baseURL: '/api',
  withCredentials: true,
  timeout: 15000, // 15秒超时，防止后端代理请求卡住导致前端无限等待
});

// 401 统一跳登录（auth 接口本身除外）。hash 路由用 location.hash。
http.interceptors.response.use(
  (r) => r,
  (err) => {
    if (
      err.response &&
      err.response.status === 401 &&
      !err.config.url.includes('/auth/')
    ) {
      window.location.hash = '#/login';
    }
    return Promise.reject(err);
  },
);

export default http;
