/**
 * 批量替换 views/rpa/*.vue 里的硬编码颜色和字号为 CSS 变量
 * 让页面样式和 linear-components.css 统一
 */
const fs = require('fs');
const path = require('path');

// 颜色映射表（硬编码 hex → CSS 变量）
const COLOR_MAP = {
  // 主题色
  '#1677ff': 'var(--accent)',
  '#4f46e5': 'var(--accent)',
  '#6366f1': 'var(--accent)',

  // 成功色（绿）
  '#52c41a': 'var(--success-color)',
  '#4caf50': 'var(--success-color)',
  '#22c55e': 'var(--success-color)', // Tailwind Green 500

  // 警告色（橙/黄）
  '#ff9800': 'var(--warning-color)',
  '#fa8c16': 'var(--warning-color)',
  '#f59e0b': 'var(--warning-color)', // Tailwind Amber 500

  // 错误色（红）
  '#f5222d': 'var(--error-color)',
  '#f87171': 'var(--error-color)', // Tailwind Red 400
  '#f44336': 'var(--error-color)',
  '#d32f2f': 'var(--error-color)',

  // 文字色
  '#334155': 'var(--text-primary)',
  '#1c2024': 'var(--text-primary)',
  '#64748b': 'var(--text-secondary)',
  '#60646c': 'var(--text-secondary)',
  '#8c8c8c': 'var(--text-secondary)',
  '#888': 'var(--text-muted)',
  '#999': 'var(--text-muted)',
  '#94a3b8': 'var(--text-muted)',
  '#6b7280': 'var(--text-muted)', // Tailwind Gray 500

  // 背景色
  '#0d0f13': 'var(--bg-page)',
  '#ffffff': 'var(--bg-card)',
  '#fff': 'var(--bg-card)',
  '#f8fafc': 'var(--bg-card-alt)',
  '#fafafa': 'var(--bg-card-alt)',

  // 边框色
  '#e5e7eb': 'var(--border-color)',
  '#e5e5e5': 'var(--border-color)',
  '#d1d5db': 'var(--border-input)',

  // 特殊背景色（警告背景）
  '#fffbe6': 'rgba(247, 107, 21, 0.08)', // 橙色半透明背景
};

// 字号映射表
const FONT_SIZE_MAP = {
  'font-size: 10px': 'font-size: var(--vben-font-size-sm)', // 10px → 12px
  'font-size: 11px': 'font-size: var(--vben-font-size-sm)', // 11px → 12px
  'font-size: 12px': 'font-size: var(--vben-font-size-sm)', // 保留 12px
  'font-size: 13px': 'font-size: var(--vben-font-size-base)', // 13px 标准
  'font-size: 14px': 'font-size: var(--vben-font-size-lg)', // 14px 大号
  'font-size: 15px': 'font-size: var(--vben-font-size-lg)', // 15px → 14px
};

function replaceInFile(filePath) {
  let content = fs.readFileSync(filePath, 'utf8');
  let changed = false;

  // 提取 <style> 块
  const styleRegex = /(<style[^>]*>)([\s\S]*?)(<\/style>)/g;
  let match;
  const replacements = [];

  while ((match = styleRegex.exec(content)) !== null) {
    const [fullMatch, openTag, styleContent, closeTag] = match;
    let newStyleContent = styleContent;

    // 替换颜色（大小写不敏感）
    Object.entries(COLOR_MAP).forEach(([hex, variable]) => {
      const hexUpper = hex.toUpperCase();
      const hexLower = hex.toLowerCase();
      const regex = new RegExp(`\\b${hex}\\b|\\b${hexUpper}\\b|\\b${hexLower}\\b`, 'g');
      if (newStyleContent.match(regex)) {
        newStyleContent = newStyleContent.replace(regex, variable);
        changed = true;
      }
    });

    // 替换字号
    Object.entries(FONT_SIZE_MAP).forEach(([old, newVal]) => {
      const regex = new RegExp(old.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'g');
      if (newStyleContent.includes(old)) {
        newStyleContent = newStyleContent.replace(regex, newVal);
        changed = true;
      }
    });

    replacements.push({
      start: match.index,
      end: match.index + fullMatch.length,
      newContent: openTag + newStyleContent + closeTag,
    });
  }

  if (changed) {
    // 逆序替换（从后往前，避免索引错乱）
    replacements.reverse().forEach(({ start, end, newContent }) => {
      content = content.slice(0, start) + newContent + content.slice(end);
    });
    fs.writeFileSync(filePath, content, 'utf8');
    return true;
  }

  return false;
}

// 查找所有 rpa 页面（递归扫描目录）
function findVueFiles(dir) {
  const results = [];
  const entries = fs.readdirSync(dir, { withFileTypes: true });
  entries.forEach((entry) => {
    const fullPath = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      results.push(...findVueFiles(fullPath));
    } else if (entry.isFile() && entry.name.endsWith('.vue')) {
      results.push(fullPath);
    }
  });
  return results;
}

const rpaDir = path.join(__dirname, '../src/views/rpa');
const files = findVueFiles(rpaDir);

console.log(`=== 开始统一颜色和字号 ===`);
console.log(`找到 ${files.length} 个 Vue 文件\n`);

let changedCount = 0;
files.forEach((file) => {
  const relativePath = path.relative(rpaDir, file);
  if (replaceInFile(file)) {
    console.log(`✓ ${relativePath}`);
    changedCount++;
  }
});

console.log(`\n=== 完成 ===`);
console.log(`修改了 ${changedCount} 个文件`);
console.log(`${files.length - changedCount} 个文件无需修改`);
