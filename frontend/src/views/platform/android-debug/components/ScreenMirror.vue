<template>
  <a-card :bordered="false" size="small" class="mirror-card">
    <template #title>
      <a-space size="small">
        <span>实时画面</span>
        <a-tag v-if="autoRefresh" color="processing" size="small">自动刷新</a-tag>
        <a-tag v-if="online" color="orange" size="small">演示</a-tag>
      </a-space>
    </template>
    <template #extra>
      <a-tooltip title="刷新画面">
        <a-button size="small" type="text" :loading="loading" :disabled="!online" @click="refresh">
          <template #icon><ReloadOutlined /></template>
        </a-button>
      </a-tooltip>
    </template>

    <div class="mirror-viewport">
      <div v-if="!online" class="mirror-placeholder">
        <a-empty description="未连接设备">
          <template #image><MobileOutlined class="placeholder-icon" /></template>
        </a-empty>
      </div>

      <template v-else-if="dev">
        <div class="phone-frame" :class="frameClass" :style="{ '--frame-color': frameColor }">
          <div class="phone-notch" v-if="dev.hasNotch"></div>
          <div
            class="phone-screen"
            :style="{ width: `${dispW}px`, height: `${dispH}px` }"
            @click="onClickScreen"
            @mousemove="onMove"
            @mouseleave="hover = null"
          >
            <DemoScreen
              :dev="dev"
              :state="pageState"
              :scale="scale"
              :clickable="clickable"
            />
            <!-- 元素查看器选中节点的边界框 -->
            <div v-if="boxStyle" class="highlight-box" :style="boxStyle" />
            <!-- 坐标提示 -->
            <div v-if="hover" class="coord-badge">{{ hover.x }}, {{ hover.y }}</div>
            <!-- 非点击模式提示 -->
            <div v-if="!clickable" class="inspector-mode-tip">
              <EyeOutlined /> 查看模式（点击无效）
            </div>
          </div>
          <div class="phone-button"></div>
        </div>
      </template>
    </div>

    <div class="mirror-footer">
      <a-space size="small" :wrap="false">
        <a-tag v-if="dev" color="blue">{{ dev.width }}×{{ dev.height }}</a-tag>
        <a-tag>显示 {{ Math.round(scale * 100) }}%</a-tag>
        <span v-if="online && clickable" class="hint">💡 点击画面可直接操作设备（演示）</span>
      </a-space>
    </div>
  </a-card>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted } from 'vue';
import { ReloadOutlined, MobileOutlined, EyeOutlined } from '@ant-design/icons-vue';
import DemoScreen from '../demo/DemoScreen.vue';
import { deviceByUdid } from '../demo/devices';
import { useAndroidDemo } from '../demo/store';

const props = withDefaults(
  defineProps<{
    udid: string;
    online?: boolean;
    scale?: number;
    refreshRate?: number;
    autoRefresh?: boolean;
    highlightBounds?: number[] | null;
    clickable?: boolean;
    frameColor?: string;
  }>(),
  {
    scale: 0.3,
    refreshRate: 200,
    autoRefresh: false,
    highlightBounds: null,
    clickable: true,
    frameColor: '#2c3e50',
  },
);

const emit = defineEmits<{
  displayWidth: [width: number];
}>();

const demo = useAndroidDemo();
const hover = ref<{ x: number; y: number } | null>(null);
const loading = ref(false);

let timer: number | null = null;

const dev = computed(() => deviceByUdid(props.udid));
// 响应式读取该设备的页面状态（store 内 reactive）
const pageState = computed(() => {
  const rt = (demo as any).devices[props.udid];
  return rt ? rt.state : { page: 'home', albumTab: 'all', selected: [], battery: 80 };
});

const dispW = computed(() => (dev.value ? Math.round(dev.value.width * props.scale) : 0));
const dispH = computed(() => (dev.value ? Math.round(dev.value.height * props.scale) : 0));

const frameClass = computed(() => {
  if (!dev.value) return 'frame-normal';
  const ratio = dev.value.width / dev.value.height;
  if (ratio > 0.5) return 'frame-tablet';
  if (dev.value.height > 2400) return 'frame-tall';
  return 'frame-normal';
});

const boxStyle = computed(() => {
  const b = props.highlightBounds;
  if (!b || b.length !== 4 || !dev.value) return null;
  const s = props.scale;
  return {
    left: `${b[0] * s}px`,
    top: `${b[1] * s}px`,
    width: `${(b[2] - b[0]) * s}px`,
    height: `${(b[3] - b[1]) * s}px`,
  };
});

// 连接 / 断开 / 缩放变化时，同步上报显示宽度（驱动父组件下拉框对齐镜像）
watch(
  () => [props.online, props.scale, props.udid] as const,
  () => {
    if (props.online && dev.value) {
      emit('displayWidth', Math.round(dev.value.width * props.scale) + 32);
      if (props.autoRefresh) start();
      else stop();
    } else {
      stop();
    }
  },
  { immediate: true },
);

