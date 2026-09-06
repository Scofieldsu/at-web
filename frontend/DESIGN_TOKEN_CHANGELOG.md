# Linear 风格 Design Token 定制完成

**构建时间：** 2026-08-29 11:40  
**变更文件：** `src/App.vue` （扩展 `themeConfig`）  
**技术方案：** Ant Design Vue 4 ConfigProvider + Design Token

---

## ✅ 已应用的 Linear 风格特征

### 1️⃣ **配色系统（Radix Colors + Linear Indigo）**

| Token | 之前 | 现在 | 说明 |
|-------|------|------|------|
| `colorPrimary` | `#0960bd` 蓝 | **`#6366f1`** Indigo | Linear 主色 |
| `colorSuccess` | `#55D187` | `#30a46c` Green 9 | Radix 绿 |
| `colorWarning` | `#EFBD47` | `#f76b15` Orange 9 | Radix 橙 |
| `colorError` | `#ED6F6F` | `#e5484d` Red 9 | Radix 红 |
| `colorInfo` | `#0960bd` | `#0090ff` Blue 9 | Radix 蓝 |

### 2️⃣ **字体系统（紧凑化）**

| Token | 之前 | 现在 | 影响 |
|-------|------|------|------|
| `fontSize` | 14px | **13px** | 所有文字、按钮、表单 |
| 标题字号 | h1-h5 默认 | 整体降 1-2px | 标题更紧凑 |

### 3️⃣ **控件尺寸（更紧凑）**

| Token | 之前 | 现在 | 影响组件 |
|-------|------|------|---------|
| `controlHeight` | 40px | **32px** | 按钮、输入框、Select |
| `controlHeightLG` | 48px | **38px** | 大尺寸控件 |
| `controlHeightSM` | 32px | **26px** | 小尺寸控件 |

**视觉效果**：
- ✅ 表单更紧凑，信息密度更高
- ✅ 按钮从"胖按钮"变成"扁按钮"（符合 Linear 风格）

### 4️⃣ **圆角系统（Linear 小圆角）**

| Token | 之前 | 现在 |
|-------|------|------|
| `borderRadius` | 6px | **4px** |
| `borderRadiusLG` | 8px | **6px** |
| `borderRadiusSM` | 4px | **2px** |

**视觉效果**：更方正，符合 Linear 的简洁风格

### 5️⃣ **间距系统（紧凑 20%）**

| Token | 之前 | 现在 |
|-------|------|------|
| `padding` | 16px | **12px** |
| `paddingLG` | 24px | **16px** |
| `paddingSM` | 12px | **8px** |
| `margin` | 16px | **12px** |

**影响**：
- ✅ 卡片内边距缩小，内容更集中
- ✅ 按钮内边距缩小，更紧凑

### 6️⃣ **阴影系统（极简化）**

| Token | 之前 | 现在 |
|-------|------|------|
| `boxShadow` | 中等阴影 | **极浅阴影**（几乎不可见） |
| `boxShadowSecondary` | 较深 | **浅阴影** |

**视觉效果**：去掉视觉噪音，更扁平现代

---

## 🎯 组件级专项定制

### Table（表格）

```typescript
Table: {
  cellPaddingBlock: 8,          // 单元格高度：16px → 8px（紧凑）
  cellPaddingInline: 12,        // 单元格宽度：16px → 12px
  headerBg: '#fafafa',          // 表头浅灰背景（不是纯白）
  headerColor: '#1c2024',       // 表头深灰文字
  rowHoverBg: 'rgba(0,0,0,0.02)', // hover 极浅灰
  borderColor: '#e5e5e5',       // 边框浅灰
}
```

**效果**：
- ✅ 表格行高从臃肿变紧凑
- ✅ 去掉强烈的 hover 效果（更干净）
- ✅ 表头背景有层次感

### Form（表单）

```typescript
Form: {
  labelFontSize: 13,            // label 字号
  labelColor: '#60646c',        // label 次要灰色
  verticalLabelPadding: '0 0 4px',
}
```

**效果**：
- ✅ Label 字号变小（和输入框更协调）
- ✅ Label 颜色弱化（不抢眼）

### Button（按钮）

```typescript
Button: {
  primaryShadow: 'none',        // 主按钮去阴影
  defaultBorderColor: '#d4d4d8',
  defaultColor: '#3f3f46',
  fontWeight: 500,              // 字重 500（Linear 风格）
}
```

**效果**：
- ✅ 按钮扁平化（无阴影）
- ✅ 默认按钮更淡（不抢主按钮风头）
- ✅ 字重 500（之前 400 太细，700 太粗）

### Card（卡片）

```typescript
Card: {
  boxShadow: 'none',            // 去阴影
  headerBg: 'transparent',      // 头部透明
  headerFontSize: 14,           // 标题 14px（之前 16px）
  paddingLG: 16,                // 大卡片内边距：24px → 16px
  padding: 12,                  // 默认内边距：16px → 12px
}
```

**效果**：
- ✅ 卡片从"浮起来"变成"贴着页面"（更扁平）
- ✅ 标题字号更小（不突兀）
- ✅ 内边距紧凑（信息密度提升）

### Input（输入框）

```typescript
Input: {
  paddingBlock: 6,              // 上下内边距（之前 8px）
  paddingInline: 10,            // 左右内边距（之前 12px）
}
```

