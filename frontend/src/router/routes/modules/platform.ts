import type { AppRouteModule } from '@/router/types';
import { LAYOUT } from '@/router/constant';

// RPA 自动化测试平台业务路由
// 方案 A：按测试工作流重新分组，从环境准备 → 消息模拟 → 测试执行 → 质量归档 → 分布式 → 系统配置
// 配色约定：一级菜单 meta.color 按语义分配（与页面区块标题 tint 色一致），菜单 logo 与页面标题一致且不重复。

// ==================== 总览（顶层直达，无子菜单） ====================
const dashboard: AppRouteModule = {
  path: '/dashboard',
  name: 'DashboardIndex',
  component: LAYOUT,
  redirect: '/dashboard/index',
  meta: {
    orderNo: 10,
    icon: 'ant-design:fund-outlined',
    title: '总览',
    color: '#6366f1',
    hideChildrenInMenu: true,  // 隐藏子菜单，点击直达
  },
  children: [
    {
      path: 'index',
      name: 'Dashboard',
      component: () => import('@/views/platform/Dashboard.vue'),
      meta: { title: '总览', icon: 'ant-design:fund-outlined' },
    },
  ],
};

// ==================== ① 环境准备 ====================
const prepare: AppRouteModule = {
  path: '/prepare',
  name: 'Prepare',
  component: LAYOUT,
  redirect: '/prepare/env',
  meta: { orderNo: 20, icon: 'ant-design:tool-outlined', title: '环境准备', color: '#30a46c' },
  children: [
    {
      path: 'env',
      name: 'EnvUsers',
      component: () => import('@/views/platform/EnvUsers.vue'),
      meta: { title: '安装与账号', icon: 'ant-design:download-outlined' },
    },
    {
      path: 'proxy',
      name: 'ProxyRules',
      component: () => import('@/views/platform/ProxyRules.vue'),
      meta: { title: '代理与规则', icon: 'ant-design:global-outlined' },
    },
    {
      path: 'weaknet',
      name: 'WeakNet',
      component: () => import('@/views/platform/WeakNet.vue'),
      meta: { title: '弱网工具', icon: 'ant-design:wifi-outlined' },
    },
    {
      path: 'machines',
      name: 'PrepareMachines',
      component: () => import('@/views/platform/distributed/machines.vue'),
      meta: { title: '机器管理', icon: 'ant-design:cloud-server-outlined' },
    },
  ],
};

// ==================== ② 消息模拟 ====================
const message: AppRouteModule = {
  path: '/message',
  name: 'Message',
  component: LAYOUT,
  redirect: '/message/send',
  meta: { orderNo: 30, icon: 'ant-design:message-outlined', title: '消息模拟', color: '#f76b15' },
  children: [
    {
      path: 'send',
      name: 'MessageSend',
      component: () => import('@/views/platform/MessageSend.vue'),
      meta: { title: '消息发送', icon: 'ant-design:send-outlined' },
    },
    {
      path: 'inject',
      name: 'MessageInject',
      component: () => import('@/views/platform/InjectMessage.vue'),
      meta: { title: '消息注入', icon: 'ant-design:enter-outlined' },
    },
    {
      path: 'sniffer',
      name: 'MessageSniffer',
      component: () => import('@/views/platform/MessageSniffer.vue'),
      meta: { title: '消息嗅探', icon: 'ant-design:radar-chart-outlined' },
    },
    {
      path: 'mock-server',
      name: 'MockServer',
      component: () => import('@/views/platform/mock-server/index.vue'),
      meta: { title: 'Mock Server', icon: 'ant-design:cloud-server-outlined' },
    },
  ],
};

// ==================== ③ 测试执行 ====================
const test: AppRouteModule = {
  path: '/test',
  name: 'Test',
  component: LAYOUT,
  redirect: '/test/params',
  meta: { orderNo: 40, icon: 'ant-design:experiment-outlined', title: '测试执行', color: '#0090ff' },
  children: [
    {
      path: 'params',
      name: 'TestPlan',
      component: () => import('@/views/platform/TestPlan.vue'),
      meta: { title: '测试参数', icon: 'ant-design:sliders-outlined' },
    },
    {
      path: 'cases',
      name: 'Cases',
      component: () => import('@/views/platform/Cases.vue'),
      meta: { title: '执行用例', icon: 'ant-design:rocket-outlined' },
    },
    {
      path: 'monitor',
      name: 'Tasks',
      component: () => import('@/views/platform/Tasks.vue'),
      meta: { title: '任务记录', icon: 'ant-design:line-chart-outlined' },
    },
    {
      path: 'report',
      name: 'TestReport',
      component: () => import('@/views/platform/TestReport.vue'),
      meta: { title: '测试报告', icon: 'ant-design:file-text-outlined' },
    },
    {
      path: 'ui-test',
      name: 'UiTest',
      component: () => import('@/views/platform/UiTest.vue'),
      meta: { title: '压力测试', icon: 'ant-design:desktop-outlined' },
    },
    {
      path: 'schedule',
      name: 'Schedule',
      component: () => import('@/views/platform/Schedule.vue'),
      meta: { title: '定时执行', icon: 'ant-design:clock-circle-outlined' },
    },
    {
      // 任务详情（隐藏）：由执行用例/任务记录/定时执行/机器页等跳转进入
      path: 'monitor/:id',
      name: 'DistributedMonitor',
      component: () => import('@/views/platform/distributed/monitor.vue'),
      meta: { title: '任务详情', icon: 'ant-design:fund-projection-screen-outlined', hideMenu: true },
    },
  ],
};

// ==================== ④ 质量归档 ====================
const quality: AppRouteModule = {
  path: '/quality',
  name: 'Quality',
  component: LAYOUT,
  redirect: '/quality/versions',
  meta: { orderNo: 50, icon: 'ant-design:folder-outlined', title: '质量归档', color: '#7c3aed' },
  children: [
    {
      path: 'versions',
      name: 'VersionRecords',
      component: () => import('@/views/platform/VersionRecords.vue'),
      meta: { title: '版本测试记录', icon: 'ant-design:history-outlined' },
    },
  ],
};

// ==================== 系统配置（最底部） ====================
const config: AppRouteModule = {
  path: '/config',
  name: 'Config',
  component: LAYOUT,
  redirect: '/config/settings',
  meta: { orderNo: 70, icon: 'ant-design:setting-outlined', title: '系统配置', color: '#64748b' },
  children: [
    {
      path: 'settings',
      name: 'ConfigPage',
      component: () => import('@/views/platform/Config.vue'),
      meta: { title: '配置管理', icon: 'ant-design:folder-open-outlined' },
    },
  ],
};

export default [dashboard, prepare, message, test, quality, config];