// 自动刷新开关系
watch(
  () => [props.autoRefresh, props.refreshRate] as const,
  ([auto]) => {
    stop();
    if (auto && props.online) start();
  },
);

function start() {
  stop();
  timer = window.setInterval(() => demo.tick(props.udid), props.refreshRate);
}

function stop() {
  if (timer !== null) {
    clearInterval(timer);
    timer = null;
  }
}

/** 手动刷新：模拟重新抓取一帧画面（frame 自增触发镜像重绘） */
function refresh() {
  if (!props.online) return;
  loading.value = true;
  demo.tick(props.udid);
  window.setTimeout(() => (loading.value = false), 120);
}

/** 点击画面 → 设备坐标（DemoScreen 元素中心，或由父层透传） */
function onClickScreen(e: MouseEvent) {
  if (!props.online || !props.clickable) return;
  const el = e.currentTarget as HTMLElement;
  const rect = el.getBoundingClientRect();
  const x = Math.round((e.clientX - rect.left) / props.scale);
  const y = Math.round((e.clientY - rect.top) / props.scale);
  demo.click(props.udid, x, y);
  demo.tick(props.udid);
}

function onMove(e: MouseEvent) {
  if (!dev.value) return;
  const el = e.currentTarget as HTMLElement;
  const rect = el.getBoundingClientRect();
  hover.value = {
    x: Math.round((e.clientX - rect.left) / props.scale),
    y: Math.round((e.clientY - rect.top) / props.scale),
  };
}

onMounted(() => {
  if (props.online && dev.value) {
    emit('displayWidth', Math.round(dev.value.width * props.scale) + 32);
  }
});
onUnmounted(stop);

defineExpose({ refresh });
</script>

<style scoped lang="less">
.mirror-card {
  height: 100%;

  :deep(.ant-card-body) {
    padding: 12px;
  }
}

.mirror-viewport {
  display: flex;
  justify-content: center;
  background: #fafafa;
  border: 1px solid #f0f0f0;
  border-radius: 8px;
  padding: 16px 8px;
}

.mirror-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 280px;
  min-height: 480px;
}

.placeholder-icon {
  font-size: 48px;
  color: #d9d9d9;
}

/* 手机边框 */
.phone-frame {
  position: relative;
  padding: 14px 8px 18px;
  background: linear-gradient(145deg, var(--frame-color, #2c3e50), color-mix(in srgb, var(--frame-color, #2c3e50) 80%, black));
  border-radius: 32px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.3),
    0 0 0 2px color-mix(in srgb, var(--frame-color, #2c3e50) 50%, black),
    inset 0 1px 2px rgba(255, 255, 255, 0.1);

  &.frame-tablet {
    border-radius: 24px;
    padding: 12px;
  }

  &.frame-tall {
    border-radius: 36px;
  }
}

/* 刘海 */
.phone-notch {
  position: absolute;
  top: 0;
  left: 50%;
  transform: translateX(-50%);
  width: 120px;
  height: 24px;
  background: var(--frame-color, #2c3e50);
  border-radius: 0 0 16px 16px;
  z-index: 10;

  &::before {
    content: '';
    position: absolute;
    top: 8px;
    left: 50%;
    transform: translateX(-50%);
    width: 6px;
    height: 6px;
    background: color-mix(in srgb, var(--frame-color, #2c3e50) 50%, black);
    border-radius: 50%;
  }
}

/* Home 按钮 */
.phone-button {
  position: absolute;
  bottom: 6px;
  left: 50%;
  transform: translateX(-50%);
  width: 40px;
  height: 4px;
  background: rgba(255, 255, 255, 0.15);
  border-radius: 2px;
}

.phone-screen {
  position: relative;
  line-height: 0;
  background: #000;
  border-radius: 4px;
  overflow: hidden;
  cursor: crosshair;
}

.highlight-box {
  position: absolute;
  border: 2px solid #ff4d4f;
  background: rgba(255, 77, 79, 0.15);
  pointer-events: none;
  transition: all 0.15s ease;
  box-shadow: 0 0 8px rgba(255, 77, 79, 0.5);
  z-index: 15;
}

.coord-badge {
  position: absolute;
  top: 6px;
  left: 6px;
  padding: 3px 8px;
  background: rgba(0, 0, 0, 0.75);
  color: #fff;
  font-size: 11px;
  font-family: 'Consolas', monospace;
  border-radius: 4px;
  pointer-events: none;
  line-height: 1.5;
  z-index: 10;
}

.inspector-mode-tip {
  position: absolute;
  bottom: 8px;
  left: 50%;
  transform: translateX(-50%);
  padding: 4px 12px;
  background: rgba(24, 144, 255, 0.9);
  color: #fff;
  font-size: 12px;
  border-radius: 12px;
  pointer-events: none;
  white-space: nowrap;
  z-index: 10;
}

.mirror-footer {
  margin-top: 10px;
  text-align: center;

  .hint {
    font-size: 12px;
    color: #666;
  }
}
</style>
