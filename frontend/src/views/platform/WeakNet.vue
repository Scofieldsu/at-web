<template>
  <div class="weaknet-container">
    <!-- 顶部行：左 弱网状态（宽对齐下方 3G 卡片右缘）/ 右 使用说明 -->
    <a-row :gutter="[16, 16]">
      <a-col :xs="24" :sm="12" :md="16" :lg="12">
    <!-- 顶部状态栏 -->
    <a-card :class="['status-card', 'theme-card', { running: isRunning }]">
      <template #title>
        <span class="sec-title" :class="isRunning ? 'tint-orange' : 'tint-gray'">
          <WifiOutlined />弱网状态
        </span>
      </template>

      <div class="status-header">
        <a-badge :status="isRunning ? 'processing' : 'default'" :text="isRunning ? '运行中' : '未启动'" />
        <a-button v-if="isRunning" danger @click="handleStop" :loading="stopping" style="margin-left: auto">
          停止弱网
        </a-button>
      </div>

      <div v-if="isRunning && currentConfig" class="status-detail">
        <a-descriptions :column="{ xs: 1, sm: 2, md: 3 }" size="small" bordered>
          <a-descriptions-item label="进程 PID">{{ statusData.pid }}</a-descriptions-item>
          <a-descriptions-item label="运行时长">{{ formatDuration(statusData.elapsed_seconds) }}</a-descriptions-item>
          <a-descriptions-item label="预设">{{ currentConfig.preset_name || '自定义' }}</a-descriptions-item>
          <a-descriptions-item label="延迟">
            <a-tag :color="currentConfig.lag_enabled ? 'orange' : 'default'">
              {{ currentConfig.lag_enabled ? `${currentConfig.lag_time}ms` : '关闭' }}
            </a-tag>
          </a-descriptions-item>
          <a-descriptions-item label="丢包">
            <a-tag :color="currentConfig.drop_enabled ? 'red' : 'default'">
              {{ currentConfig.drop_enabled ? `${(currentConfig.drop_chance * 100).toFixed(0)}%` : '关闭' }}
            </a-tag>
          </a-descriptions-item>
          <a-descriptions-item label="节流">
            <a-tag :color="currentConfig.throttle_enabled ? 'blue' : 'default'">
              {{ currentConfig.throttle_enabled ? `${currentConfig.throttle_timeframe}ms` : '关闭' }}
            </a-tag>
          </a-descriptions-item>
          <a-descriptions-item label="配置摘要" :span="3">
            <code>{{ statusData.summary || '无弱网注入' }}</code>
          </a-descriptions-item>
        </a-descriptions>
      </div>

      <div v-else-if="isRunning && !currentConfig" class="status-detail">
        <a-alert type="warning" show-icon>
          <template #message>外部启动</template>
          <template #description>
            检测到系统中运行的 Clumsy 实例（PID={{ statusData.pid }}），但该实例不是通过本管理控制台启动，无法查看配置详情。
            可点击「停止弱网」结束该进程。
          </template>
        </a-alert>
      </div>
    </a-card>
      </a-col>

      <a-col :xs="24" :sm="12" :md="8" :lg="12">
      <!-- 使用说明 -->
      <a-card class="theme-card">
        <template #title>
          <span class="sec-title tint-purple"><QuestionCircleOutlined />使用说明</span>
        </template>

        <a-alert type="info" show-icon style="margin-bottom: 16px">
          <template #message>重要提示</template>
          <template #description>
            <!-- 2×2 紧凑网格：文案精简，高度比原 4 行列表减半 -->
            <div class="tips-grid">
              <div class="tips-item">弱网工具需<strong>管理员权限</strong>运行</div>
              <div class="tips-item">仅影响匹配过滤规则的流量</div>
              <div class="tips-item">测试完成后<strong>务必停止</strong>弱网</div>
              <div class="tips-item">演示环境不实际影响流量</div>
            </div>
          </template>
        </a-alert>

        <a-collapse v-model:activeKey="activeKeys">
          <a-collapse-panel header="安装状态检查" key="4">
            <div v-if="installStatus">
              <a-descriptions :column="1" bordered size="small">
                <a-descriptions-item label="安装状态">
                  <a-tag :color="installStatus.installed ? 'success' : 'error'">
                    {{ installStatus.installed ? '已安装' : '未安装' }}
                  </a-tag>
                </a-descriptions-item>
                <a-descriptions-item label="可执行文件">
                  <code>{{ installStatus.path }}</code>
                </a-descriptions-item>
                <a-descriptions-item label="版本">{{ installStatus.version || '-' }}</a-descriptions-item>
                <a-descriptions-item label="消息">{{ installStatus.message }}</a-descriptions-item>
              </a-descriptions>
              <a-button
                v-if="!installStatus.installed"
                type="link"
                style="margin-top: 8px"
                @click="showInstallGuide"
              >
                查看安装指南
              </a-button>
            </div>
            <a-button type="primary" size="small" @click="checkInstallation">刷新状态</a-button>
          </a-collapse-panel>

          <a-collapse-panel header="预设配置说明" key="2">
            <a-descriptions :column="1" bordered size="small">
              <a-descriptions-item label="基线">无弱网注入，用于对比测试基线性能</a-descriptions-item>
              <a-descriptions-item label="3G 网络">
                延迟 200ms，丢包 5% - 模拟 3G 网络环境，适合轻度弱网测试
              </a-descriptions-item>
              <a-descriptions-item label="2G 网络">
                <strong>延迟 500ms，丢包 10% - 推荐用于日常弱网测试</strong>
              </a-descriptions-item>
              <a-descriptions-item label="极差网络">
                延迟 1000ms，丢包 20% - 极端弱网场景，测试系统降级能力
              </a-descriptions-item>
              <a-descriptions-item label="断网模拟">
                100% 丢包 - 模拟完全断网，测试断网后的恢复逻辑
              </a-descriptions-item>
            </a-descriptions>
          </a-collapse-panel>

          <a-collapse-panel header="过滤规则语法" key="3">
            <p>使用 WinDivert 过滤语法，常用规则示例：</p>
            <pre
              style="background: #f5f5f5; padding: 12px; border-radius: 4px; font-size: 12px"
            ><code># 只影响 Mock 服务流量（推荐，演示端口 8765）
