<template>
  <div class="android-debug">
    <!-- 页面标题 -->
    <div class="page-title">
      <span class="title-icon">📱</span>
      <span class="title-text">Android 设备调试</span>
      <a-tag color="orange" class="demo-tag">演示模式 · 无真实设备</a-tag>
    </div>

    <a-alert type="info" show-icon class="demo-alert">
      <template #description>
        演示环境未连接真实 Android 设备，下方两台机器为<strong>虚拟设备</strong>：实时画面、按键、滑动、
        相册选择、UI 层级树、混淆 ID 查找等均在浏览器内内存模拟，用于演示调试流程与界面。
      </template>
    </a-alert>

    <!-- 顶部设备选择栏 -->
    <div class="device-bar">
      <div class="device-controls">
        <!-- 设备1控制区 -->
        <div class="device-control-group" :style="{ width: `${displayWidth1}px` }">
          <div class="control-label">
            <span class="frame-dot" style="background: #2c3e50"></span>
            设备 1
          </div>
          <a-select
            v-model:value="device1"
            placeholder="选择设备"
            class="device-dropdown"
            size="small"
            :loading="devicesLoading"
            :dropdown-match-select-width="false"
            @change="() => onDeviceChange(1)"
          >
            <a-select-option v-for="dev in devices" :key="dev.udid" :value="dev.udid">
              <div class="device-option">
                <a-badge :status="dev.online ? 'success' : 'default'" />
                <span class="device-name">{{ dev.name }}</span>
                <span class="udid-text">{{ dev.udid }}</span>
              </div>
            </a-select-option>
          </a-select>
          <div class="control-buttons">
            <a-button
              type="primary"
              size="small"
              :loading="connecting1"
              :disabled="!device1 || online1"
              @click="() => connect(1)"
            >
              {{ online1 ? '已连接' : '连接' }}
            </a-button>
            <a-button size="small" :disabled="!online1" @click="() => disconnect(1)">
              断开
            </a-button>
          </div>
          <!-- 设备1状态 -->
          <div v-if="info1.width" class="device-status">
            <a-tag color="blue" size="small">{{ info1.width }}×{{ info1.height }}</a-tag>
            <a-tag v-if="info1.sdk" color="green" size="small">
              {{ getAndroidVersion(info1.sdk) }}
            </a-tag>
            <a-tag v-if="info1.current_app?.activity" color="purple" size="small">
              {{ getActivityShortName(info1.current_app.activity) }}
            </a-tag>
          </div>
        </div>

        <!-- 设备2控制区 -->
        <div class="device-control-group" :style="{ width: `${displayWidth2}px` }">
          <div class="control-label">
            <span class="frame-dot" style="background: #8b4513"></span>
            设备 2
          </div>
          <a-select
            v-model:value="device2"
            placeholder="选择设备"
            class="device-dropdown"
            size="small"
            :loading="devicesLoading"
            :dropdown-match-select-width="false"
            @change="() => onDeviceChange(2)"
          >
            <a-select-option v-for="dev in devices" :key="dev.udid" :value="dev.udid">
              <div class="device-option">
                <a-badge :status="dev.online ? 'success' : 'default'" />
                <span class="device-name">{{ dev.name }}</span>
                <span class="udid-text">{{ dev.udid }}</span>
              </div>
            </a-select-option>
          </a-select>
          <div class="control-buttons">
            <a-button
              type="primary"
              size="small"
              :loading="connecting2"
              :disabled="!device2 || online2"
              @click="() => connect(2)"
            >
              {{ online2 ? '已连接' : '连接' }}
            </a-button>
            <a-button size="small" :disabled="!online2" @click="() => disconnect(2)">
              断开
            </a-button>
          </div>
          <!-- 设备2状态 -->
          <div v-if="info2.width" class="device-status">
            <a-tag color="blue" size="small">{{ info2.width }}×{{ info2.height }}</a-tag>
            <a-tag v-if="info2.sdk" color="green" size="small">
              {{ getAndroidVersion(info2.sdk) }}
            </a-tag>
            <a-tag v-if="info2.current_app?.activity" color="purple" size="small">
              {{ getActivityShortName(info2.current_app.activity) }}
            </a-tag>
          </div>
        </div>

        <!-- 刷新按钮 -->
        <div class="refresh-control">
          <a-button :loading="devicesLoading" @click="loadDevices">
            <template #icon><ReloadOutlined /></template>
            刷新设备列表
          </a-button>
        </div>
      </div>
    </div>

    <!-- 主体布局：左侧双镜像，右侧Tab -->
    <div class="debug-body">
      <!-- 左侧：双镜像 -->
      <div class="mirrors-pane">
        <ScreenMirror
          v-if="device1"
          ref="mirror1"
          :udid="device1"
          :online="online1"
          :scale="scale"
          :refresh-rate="refreshRate"
          :auto-refresh="autoRefresh"
          :highlight-bounds="activeDevice === 1 ? highlightBounds : null"
          :clickable="activeTab !== 'inspector'"
          frame-color="#2c3e50"
          @display-width="(w) => onDisplayWidth(1, w)"
        />
        <ScreenMirror
          v-if="device2"
          ref="mirror2"
          :udid="device2"
          :online="online2"
          :scale="scale"
          :refresh-rate="refreshRate"
          :auto-refresh="autoRefresh"
          :highlight-bounds="activeDevice === 2 ? highlightBounds : null"
          :clickable="activeTab !== 'inspector'"
          frame-color="#8b4513"
          @display-width="(w) => onDisplayWidth(2, w)"
        />
      </div>

      <!-- 右侧：Tab -->
      <div class="tabs-pane">
        <a-tabs v-model:activeKey="activeTab" type="card" class="control-tabs">
          <a-tab-pane key="control">
            <template #tab>
              <span class="tab-label">⚙️ 操作与设置</span>
            </template>
            <DeviceControlTab
              v-model:scale="scale"
              v-model:refresh-rate="refreshRate"
              v-model:auto-refresh="autoRefresh"
              v-model:active-device="activeDevice"
              :device1="device1"
              :device2="device2"
              :online1="online1"
              :online2="online2"
              :info1="info1"
              :info2="info2"
              @refresh-info="refreshInfo"
              @acted="onActed"
            />
          </a-tab-pane>

          <a-tab-pane key="inspector">
            <template #tab>
              <span class="tab-label">🔍 元素查看</span>
            </template>
            <ElementViewer
              v-model:active-device="activeDevice"
              :device1="device1"
              :device2="device2"
              :online1="online1"
              :online2="online2"
              @select="onNodeSelect"
            />
          </a-tab-pane>

          <a-tab-pane key="files">
            <template #tab>
              <span class="tab-label">📁 文件操作</span>
            </template>
            <FileManager
              v-model:active-device="activeDevice"
              :device1="device1"
              :device2="device2"
              :online1="online1"
              :online2="online2"
            />
          </a-tab-pane>
        </a-tabs>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import { message } from 'ant-design-vue';
