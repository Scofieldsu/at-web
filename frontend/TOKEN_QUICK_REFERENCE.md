# Design Token 快速调整参考

**文件位置：** `src/App.vue`（第 22-135 行）

如果你觉得某个效果不满意，直接改对应 Token 的数值，重新 `pnpm build` 即可。

---

## 常见调整场景

### 😐 "字太小了，看着累"
**原因：** `fontSize: 13` 可能不适合你的显示器

**改法：**
```typescript
fontSize: 14,  // 改回 14px（antd 默认）
```

**影响**：所有文字、按钮、表单 label 都会变大

---

### 😐 "表格太挤了，行距太小"
**原因：** `cellPaddingBlock: 8` 太紧凑

**改法：**
```typescript
Table: {
  cellPaddingBlock: 12,  // 8 → 12（增大行高）
  cellPaddingInline: 16, // 12 → 16（增大左右间距）
}
```

---

### 😐 "按钮太矮了，不好点"
**原因：** `controlHeight: 32` 太紧凑

**改法：**
```typescript
controlHeight: 36,  // 32 → 36（折中，不回到 40）
```

**影响**：所有按钮、输入框、Select 都会变高

---

### 😐 "卡片太方了，想要点圆角"
**原因：** `borderRadius: 4` 太小

**改法：**
```typescript
borderRadius: 6,     // 4 → 6（恢复 antd 默认）
borderRadiusLG: 8,   // 6 → 8
```

---

### 😐 "主色太紫了，想要蓝色"
**原因：** `colorPrimary: '#6366f1'` 是 Indigo

**改法（选一个）：**
```typescript
colorPrimary: '#0090ff',  // Radix Blue 9（亮蓝）
colorPrimary: '#3b82f6',  // Tailwind Blue 500（标准蓝）
colorPrimary: '#0588f0',  // Radix Blue 10（深蓝）
```

---

### 😐 "表头背景太灰了，想要纯白"
**原因：** `headerBg: '#fafafa'` 是浅灰

**改法：**
```typescript
Table: {
  headerBg: '#ffffff',  // 改成纯白
}
```

---

### 😐 "间距太挤了，想松一点"
**原因：** `padding: 12` 太紧

**改法：**
```typescript
padding: 16,    // 12 → 16（恢复 antd 默认）
paddingLG: 24,  // 16 → 24
```

---

### 😐 "阴影太浅了，卡片看不出层次"
**原因：** `boxShadow` 太浅 + `Card.boxShadow: 'none'`

**改法：**
```typescript
// 1. 调整全局阴影（token 部分）
boxShadow: '0 1px 3px 0 rgba(0, 0, 0, 0.1)',  // 加深

// 2. 让卡片用全局阴影（components.Card 部分）
Card: {
  boxShadow: undefined,  // 删掉这行，用全局的
}
```

---

### 😐 "按钮字太细了"
**原因：** `Button.fontWeight: 500`

**改法：**
```typescript
Button: {
  fontWeight: 600,  // 500 → 600（更粗）
}
```

---

### 😐 "表格 hover 效果看不出来"
**原因：** `rowHoverBg: 'rgba(0, 0, 0, 0.02)'` 太浅

**改法：**
```typescript
Table: {
  rowHoverBg: 'rgba(0, 0, 0, 0.04)',  // 0.02 → 0.04（加深）
}
```

---

### 😐 "输入框太矮了，光标显示不全"
**原因：** `Input.paddingBlock: 6` 太小

**改法：**
```typescript
Input: {
  paddingBlock: 8,  // 6 → 8（增大上下内边距）
}
```

---

## 💡 调整技巧

### 1. **渐进式调整**
不要一次改多个 Token，改一个 → build → 刷新 → 看效果 → 再改下一个

### 2. **只改你不满意的**
不是所有 Token 都要改，只调那些"不舒服"的地方

### 3. **用浏览器 DevTools 先试**
在浏览器控制台里直接改 CSS 变量，看效果满意了再改 Token：
```javascript
// 浏览器控制台
document.documentElement.style.setProperty('--ant-font-size', '14px');
```

### 4. **参考 antd 默认值**
如果想知道某个 Token 的原始值，查 [Ant Design Token 文档](https://ant.design/docs/react/customize-theme#seedtoken)

---

## 📏 Token 数值参考

### 字号梯度（常见选择）
```
12px - 极小（辅助信息）
13px - 当前选择（紧凑）
14px - antd 默认
15px - 略大
16px - 大正文
```

### 控件高度梯度
```
28px - 极紧凑
32px - 当前选择（Linear 风格）
36px - 折中
40px - antd 默认
44px - 宽松
```

### 圆角梯度
```
0px  - 无圆角（极简）
2px  - 极小
4px  - 当前选择（Linear）
6px  - antd 默认
8px  - 较圆
12px - 很圆
```

### 间距梯度
```
8px  - 紧凑
12px - 当前选择
16px - antd 默认
20px - 宽松
24px - 很宽松
```

---

## 🎨 预设主题色（直接复制）

### 蓝色系
```typescript
colorPrimary: '#0090ff',  // Radix Blue 9（亮蓝）
colorPrimary: '#3b82f6',  // Tailwind Blue 500（标准蓝）
colorPrimary: '#1677ff',  // antd 默认蓝
```

### 紫色系
```typescript
colorPrimary: '#6366f1',  // Indigo 500（当前）
colorPrimary: '#8b5cf6',  // Violet 500（更紫）
colorPrimary: '#a855f7',  // Purple 500（亮紫）
```

### 绿色系
```typescript
colorPrimary: '#30a46c',  // Radix Green 9
colorPrimary: '#10b981',  // Emerald 500
colorPrimary: '#22c55e',  // Green 500
```

### 红色系
```typescript
colorPrimary: '#e5484d',  // Radix Red 9
colorPrimary: '#ef4444',  // Red 500
colorPrimary: '#dc2626',  // Red 600
```

---

## 🔧 完整 Token 列表位置

在 `src/App.vue` 里搜索对应关键字：

| 想改的内容 | 搜索关键字 | 行数范围 |
|-----------|-----------|---------|
| 主色 | `colorPrimary` | ~27 |
| 字号 | `fontSize` | ~34 |
| 控件高度 | `controlHeight` | ~42 |
| 圆角 | `borderRadius` | ~48 |
| 间距 | `padding` | ~56 |
| 阴影 | `boxShadow` | ~69 |
| 表格 | `Table:` | ~75 |
| 表单 | `Form:` | ~84 |
| 按钮 | `Button:` | ~91 |
| 输入框 | `Input:` | ~98 |
| 卡片 | `Card:` | ~104 |
| 菜单 | `Menu:` | ~113 |

---

## 🚀 快速还原

如果改乱了，想一键还原到 Linear 版本：

```bash
cd c:/harper/rpa-test-automation/web-vben
git checkout src/App.vue
pnpm build
```

（前提是你之前 commit 了这次改动）

---

## 📞 常见问题

**Q: 改了 Token 但没生效？**  
A: 硬刷新浏览器（Ctrl + Shift + R），清除缓存

**Q: 只想改某个页面的样式，不想全局改？**  
A: Design Token 是全局的。单页面定制要用 CSS 覆盖

**Q: Token 和之前改的 menu-theme.less 冲突了？**  
A: CSS 优先级更高，menu-theme.less 会覆盖 Token。如果想让 Token 生效，删掉 LESS 里对应的规则

**Q: 深色主题下 Token 不生效？**  
A: `darkTheme` 的优先级更高。要改深色下的效果，需要在 `useDarkModeTheme()` 里调整

---

**修改后记得重新构建：** `pnpm build`
