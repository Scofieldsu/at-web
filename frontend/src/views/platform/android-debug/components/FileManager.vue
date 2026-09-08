<template>
  <div class="file-manager">
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
      <!-- 左侧：一键推送 + 上传 -->
      <a-col :span="12">
        <a-card title="🚀 一键推送测试资产" size="small" :bordered="false" class="file-card">
          <a-alert
            message="抖音 buyer_image / buyer_video 场景依赖设备相册里有测试资产"
            description="推送图片到 /sdcard/Pictures/，视频到 /sdcard/DCIM/Camera/，并触发媒体扫描让相册识别（演示：内存记录，不落地真实设备）。"
            type="info"
            show-icon
            style="margin-bottom: 16px"
          />

          <a-button
            type="primary"
            block
            size="large"
            :loading="pushingAssets"
            :disabled="!currentOnline"
            @click="handlePushAssets"
          >
            <template #icon><CloudUploadOutlined /></template>
            推送项目测试资产
          </a-button>

          <div v-if="pushResult" style="margin-top: 16px">
            <a-alert
              v-if="pushResult.pushed.length"
              :message="`成功推送 ${pushResult.pushed.length} 个文件`"
              type="success"
              show-icon
            >
              <template #description>
                <div class="file-list">
                  <a-tag v-for="name in pushResult.pushed" :key="name" color="green" style="margin: 4px">
                    {{ name }}
                  </a-tag>
                </div>
              </template>
            </a-alert>

            <a-alert
              v-if="pushResult.failed.length"
              :message="`${pushResult.failed.length} 个文件推送失败`"
              type="error"
              show-icon
              style="margin-top: 12px"
            >
              <template #description>
                <div v-for="item in pushResult.failed" :key="item.name" style="margin: 4px 0">
                  {{ item.name }}: {{ item.error }}
                </div>
              </template>
            </a-alert>
          </div>
        </a-card>

        <a-card title="📤 上传文件到设备" size="small" :bordered="false" class="file-card" style="margin-top: 16px">
          <a-upload-dragger
            :file-list="fileList"
            :before-upload="handleBeforeUpload"
            :disabled="!currentOnline"
            multiple
            @remove="handleRemove"
          >
            <p class="ant-upload-drag-icon">
              <InboxOutlined style="color: #1890ff" />
            </p>
            <p class="ant-upload-text">点击或拖拽文件到此区域</p>
            <p class="ant-upload-hint">
              图片自动推送到 /sdcard/Pictures/，视频推送到 /sdcard/DCIM/Camera/
            </p>
          </a-upload-dragger>

          <a-form layout="vertical" style="margin-top: 16px">
            <a-form-item label="自定义远程目录（可选）">
              <a-input
                v-model:value="customRemoteDir"
                placeholder="留空则按扩展名自动选择"
                allow-clear
              />
            </a-form-item>
          </a-form>

          <a-button
            type="primary"
            block
            size="large"
            :loading="uploading"
            :disabled="!currentOnline || !fileList.length"
            @click="handleUpload"
          >
            <template #icon><UploadOutlined /></template>
            推送 {{ fileList.length }} 个文件
          </a-button>
        </a-card>
      </a-col>

      <!-- 右侧：设备相册内容 -->
      <a-col :span="12">
        <a-card title="📱 设备相册内容" size="small" :bordered="false" class="file-card">
          <template #extra>
            <a-button size="small" :loading="listingFiles" :disabled="!currentOnline" @click="listAlbumFiles">
              <template #icon><ReloadOutlined /></template>
              刷新
            </a-button>
          </template>

          <a-tabs v-model:activeKey="albumTab" size="small">
            <a-tab-pane key="pictures" tab="📷 图片 (/sdcard/Pictures/)">
              <pre class="file-output">{{ picturesOutput || '点击刷新查看' }}</pre>
            </a-tab-pane>
            <a-tab-pane key="videos" tab="🎬 视频 (/sdcard/DCIM/Camera/)">
              <pre class="file-output">{{ videosOutput || '点击刷新查看' }}</pre>
            </a-tab-pane>
          </a-tabs>
        </a-card>
      </a-col>
    </a-row>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue';
import { message } from 'ant-design-vue';
import {
  CloudUploadOutlined,
  InboxOutlined,
  UploadOutlined,
  ReloadOutlined,
} from '@ant-design/icons-vue';
import { useAndroidDemo } from '../demo/store';

const props = defineProps<{
  device1: string;
  device2: string;
  online1?: boolean;
  online2?: boolean;
  activeDevice: 1 | 2;
}>();

defineEmits<{
  'update:activeDevice': [value: 1 | 2];
}>();

const demo = useAndroidDemo();

const pushingAssets = ref(false);
const pushResult = ref<{ pushed: string[]; failed: any[] } | null>(null);
const fileList = ref<any[]>([]);
const uploading = ref(false);
const customRemoteDir = ref('');
const albumTab = ref('pictures');
const picturesOutput = ref('');
const videosOutput = ref('');
const listingFiles = ref(false);

const currentDevice = computed(() => (props.activeDevice === 1 ? props.device1 : props.device2));
const currentOnline = computed(() => (props.activeDevice === 1 ? props.online1 : props.online2));

function handlePushAssets() {
  if (!currentOnline.value) {
    message.warning('请先连接设备');
    return;
  }
  pushingAssets.value = true;
  pushResult.value = null;
  window.setTimeout(() => {
    const res = demo.pushAssets(currentDevice.value);
    pushResult.value = { pushed: res.pushed, failed: res.failed };
    if (res.pushed.length) message.success(`已推送 ${res.pushed.length} 个文件（演示）`);
    else message.warning('没有找到可推送的资产文件');
    pushingAssets.value = false;
  }, 500);
}

function handleBeforeUpload(file: File) {
  fileList.value = [...fileList.value, file];
  return false; // 阻止自动上传
}

function handleRemove(file: any) {
  fileList.value = fileList.value.filter((f) => f.uid !== file.uid && f !== file);
}

function handleUpload() {
  if (!currentOnline.value || !fileList.value.length) return;
  uploading.value = true;
  let ok = 0;
  const errors: string[] = [];

  fileList.value.forEach((file) => {
    try {
      const ext = (file.name.includes('.') ? file.name.split('.').pop() : '').toLowerCase();
      demo.pushFile(currentDevice.value, file.name, ext, customRemoteDir.value || undefined);
      ok += 1;
    } catch (error: any) {
      errors.push(`${file.name}: ${error.message}`);
    }
  });

  uploading.value = false;
  if (ok) {
    message.success(`已推送 ${ok} 个文件（演示）`);
    fileList.value = [];
  }
  if (errors.length) message.error(`${errors.length} 个失败: ${errors[0]}`);
}

function listAlbumFiles() {
  if (!currentOnline.value) {
    message.warning('请先连接设备');
    return;
  }
  listingFiles.value = true;
  window.setTimeout(() => {
    const res = demo.listAlbum(currentDevice.value);
    picturesOutput.value = res.pictures;
    videosOutput.value = res.videos;
    listingFiles.value = false;
  }, 300);
}
</script>

<style scoped lang="less">
.file-manager {
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

.file-card {
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

.file-list {
  margin-top: 8px;
  max-height: 160px;
  overflow: auto;
}

.file-output {
  max-height: 420px;
  overflow: auto;
  padding: 12px;
  background: #f5f5f5;
  border: 1px solid #d9d9d9;
  border-radius: 6px;
  font-size: 12px;
  font-family: 'Consolas', 'Monaco', monospace;
  margin: 0;
  line-height: 1.6;
}
</style>
