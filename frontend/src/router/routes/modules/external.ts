import type { AppRouteModule } from '@/router/types';
import { LAYOUT } from '@/router/constant';

// 外链直达（外部系统入口集合）。
//
// 菜单项的 path 直接写成完整 URL：菜单组件（layouts/default/menu 的
// beforeMenuClickFn、SimpleMenu 的 handleSelect）都会先用 isHttpUrl 判定，
// 命中就调 openWindow 新标签打开、不做路由跳转，因此这些 path 不会真的被导航。
// 组件挂 FrameBlank（空白占位）只为满足路由表要求。
//
// 注意：演示版指向后端内置演示页（/ext/*，JIRA 风格缺陷跟踪 + 文件存储风格），
// 真实环境替换为对应系统控制台地址即可。
// 用 origin 拼绝对 URL：dev 由 vite 的 /ext 代理转发到 Flask，prod 由 Flask 同源直出。
const DEFECTS_URL = `${window.location.origin}/ext/defects`;
const FILES_URL = `${window.location.origin}/ext/files`;

// orderNo 80 > 系统配置的 70，排在菜单最底部。
// 注意：ROLE 模式的排序读 meta.orderNo（见 store/modules/permission.ts），
// 与 platform.ts 各模块写法保持一致，都放在 meta 里。
const external: AppRouteModule = {
  path: '/external',
  name: 'External',
  component: LAYOUT,
  meta: {
    orderNo: 80,
    icon: 'ion:open-outline',
    title: '外链直达',
    // 一级菜单配色：青色（tint-cyan，与页面 tint 语义一致），与其余六个菜单
    // （indigo/green/orange/blue/violet/slate）不撞色
    color: '#06b6d4',
    tag: {
      // tag 仅侧边栏 SimpleMenu 渲染；顶部菜单条按 meta.color 取色
      type: 'cyan' as any,
      content: 'External',
      dot: false,
    },
  },
  children: [
    {
      path: DEFECTS_URL,
      name: 'ExternalDefects',
      component: () => import('@/views/sys/iframe/FrameBlank.vue'),
      meta: { title: '缺陷跟踪平台', icon: 'ion:bug-outline' },
    },
    {
      path: FILES_URL,
      name: 'ExternalFiles',
      component: () => import('@/views/sys/iframe/FrameBlank.vue'),
      meta: { title: '文件存储', icon: 'ion:folder-open-outline' },
    },
  ],
};

export default external;