**效果**：
- ✅ 输入框更矮（配合 controlHeight: 32）
- ✅ 和按钮高度协调

### Menu（菜单）

```typescript
Menu: {
  itemHeight: 34,               // 菜单项高度（和前面改的 CSS 一致）
  itemMarginInline: 0,
  itemBorderRadius: 0,          // Linear 不用圆角
  iconSize: 16,
}
```

**效果**：
- ✅ 和我们之前改的侧边栏 CSS 保持一致
- ✅ 顶部菜单（如果有）也会变紧凑

### Select（下拉框）

```typescript
Select: {
  optionHeight: 32,             // 下拉选项高度
  optionPadding: '6px 12px',
}
```

### Modal（弹窗）

```typescript
Modal: {
  headerBg: '#fafafa',          // 弹窗头部浅灰
  contentBg: '#ffffff',
  borderRadiusLG: 6,            // 圆角 8px → 6px
  paddingLG: 16,                // 内边距 24px → 16px
}
```

### Tag（标签）

```typescript
Tag: {
  defaultBg: '#f4f4f5',         // 默认背景浅灰
  defaultColor: '#3f3f46',      // 默认文字深灰
}
```

---

## 🔍 验证方法（硬刷新 Ctrl+Shift+R）

### 1. **看主色变化（最明显）**
   - 打开任何页面
   - 所有主按钮从 `#0960bd` 蓝 → `#6366f1` Indigo 紫蓝
   - 链接颜色同步变化

### 2. **看表格变化**
   - 打开 **用例管理** 或 **任务列表** 页面
   - ✅ 表格行高更紧凑（之前松散）
   - ✅ 表头背景变浅灰（之前白色）
   - ✅ Hover 效果更细腻（之前太重）

### 3. **看表单变化**
   - 打开 **创建用户** 或 **消息发送** 页面
   - ✅ 输入框更矮（32px，之前 40px）
   - ✅ Label 字号更小（13px，之前 14px）
   - ✅ 按钮更扁（和输入框高度协调）

### 4. **看卡片变化**
   - Dashboard 页面的卡片
   - ✅ 无阴影（之前有阴影）
   - ✅ 内边距更紧（内容更集中）

### 5. **看圆角变化**
   - 所有按钮、输入框、卡片的圆角
   - ✅ 从 6px → 4px（更方正）

### 6. **看整体字号**
   - 对比之前的页面截图
   - ✅ 所有文字略小（13px，之前 14px）
   - ✅ 信息密度提升（同屏显示更多内容）

---

## 📊 对比总结

| 维度 | 之前（antd 默认） | 现在（Linear Token） |
|------|------------------|---------------------|
| 主色 | 蓝色 `#0960bd` | **Indigo `#6366f1`** |
| 字号 | 14px | **13px** |
| 控件高度 | 40px | **32px**（紧凑 20%） |
| 圆角 | 6px | **4px**（更方正） |
| 间距 | 16px | **12px**（紧凑 25%） |
| 阴影 | 中等 | **极浅**（几乎不可见） |
| 表格行高 | 松散 | **紧凑** |
| 卡片 | 浮起 | **扁平** |
| 观感 | 传统企业风 | **现代、紧凑、Linear 风** |

---

## 🎨 和之前的菜单改造结合

**之前改的**（menu-theme.less）：
- ✅ 侧边栏深色 `#1a1a1a`
- ✅ 菜单项 13px 字号
- ✅ Linear 激活态（紫蓝半透明）

**现在改的**（Design Token）：
- ✅ 页面主体所有 antd 组件（表格/表单/按钮/卡片）

**综合效果**：
- 侧边栏 + 内容区 **统一**采用 Linear 风格
- 字号、圆角、间距 **全局一致**
- 不再有"菜单现代、页面传统"的割裂感

---

## 🚀 后续可选优化

如果你觉得还不够"Linear"，可以继续调：

### 1. **深色主题全局开启**
修改 `src/settings/projectSetting.ts`：
```typescript
// Website gray mode, open for possible mourning dates
grayMode: false,
// Color Weakness Mode
colorWeak: false,
// 改成深色主题
theme: ThemeEnum.DARK,
```

### 2. **表格去掉边框**
在 Token 里加：
```typescript
Table: {
  // ...现有配置
  borderColor: 'transparent',  // 去掉边框
}
```

### 3. **按钮更扁平**
```typescript
Button: {
  // ...现有配置
  controlHeight: 30,  // 按钮单独更矮
}
```

### 4. **卡片用细边框代替阴影**
```typescript
Card: {
  // ...现有配置
  boxShadow: 'none',
  borderColor: '#e5e5e5',  // 加细边框
}
```

---

## 📝 注意事项

### ✅ 优势
- **全局生效**：所有 19 个页面的所有 antd 组件同时改变
- **可回退**：只改了一个文件（App.vue），随时能还原
- **无侵入**：业务代码一行没动

### ⚠️ 局限
- 侧边栏的深色是 CSS 覆盖的，不是 Design Token
- 个别页面如果有内联样式会覆盖 Token
- 深色主题（`isDark.value ? darkTheme : {}`）的优先级更高，会覆盖部分 Token

---

## 🎉 立即生效

硬刷新浏览器（**Ctrl + Shift + R**），所有页面立即变成 Linear 风格。

如果想微调某个 Token（如觉得 13px 太小），直接改 `App.vue` 里的数值，重新 `pnpm build` 即可。