tcp.DstPort == 8765 or tcp.SrcPort == 8765

# 只影响出站流量
outbound and tcp.DstPort == 8765

# 只影响某个网段
(ip.DstAddr >= 10.0.1.0 and ip.DstAddr <= 10.0.1.255)</code></pre>
          </a-collapse-panel>

        </a-collapse>
      </a-card>
      </a-col>
    </a-row>

    <!-- 快捷预设卡片 -->
    <a-card class="theme-card" style="margin-top: 16px">
      <template #title>
        <span class="sec-title tint-blue"><ThunderboltOutlined />快捷预设</span>
      </template>

      <a-row :gutter="[16, 16]">
        <a-col v-for="preset in displayPresets" :key="preset.key" :xs="24" :sm="12" :md="8" :lg="6">
          <a-card
            :class="['preset-card', { recommended: isRecommended(preset.key) }]"
            hoverable
            @click="handlePresetSelect(preset.key)"
          >
            <template #title>
              <div class="card-title">
                {{ preset.name }}
                <a-tag v-if="isRecommended(preset.key)" color="success" style="margin-left: 8px">推荐</a-tag>
              </div>
            </template>

            <div class="card-content">
              <p class="description">{{ preset.description }}</p>
              <a-divider style="margin: 12px 0" />
              <div class="params">
                <div class="param-item">
                  <ClockCircleOutlined />
                  <span>{{ getParamText(preset.config, 'lag') }}</span>
                </div>
                <div class="param-item">
                  <DisconnectOutlined />
                  <span>{{ getParamText(preset.config, 'drop') }}</span>
                </div>
                <div class="param-item">
                  <DashboardOutlined />
                  <span>{{ getParamText(preset.config, 'throttle') }}</span>
                </div>
              </div>
            </div>
          </a-card>
        </a-col>
      </a-row>
    </a-card>

    <!-- 自定义配置表单 -->
    <a-card class="theme-card" style="margin-top: 16px">
      <template #title>
        <span class="sec-title tint-green"><SettingOutlined />自定义配置</span>
      </template>

      <a-form :model="customConfig" layout="vertical">
        <a-row :gutter="16">
          <a-col :span="24">
            <a-form-item label="过滤规则（WinDivert 语法）">
              <a-input
                v-model:value="customConfig.filter_rule"
                placeholder="tcp.DstPort == 8765 or tcp.SrcPort == 8765"
              />
              <div style="font-size: 12px; color: #666; margin-top: 4px">
                仅影响匹配规则的流量，其他流量不受影响
              </div>
            </a-form-item>
          </a-col>
        </a-row>

        <a-row :gutter="16">
          <a-col :xs="24" :sm="12" :md="8">
            <a-form-item>
              <template #label>
                <a-checkbox v-model:checked="customConfig.lag_enabled">延迟（Lag）</a-checkbox>
              </template>
              <a-input-number
                v-model:value="customConfig.lag_time"
                :min="0"
                :max="10000"
                :disabled="!customConfig.lag_enabled"
                placeholder="毫秒"
                style="width: 100%"
              />
            </a-form-item>
          </a-col>

          <a-col :xs="24" :sm="12" :md="8">
            <a-form-item>
              <template #label>
                <a-checkbox v-model:checked="customConfig.drop_enabled">丢包（Drop）</a-checkbox>
              </template>
              <a-input-number
                v-model:value="dropPercent"
                :min="0"
                :max="100"
                :disabled="!customConfig.drop_enabled"
                placeholder="百分比"
                style="width: 100%"
              />
            </a-form-item>
          </a-col>

          <a-col :xs="24" :sm="12" :md="8">
            <a-form-item>
              <template #label>
                <a-checkbox v-model:checked="customConfig.throttle_enabled">节流（Throttle）</a-checkbox>
              </template>
              <a-input-number
                v-model:value="customConfig.throttle_timeframe"
                :min="0"
                :max="5000"
                :disabled="!customConfig.throttle_enabled"
                placeholder="时间窗（ms）"
                style="width: 100%"
              />
            </a-form-item>
          </a-col>
        </a-row>

        <a-form-item>
          <a-button type="primary" :loading="starting" @click="handleCustomStart">
            <PlayCircleOutlined />启动自定义弱网
          </a-button>
        </a-form-item>
      </a-form>
    </a-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue';
