/**
 * 演示页面布局 — 把「设备当前页面」建模为一组带真实像素 bounds 的元素。
 *
 * 单一数据源，同时驱动：
 *  1. DemoScreen.vue  — 按 bounds（设备像素）绝对定位渲染手机实时画面；
 *  2. tree.ts        — 序列化成 uiautomator2 风格的 UI 层级树（元素查看器用）；
 *  3. hit-test       — 点击镜像画面时，按 bounds 反查命中的元素并触发其 action。
 *
 * 覆盖两个页面（与 RPA 驱动的真实流程一致：首页 → ＋ → 相册选择页）：
 *  - home  抖音极速版信息流（状态栏 / 搜索 / 视频卡片 / 底部导航）
 *  - album 相册选择页（全部·图片·视频 Tab / 缩略图网格 / 圆圈选择器 / 发送按钮）
 *
 * bounds 使用「设备像素」，因此 1080×2400 与 1200×2670 两台设备的元素
 * 坐标都按各自分辨率换算，版式一致 —— 正好演示「坐标按分辨率兜底」。
 */
import type { DemoDevice } from './devices';

export type PageId = 'home' | 'album';
export type AlbumTab = 'all' | 'pics' | 'vids';

/** 演示页面状态（store 里每台设备一份，响应式） */
export interface PageState {
  page: PageId;
  albumTab: AlbumTab;
  /** 相册里已选中的缩略图下标 */
  selected: number[];
  battery: number;
}

/** 一个可视化元素（= 镜像画面里的一块，也是 UI 树的一个节点） */
export interface DemoElement {
  key: string;
  /** uiautomator 的 class，如 android.widget.ImageView */
  cls: string;
  /** resource-id，如 :id/dsb（混淆 id） */
  id?: string;
  text?: string;
  desc?: string;
  /** 设备像素坐标 [x1, y1, x2, y2] */
  bounds: [number, number, number, number];
  clickable?: boolean;
  checkable?: boolean;
  checked?: boolean;
  enabled?: boolean;
  /** 语义动作：命中后 store 据此改状态（open-album / select / send / back / tab:* ...） */
  action?: string;
  /** 动作负载（如下标） */
  payload?: number;
  /** 视觉类型（DemoScreen 按此渲染外观） */
  kind:
    | 'statusbar'
    | 'search'
    | 'card'
    | 'avatar'
    | 'rail'
    | 'tabbar'
    | 'tab'
    | 'grid'
    | 'circle'
    | 'send'
    | 'title'
    | 'icon'
    | 'text'
    | 'badge'
    | 'default';
  bg?: string;
  color?: string;
  border?: string;
  radius?: string;
  /** 字体大小（设备像素） */
  font?: number;
  /** 图标字形（tab bar 的 emoji，与 text 分开：图标大、标签小） */
  icon?: string;
}

/** 相册缩略图数量（3 列 × 2 行 = 6） */
export const ALBUM_COUNT = 6;
/** 各下标是否为视频（相册「视频」Tab / 角标用） */
export const ALBUM_IS_VIDEO = [false, true, false, false, true, false];

// ── 颜色工具 ──────────────────────────────────────────────────

function grad(hue: number): string {
  return `linear-gradient(135deg, hsl(${hue} 62% 72%), hsl(${(hue + 40) % 360} 60% 52%))`;
}

function frac(w: number, h: number, x1: number, y1: number, x2: number, y2: number): [number, number, number, number] {
  return [Math.round(x1 * w), Math.round(y1 * h), Math.round(x2 * w), Math.round(y2 * h)];
}

// ── 通用 chrome ───────────────────────────────────────────────

function statusBar(state: PageState, w: number, h: number, dark: boolean): DemoElement {
  const c = dark ? '#ffffff' : '#111827';
  return {
    key: 'statusbar',
    cls: 'android.widget.FrameLayout',
    desc: '状态栏',
    bounds: frac(w, h, 0, 0, 1, 0.036),
    kind: 'statusbar',
    bg: dark ? '#000000' : '#ffffff',
    color: c,
    font: Math.round(h * 0.02),
    payload: state.battery,
  };
}

// ── 页面：首页（信息流） ─────────────────────────────────────

