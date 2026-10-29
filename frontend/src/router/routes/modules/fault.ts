import type { AppRouteModule } from '@/router/types';
import { LAYOUT } from '@/router/constant';

// 故障模拟业务路由（演示版：全部数据为模拟，无真实注入）
// 子菜单：代理拦截 → 弱网设置 → 弹窗模拟 → 运行时补丁

const fault: AppRouteModule = {
  path: '/fault',
  name: 'Fault',
  component: LAYOUT,
  redirect: '/fault/proxy-intercept',
  meta: { orderNo: 25, icon: 'ant-design:bug-outlined', title: '故障模拟', color: '#e5484d' },
  children: [
    {
      path: 'proxy-intercept',
      name: 'FaultProxyIntercept',
      component: () => import('@/views/fault/ProxyIntercept.vue'),
      meta: { title: '代理拦截', icon: 'ant-design:stop-outlined' },
    },
    {
      path: 'weaknet',
      name: 'FaultWeakNet',
      component: () => import('@/views/fault/WeakNet.vue'),
      meta: { title: '弱网设置', icon: 'ant-design:wifi-outlined' },
    },
    {
      path: 'popup-sim',
      name: 'FaultPopupSim',
      component: () => import('@/views/fault/PopupSim.vue'),
      meta: { title: '弹窗模拟', icon: 'ant-design:alert-outlined' },
    },
    {
      path: 'runtime-patch',
      name: 'FaultRuntimePatch',
      component: () => import('@/views/fault/RuntimePatch.vue'),
      meta: { title: '运行时补丁', icon: 'ant-design:code-outlined' },
    },
  ],
};

export default fault;
