<template>
  <div class="weaknet-container">
    <!-- 顶部行：左 弱网状态 / 右 使用说明 -->
    <a-row :gutter="[16, 16]">
      <a-col :xs="24" :sm="12" :md="16" :lg="12">
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
                检测到系统中运行的弱网实例（PID={{ statusData.pid }}），但该实例不是通过本管理控制台启动，无法查看配置详情。
                可点击「停止弱网」结束该进程。
              </template>
            </a-alert>
          </div>
        </a-card>
      </a-col>

      <a-col :xs="24" :sm="12" :md="8" :lg="12">
        <a-card class="theme-card">
          <template #title>
            <span class="sec-title tint-purple"><QuestionCircleOutlined />使用说明</span>
          </template>

          <a-alert type="info" show-icon style="margin-bottom: 16px">
            <template #message>重要提示</template>
            <template #description>
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
                <a-descriptions-item label="3G 网络">延迟 200ms，丢包 5% - 模拟 3G 网络环境，适合轻度弱网测试</a-descriptions-item>
                <a-descriptions-item label="2G 网络"><strong>延迟 500ms，丢包 10% - 推荐用于日常弱网测试</strong></a-descriptions-item>
                <a-descriptions-item label="极差网络">延迟 1000ms，丢包 20% - 极端弱网场景，测试系统降级能力</a-descriptions-item>
                <a-descriptions-item label="断网模拟">100% 丢包 - 模拟完全断网，测试断网后的恢复逻辑</a-descriptions-item>
                <a-descriptions-item label="平台预设">仅影响对应平台的虚拟网段流量（演示数据），可配合「采集 IP 段」更新</a-descriptions-item>
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
      <template #extra>
        <span class="extra-hint">点卡片启动；「设置」可改参数，修改保存在本浏览器</span>
        <a-button size="small" @click="openCollect()"><AimOutlined />采集 IP 段</a-button>
      </template>

      <a-row :gutter="[16, 16]">
        <a-col v-for="preset in displayPresets" :key="preset.key" :xs="24" :sm="12" :md="8" :lg="6">
          <a-card
            :class="['preset-card', { recommended: isRecommended(preset.key), customized: !!overrides[preset.key] }]"
            hoverable
            @click="handlePresetSelect(preset.key)"
          >
            <template #title>
              <div class="card-title">
                <span>
                  {{ preset.name }}
                  <a-tag v-if="isRecommended(preset.key)" color="success" style="margin-left: 8px">推荐</a-tag>
                  <a-tag v-if="overrides[preset.key]" color="orange" style="margin-left: 4px">已改</a-tag>
                </span>
              </div>
            </template>
            <template #extra>
              <a-button type="link" size="small" @click.stop="openPresetEditor(preset.key)">
                <EditOutlined />设置
              </a-button>
            </template>

            <div class="card-content">
              <p class="description">{{ preset.description }}</p>
              <a-divider style="margin: 12px 0" />
              <div class="params">
                <div v-for="line in describeConfig(effectiveConfig(preset.key))" :key="line" class="param-item">
                  <DashboardOutlined />
                  <span>{{ line }}</span>
                </div>
                <div
                  v-if="overrides[preset.key] && overrides[preset.key].filter_rule !== preset.config.filter_rule"
                  class="param-item"
                >
                  <FilterOutlined />
                  <span>过滤规则已改</span>
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
        <ClumsyParamsForm v-model="customConfig" />
        <a-form-item style="margin-top: 12px">
          <a-button type="primary" :loading="starting" @click="handleCustomStart">
            <PlayCircleOutlined />启动自定义弱网
          </a-button>
        </a-form-item>
      </a-form>
    </a-card>

    <!-- 预设卡片参数编辑 -->
    <a-modal
      v-model:open="editorOpen"
      :title="`设置参数：${editingPreset?.name || ''}`"
      width="980px"
      :mask-closable="false"
    >
      <a-form v-if="editingConfig" layout="vertical">
        <ClumsyParamsForm v-model="editingConfig" />
      </a-form>
      <template #footer>
        <a-button style="float: left" @click="resetPresetEditor">恢复预设默认</a-button>
        <a-button v-if="editingPlatform" style="float: left" @click="openCollect(editingPlatform.key)">
          <AimOutlined />采集{{ editingPlatform.label }} IP 段
        </a-button>
        <a-button @click="editorOpen = false">取消</a-button>
        <a-button @click="savePresetEditor(false)">保存</a-button>
        <a-button type="primary" :loading="starting" @click="savePresetEditor(true)">保存并启动</a-button>
      </template>
    </a-modal>

    <!-- 按平台采集 IP 段 -->
    <a-modal v-model:open="collectOpen" title="采集平台 IP 段" width="900px" :mask-closable="!collecting">
      <a-form layout="inline" style="row-gap: 8px">
        <a-form-item label="平台">
          <a-select v-model:value="collectForm.platform" style="width: 130px" :disabled="collecting">
            <a-select-option v-for="p in collectPlatforms" :key="p.key" :value="p.key">{{ p.label }}</a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item label="采样时长">
          <a-input-number v-model:value="collectForm.seconds" :min="5" :max="60" addon-after="秒" style="width: 120px" :disabled="collecting" />
        </a-form-item>
        <a-form-item label="归并网段">
          <a-select v-model:value="collectForm.prefix_len" style="width: 100px" :disabled="collecting">
            <a-select-option :value="16">/16</a-select-option>
            <a-select-option :value="24">/24</a-select-option>
            <a-select-option :value="32">单 IP</a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item>
          <a-button type="primary" :loading="collecting" @click="runCollect">
            {{ collecting ? `采样中 ${collectRemain}s` : '开始采集' }}
          </a-button>
        </a-form-item>
      </a-form>
      <a-alert
        v-if="currentCollectPlatform"
        type="info"
        show-icon
        style="margin: 12px 0"
        :message="currentCollectPlatform.hint + '（演示：IP 为模拟数据）'"
      />

      <template v-if="collectResult">
        <a-alert
          v-for="w in collectResult.warnings"
          :key="w"
          type="warning"
          show-icon
          style="margin-bottom: 8px"
          :message="w"
        />
        <a-table
          :data-source="collectResult.networks"
          :columns="collectColumns"
          row-key="cidr"
          size="small"
          :pagination="false"
          :scroll="{ y: 260 }"
        >
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'covered'">
              <a-tag :color="record.covered ? 'default' : 'orange'">{{ record.covered ? '已覆盖' : '新网段' }}</a-tag>
            </template>
            <template v-else-if="column.key === 'ips'">{{ record.ips.join(', ') }}</template>
          </template>
        </a-table>
        <div class="collect-meta">
          共 {{ collectResult.ip_count }} 个 IP / {{ collectResult.networks.length }} 个网段；
          采到的进程：{{ Object.entries(collectResult.processes).map(([n, c]) => `${n}×${c}`).join('、') }}；
          已排除中控：{{ collectResult.excluded.join('、') || '无' }}
        </div>
        <a-textarea :value="collectResult.filter_rule" :auto-size="{ minRows: 2, maxRows: 5 }" readonly />
      </template>

      <template #footer>
        <a-button @click="collectOpen = false">关闭</a-button>
        <a-button :disabled="!collectResult" @click="applyCollect('custom')">填入自定义配置</a-button>
        <a-button type="primary" :disabled="!collectResult || !collectTargetPreset" @click="applyCollect('preset')">
          应用到「{{ collectTargetPresetName }}」卡片
        </a-button>
      </template>
    </a-modal>
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
  DashboardOutlined,
  PlayCircleOutlined,
  EditOutlined,
  FilterOutlined,
  AimOutlined,
} from '@ant-design/icons-vue';
import {
  startWeaknet,
  stopWeaknet,
  getStatus,
  getPresets,
  getCollectPlatforms,
  collectIps,
  defaultClumsyConfig,
  checkInstallation as apiCheckInstallation,
  type ClumsyConfig,
  type CollectPlatform,
  type CollectResult,
} from '@/api/fault/clumsy';
import ClumsyParamsForm from './ClumsyParamsForm.vue';