import { ReloadOutlined } from '@ant-design/icons-vue';
import ScreenMirror from './components/ScreenMirror.vue';
import DeviceControlTab from './components/DeviceControlTab.vue';
import ElementViewer from './components/ElementViewer.vue';
import FileManager from './components/FileManager.vue';
import { useAndroidDemo } from './demo/store';
import { deviceByUdid } from './demo/devices';

const demo = useAndroidDemo();

const activeTab = ref('control');
const activeDevice = ref<1 | 2>(1); // 当前操作哪个设备

const devices = ref<any[]>([]);
const devicesLoading = ref(false);

const device1 = ref('');
const device2 = ref('');
const connecting1 = ref(false);
const connecting2 = ref(false);

const scale = ref(0.3);
const refreshRate = ref(200);
const autoRefresh = ref(false);
const highlightBounds = ref<number[] | null>(null);

const mirror1 = ref();
const mirror2 = ref();

// 镜像实际显示宽度（用于驱动下拉框宽度）
const displayWidth1 = ref(280);
const displayWidth2 = ref(280);

// 响应式读取设备运行时状态
const rt1 = computed<any>(() => (demo as any).devices[device1.value]);
const rt2 = computed<any>(() => (demo as any).devices[device2.value]);

const online1 = computed(() => rt1.value?.online || false);
const online2 = computed(() => rt2.value?.online || false);

