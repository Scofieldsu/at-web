<template>
  <div class="popup-sim-container">
    <a-row :gutter="[16, 16]">
      <a-col :xs="24" :lg="12">
        <a-card :class="['theme-card', 'status-card', { running: hasOpen }]">
          <template #title>
            <span class="sec-title" :class="hasOpen ? 'tint-red' : 'tint-gray'">
              <AlertOutlined />系统硬错误框（模拟）
            </span>
          </template>
          <div class="status-header">
            <a-badge :status="hasOpen ? 'processing' : 'default'" :text="statusText" />
          </div>
          <a-form layout="vertical" class="trigger-form">
            <a-form-item label="模式">
              <a-radio-group v-model:value="mode" :disabled="triggering || !status?.exe_exists">
                <a-radio v-for="(label, key) in status?.modes || defaultModes" :key="key" :value="key">
                  {{ label }}
                </a-radio>
              </a-radio-group>
            </a-form-item>
            <a-form-item v-if="mode === 'std'" label="内层状态码">
              <a-input
                v-model:value="code"
                allow-clear
                placeholder="0xc000012d"
                :disabled="triggering"
                style="max-width: 220px"
              />
            </a-form-item>
            <a-form-item>
              <a-button
                type="primary"
                danger
                :loading="triggering"
                :disabled="!status?.exe_exists"
                @click="handleTrigger"
              >
                弹出（模拟）
              </a-button>
            </a-form-item>
          </a-form>
          <a-alert v-if="status && !status.exe_exists" type="error" show-icon class="mt">
            <template #message>模拟器不存在</template>
            <template #description>
              请部署 {{ status.exe_name }}。路径：{{ status.exe_path }}
            </template>
          </a-alert>
          <div class="table-title">最近记录</div>
          <a-table
            :data-source="historyRows"
            :columns="HISTORY_COLUMNS"
            size="small"
            :pagination="false"
            row-key="pid"
            :locale="{ emptyText: '还没有弹出记录（服务重启后会清空）' }"
          >
            <template #bodyCell="{ column, record }">
              <template v-if="column.dataIndex === 'alive'">
                <a-tag :color="record.alive ? 'red' : 'green'">
                  {{ record.alive ? '未关闭' : '已关闭' }}
                </a-tag>
              </template>
              <template v-else-if="column.dataIndex === 'args'">
                {{ (record.args || []).join(' ') || '-' }}
              </template>
            </template>
          </a-table>
        </a-card>
      </a-col>

      <a-col :xs="24" :lg="12">
        <a-card class="theme-card">
          <template #title>
            <span class="sec-title tint-purple"><QuestionCircleOutlined />使用说明</span>
          </template>
          <div class="tips-grid">
            <div class="tips-item">演示环境不真正弹框，全部为模拟记录，弹出约 5-8 秒后自动标记「已关闭」</div>
            <div class="tips-item">真实实现中框由<strong>系统</strong>弹出，与线上真实框一样，不属于模拟器进程</div>
            <div class="tips-item">框关闭后模拟器进程退出，所以「未关闭」就表示框还在屏幕上</div>
            <div class="tips-item">平台不负责关框：由被测应用自动关闭，或人工点「确定」</div>
            <div class="tips-item">运行中约 60 秒内应被被测应用关掉；登录前弹出，登录应能正常完成</div>
            <div class="tips-item">回归项：被测应用自己弹出的提示框不应被关掉</div>
          </div>
        </a-card>
      </a-col>

      <a-col :span="24">
        <a-card class="theme-card">
          <template #title>
            <span class="sec-title tint-blue">
              <UnorderedListOutlined />处理日志（{{ eventRows.length }}）
            </span>
          </template>
          <template #extra>
            <a-button size="small" @click="fetchEvents">刷新</a-button>
          </template>
          <div class="keyword-row">
            <a-tag v-for="k in eventData?.keywords || []" :key="k">{{ k }}</a-tag>
          </div>
          <div class="muted log-path">
            {{ eventData?.log_file || status?.log_file || '' }}
            <template v-if="eventData && !eventData.exists">（当天日志不存在）</template>
          </div>
          <a-table
            :data-source="eventRows"
            :columns="EVENT_COLUMNS"
            size="small"
            :pagination="{ pageSize: 20 }"
            row-key="key"
            :locale="{ emptyText: '没有命中关键词的日志' }"
          >
            <template #bodyCell="{ column, record }">
              <template v-if="column.dataIndex === 'keyword'">
                <a-tag :color="keywordColor(record.line)">{{ record.keyword }}</a-tag>
              </template>
            </template>
          </a-table>
        </a-card>
      </a-col>
    </a-row>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue';