const isRunning = ref(false);
const statusData = ref<any>({});
const currentConfig = ref<any>(null);
const presets = ref<any[]>([]);
const starting = ref(false);
const stopping = ref(false);
const installStatus = ref<any>(null);
const activeKeys = ref<string[]>(['4']);

const customConfig = ref<ClumsyConfig>({
  ...defaultClumsyConfig(),
  lag_time: 500,
  drop_chance: 0.1,
  throttle_timeframe: 200,
  throttle_chance: 0.9,
});

// 预设卡片的参数修改：按 preset key 存整份配置，持久化到 localStorage
const OVERRIDES_KEY = 'at-web-weaknet-preset-overrides';
const overrides = ref<Record<string, ClumsyConfig>>(loadOverrides());

function loadOverrides(): Record<string, ClumsyConfig> {
  try {
    return JSON.parse(localStorage.getItem(OVERRIDES_KEY) || '{}');
  } catch {
    return {};
  }
}

function saveOverrides() {
  localStorage.setItem(OVERRIDES_KEY, JSON.stringify(overrides.value));
}

function presetByKey(key: string) {
  return presets.value.find((p) => p.key === key);
}

/** 卡片当前生效的配置：用户改过的覆盖优先，补齐新增字段的默认值 */
function effectiveConfig(key: string): ClumsyConfig {
  const base = presetByKey(key)?.config || {};
  return { ...defaultClumsyConfig(), ...base, ...(overrides.value[key] || {}) };
}