const info1 = computed(() => {
  const dev = deviceByUdid(device1.value);
  const rt = rt1.value;
  if (!dev || !rt) return {};
  return { width: dev.width, height: dev.height, sdk: dev.sdk, current_app: rt.currentApp };
});
const info2 = computed(() => {
  const dev = deviceByUdid(device2.value);
  const rt = rt2.value;
  if (!dev || !rt) return {};
  return { width: dev.width, height: dev.height, sdk: dev.sdk, current_app: rt.currentApp };
});

onMounted(() => {
  loadDevices();
});

function loadDevices() {
  devicesLoading.value = true;
  window.setTimeout(() => {
    devices.value = demo.list();
    if (devices.value.length > 0 && !device1.value) {
      device1.value = devices.value[0].udid;
    }
    if (devices.value.length > 1 && !device2.value) {
      device2.value = devices.value[1].udid;
    }
    devicesLoading.value = false;
  }, 200);
}

function connect(slot: 1 | 2) {
  const udid = slot === 1 ? device1.value : device2.value;
  if (!udid) return;
  const connecting = slot === 1 ? connecting1 : connecting2;
  connecting.value = true;
  window.setTimeout(() => {
    demo.connect(udid);
    message.success(`设备 ${slot} 连接成功（演示）`);
    connecting.value = false;
  }, 500);
}

function disconnect(slot: 1 | 2) {
  const udid = slot === 1 ? device1.value : device2.value;
  if (!udid) return;
  demo.disconnect(udid);
  message.success(`设备 ${slot} 已断开`);
}

function refreshInfo(_slot?: 1 | 2) {
  // 演示：状态来自内存响应式 store，无需请求；保留接口以对齐组件契约
  demo.tick(device1.value);
  demo.tick(device2.value);
}

function onDeviceChange(_slot: 1 | 2) {
  // 切换设备后刷新状态（响应式，实际无需额外处理）
}

function onDisplayWidth(slot: 1 | 2, width: number) {
  if (slot === 1) displayWidth1.value = width;
  else displayWidth2.value = width;
}

function onNodeSelect(bounds: number[]) {
  highlightBounds.value = bounds.length === 4 ? bounds : null;
}

// Android SDK 版本映射
const sdkVersionMap: Record<number, string> = {
  21: 'Android 5.0', 22: 'Android 5.1', 23: 'Android 6.0', 24: 'Android 7.0',
  25: 'Android 7.1', 26: 'Android 8.0', 27: 'Android 8.1', 28: 'Android 9',
  29: 'Android 10', 30: 'Android 11', 31: 'Android 12', 32: 'Android 12L',
  33: 'Android 13', 34: 'Android 14', 35: 'Android 15',
};

function getAndroidVersion(sdk: number): string {
  const version = sdkVersionMap[sdk] || 'Android';
  return `${version} (SDK ${sdk})`;
}

function getActivityShortName(activity: string): string {
  if (!activity) return '';
  const parts = activity.split('.');
  return parts[parts.length - 1];
}

function onActed() {
  const ref = activeDevice.value === 1 ? mirror1.value : mirror2.value;
  if (ref?.refresh) window.setTimeout(() => ref.refresh(), 200);
}
</script>

