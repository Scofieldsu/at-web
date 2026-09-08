<template>
  <div class="control-tab">
    <!-- 设备选择器 -->
    <div class="device-switcher">
      <span class="switcher-label">当前操作设备：</span>
      <a-radio-group
        :value="activeDevice"
        button-style="solid"
        @change="(e) => $emit('update:activeDevice', e.target.value)"
      >
        <a-radio-button :value="1" :disabled="!online1">
          设备 1 {{ online1 ? '✓' : '✗' }}
        </a-radio-button>
        <a-radio-button :value="2" :disabled="!online2">
          设备 2 {{ online2 ? '✓' : '✗' }}
        </a-radio-button>
      </a-radio-group>
    </div>

    <a-row :gutter="[16, 16]">
      <!-- 左列：镜像设置 + 抖音快捷 -->
      <a-col :span="12">
        <a-card title="🎨 镜像设置" size="small" :bordered="false" class="setting-card">
          <a-form layout="vertical" size="small">
            <a-form-item label="缩放比例" style="margin-bottom: 16px">
              <a-slider
                :value="scale"
                :min="0.1"
                :max="1.0"
                :step="0.1"
                :marks="{ 0.3: '30%', 0.5: '50%', 0.8: '80%', 1.0: '100%' }"
                @change="(v) => $emit('update:scale', v)"
              />
            </a-form-item>

            <a-form-item label="刷新率" style="margin-bottom: 16px">
              <a-radio-group
                :value="refreshRate"
                button-style="solid"
                size="small"
                @change="(e) => $emit('update:refreshRate', e.target.value)"
              >
                <a-radio-button :value="500">2fps</a-radio-button>
                <a-radio-button :value="200">5fps</a-radio-button>
                <a-radio-button :value="100">10fps</a-radio-button>
              </a-radio-group>
            </a-form-item>

            <a-form-item style="margin-bottom: 0">
              <a-checkbox
                :checked="autoRefresh"
                @change="(e) => $emit('update:autoRefresh', e.target.checked)"
              >
                🔄 自动刷新
              </a-checkbox>
            </a-form-item>
          </a-form>
        </a-card>

        <a-card title="🚀 抖音快捷操作" size="small" :bordered="false" class="setting-card" style="margin-top: 16px">
          <a-space direction="vertical" style="width: 100%" size="middle">
            <a-button type="primary" :loading="launching" :disabled="!currentOnline" @click="launchApp" style="width: 100%; max-width: 280px">
              启动抖音极速版
            </a-button>

            <a-divider style="margin: 8px 0">混淆 ID 查找器</a-divider>

            <a-select
              v-model:value="findKind"
              size="small"
              placeholder="元素类型"
              style="width: 100%; max-width: 280px"
            >
              <a-select-option value="all">全部</a-select-option>
              <a-select-option value="album_tab">相册 Tab</a-select-option>
              <a-select-option value="album_circle">圆圈选择器</a-select-option>
              <a-select-option value="album_send">发送按钮</a-select-option>
            </a-select>

            <a-button
              type="primary"
              :loading="finding"
              :disabled="!currentOnline"
              @click="handleFind"
              style="width: 100%; max-width: 280px"
            >
              <template #icon><SearchOutlined /></template>
              扫描当前页面
            </a-button>

            <div v-if="results" class="find-results">
              <a-alert
                v-if="results.error"
                type="error"
                show-icon
                :message="results.error"
                style="margin-bottom: 12px"
              />
              <a-collapse v-else size="small" accordion>
                <a-collapse-panel
                  v-for="(list, kind) in results"
                  :key="kind"
                  :header="getKindLabel(kind)"
                >
                  <a-list v-if="list.length" size="small" :data-source="list">
                    <template #renderItem="{ item }">
                      <a-list-item>
                        <a-list-item-meta>
                          <template #title>
                            <a-typography-text
                              :type="item.confidence === 'high' ? 'success' : 'warning'"
                              copyable
                              code
                            >
                              {{ item.id || '(未找到)' }}
                            </a-typography-text>
                          </template>
                          <template #description>
                            <a-tag :color="getConfidenceColor(item.confidence)" size="small">
                              {{ item.confidence }}
                            </a-tag>
                            {{ item.reason }}
                          </template>
                        </a-list-item-meta>
                      </a-list-item>
                    </template>
                  </a-list>
                  <a-empty v-else description="未找到" :image="Empty.PRESENTED_IMAGE_SIMPLE" />
                </a-collapse-panel>
              </a-collapse>
            </div>
          </a-space>
        </a-card>
      </a-col>

      <!-- 右列：设备操作 -->
      <a-col :span="12">
        <a-card title="⌨️ 物理按键" size="small" :bordered="false" class="control-card">
          <a-space wrap :size="[12, 12]">
            <a-button @click="press('home')" :disabled="!currentOnline" class="key-home">
              <template #icon><HomeOutlined /></template>
              Home
            </a-button>
            <a-button @click="press('back')" :disabled="!currentOnline" class="key-back">
              <template #icon><RollbackOutlined /></template>
              Back
            </a-button>
            <a-button @click="press('recent')" :disabled="!currentOnline" class="key-recent">
              <template #icon><AppstoreOutlined /></template>
              Recent
            </a-button>
            <a-button @click="press('volume_up')" :disabled="!currentOnline" class="key-volume-up">
              <template #icon><SoundOutlined /></template>
              音量+
            </a-button>
            <a-button @click="press('volume_down')" :disabled="!currentOnline" class="key-volume-down">
              <template #icon><SoundOutlined /></template>
              音量-
            </a-button>
            <a-button @click="press('power')" :disabled="!currentOnline" class="key-power">
              <template #icon><PoweroffOutlined /></template>
              电源
            </a-button>
          </a-space>
        </a-card>

        <a-card title="👆 滑动手势" size="small" :bordered="false" class="control-card" style="margin-top: 16px">
          <a-row :gutter="[12, 12]">
            <a-col :span="12">
              <a-button block @click="swipe('up')" :disabled="!currentOnline" size="large" class="swipe-up">
                <template #icon><ArrowUpOutlined /></template>
                上滑
              </a-button>
            </a-col>
            <a-col :span="12">
              <a-button block @click="swipe('down')" :disabled="!currentOnline" size="large" class="swipe-down">
                <template #icon><ArrowDownOutlined /></template>
                下滑
              </a-button>
            </a-col>
            <a-col :span="12">
              <a-button block @click="swipe('left')" :disabled="!currentOnline" size="large" class="swipe-left">
                <template #icon><ArrowLeftOutlined /></template>
                左滑
              </a-button>
            </a-col>
            <a-col :span="12">
              <a-button block @click="swipe('right')" :disabled="!currentOnline" size="large" class="swipe-right">
                <template #icon><ArrowRightOutlined /></template>
                右滑
              </a-button>
            </a-col>
          </a-row>
        </a-card>

        <a-card title="✏️ 文本输入" size="small" :bordered="false" class="control-card" style="margin-top: 16px">
          <a-input-search
            v-model:value="inputText"
            placeholder="输入文本"
            enter-button="发送"
            :disabled="!currentOnline"
            @search="sendText"
          />
        </a-card>

        <a-card title="📦 App 管理" size="small" :bordered="false" class="control-card" style="margin-top: 16px">
          <a-input
            v-model:value="packageName"
            placeholder="com.ss.android.ugc.aweme.lite"
            style="margin-bottom: 12px"
            :disabled="!currentOnline"
          />
          <a-space :size="12">
            <a-button type="primary" :disabled="!packageName || !currentOnline" @click="startApp">
              <template #icon><PlayCircleOutlined /></template>
              启动
            </a-button>
            <a-button danger :disabled="!packageName || !currentOnline" @click="stopApp">
              <template #icon><StopOutlined /></template>
              停止
            </a-button>
          </a-space>
        </a-card>
      </a-col>
    </a-row>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue';