function buildHome(state: PageState, dev: DemoDevice): DemoElement[] {
  const w = dev.width;
  const h = dev.height;
  const els: DemoElement[] = [];

  els.push(statusBar(state, w, h, true));

  // 搜索框
  els.push({
    key: 'search',
    cls: 'android.widget.EditText',
    text: '🔍  关注 / 视频 / 同城',
    desc: '搜索',
    bounds: frac(w, h, 0.055, 0.048, 0.945, 0.076),
    kind: 'search',
    bg: '#f2f3f5',
    color: '#9aa0a6',
    radius: '999px',
    font: Math.round(h * 0.017),
  });

  // 当前视频卡片（大图占位）
  els.push({
    key: 'video',
    cls: 'android.widget.ImageView',
    desc: '视频 · 当前正在播放',
    bounds: frac(w, h, 0, 0.084, 1, 0.9),
    kind: 'card',
    bg: 'linear-gradient(160deg, #1f2937 0%, #374151 55%, #111827 100%)',
    color: '#ffffff',
    radius: '14px',
    action: 'noop',
  });

  // 卡片左上角用户头像
  els.push({
    key: 'avatar',
    cls: 'android.widget.ImageView',
    desc: '用户头像',
    bounds: frac(w, h, 0.045, 0.094, 0.135, 0.124),
    kind: 'avatar',
    bg: grad(200),
    action: 'noop',
  });

  // 右侧操作栏：点赞 / 评论 / 分享
  const rail = [
    { key: 'like', ch: '❤️', d: '点赞' },
    { key: 'comment', ch: '💬', d: '评论' },
    { key: 'share', ch: '↗️', d: '分享' },
  ];
  rail.forEach((r, i) => {
    els.push({
      key: r.key,
      cls: 'android.widget.ImageView',
      desc: r.d,
      text: r.ch,
      bounds: frac(w, h, 0.86, 0.62 + i * 0.09, 0.935, 0.62 + i * 0.09 + 0.062),
      kind: 'rail',
      bg: 'rgba(0,0,0,0.28)',
      color: '#ffffff',
      radius: '50%',
      font: Math.round(h * 0.02),
      action: 'noop',
    });
  });

  // 底部导航（＋ 打开相册选择页 —— 演示进入相册的入口）
  const tabs = [
    { key: 'nav_home', icon: '🏠', label: '首页', active: true },
    { key: 'nav_friend', icon: '👥', label: '朋友', active: false },
    { key: 'nav_create', icon: '＋', label: '', active: false, desc: '拍摄 / 选择图片', action: 'open-album' },
    { key: 'nav_msg', icon: '✉️', label: '消息', active: false },
    { key: 'nav_me', icon: '👤', label: '我的', active: false },
  ];
  tabs.forEach((t, i) => {
    els.push({
      key: t.key,
      cls: 'android.widget.TextView',
      icon: t.icon,
      text: t.label,
      desc: t.desc || t.label,
      bounds: frac(w, h, i / 5, 0.9, (i + 1) / 5, 1),
      kind: 'tabbar',
      bg: '#ffffff',
      color: t.active ? '#ff2d55' : '#6b7280',
      font: Math.round(h * 0.013),
      clickable: true,
      action: t.action || 'noop',
      checked: t.active,
    });
  });

  return els;
}

// ── 页面：相册选择页 ─────────────────────────────────────────

