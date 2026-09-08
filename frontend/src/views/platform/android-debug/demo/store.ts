/**
 * 演示设备状态机 — at-web 无真实设备，这里用纯内存 + 响应式 ref 模拟
 * 「双设备并行调试」的全部行为，对外暴露与真实 API 同名的方法，页面层
 * 与 rpa-test-automation 的组件写法保持一致，只是数据源换成内存。
 *
 * 语义动作（layout.ts 元素上的 action）在此被解释为状态迁移：
 *   open-album / back / tab-xxx / select / send / press-home / app-start ...
 *
 * 用法（index.vue 里）：
 *   const demo = useAndroidDemo();
 *   demo.connect(udid); demo.click(udid, x, y); demo.press(udid, 'back');
 */
import { reactive, readonly } from 'vue';
import type { DemoDevice } from './devices';
import { DEMO_DEVICES } from './devices';
import type { PageState } from './layout';
import { buildElements } from './layout';
import { buildTree, summarize } from './tree';

interface DeviceRuntime {
  udid: string;
  online: boolean;
  state: PageState;
  /** 相册目录里已"推送"的文件名（演示：内存记录，用于相册列表/刷新展示） */
  pushedPictures: string[];
  pushedVideos: string[];
  /** 当前前台 App（app-start / home 时更新） */
  currentApp: { package: string; activity: string };
  /** 画面帧号 — 每次「刷新/自动刷新」自增，驱动镜像重绘（模拟实时画面） */
  frame: number;
}

export type { DeviceRuntime };

const DYPACKAGE = 'com.ss.android.ugc.aweme.lite';
const DY_ACTIVITY = '.lite.activity.LiteMainActivity';

function freshPageState(): PageState {
  return { page: 'home', albumTab: 'all', selected: [], battery: 80 };
}

function makeRuntime(dev: DemoDevice): DeviceRuntime {
  return {
    udid: dev.udid,
    online: false,
    state: freshPageState(),
    pushedPictures: [
      'IMG_20260901_103021.jpg',
      'IMG_20260902_084115.jpg',
      'IMG_20260905_190233.png',
      'Screenshot_20260907_111200.jpg',
    ],
    pushedVideos: ['VID_20260903_142210.mp4'],
    currentApp: { package: 'com.android.launcher3', activity: '.Launcher' },
    frame: 0,
  };
}

interface DemoStore {
  devices: Record<string, DeviceRuntime>;
  /** 设备列表（含 online 标记），对齐真实 /devices 返回 */
  list: () => { udid: string; name: string; wired_udid: string; notes: string; source: string; online: boolean; in_adb: boolean }[];
  connect: (udid: string) => void;
  disconnect: (udid: string) => void;
  /** 画面重绘一帧（手动刷新 / 自动刷新 / 操作后触发都走这里，frame 自增驱动镜像） */
  tick: (udid: string) => void;
  info: (udid: string) => { udid: string; name: string; online: boolean; model: string; sdk: number; width: number; height: number; current_app: { package: string; activity: string } };
  click: (udid: string, x: number, y: number) => void;
  swipe: (udid: string, x1: number, y1: number, x2: number, y2: number) => void;
  press: (udid: string, key: string) => void;
  input: (udid: string, text: string) => void;
  appStart: (udid: string, pkg: string) => void;
  appStop: (udid: string, pkg: string) => void;
  pushFile: (udid: string, name: string, ext: string, dir?: string) => string;
  pushAssets: (udid: string) => { pushed: string[]; failed: { name: string; error: string }[] };
  listAlbum: (udid: string) => { pictures: string; videos: string };
  dump: (udid: string) => { tree: any; summary: { total: number; clickable: number; checkable: number; packages: string[] }; window_size: number[]; current_app: { package: string; activity: string } };
  findSelectors: (udid: string, kind: string) => Record<string, { id: string; confidence: string; reason: string }[]>;
}

let _store: DemoStore | null = null;