<style scoped lang="less">
.android-debug {
  padding: 16px;
  background: var(--bg-card, #fff);
  border-radius: 8px;
}

.page-title {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;

  .title-icon {
    font-size: 24px;
  }

  .title-text {
    font-size: 20px;
    font-weight: 600;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
  }
}

.demo-tag {
  margin-left: 4px;
}

.demo-alert {
  margin-bottom: 16px;
}

.device-bar {
  margin-bottom: 16px;
  padding: 16px;
  background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.device-controls {
  display: flex;
  gap: 16px;
  align-items: flex-start;
}

.device-control-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
  flex: 0 0 auto;
  min-width: 240px;

  .control-label {
    display: flex;
    align-items: center;
    gap: 6px;
    font-weight: 600;
    color: #1890ff;
    font-size: 13px;
  }

  .frame-dot {
    width: 10px;
    height: 10px;
    border-radius: 50%;
    flex-shrink: 0;
    box-shadow: 0 0 0 2px rgba(255, 255, 255, 0.6);
  }

  .device-dropdown {
    width: 100%;

    :deep(.ant-select-selector) {
      border: 2px solid #1890ff !important;
      border-radius: 6px;
      padding: 4px 11px !important;
      min-height: 32px;
      display: flex;
      align-items: center;
    }

    :deep(.ant-select-selection-item) {
      display: flex !important;
      align-items: center;
      padding: 0 !important;
      line-height: 1.5;
    }

    :deep(.device-option) {
      display: flex;
      align-items: center;
      gap: 8px;
      width: 100%;
      overflow: hidden;

      .device-name {
        flex-shrink: 0;
      }

      .udid-text {
        margin-left: auto;
        padding-left: 8px;
        flex-shrink: 1;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }
    }
  }

  .control-buttons {
    display: flex;
    gap: 8px;
  }

  .device-status {
    display: flex;
    gap: 6px;
    flex-wrap: wrap;
  }
}

:global(.ant-select-dropdown) {
  .device-option {
    display: flex;
    align-items: center;
    gap: 8px;
    white-space: nowrap;
  }
}

.refresh-control {
  margin-left: auto;
  display: flex;
  align-items: flex-start;
  padding-top: 20px;
}

.device-option {
  display: flex;
  align-items: center;
  gap: 8px;
  overflow: hidden;

  .device-name {
    flex-shrink: 0;
    font-weight: 500;
  }

  .udid-text {
    margin-left: auto;
    font-size: 11px;
    color: #666;
    font-family: monospace;
    white-space: nowrap;
  }
}

.debug-body {
  display: flex;
  gap: 16px;
  min-height: 520px;
  overflow: hidden;
}

.mirrors-pane {
  display: flex;
  gap: 16px;
  flex: 0 0 auto;
  align-items: flex-start;
  overflow-y: auto;
  overflow-x: hidden;
  max-height: calc(100vh - 300px);
  padding-right: 8px;
}

.tabs-pane {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  height: calc(100vh - 300px);
  min-height: 520px;
  overflow: hidden;
}

.control-tabs {
  height: 100%;
  display: flex;
  flex-direction: column;

  :deep(.ant-tabs-nav) {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    padding: 8px 16px;
    border-radius: 8px 8px 0 0;
    margin-bottom: 0;
    flex-shrink: 0;

    .ant-tabs-tab {
      color: rgba(255, 255, 255, 0.7);
      border: none;
      background: transparent;

      &:hover {
        color: rgba(255, 255, 255, 0.9);
      }

      &.ant-tabs-tab-active {
        background: #fff;
        border-radius: 6px 6px 0 0;

        .tab-label {
          background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
          font-weight: 600;
        }
      }
    }
  }

  :deep(.ant-tabs-content-holder) {
    flex: 1;
    overflow: hidden;
  }

  :deep(.ant-tabs-content) {
    height: 100%;
    overflow: auto;
    background: #fff;
    border-radius: 0 0 8px 8px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
  }

  :deep(.ant-tabs-tabpane) {
    height: 100%;
    overflow: auto;
  }

  .tab-label {
    font-size: 14px;
    font-weight: 500;
  }
}
</style>