import { message, Empty } from 'ant-design-vue';
import {
  HomeOutlined,
  RollbackOutlined,
  AppstoreOutlined,
  SoundOutlined,
  PoweroffOutlined,
  ArrowUpOutlined,
  ArrowDownOutlined,
  ArrowLeftOutlined,
  ArrowRightOutlined,
  SearchOutlined,
  PlayCircleOutlined,
  StopOutlined,
} from '@ant-design/icons-vue';
import { useAndroidDemo } from '../demo/store';

const props = defineProps<{
  device1: string;
  device2: string;
  online1?: boolean;
  online2?: boolean;
  info1?: any;
  info2?: any;
  scale: number;
  refreshRate: number;
  autoRefresh: boolean;
  activeDevice: 1 | 2;
}>();

const emit = defineEmits<{
  'update:scale': [value: number];
  'update:refreshRate': [value: number];
  'update:autoRefresh': [value: boolean];
  'update:activeDevice': [value: 1 | 2];
  refreshInfo: [slot?: 1 | 2];
  acted: [];
}>();

const demo = useAndroidDemo();

const inputText = ref('');
const packageName = ref('com.ss.android.ugc.aweme.lite');
const findKind = ref('all');
const finding = ref(false);
const launching = ref(false);
const results = ref<any>(null);