function buildAlbum(state: PageState, dev: DemoDevice): DemoElement[] {
  const w = dev.width;
  const h = dev.height;
  const els: DemoElement[] = [];
  const selected = state.selected;

  els.push(statusBar(state, w, h, false));

  // 顶栏：返回 / 标题 / 取消
  els.push({
    key: 'album_back',
    cls: 'android.widget.ImageView',
    desc: '返回',
    text: '←',
    bounds: frac(w, h, 0, 0.036, 0.13, 0.086),
    kind: 'icon',
    color: '#111827',
    font: Math.round(h * 0.03),
    clickable: true,
    action: 'back',
  });
  els.push({
    key: 'album_title',
    cls: 'android.widget.TextView',
    text: '选择图片',
    bounds: frac(w, h, 0.13, 0.036, 0.6, 0.086),
    kind: 'title',
    color: '#111827',
    font: Math.round(h * 0.022),
  });
  els.push({
    key: 'album_cancel',
    cls: 'android.widget.TextView',
    text: '取消',
    bounds: frac(w, h, 0.6, 0.036, 0.92, 0.086),
    kind: 'text',
    color: '#0090ff',
    font: Math.round(h * 0.018),
    clickable: true,
    action: 'back',
  });

  // 顶部 Tab：全部 / 图片 / 视频（混淆 id :id/dr8）
  const tabDefs: { id: AlbumTab; label: string }[] = [
    { id: 'all', label: '全部' },
    { id: 'pics', label: '图片' },
    { id: 'vids', label: '视频' },
  ];
  tabDefs.forEach((t, i) => {
    els.push({
      key: `tab_${t.id}`,
      cls: 'android.widget.RadioButton',
      id: ':id/dr8',
      text: t.label,
      bounds: frac(w, h, i / 3, 0.09, (i + 1) / 3, 0.14),
      kind: 'tab',
      color: state.albumTab === t.id ? '#0090ff' : '#6b7280',
      font: Math.round(h * 0.019),
      checkable: true,
      checked: state.albumTab === t.id,
      clickable: true,
      action: `tab:${t.id}`,
    });
  });

  // 缩略图网格：3 列 × 2 行方形格子（root_view）+ 右上角圆圈选择器 :id/dsb
  // 用 px 计算保证格子是正方形（宽 = 高），不随屏幕比例拉伸
  const pad = Math.round(w * 0.02);
  const gap = Math.round(w * 0.012);
  const cell = Math.floor((w - pad * 2 - gap * 2) / 3);
  const gridTopPx = Math.round(h * 0.15);
  for (let i = 0; i < ALBUM_COUNT; i++) {
    const col = i % 3;
    const row = Math.floor(i / 3);
    const gx1 = pad + col * (cell + gap);
    const gy1 = gridTopPx + row * (cell + gap);
    const gx2 = gx1 + cell;
    const gy2 = gy1 + cell;
    const isVideo = ALBUM_IS_VIDEO[i];
    const show = state.albumTab === 'all' || (state.albumTab === 'pics' && !isVideo) || (state.albumTab === 'vids' && isVideo);
    const isChecked = selected.includes(i);

    // 缩略图格子（不匹配当前 Tab 的保留在树里，但渲染为占位灰）
    els.push({
      key: `g_${i}`,
      cls: 'android.widget.FrameLayout',
      id: ':id/root_view',
      desc: isVideo ? `视频 ${i + 1}` : `图片 ${i + 1}`,
      text: isVideo ? '🎬' : '🖼️',
      bounds: [gx1, gy1, gx2, gy2],
      kind: 'grid',
      bg: show ? grad(120 + i * 40) : '#e5e7eb',
      color: '#ffffff',
      radius: `${Math.round(cell * 0.04)}px`,
      font: Math.round(cell * 0.24),
      clickable: true,
      action: 'select',
      payload: i,
      enabled: show,
    });

    // 右上角圆圈选择器（直径约为格子宽度的 1/4）
    const d = Math.round(cell * 0.24);
    els.push({
      key: `c_${i}`,
      cls: 'android.widget.CheckBox',
      id: ':id/dsb',
      desc: `选择${isVideo ? '视频' : '图片'}${i + 1}`,
      text: isChecked ? '✓' : '',
      bounds: [gx2 - d - Math.round(d * 0.2), gy1 + Math.round(d * 0.2), gx2 - Math.round(d * 0.2), gy1 + Math.round(d * 1.2)],
      kind: 'circle',
      color: isChecked ? '#ffffff' : 'transparent',
      bg: isChecked ? '#ff2d55' : 'rgba(255,255,255,0.85)',
      border: isChecked ? 'none' : '2px solid #ffffff',
      radius: '50%',
      font: Math.round(d * 0.6),
      checkable: true,
      checked: isChecked,
      clickable: true,
      action: 'select',
      payload: i,
    });
  }

  // 底部：已选计数 + 发送按钮 :id/duf
  els.push({
    key: 'album_count',
    cls: 'android.widget.TextView',
    text: `已选 ${selected.length} 张`,
    bounds: frac(w, h, 0.05, 0.9, 0.6, 0.955),
    kind: 'text',
    color: '#374151',
    font: Math.round(h * 0.018),
  });
  els.push({
    key: 'album_send',
    cls: 'android.widget.Button',
    id: ':id/duf',
    text: '发送',
    bounds: frac(w, h, 0.62, 0.882, 0.955, 0.972),
    kind: 'send',
    bg: selected.length > 0 ? 'linear-gradient(135deg, #ff2d55, #ff5a3c)' : '#d1d5db',
    color: '#ffffff',
    radius: '999px',
    font: Math.round(h * 0.02),
    clickable: true,
    enabled: selected.length > 0,
    action: 'send',
  });

  return els;
}

/** 依据状态构建当前页面的元素列表 */
export function buildElements(state: PageState, dev: DemoDevice): DemoElement[] {
  return state.page === 'home' ? buildHome(state, dev) : buildAlbum(state, dev);
}

/**
 * 点击命中检测：在所有 bounds 覆盖该点的元素里，取面积最小（最具体）的一个。
 * 这样圆圈选择器（小）会压过它所在的缩略图格子（大）。
 */
export function hitTest(x: number, y: number, elements: DemoElement[]): DemoElement | null {
  let best: DemoElement | null = null;
  let bestArea = Infinity;
  for (const el of elements) {
    const [x1, y1, x2, y2] = el.bounds;
    if (x >= x1 && x <= x2 && y >= y1 && y <= y2) {
      const area = (x2 - x1) * (y2 - y1);
      if (area < bestArea) {
        bestArea = area;
        best = el;
      }
    }
  }
  return best;
}