import { message, Modal } from 'ant-design-vue';
import {
  WifiOutlined,
  ThunderboltOutlined,
  SettingOutlined,
  QuestionCircleOutlined,
  ClockCircleOutlined,
  DisconnectOutlined,
  DashboardOutlined,
  PlayCircleOutlined,
} from '@ant-design/icons-vue';
import { startWeaknet, stopWeaknet, getStatus, getPresets, checkInstallation as apiCheckInstallation } from '@/api/platform/clumsy';

const isRunning = ref(false);
const statusData = ref<any>({});
const currentConfig = ref<any>(null);
const presets = ref<any[]>([]);
const starting = ref(false);
const stopping = ref(false);
const installStatus = ref<any>(null);
// 使用说明折叠面板：默认展开「安装状态检查」
const activeKeys = ref<string[]>(['4']);

const customConfig = ref({
  filter_rule: 'tcp.DstPort == 8765 or tcp.SrcPort == 8765',
  lag_enabled: false,
  lag_time: 500,
  drop_enabled: false,
  drop_chance: 0.1,
  throttle_enabled: false,
  throttle_timeframe: 200,
  throttle_chance: 0.9,
});

const dropPercent = computed({
  get: () => (customConfig.value.drop_chance * 100).toFixed(0),
  set: (val) => {
    customConfig.value.drop_chance = parseFloat(val) / 100;
  },
});

let statusTimer: number | null = null;

// 推荐的预设
const recommendedPresets = ['2g', '3g'];

// 优先显示的预设（排序）
const displayPresets = computed(() => {
  const order = ['baseline', '3g', '2g', 'extreme', 'disconnect', 'chaos'];
  return presets.value.sort((a, b) => {
    const aIndex = order.indexOf(a.key);
    const bIndex = order.indexOf(b.key);
    return (aIndex === -1 ? 999 : aIndex) - (bIndex === -1 ? 999 : bIndex);
  });
});

function isRecommended(key: string) {
  return recommendedPresets.includes(key);
}

function getParamText(config: any, type: 'lag' | 'drop' | 'throttle'): string {
  if (type === 'lag') {
    return config.lag_enabled ? `延迟 ${config.lag_time}ms` : '延迟关闭';
  }
  if (type === 'drop') {
    return config.drop_enabled ? `丢包 ${(config.drop_chance * 100).toFixed(0)}%` : '丢包关闭';
  }
  if (type === 'throttle') {
    return config.throttle_enabled ? `节流 ${config.throttle_timeframe}ms` : '节流关闭';
  }
  return '-';
}

function formatDuration(seconds: number): string {
  if (!seconds) return '-';
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = seconds % 60;
  if (h > 0) return `${h}h ${m}m ${s}s`;
  if (m > 0) return `${m}m ${s}s`;
  return `${s}s`;
}