const currentDevice = computed(() => (props.activeDevice === 1 ? props.device1 : props.device2));
const currentOnline = computed(() => (props.activeDevice === 1 ? props.online1 : props.online2));
const currentInfo = computed(() => (props.activeDevice === 1 ? props.info1 : props.info2));

function act() {
  demo.tick(currentDevice.value);
  emit('acted');
}

function press(key: string) {
  if (!currentOnline.value) return;
  demo.press(currentDevice.value, key);
  message.success(`已按键: ${key}（演示）`);
  act();
}

function swipe(dir: string) {
  if (!currentOnline.value) return;
  const w = currentInfo.value?.width || 1080;
  const h = currentInfo.value?.height || 2400;
  let x1 = w / 2, y1 = h / 2, x2 = w / 2, y2 = h / 2;
  switch (dir) {
    case 'up': y1 = h * 0.8; y2 = h * 0.2; break;
    case 'down': y1 = h * 0.2; y2 = h * 0.8; break;
    case 'left': x1 = w * 0.8; x2 = w * 0.2; break;
    case 'right': x1 = w * 0.2; x2 = w * 0.8; break;
  }
  demo.swipe(currentDevice.value, x1, y1, x2, y2);
  message.success(`已滑动: ${dir}（演示）`);
  act();
}

function sendText() {
  if (!currentOnline.value || !inputText.value) return;
  demo.input(currentDevice.value, inputText.value);
  message.success('已输入（演示，当前页无输入框）');
  inputText.value = '';
  act();
}

function startApp() {
  if (!currentOnline.value || !packageName.value) return;
  demo.appStart(currentDevice.value, packageName.value);
  message.success(`已启动: ${packageName.value}（演示）`);
  window.setTimeout(() => emit('refreshInfo', props.activeDevice), 500);
  act();
}

function stopApp() {
  if (!currentOnline.value || !packageName.value) return;
  demo.appStop(currentDevice.value, packageName.value);
  message.success(`已停止: ${packageName.value}（演示）`);
  window.setTimeout(() => emit('refreshInfo', props.activeDevice), 500);
  act();
}

function launchApp() {
  packageName.value = 'com.ss.android.ugc.aweme.lite';
  launching.value = true;
  window.setTimeout(() => {
    startApp();
    launching.value = false;
  }, 400);
}

function handleFind() {
  if (!currentOnline.value) return;
  finding.value = true;
  results.value = null;
  window.setTimeout(() => {
    results.value = demo.findSelectors(currentDevice.value, findKind.value);
    finding.value = false;
    message.success('扫描完成（演示）');
  }, 500);
}

function getKindLabel(kind: any): string {
  const map: Record<string, string> = {
    album_tab: '相册 Tab',
    album_circle: '圆圈选择器',
    album_send: '发送按钮',
  };
  return map[kind] || kind;
}

function getConfidenceColor(c: string): string {
  const map: Record<string, string> = {
    high: 'green',
    medium: 'orange',
    low: 'default',
    none: 'red',
  };
  return map[c] || 'default';
}
</script>

<style scoped lang="less">
.control-tab {
  padding: 20px;
}

.device-switcher {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 20px;
  padding: 12px 16px;
  background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%);
  border-radius: 8px;
  border-left: 4px solid #2196f3;

  .switcher-label {
    font-weight: 500;
    color: #1976d2;
  }
}

.setting-card,
.control-card {
  border: 1px solid #e8e8e8;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);

  :deep(.ant-card-head) {
    background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
    border-bottom: 2px solid #1890ff;
    min-height: 42px;
    padding: 0 16px;

    .ant-card-head-title {
      font-weight: 600;
      font-size: 14px;
      padding: 10px 0;
    }
  }

  :deep(.ant-card-body) {
    padding: 16px;
  }
}