import { message } from 'ant-design-vue';
import { AlertOutlined, QuestionCircleOutlined, UnorderedListOutlined } from '@ant-design/icons-vue';
import {
  getPopupSimEvents,
  getPopupSimStatus,
  triggerPopupSim,
  type PopupSimEvents,
  type PopupSimMode,
  type PopupSimStatus,
} from '@/api/fault/popup';

const HISTORY_COLUMNS = [
  { title: '时间', dataIndex: 'at', width: 180 },
  { title: '模式', dataIndex: 'mode', width: 80 },
  { title: '参数', dataIndex: 'args', ellipsis: true },
  { title: 'PID', dataIndex: 'pid', width: 100 },
  { title: '状态', dataIndex: 'alive', width: 100 },
];

const EVENT_COLUMNS = [
  { title: '时间', dataIndex: 'time', width: 180 },
  { title: '关键词', dataIndex: 'keyword', width: 200 },
  { title: '日志', dataIndex: 'line', ellipsis: true },
];

const defaultModes: Record<PopupSimMode, string> = {
  zh: '线上原文（中文标题）',
  std: '系统标准硬错误（标题由系统按语言生成）',
};

const status = ref<PopupSimStatus | null>(null);
const eventData = ref<PopupSimEvents | null>(null);
const mode = ref<PopupSimMode>('zh');
const code = ref('');
const triggering = ref(false);

const hasOpen = computed(() => (status.value?.running?.length || 0) > 0);
const statusText = computed(() => {
  const n = status.value?.running?.length || 0;
  return n > 0 ? `${n} 个框未关闭` : '当前没有模拟框';
});
const historyRows = computed(() => status.value?.history || []);
const eventRows = computed(() =>
  (eventData.value?.events || []).map((e, i) => ({
    ...e,
    key: `${i}-${e.time}-${e.keyword}`,
  })),
);

function keywordColor(line: string) {
  if (line.includes('关闭成功')) return 'green';
  if (line.includes('已清理')) return 'blue';
  if (line.includes('检测到')) return 'orange';
  return 'default';
}

function errMsg(e: any, fallback: string) {
  return e?.response?.data?.message || e?.message || fallback;
}

async function fetchStatus() {
  try {
    status.value = await getPopupSimStatus();
  } catch (e) {
    console.error('获取弹窗模拟状态失败:', e);
  }
}

async function fetchEvents() {
  try {
    eventData.value = await getPopupSimEvents();
  } catch (e) {
    console.error('获取弹窗模拟日志失败:', e);
  }
}

async function handleTrigger() {
  triggering.value = true;
  try {
    const body: { mode: PopupSimMode; code?: string } = { mode: mode.value };
    if (mode.value === 'std') {
      const trimmed = code.value.trim();
      if (trimmed) body.code = trimmed;
    }
    const res = await triggerPopupSim(body);
    res.success ? message.success(res.message) : message.error({ content: res.message, duration: 8 });
  } catch (e: any) {
    message.error({ content: errMsg(e, '弹出失败'), duration: 8 });
  } finally {
    triggering.value = false;
    await Promise.all([fetchStatus(), fetchEvents()]);
  }
}

let timer: number | null = null;
onMounted(async () => {
  await Promise.all([fetchStatus(), fetchEvents()]);
  timer = window.setInterval(() => {
    fetchStatus();
    fetchEvents();
  }, 3000);
});
onUnmounted(() => {
  if (timer) clearInterval(timer);
});
</script>

<style scoped lang="less">
.popup-sim-container {
  padding: 16px;
}

.status-card.running {
  border-color: #e5484d;
}

.status-header {
  display: flex;
  align-items: center;
  margin-bottom: 16px;
}

.mt {
  margin-top: 12px;
}

.muted {
  color: #888;
  font-size: 12px;
}

.tint-gray {
  background: rgba(100, 116, 139, 0.12);
  color: #64748b;
}

.trigger-form {
  margin-bottom: 8px;
}

.table-title {
  margin: 12px 0 8px;
  font-size: 13px;
  font-weight: 600;
  color: var(--text-secondary, #60646c);
}

.tips-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 6px 16px;
  font-size: 12px;
  line-height: 1.6;

  .tips-item {
    position: relative;
    padding-left: 12px;

    &::before {
      content: '';
      position: absolute;
      left: 2px;
      top: 8px;
      width: 4px;
      height: 4px;
      border-radius: 50%;
      background: #1677ff;
    }
  }
}

.keyword-row {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-bottom: 8px;
}

.log-path {
  margin-bottom: 8px;
  word-break: break-all;
}
</style>
