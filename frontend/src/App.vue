<template>
  <ConfigProvider :locale="getAntdLocale" :theme="themeConfig">
    <AppProvider>
      <RouterView />
    </AppProvider>
  </ConfigProvider>
</template>

<script lang="ts" setup>
  import { AppProvider } from '@/components/Application';
  import { useTitle } from '@/hooks/web/useTitle';
  import { useLocale } from '@/locales/useLocale';
  import { ConfigProvider } from 'ant-design-vue';

  import { useDarkModeTheme } from '@/hooks/setting/useDarkModeTheme';
  import 'dayjs/locale/zh-cn';
  import { computed } from 'vue';

  // support Multi-language
  const { getAntdLocale } = useLocale();

  const { isDark, darkTheme } = useDarkModeTheme();

  // Linear 风格 Design Token - 紧凑、现代、深色优先
  const linearTheme = {
    token: {
      // ── 主色系（Linear Indigo） ──
      colorPrimary: '#6366f1',       // Indigo 500 - 主色
      colorSuccess: '#30a46c',       // Green 9 - 成功（Radix）
      colorWarning: '#f76b15',       // Orange 9 - 警告（Radix）
      colorError: '#e5484d',         // Red 9 - 错误（Radix）
      colorInfo: '#0090ff',          // Blue 9 - 信息（Radix）

      // ── 字体系统（紧凑） ──
      fontSize: 13,                  // 基础字号从 14px → 13px
      fontSizeHeading1: 24,          // h1
      fontSizeHeading2: 20,          // h2
      fontSizeHeading3: 16,          // h3
      fontSizeHeading4: 14,          // h4
      fontSizeHeading5: 13,          // h5

      // ── 控件尺寸（更紧凑） ──
      controlHeight: 32,             // 默认控件高度 40 → 32
      controlHeightLG: 38,           // 大尺寸 48 → 38
      controlHeightSM: 26,           // 小尺寸 32 → 26
      controlHeightXS: 22,           // 超小 24 → 22

      // ── 圆角系统（Linear 小圆角） ──
      borderRadius: 4,               // 基础圆角 6 → 4
      borderRadiusLG: 6,             // 大圆角 8 → 6
      borderRadiusSM: 2,             // 小圆角 4 → 2
      borderRadiusXS: 2,             // 超小 2 → 2

      // ── 边框（细边框） ──
      lineWidth: 1,                  // 边框宽度保持 1px
      lineType: 'solid',

      // ── 间距系统（紧凑） ──
      padding: 12,                   // 默认内边距 16 → 12
      paddingLG: 16,                 // 大间距 24 → 16
      paddingSM: 8,                  // 小间距 12 → 8
      paddingXS: 4,                  // 超小 8 → 4
      paddingXXS: 2,                 // 最小 4 → 2
      margin: 12,                    // 默认外边距
      marginLG: 16,
      marginSM: 8,
      marginXS: 4,
      marginXXS: 2,

      // ── 表格（紧凑、干净） ──
      // 这些会影响所有 a-table
      controlItemBgActive: 'rgba(99, 102, 241, 0.08)',  // 激活行背景（淡紫）
      controlItemBgActiveHover: 'rgba(99, 102, 241, 0.12)',

      // ── 阴影（Linear 极简，几乎无阴影） ──
      boxShadow: '0 1px 2px 0 rgba(0, 0, 0, 0.03)',           // 极浅
      boxShadowSecondary: '0 2px 4px 0 rgba(0, 0, 0, 0.06)',  // 次级
    },
    components: {
      // ── Table 组件专项定制 ──
      Table: {
        cellPaddingBlock: 8,         // 单元格上下边距 16 → 8（更紧）
        cellPaddingInline: 12,       // 单元格左右边距 16 → 12
        headerBg: '#fafafa',         // 表头背景（浅灰，不是纯白）
        headerColor: '#1c2024',      // 表头文字（深灰）
        rowHoverBg: 'rgba(0, 0, 0, 0.02)', // hover 背景（极浅灰）
        borderColor: '#e5e5e5',      // 边框颜色（浅灰）
      },

      // ── Form 组件专项定制 ──
      Form: {
        labelFontSize: 13,           // label 字号
        labelColor: '#60646c',       // label 颜色（次要文字）
        verticalLabelPadding: '0 0 4px', // 垂直布局 label 下边距
      },

      // ── Button 组件专项定制 ──
      Button: {
        primaryShadow: 'none',       // 主按钮去掉阴影
        defaultBorderColor: '#d4d4d8', // 默认按钮边框（浅灰）
        defaultColor: '#3f3f46',     // 默认按钮文字（深灰）
        fontWeight: 500,             // 按钮字重 400 → 500
      },

      // ── Input 组件专项定制 ──
      Input: {
        paddingBlock: 6,             // 输入框上下内边距（更紧）
        paddingInline: 10,           // 输入框左右内边距
      },

      // ── Card 组件专项定制 ──
      Card: {
        boxShadow: 'none',           // 卡片去掉阴影
        headerBg: 'transparent',     // 卡片头部透明
        headerFontSize: 14,          // 卡片标题字号
        headerFontSizeSM: 13,
        paddingLG: 16,               // 卡片大尺寸内边距 24 → 16
        padding: 12,                 // 卡片默认内边距
      },

      // ── Menu 组件（虽然用了自定义 CSS，但保持一致） ──
      Menu: {
        itemHeight: 34,              // 菜单项高度（和我们改的 CSS 一致）
        itemMarginInline: 0,         // 菜单项左右边距
        itemBorderRadius: 0,         // 菜单项圆角（Linear 不用圆角）
        iconSize: 16,                // 图标尺寸
      },

      // ── Select 组件 ──
      Select: {
        optionHeight: 32,            // 下拉选项高度
        optionPadding: '6px 12px',   // 下拉选项内边距
      },

      // ── Modal 组件 ──
      Modal: {
        headerBg: '#fafafa',         // 弹窗头部背景
        contentBg: '#ffffff',
        borderRadiusLG: 6,           // 弹窗圆角
        paddingLG: 16,
      },

      // ── Tag 组件 ──
      Tag: {
        defaultBg: '#f4f4f5',        // 默认标签背景
        defaultColor: '#3f3f46',     // 默认标签文字
      },
    },
  };

  const themeConfig = computed(() =>
    Object.assign(
      linearTheme,
      isDark.value ? darkTheme : {},
    ),
  );
  // Listening to page changes and dynamically changing site titles
  useTitle();
</script>