.find-results {
  max-height: 320px;
  overflow: auto;
  border: 1px solid #f0f0f0;
  border-radius: 6px;
  padding: 8px;
}

/* 物理按键颜色 - 柔和浅色系 */
.key-home {
  background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%);
  color: #1976d2;
  border: 1px solid #90caf9;

  &:hover:not(:disabled) {
    background: linear-gradient(135deg, #bbdefb 0%, #e3f2fd 100%);
    color: #1565c0;
    border-color: #64b5f6;
  }
}

.key-back {
  background: linear-gradient(135deg, #f3e5f5 0%, #e1bee7 100%);
  color: #7b1fa2;
  border: 1px solid #ce93d8;

  &:hover:not(:disabled) {
    background: linear-gradient(135deg, #e1bee7 0%, #f3e5f5 100%);
    color: #6a1b9a;
    border-color: #ba68c8;
  }
}

.key-recent {
  background: linear-gradient(135deg, #e0f2f1 0%, #b2dfdb 100%);
  color: #00796b;
  border: 1px solid #80cbc4;

  &:hover:not(:disabled) {
    background: linear-gradient(135deg, #b2dfdb 0%, #e0f2f1 100%);
    color: #00695c;
    border-color: #4db6ac;
  }
}

.key-volume-up {
  background: linear-gradient(135deg, #e8f5e9 0%, #c8e6c9 100%);
  color: #388e3c;
  border: 1px solid #a5d6a7;

  &:hover:not(:disabled) {
    background: linear-gradient(135deg, #c8e6c9 0%, #e8f5e9 100%);
    color: #2e7d32;
    border-color: #81c784;
  }
}

.key-volume-down {
  background: linear-gradient(135deg, #fff3e0 0%, #ffe0b2 100%);
  color: #f57c00;
  border: 1px solid #ffcc80;

  &:hover:not(:disabled) {
    background: linear-gradient(135deg, #ffe0b2 0%, #fff3e0 100%);
    color: #ef6c00;
    border-color: #ffb74d;
  }
}

.key-power {
  background: linear-gradient(135deg, #fce4ec 0%, #f8bbd0 100%);
  color: #c2185b;
  border: 1px solid #f48fb1;

  &:hover:not(:disabled) {
    background: linear-gradient(135deg, #f8bbd0 0%, #fce4ec 100%);
    color: #ad1457;
    border-color: #f06292;
  }
}

/* 滑动手势颜色 - 与物理按键同一套浅色规范 */
.swipe-up {
  background: linear-gradient(135deg, #e8eaf6 0%, #c5cae9 100%);
  color: #3949ab;
  border: 1px solid #9fa8da;
  font-weight: 500;

  &:hover:not(:disabled) {
    background: linear-gradient(135deg, #c5cae9 0%, #e8eaf6 100%);
    color: #303f9f;
    border-color: #7986cb;
  }
}

.swipe-down {
  background: linear-gradient(135deg, #e1f5fe 0%, #b3e5fc 100%);
  color: #0277bd;
  border: 1px solid #81d4fa;
  font-weight: 500;

  &:hover:not(:disabled) {
    background: linear-gradient(135deg, #b3e5fc 0%, #e1f5fe 100%);
    color: #01579b;
    border-color: #4fc3f7;
  }
}

.swipe-left {
  background: linear-gradient(135deg, #f1f8e9 0%, #dcedc8 100%);
  color: #558b2f;
  border: 1px solid #c5e1a5;
  font-weight: 500;

  &:hover:not(:disabled) {
    background: linear-gradient(135deg, #dcedc8 0%, #f1f8e9 100%);
    color: #33691e;
    border-color: #aed581;
  }
}

.swipe-right {
  background: linear-gradient(135deg, #fff8e1 0%, #ffecb3 100%);
  color: #ff8f00;
  border: 1px solid #ffe082;
  font-weight: 500;

  &:hover:not(:disabled) {
    background: linear-gradient(135deg, #ffecb3 0%, #fff8e1 100%);
    color: #ef6c00;
    border-color: #ffd54f;
  }
}
</style>
