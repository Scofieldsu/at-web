import { defineStore } from 'pinia';
import { store } from '@/store';
import http from '@/api/platform/http';
import { usePermissionStore } from './permission';

interface EnvState {
  env: string;
  envs: string[];
  loaded: boolean;
}

export const useEnvStore = defineStore({
  id: 'app-env',
  state: (): EnvState => ({
    env: '',
    envs: ['dev', 'prod'],
    loaded: false,
  }),
  getters: {
    getEnv(state): string {
      return state.env;
    },
    getEnvs(state): string[] {
      return state.envs;
    },
    getEnvLabel(state): string {
      return state.env === 'dev' ? '开发环境' : '生产环境';
    },
    getEnvTagType(state): 'primary' | 'warn' {
      return state.env === 'dev' ? 'primary' : 'warn';
    },
  },
  actions: {
    setEnv(env: string) {
      this.env = env;
      this.loaded = true;
      this.updateDashboardMenuTag();
    },
    async loadEnv() {
      if (this.loaded) return;
      try {
        const { data } = await http.get('/env/current');
        if (data?.env) {
          this.envs = Array.isArray(data.envs) && data.envs.length ? data.envs : ['dev', 'prod'];
          this.setEnv(data.env);
        }
      } catch (e) {
        console.warn('[env store] Failed to load environment:', e);
      }
    },
    /**
     * 切换当前环境 — 写入服务端 config/env.json 的 current，
     * 成功后立即更新本地环境标签，无需刷新。
     */
    async switchEnv(env: string) {
      const { data } = await http.put('/env/current', { env });
      this.setEnv(data?.env ?? env);
      return data?.env ?? env;
    },
    /** 动态更新总览菜单的 tag（环境标签）。
     *
     * 权限模式为 ROLE 时菜单取自 staticMenuList，ROUTE_MAPPING 时取自 frontMenuList，
     * 两个列表都尝试写入，避免因模式切换漏掉。
     */
    updateDashboardMenuTag() {
      const permissionStore = usePermissionStore();
      const tag = {
        type: this.getEnvTagType,
        content: this.getEnvLabel,
        // 添加 env 修饰符触发浅底深字样式（与测试参数页 a-tag 一致）
        dot: false,
        class: 'env',
      };
      for (const menus of [permissionStore.staticMenuList, permissionStore.frontMenuList]) {
        const dashboard = menus?.find((m) => m.path === '/dashboard');
        if (dashboard) dashboard.tag = tag;
      }
      // 触发菜单重新渲染
      permissionStore.setLastBuildMenuTime();
    },
  },
});

// Need to be used outside the setup
export function useEnvStoreWithOut() {
  return useEnvStore(store);
}
