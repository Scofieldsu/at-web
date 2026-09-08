/**
 * 演示 UI 层级树生成 — 把 layout.ts 的元素序列化成 uiautomator2 风格节点树，
 * 供「元素查看」Tab 渲染。形状与真实后端 server/modules/android/xml_parser.py
 * 的 parse_hierarchy 输出一致：
 *
 *   { tag: "node", attrs: {...}, bounds: [x1,y1,x2,y2], children: [...] }
 */
import type { DemoDevice } from './devices';
import type { DemoElement, PageState } from './layout';
import { buildElements } from './layout';

export interface DemoTree {
  tag: string;
  attrs: Record<string, string>;
  bounds: number[];
  children: DemoTree[];
}

const PKG = 'com.ss.android.ugc.aweme.lite';

/** 把一个演示元素映射为节点（仅保留 ElementViewer 用到的属性） */
function toNode(el: DemoElement, dev: DemoDevice, state: PageState): DemoTree {
  const attrs: Record<string, string> = {
    class: el.cls,
    package: PKG,
    bounds: `[${el.bounds[0]},${el.bounds[1]}][${el.bounds[2]},${el.bounds[3]}]`,
    clickable: el.clickable ? 'true' : 'false',
    enabled: el.enabled === false ? 'false' : 'true',
  };
  if (el.checkable) attrs.checkable = 'true';
  if (el.checked !== undefined) attrs.checked = el.checked ? 'true' : 'false';
  if (el.id) attrs['resource-id'] = `${PKG}:${el.id}`;
  if (el.text) attrs.text = el.text;
  if (el.desc) attrs['content-desc'] = el.desc;

  return {
    tag: 'node',
    attrs,
    bounds: el.bounds,
    children: [],
  };
}

/**
 * 构造整棵 UI 树。把扁平元素按页面组织成有层级的结构（root → 分区 → 元素），
 * 这样树的「节点总数 / 可点击」统计、展开折叠都更接近真实 dump。
 */
export function buildTree(state: PageState, dev: DemoDevice): DemoTree {
  const els = buildElements(state, dev);
  const root: DemoTree = {
    tag: 'node',
    attrs: {
      class: 'android.widget.FrameLayout',
      package: PKG,
      bounds: `[0,0][${dev.width},${dev.height}]`,
      clickable: 'false',
      enabled: 'true',
    },
    bounds: [0, 0, dev.width, dev.height],
    children: [],
  };

  // 分区容器（视觉分组，bounds 覆盖该分区元素的外接矩形）
  const sections: { name: string; keys: Set<string> }[] =
    state.page === 'home'
      ? [
          { name: '状态栏', keys: new Set(['statusbar']) },
          { name: '搜索', keys: new Set(['search']) },
          { name: '视频卡片', keys: new Set(['video', 'avatar', 'like', 'comment', 'share']) },
          { name: '底部导航', keys: new Set(['nav_home', 'nav_friend', 'nav_create', 'nav_msg', 'nav_me']) },
        ]
      : [
          { name: '状态栏', keys: new Set(['statusbar']) },
          { name: '顶栏', keys: new Set(['album_back', 'album_title', 'album_cancel']) },
          { name: '分类 Tab', keys: new Set(['tab_all', 'tab_pics', 'tab_vids']) },
          { name: '缩略图网格', keys: new Set(els.filter((e) => e.key.startsWith('g_') || e.key.startsWith('c_')).map((e) => e.key)) },
          { name: '操作栏', keys: new Set(['album_count', 'album_send']) },
        ];

  const byKey = new Map(els.map((e) => [e.key, e]));
  for (const sec of sections) {
    const secEls = [...sec.keys].map((k) => byKey.get(k)).filter((e): e is DemoElement => !!e);
    if (!secEls.length) continue;
    const b = unionBounds(secEls);
    const secNode: DemoTree = {
      tag: 'node',
      attrs: {
        class: 'android.view.ViewGroup',
        package: PKG,
        bounds: `[${b[0]},${b[1]}][${b[2]},${b[3]}]`,
        clickable: 'false',
        enabled: 'true',
      },
      bounds: b,
      children: secEls.map((e) => toNode(e, dev, state)),
    };
    root.children.push(secNode);
  }
  return root;
}

/** 一组元素 bounds 的外接矩形 */
function unionBounds(els: DemoElement[]): number[] {
  let x1 = Infinity, y1 = Infinity, x2 = -Infinity, y2 = -Infinity;
  for (const e of els) {
    x1 = Math.min(x1, e.bounds[0]);
    y1 = Math.min(y1, e.bounds[1]);
    x2 = Math.max(x2, e.bounds[2]);
    y2 = Math.max(y2, e.bounds[3]);
  }
  return [x1, y1, x2, y2];
}

/** 统计（与 xml_parser.summarize 对齐） */
export function summarize(tree: DemoTree): { total: number; clickable: number; checkable: number; packages: string[] } {
  let total = 0, clickable = 0, checkable = 0;
  const packages = new Set<string>();
  const walk = (n: DemoTree) => {
    total += 1;
    if (n.attrs.clickable === 'true') clickable += 1;
    if (n.attrs.checkable === 'true') checkable += 1;
    if (n.attrs.package) packages.add(n.attrs.package);
    n.children.forEach(walk);
  };
  walk(tree);
  return { total, clickable, checkable, packages: [...packages] };
}
