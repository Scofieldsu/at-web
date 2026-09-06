import { ThemeEnum } from '../enums/appEnum';

export const prefixCls = 'vben';

export const multipleTabHeight = 30;

export const darkMode = ThemeEnum.LIGHT;

// 页脚固定高度
export const footerHeight = 75;

// .@{namespace}-layout-multiple-header__placeholder
// 全屏页头动画时长
export const layoutMultipleHeadePlaceholderTime = 0.6;

// app theme preset color - Linear 风格（紫蓝为主）
export const APP_PRESET_COLOR_LIST: string[] = [
  '#6366f1', // Indigo 500 - Linear 主色
  '#8b5cf6', // Violet 500 - 紫罗兰
  '#0090ff', // Blue 9 - 亮蓝
  '#00a2c7', // Cyan 9 - 青色
  '#30a46c', // Green 9 - 绿色
  '#f76b15', // Orange 9 - 橙色
  '#e5484d', // Red 9 - 红色
  '#d6409f', // Pink 9 - 粉色
  '#12a594', // Teal 9 - 青绿
];

// header preset color - 干净的顶部配色
export const HEADER_PRESET_BG_COLOR_LIST: string[] = [
  '#ffffff', // 白色（推荐）
  '#f8fafc', // 极浅灰
  '#1e293b', // 深蓝灰
  '#0f172a', // 深色模式
  '#312e81', // 深靛蓝
  '#1e40af', // 深蓝
  '#be123c', // 深玫红
  '#0369a1', // 深天蓝
  '#064e3b', // 深绿
  '#6366f1', // 靛蓝
  '#334155', // 中灰蓝
];

// sider preset color - Linear 风格浅色侧边栏
export const SIDE_BAR_BG_COLOR_LIST: string[] = [
  '#f1f5f9', // Slate 100 蓝灰（推荐）
  '#ffffff', // 白色
  '#fafafa', // 极浅灰
  '#f4f4f5', // Zinc 100
  '#f8fafc', // Slate 50 - 极浅蓝灰
  '#eef2ff', // Indigo 50（浅靛蓝调）
  '#f0f9ff', // Sky 50 - 浅天蓝
  '#f0fdf4', // Green 50 - 浅绿
  '#fff7ed', // Orange 50 - 浅橙
  '#fdf2f8', // Pink 50 - 浅粉
  '#faf5ff', // Violet 50 - 浅紫
  '#fef2f2', // Red 50 - 浅红
];
