/**
 * JSON 语法高亮（轻量、零依赖）。
 *
 * 输入任意值或 JSON 字符串，返回安全 HTML；调用方在 <pre> 内以 v-html 渲染。
 * 着色 class：jv-key / jv-string / jv-number / jv-bool / jv-null，
 * 各页面在 scoped 样式里用 `:deep()` 配系统色板即可。
 */

const ENTITY: Record<string, string> = {
  '&': '&amp;',
  '<': '&lt;',
  '>': '&gt;',
};

function escapeHtml(s: string): string {
  return s.replace(/[&<>]/g, (c) => ENTITY[c]);
}

/** 归一化：对象 → pretty JSON；JSON 字符串 → pretty JSON；普通文本原样返回 */
function toPretty(value: unknown): string {
  if (typeof value === 'string') {
    const t = value.trim();
    if (t) {
      try {
        return JSON.stringify(JSON.parse(t), null, 2);
      } catch {
        return value; // 非 JSON 文本，原样返回
      }
    }
    return value;
  }
  if (value === undefined || value === null) return value === null ? 'null' : '';
  if (typeof value === 'object') return JSON.stringify(value, null, 2);
  return String(value);
}

// 键（含冒号）/字符串值 / true / false / null / 数字
const TOKEN_RE =
  /"(\\u[a-fA-F0-9]{4}|\\[^u]|[^\\"])*"(\s*:)?|\b(true|false|null)\b|-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?/g;

function classify(token: string): string {
  if (token[0] === '"') {
    return token.endsWith(':') ? 'jv-key' : 'jv-string';
  }
  if (token === 'true' || token === 'false') return 'jv-bool';
  if (token === 'null') return 'jv-null';
  return 'jv-number';
}

/**
 * 高亮 JSON：仅对 JSON 形态（对象 / 数组 / null）着色；
 * 普通文本只做 HTML 转义，保证 v-html 安全。
 */
export function highlightJson(value: unknown): string {
  const src = toPretty(value);
  if (!src) return '';
  const trimmed = src.trim();
  const isJsonShape = trimmed === 'null' || trimmed[0] === '{' || trimmed[0] === '[';
  if (!isJsonShape) return escapeHtml(src);

  // 结构化字符（{}[]:, 空白）留在间隙中天然安全；字符串/关键字/数字整体转义后包 span
  return src.replace(TOKEN_RE, (m) => {
    return `<span class="${classify(m)}">${escapeHtml(m)}</span>`;
  });
}
