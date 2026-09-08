<template>
  <!-- 手机实时画面：按设备像素 bounds 绝对定位渲染。父容器尺寸 = devW*scale × devH*scale，
       本组件用 left/top = bounds*scale 定位，因此不同分辨率下版式一致。 -->
  <div class="ds-root" :style="rootStyle">
    <template v-for="el in elements" :key="el.key">
      <!-- 状态栏：特殊处理（左侧时钟 + 右侧信号/WiFi/电量） -->
      <div v-if="el.kind === 'statusbar'" class="ds-statusbar" :style="styleOf(el)">
        <span class="ds-status-time">09:41</span>
        <span class="ds-status-right">
          <span class="ds-status-signal">▂▄▆█</span>
          <span>5G</span>
          <span class="ds-status-bat">▰▰▰▰▱ {{ el.payload }}%</span>
        </span>
      </div>

      <!-- 底部导航：图标（大）+ 标签（小） -->
      <div
        v-else-if="el.kind === 'tabbar'"
        class="ds-tabbar"
        :style="{ ...styleOf(el), color: el.color, background: el.bg, borderBottom: el.checked ? `2px solid ${el.color}` : 'none' }"
        @click="emitAction(el)"
      >
        <span class="ds-tab-icon" :style="{ fontSize: `${Math.round(el.font! * 1.6)}px` }">{{ el.icon || el.text }}</span>
        <span v-if="el.text" class="ds-tab-label" :style="{ fontSize: `${el.font}px` }">{{ el.text }}</span>
      </div>

      <!-- 普通元素 -->
      <div
        v-else
        class="ds-el"
        :class="`ds-${el.kind}`"
        :style="{ ...styleOf(el), background: el.bg, color: el.color, border: el.border, borderRadius: el.radius, fontSize: el.font ? `${el.font}px` : undefined, opacity: el.enabled === false ? 0.55 : 1 }"
        @click="emitAction(el)"
      >
        <span v-if="el.text" class="ds-el-text">{{ el.text }}</span>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import type { DemoDevice } from './devices';
import type { PageState, DemoElement } from './layout';
import { buildElements } from './layout';

const props = withDefaults(
  defineProps<{
    dev: DemoDevice;
    state: PageState;
    scale: number;
    /** 是否允许点击操作设备（元素查看模式下关闭） */
    clickable?: boolean;
  }>(),
  {
    clickable: true,
  },
);

const emit = defineEmits<{
  click: [x: number, y: number];
}>();

const rootStyle = computed(() => ({
  width: `${Math.round(props.dev.width * props.scale)}px`,
  height: `${Math.round(props.dev.height * props.scale)}px`,
}));

const elements = computed(() => buildElements(props.state, props.dev));

/** 把设备像素 bounds 换算为屏幕 px 的绝对定位样式 */
function styleOf(el: DemoElement): Record<string, string> {
  const [x1, y1, x2, y2] = el.bounds;
  const s = props.scale;
  return {
    position: 'absolute' as const,
    left: `${x1 * s}px`,
    top: `${y1 * s}px`,
    width: `${(x2 - x1) * s}px`,
    height: `${(y2 - y1) * s}px`,
  };
}

function emitAction(el: DemoElement) {
  if (!props.clickable) return;
  const [x1, , x2, y2] = el.bounds;
  emit('click', Math.round((x1 + x2) / 2), Math.round(y2));
}
</script>

<style scoped lang="less">
.ds-root {
  position: relative;
  overflow: hidden;
  background: #000;
  border-radius: 4px;
  user-select: none;
  line-height: 1.15;
}

.ds-el {
  box-sizing: border-box;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  white-space: nowrap;
  cursor: pointer;

  &:active {
    filter: brightness(0.92);
  }
}

.ds-el-text {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* 状态栏 */
.ds-statusbar {
  box-sizing: border-box;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 3.2%;
  cursor: default;

  .ds-status-time {
    font-weight: 600;
    letter-spacing: 0.04em;
  }

  .ds-status-right {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    font-size: 0.82em;
    opacity: 0.95;
  }

  .ds-status-signal {
    letter-spacing: -0.15em;
    font-size: 0.9em;
  }
}

/* 底部导航 */
.ds-tabbar {
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 1px;
  cursor: pointer;

  &:active {
    background: rgba(0, 0, 0, 0.04);
  }

  .ds-tab-icon {
    line-height: 1;
  }

  .ds-tab-label {
    line-height: 1;
    font-weight: 500;
  }
}

/* 高亮框（元素查看器选中节点） */
.ds-highlight {
  position: absolute;
  border: 2px solid #ff4d4f;
  background: rgba(255, 77, 79, 0.15);
  pointer-events: none;
  box-shadow: 0 0 8px rgba(255, 77, 79, 0.5);
  z-index: 20;
}
</style>