export function useAndroidDemo(): DemoStore {
  if (_store) return _store;

  const devices: Record<string, DeviceRuntime> = {};
  for (const dev of DEMO_DEVICES) {
    devices[dev.udid] = makeRuntime(dev);
  }
  const store = reactive(devices) as any; // 内部响应式容器

  function rt(udid: string): DeviceRuntime | undefined {
    return (store as any)[udid];
  }

  // ── 语义动作 → 状态迁移 ──────────────────────────────────
  function applyAction(r: DeviceRuntime, action?: string, payload?: number) {
    if (!action) return;
    const s = r.state;
    if (action === 'open-album') {
      s.page = 'album';
      s.albumTab = 'all';
      s.selected = [];
      r.currentApp = { package: DYPACKAGE, activity: DY_ACTIVITY };
      return;
    }
    if (action === 'back') {
      if (s.page === 'album') s.page = 'home';
      return;
    }
    if (action.startsWith('tab:')) {
      s.albumTab = action.slice(4) as PageState['albumTab'];
      return;
    }
    if (action === 'select') {
      if (payload === undefined) return;
      const i = s.selected.indexOf(payload);
      if (i >= 0) s.selected.splice(i, 1);
      else s.selected.push(payload);
      return;
    }
    if (action === 'send') {
      // 演示：发送后回到首页并清空选择
      s.page = 'home';
      s.selected = [];
      r.currentApp = { package: DYPACKAGE, activity: DY_ACTIVITY };
    }
  }

  // ── 设备操作入口（页面层调用，方法名对齐真实 API） ───────
  const demo: DemoStore = {
    devices: readonly(store) as any,

    list() {
      return DEMO_DEVICES.map((d) => ({
        udid: d.udid,
        name: d.name,
        wired_udid: d.wired_udid,
        notes: d.notes,
        source: d.source,
        online: devices[d.udid]?.online || false,
        in_adb: true,
      }));
    },

    connect(udid) {
      const r = rt(udid);
      if (!r) return;
      // 模拟真实设备的连接探测（几百 ms 冷连接），演示里直接置在线
      r.online = true;
      // 已连接且停留在相册的，保持当前页；新连接默认首页
      if (!r.state.page) r.state = freshPageState();
    },

    disconnect(udid) {
      const r = rt(udid);
      if (!r) return;
      r.online = false;
      r.state = freshPageState();
      r.currentApp = { package: 'com.android.launcher3', activity: '.Launcher' };
    },

    tick(udid) {
      const r = rt(udid);
      if (r && r.online) r.frame += 1;
    },

    info(udid) {
      const dev = DEMO_DEVICES.find((d) => d.udid === udid);
      const r = rt(udid);
      if (!dev || !r) return { udid, name: udid, online: false, model: '', sdk: 0, width: 0, height: 0, current_app: {} as any };
      return {
        udid,
        name: dev.name,
        online: r.online,
        model: dev.model,
        sdk: dev.sdk,
        width: dev.width,
        height: dev.height,
        current_app: r.currentApp,
      };
    },

    click(udid, x, y) {
      const r = rt(udid);
      const dev = DEMO_DEVICES.find((d) => d.udid === udid);
      if (!r || !dev || !r.online) return;
      // 按 bounds 命中元素并触发其动作（layout.hitTest 逻辑，这里内联取最小面积）
      const els = buildElements(r.state, dev);
      let best: (typeof els)[number] | null = null;
      let bestArea = Infinity;
      for (const el of els) {
        const [x1, y1, x2, y2] = el.bounds;
        if (x >= x1 && x <= x2 && y >= y1 && y <= y2) {
          const area = (x2 - x1) * (y2 - y1);
          if (area < bestArea) { bestArea = area; best = el; }
        }
      }
      applyAction(r, best?.action, best?.payload);
    },

    swipe() {
      // 演示：信息流/相册滑动不改变页面（保留当前页），仅模拟
    },

    press(udid, key) {
      const r = rt(udid);
      if (!r) return;
      if (key === 'home') {
        r.state = freshPageState();
        r.currentApp = { package: 'com.android.launcher3', activity: '.Launcher' };
        return;
      }
      if (key === 'back') {
        applyAction(r, 'back');
      }
      // recent / volume / power：演示无可见变化
    },

    input() {
      // 演示：不落到 UI（相册页无输入框），保留接口
    },

    appStart(udid, pkg) {
      const r = rt(udid);
      if (!r) return;
      r.state = freshPageState();
      if (pkg === DYPACKAGE) {
        r.currentApp = { package: DYPACKAGE, activity: DY_ACTIVITY };
      } else {
        r.currentApp = { package: pkg, activity: '.MainActivity' };
      }
    },

    appStop(udid, pkg) {
      const r = rt(udid);
      if (!r) return;
      if (r.currentApp.package === pkg) {
        r.currentApp = { package: 'com.android.launcher3', activity: '.Launcher' };
      }
    },

    pushFile(udid, name, ext, dir) {
      const r = rt(udid);
      if (!r) return '';
      const lower = ext.toLowerCase();
      const video = ['.mp4', '.mov', '.avi', '.3gp'].includes(lower);
      const remote = dir || (video ? '/sdcard/DCIM/Camera/' : '/sdcard/Pictures/');
      if (video) r.pushedVideos.push(name);
      else r.pushedPictures.push(name);
      return `${remote}${name}`;
    },

    pushAssets(udid) {
      const r = rt(udid);
      const pushed: string[] = [];
      if (r) {
        for (const f of ['assets_photo_01.jpg', 'assets_photo_02.jpg', 'assets_photo_03.png']) {
          r.pushedPictures.push(f);
          pushed.push(f);
        }
        for (const f of ['assets_video_01.mp4', 'assets_video_02.mp4']) {
          r.pushedVideos.push(f);
          pushed.push(f);
        }
      }
      return { pushed, failed: [] };
    },

    listAlbum(udid) {
      const r = rt(udid);
      const fmt = (files: string[], dir: string) =>
        files.length
          ? files.map((f) => `-rw-rw-rw- 1 u0_a123 media 1.2M 2026-09-08 ${f.padEnd(28)} ${dir}${f}`).join('\n')
          : '(空)';
      if (!r) return { pictures: '(空)', videos: '(空)' };
      return {
        pictures: fmt(r.pushedPictures, '/sdcard/Pictures/'),
        videos: fmt(r.pushedVideos, '/sdcard/DCIM/Camera/'),
      };
    },

    dump(udid) {
      const dev = DEMO_DEVICES.find((d) => d.udid === udid);
      const r = rt(udid);
      if (!dev || !r) return { tree: null, summary: { total: 0, clickable: 0, checkable: 0, packages: [] }, window_size: [0, 0], current_app: {} as any };
      const tree = buildTree(r.state, dev);
      return {
        tree,
        summary: summarize(tree),
        window_size: [dev.width, dev.height],
        current_app: r.currentApp,
      };
    },

    findSelectors(udid, kind) {
      const dev = DEMO_DEVICES.find((d) => d.udid === udid);
      const r = rt(udid);
      const none = { id: '', confidence: 'none', reason: '未找到（请确保在相册选择页且已选中图片）' } as { id: string; confidence: string; reason: string };
      if (!dev || !r || r.state.page !== 'album') {
        if (kind === 'all') {
          return { album_tab: [none], album_circle: [none], album_send: [none] };
        }
        return { [kind]: [none] };
      }
      const selected = r.state.selected.length > 0;
      const res: Record<string, { id: string; confidence: string; reason: string }[]> = {
        album_tab: [{ id: ':id/dr8', confidence: 'high', reason: '三个 Tab（全部/图片/视频）共用同一 id' }],
        album_circle: [
          r.state.selected.length
            ? { id: ':id/dsb', confidence: 'high', reason: `在 ${r.state.selected.length} 个格子右上角找到（圆圈选择器）` }
            : { id: ':id/dsb', confidence: 'low', reason: '找到多个候选（未选中，置信度低）' },
        ],
        album_send: [
          selected
            ? { id: ':id/duf', confidence: 'high', reason: `文本「发送」+ enabled + 右下角（已选 ${r.state.selected.length} 张）` }
            : { id: ':id/duf', confidence: 'none', reason: '发送按钮 disabled（请先选中一张图）' },
        ],
      };
      if (kind === 'all') return res;
      return { [kind]: res[kind] || [none] };
    },
  };

  _store = demo;
  return demo;
}
