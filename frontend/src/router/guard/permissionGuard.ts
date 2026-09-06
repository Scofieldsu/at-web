import type { Router } from 'vue-router';

import { usePermissionStoreWithOut } from '@/store/modules/permission';
import { useEnvStoreWithOut } from '@/store/modules/env';

import { PageEnum } from '@/enums/pageEnum';
import { useUserStoreWithOut } from '@/store/modules/user';

const LOGIN_PATH = PageEnum.BASE_LOGIN;

const whitePathList: PageEnum[] = [LOGIN_PATH];

export function createPermissionGuard(router: Router) {
  const userStore = useUserStoreWithOut();
  const permissionStore = usePermissionStoreWithOut();
  const envStore = useEnvStoreWithOut();
  router.beforeEach(async (to, from, next) => {
    const token = userStore.getToken;

    // 白名单直接放行
    if (whitePathList.includes(to.path as PageEnum)) {
      next();
      return;
    }

    // 未登录 → 跳转登录页
    if (!token) {
      if (to.meta.ignoreAuth) {
        next();
        return;
      }
      next({ path: LOGIN_PATH, replace: true, query: to.fullPath ? { redirect: to.fullPath } : {} });
      return;
    }

    // 首次加载：获取用户信息 + 构建菜单（路由已静态注册，buildRoutesAction 只用于生成菜单数据）
    if (userStore.getLastUpdateTime === 0) {
      await userStore.getUserInfoAction();
    }
    if (!permissionStore.getIsDynamicAddedRoute) {
      await permissionStore.buildRoutesAction();
      permissionStore.setDynamicAddedRoute(true);
      // 菜单构建完成后，加载环境标签并注入到总览菜单
      envStore.loadEnv();
    }

    next();
  });
}