// 查询状态
async function fetchStatus() {
  try {
    const res = await getStatus();
    isRunning.value = res.running;
    statusData.value = res;
    currentConfig.value = res.config;
  } catch (error) {
    console.error('获取状态失败:', error);
  }
}

// 加载预设配置
async function loadPresets() {
  try {
    const res = await getPresets();
    presets.value = Object.entries(res).map(([key, value]: [string, any]) => ({
      key,
      ...value,
    }));
  } catch (error) {
    message.error('加载预设配置失败');
  }
}

// 启动预设配置
async function handlePresetSelect(presetKey: string) {
  if (isRunning.value) {
    message.warning('请先停止当前弱网');
    return;
  }

  starting.value = true;
  try {
    const res = await startWeaknet({ preset: presetKey });
    if (res.success) {
      message.success(res.message);
      await fetchStatus();
    } else {
      message.error(res.message);
    }
  } catch (error: any) {
    const errMsg = error.response?.data?.message || error.message || '启动失败';
    message.error({ content: `启动失败: ${errMsg}`, duration: 8 });
  } finally {
    starting.value = false;
  }
}

// 启动自定义配置
async function handleCustomStart() {
  if (isRunning.value) {
    message.warning('请先停止当前弱网');
    return;
  }

  starting.value = true;
  try {
    const res = await startWeaknet({ config: customConfig.value });
    if (res.success) {
      message.success(res.message);
      await fetchStatus();
    } else {
      message.error(res.message);
    }
  } catch (error: any) {
    const errMsg = error.response?.data?.message || error.message || '启动失败';
    message.error({ content: `启动失败: ${errMsg}`, duration: 8 });
  } finally {
    starting.value = false;
  }
}

// 停止弱网
async function handleStop() {
  stopping.value = true;
  try {
    const res = await stopWeaknet();
    if (res.success) {
      message.success(res.message);
      await fetchStatus();
    } else {
      message.error(res.message);
    }
  } catch (error: any) {
    const errMsg = error.response?.data?.message || error.message || '停止失败';
    message.error({ content: `停止失败: ${errMsg}`, duration: 8 });
  } finally {
    stopping.value = false;
  }
}

// 检查安装状态
async function checkInstallation() {
  try {
    const res = await apiCheckInstallation();
    installStatus.value = res;
  } catch (error) {
    message.error('检查安装状态失败');
  }
}

function showInstallGuide() {
  Modal.info({
    title: '弱网工具安装指南',
    width: 600,
    content: `
      请按以下步骤部署弱网工具：

      1. 以管理员身份运行 PowerShell
      2. 确认后端服务已以管理员身份启动（需要管理员权限）
      3. 将 weaknet.exe 放置于项目 tools/weaknet/ 目录下
      4. 等待安装完成后刷新此页面

      说明：
      演示环境下弱网工具不实际影响网络流量，仅用于界面与交互演示。
    `,
  });
}

onMounted(() => {
  fetchStatus();
  loadPresets();
  checkInstallation();
  // 每 5 秒刷新状态
  statusTimer = window.setInterval(fetchStatus, 5000);
});

onUnmounted(() => {
  if (statusTimer) {
    clearInterval(statusTimer);
  }
});
</script>

<style scoped lang="less">
.weaknet-container {
  padding: 16px;
}

.status-card {
  &.running {
    border-color: #ff7a00;
  }
}

.status-header {
  display: flex;
  align-items: center;
  margin-bottom: 16px;
}

/* 重要提示：2×2 紧凑网格（小圆点 + 12px 小字），节约竖向空间 */
.tips-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 2px 16px;
  font-size: 12px;
  line-height: 1.55;
  text-align: left;

  .tips-item {
    position: relative;
    padding-left: 12px;

    &::before {
      content: '';
      position: absolute;
      left: 2px;
      top: 7px;
      width: 4px;
      height: 4px;
      border-radius: 50%;
      background: #1677ff;
    }
  }
}

.status-detail {
  padding-top: 16px;
  border-top: 1px solid #f0f0f0;
}

.preset-card {
  height: 100%;
  cursor: pointer;
  transition: all 0.3s;

  &:hover {
    transform: translateY(-4px);
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  }

  &.recommended {
    border-color: #52c41a;
  }
}

.card-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 14px;
}

.card-content {
  .description {
    font-size: 13px;
    color: #666;
    line-height: 1.6;
    min-height: 40px;
  }

  .params {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .param-item {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 13px;
    color: #333;

    .anticon {
      color: #1890ff;
    }
  }
}
</style>