let statusTimer: number | null = null;

const recommendedPresets = ['2g', '3g'];

const displayPresets = computed(() => {
  const order = [
    'baseline', '3g', '2g', 'extreme', 'disconnect',
    'platform_a_2g', 'platform_b_2g', 'platform_c_2g', 'platform_d_2g', 'chaos',
  ];
  return [...presets.value].sort((a, b) => {
    const aIndex = order.indexOf(a.key);
    const bIndex = order.indexOf(b.key);
    return (aIndex === -1 ? 999 : aIndex) - (bIndex === -1 ? 999 : bIndex);
  });
});

function isRecommended(key: string) {
  return recommendedPresets.includes(key);
}

const pct = (v: number) => `${Math.round((v || 0) * 10000) / 100}%`;

/** 卡片上逐行展示的参数；口径与后端 summary 一致 */
function describeConfig(c: ClumsyConfig): string[] {
  const rows: [string, boolean, string][] = [
    ['lag', c.lag_enabled && c.lag_time > 0, `延迟 ${c.lag_time}ms`],
    ['drop', c.drop_enabled && c.drop_chance > 0, `丢包 ${pct(c.drop_chance)}`],
    ['throttle', c.throttle_enabled && c.throttle_chance > 0, `节流 ${c.throttle_timeframe}ms / ${pct(c.throttle_chance)}`],
    ['bandwidth', c.bandwidth_enabled && c.bandwidth_limit > 0, `限速 ${c.bandwidth_limit}KB/s`],
    ['dup', c.dup_enabled && c.dup_chance > 0, `重复 ${pct(c.dup_chance)} ×${c.dup_count}`],
    ['out_of_order', c.out_of_order_enabled && c.out_of_order_chance > 0, `乱序 ${pct(c.out_of_order_chance)}`],
    ['tamper', c.tamper_enabled && c.tamper_chance > 0, `篡改 ${pct(c.tamper_chance)}`],
    ['reset', c.reset_enabled && c.reset_chance > 0, `TCP RST ${pct(c.reset_chance)}`],
  ];
  const lines: string[] = [];
  for (const [key, on, text] of rows) {
    const inbound = (c as any)[`${key}_inbound`] ?? true;
    const outbound = (c as any)[`${key}_outbound`] ?? true;
    if (!on || (!inbound && !outbound)) continue;
    lines.push(inbound === outbound ? text : `${text}（${inbound ? '下行' : '上行'}）`);
  }
  return lines.length ? lines : ['无弱网注入'];
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

async function loadPresets() {
  try {
    const res = await getPresets();
    presets.value = Object.entries(res).map(([key, value]: [string, any]) => ({ key, ...value }));
  } catch (error) {
    message.error('加载预设配置失败');
  }
}

async function handlePresetSelect(presetKey: string) {
  if (isRunning.value) {
    message.warning('请先停止当前弱网');
    return;
  }
  starting.value = true;
  try {
    const override = overrides.value[presetKey];
    const res = override
      ? await startWeaknet({
          config: { ...effectiveConfig(presetKey), preset_name: `${presetByKey(presetKey)?.name}（已改）` },
        })
      : await startWeaknet({ preset: presetKey });
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

// ── 预设卡片参数编辑 ──
const editorOpen = ref(false);
const editingKey = ref('');
const editingConfig = ref<ClumsyConfig | null>(null);
const editingPreset = computed(() => presetByKey(editingKey.value));
const editingPlatform = computed(() => collectPlatforms.value.find((p) => p.preset === editingKey.value));

function openPresetEditor(key: string) {
  editingKey.value = key;
  editingConfig.value = JSON.parse(JSON.stringify(effectiveConfig(key)));
  editorOpen.value = true;
}

function resetPresetEditor() {
  editingConfig.value = { ...defaultClumsyConfig(), ...JSON.parse(JSON.stringify(editingPreset.value?.config || {})) };
}

async function savePresetEditor(andStart: boolean) {
  if (!editingConfig.value) return;
  const base = { ...defaultClumsyConfig(), ...(editingPreset.value?.config || {}) };
  if (JSON.stringify({ ...editingConfig.value, preset_name: null }) === JSON.stringify({ ...base, preset_name: null })) {
    delete overrides.value[editingKey.value];
  } else {
    overrides.value[editingKey.value] = { ...editingConfig.value };
  }
  saveOverrides();
  editorOpen.value = false;
  if (andStart) await handlePresetSelect(editingKey.value);
}

// ── 按平台采集 IP 段 ──
const collectPlatforms = ref<CollectPlatform[]>([]);
const collectOpen = ref(false);
const collecting = ref(false);
const collectRemain = ref(0);
const collectResult = ref<CollectResult | null>(null);
const collectForm = ref({ platform: 'client_a', seconds: 20, prefix_len: 16 });
const currentCollectPlatform = computed(() => collectPlatforms.value.find((p) => p.key === collectForm.value.platform));
const collectTargetPreset = computed(() => currentCollectPlatform.value?.preset || '');
const collectTargetPresetName = computed(
  () => presetByKey(collectTargetPreset.value)?.name || collectTargetPreset.value,
);
const collectColumns = [
  { title: '网段', dataIndex: 'cidr', key: 'cidr', width: 150 },
  { title: '采到的 IP', dataIndex: 'ips', key: 'ips', ellipsis: true },
  { title: '连接次数', dataIndex: 'hits', key: 'hits', width: 90 },
  { title: '原预设', key: 'covered', width: 90 },
];

async function loadCollectPlatforms() {
  try {
    collectPlatforms.value = await getCollectPlatforms();
  } catch {
    collectPlatforms.value = [];
  }
}

function openCollect(platform?: string) {
  if (platform) collectForm.value.platform = platform;
  if (collectResult.value?.platform !== collectForm.value.platform) collectResult.value = null;
  collectOpen.value = true;
}

async function runCollect() {
  collecting.value = true;
  collectResult.value = null;
  collectRemain.value = collectForm.value.seconds;
  const timer = window.setInterval(() => {
    collectRemain.value = Math.max(0, collectRemain.value - 1);
  }, 1000);
  try {
    const res = await collectIps(collectForm.value);
    if (res.success && res.data) {
      collectResult.value = res.data;
      const fresh = res.data.networks.filter((n) => !n.covered).length;
      message.success(`采到 ${res.data.networks.length} 个网段，其中 ${fresh} 个不在原预设规则里`);
    } else {
      message.error(res.message || '采集失败');
    }
  } catch (error: any) {
    message.error({ content: error.response?.data?.message || error.message || '采集失败', duration: 8 });
  } finally {
    window.clearInterval(timer);
    collecting.value = false;
  }
}

function applyCollect(target: 'custom' | 'preset') {
  const rule = collectResult.value?.filter_rule;
  if (!rule) return;
  if (target === 'custom') {
    customConfig.value.filter_rule = rule;
    message.success('已填入自定义配置的过滤规则');
  } else {
    const key = collectTargetPreset.value;
    if (editorOpen.value && editingKey.value === key && editingConfig.value) {
      editingConfig.value.filter_rule = rule;
    } else {
      overrides.value[key] = { ...effectiveConfig(key), filter_rule: rule };
      saveOverrides();
    }
    message.success(`已应用到「${collectTargetPresetName.value}」卡片`);
  }
  collectOpen.value = false;
}

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
  loadCollectPlatforms();
  checkInstallation();
  statusTimer = window.setInterval(fetchStatus, 5000);
});

onUnmounted(() => {
  if (statusTimer) clearInterval(statusTimer);
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

  &.customized {
    border-color: #fa8c16;
  }
}

.extra-hint {
  margin-right: 12px;
  font-size: 12px;
  color: #999;
}

.collect-meta {
  margin: 8px 0;
  font-size: 12px;
  color: #666;
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
