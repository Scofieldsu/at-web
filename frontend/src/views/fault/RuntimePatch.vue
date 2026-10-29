<template>
  <div class="patch-container">
    <a-row :gutter="[16, 16]">
      <a-col :xs="24" :lg="12">
        <a-card :class="['theme-card', 'status-card', { running: injected }]">
          <template #title>
            <span class="sec-title" :class="injected ? 'tint-red' : 'tint-gray'">
              <CodeOutlined />补丁状态
            </span>
          </template>
          <div class="status-header">
            <a-badge :status="injected ? 'processing' : 'default'" :text="statusText" />
            <a-button
              v-if="active?.mode === 'always'"
              danger
              :loading="removing"
              style="margin-left: auto"
              @click="handleRemove"
            >
              移除补丁
            </a-button>
          </div>
          <a-descriptions :column="{ xs: 1, sm: 2 }" size="small" bordered>
            <a-descriptions-item label="当前场景" :span="2">
              <template v-if="active?.key">
                <a-tag :color="injected ? 'red' : 'default'">{{ active.no }}. {{ active.title }}</a-tag>
                <span class="muted">{{ active.injected_at }}</span>
              </template>
              <span v-else class="muted">未注入</span>
            </a-descriptions-item>
            <a-descriptions-item label="参数" :span="2">
              <template v-if="active && Object.keys(active.params || {}).length">
                <a-tag v-for="(val, name) in active.params" :key="name">{{ name }}={{ val }}</a-tag>
              </template>
              <span v-else>-</span>
            </a-descriptions-item>
            <a-descriptions-item label="注入 PID">
              {{ active?.pid ?? '-' }}
              <a-tag v-if="active?.mode === 'always'" :color="active.pid_alive ? 'green' : 'orange'" class="ml">
                {{ active.pid_alive ? '进程仍在' : '进程已退出' }}
              </a-tag>
            </a-descriptions-item>
            <a-descriptions-item label="服务权限">
              <a-tag :color="status?.is_admin ? 'green' : 'default'">
                {{ status?.is_admin ? '管理员' : '普通' }}
              </a-tag>
            </a-descriptions-item>
            <a-descriptions-item label="注入目标" :span="2">
              <a-select v-model:value="pidChoice" style="width: 100%" :disabled="applying || removing">
                <a-select-option :value="0">
                  自动（{{ status?.selected_pid ? `主进程 ${status.selected_pid}` : '未找到被测客户端' }}）
                </a-select-option>
                <a-select-option v-for="p in status?.processes || []" :key="p.pid" :value="p.pid">
                  PID {{ p.pid }} · 父 {{ p.ppid }} · {{ p.memory_mb }}MB · {{ p.role }}
                </a-select-option>
              </a-select>
            </a-descriptions-item>
            <a-descriptions-item label="最近结果" :span="2">
              <span>{{ active?.message || '-' }}</span>
            </a-descriptions-item>
          </a-descriptions>
          <a-alert v-if="injected" type="info" show-icon class="mt">
            <template #message>同时只能有一个补丁</template>
            <template #description>
              进程里现在是「{{ active?.no }}. {{ active?.title }}」。再注入其他场景会先还原这一条，两个不会一起生效。
            </template>
          </a-alert>
          <a-alert v-if="active?.stale" type="warning" show-icon class="mt">
            <template #message>补丁已失效</template>
            <template #description>
              目标进程已退出。客户端重启后补丁失效，需要重新注入。
            </template>
          </a-alert>
          <a-alert v-if="status && !status.is_admin" type="warning" show-icon class="mt">
            <template #message>服务不是管理员</template>
            <template #description>注入被测客户端需要管理员权限，否则注入器会失败。</template>
          </a-alert>
          <a-alert v-if="status && !status.tool_ready" type="error" show-icon class="mt">
            <template #message>注入工具未就绪</template>
            <template #description>注入器需要专用解释器与注入依赖，请先部署。</template>
          </a-alert>
          <pre v-if="status?.status_lines?.length" class="status-log">{{ status.status_lines.join('\n') }}</pre>
        </a-card>
      </a-col>

      <a-col :xs="24" :lg="12">
        <a-card class="theme-card">
          <template #title>
            <span class="sec-title tint-purple"><QuestionCircleOutlined />使用说明</span>
          </template>
          <div class="tips-grid">
            <div class="tips-item">补丁注入正在运行的<strong>被测客户端主进程</strong>（client-a），跳过守护进程</div>
            <div class="tips-item">真实实现需要 <strong>管理员</strong> 与注入依赖；演示环境已模拟就绪</div>
            <div class="tips-item">只有标记「可用」的场景可以注入，其余显示「未实现」</div>
            <div class="tips-item">客户端重启后补丁失效，需重新注入</div>
            <div class="tips-item">同时只能注入一个场景。已有补丁时再注入，会先还原当前这条</div>
            <div class="tips-item">移除补丁会再注入一次，模式为关闭</div>
            <div class="tips-item">演示环境不真实改内存，全部为模拟状态与日志</div>
            <div class="tips-item">下方事件按所选场景的日志关键词筛选当天日志</div>
          </div>
        </a-card>
      </a-col>

      <a-col :span="24">
        <a-card class="theme-card">
          <template #title>
            <span class="sec-title tint-orange"><ExperimentOutlined />场景</span>
          </template>
          <div v-for="group in groups" :key="group.name" class="group">
            <div class="group-title">{{ group.name }}</div>
            <div
              v-for="s in group.items"
              :key="s.key"
              class="scenario"
              :class="{ on: selectedKey === s.key, live: injected && active?.key === s.key, off: !s.available }"
              @click="selectScenario(s)"
            >
              <div class="scenario-head">
                <a-radio :checked="selectedKey === s.key" :disabled="!s.available" />
                <span class="no">{{ s.no }}</span>
                <span class="title">{{ s.title }}</span>
                <a-tag :color="riskColor(s.risk)">{{ s.risk_label }}</a-tag>
                <a-tag v-if="injected && active?.key === s.key" color="red">生效中</a-tag>
                <a-tag v-else-if="s.available" color="blue">可用</a-tag>
                <a-tag v-else>未实现</a-tag>
              </div>
              <div class="desc">{{ s.desc }}</div>
              <div v-if="selectedKey === s.key" class="params" @click.stop>
                <a-form layout="inline">
                  <a-form-item v-for="(sample, name) in s.params" :key="name" :label="String(name)">
                    <a-input-number
                      v-if="typeof sample === 'number'"
                      v-model:value="draft[name]"
                      :precision="0"
                      style="width: 120px"
                    />
                    <a-input
                      v-else
                      v-model:value="draft[name]"
                      allow-clear
                      :placeholder="name === 'target' ? '留空取第一行' : ''"
                      style="width: 220px"
                    />
                  </a-form-item>
                  <a-form-item v-if="!Object.keys(s.params).length">
                    <span class="muted">此场景无参数</span>
                  </a-form-item>
                  <a-form-item>
                    <a-button type="primary" danger :loading="applying" @click="handleApply">
                      {{ replacing ? '替换当前补丁' : '注入' }}
                    </a-button>
                  </a-form-item>
                </a-form>
                <div v-if="replacing" class="replace-hint">
                  当前生效的是「{{ active?.no }}. {{ active?.title }}」。注入本场景会先还原它。
                </div>
                <div v-if="feedback" class="feedback" :class="feedbackOk ? 'ok' : 'bad'">{{ feedback }}</div>
              </div>
            </div>
          </div>
        </a-card>
      </a-col>

      <a-col :span="24">
        <a-card class="theme-card">
          <template #title>
            <span class="sec-title tint-blue">
              <UnorderedListOutlined />事件（{{ eventRows.length }}）
            </span>
          </template>
          <template #extra>
            <a-button size="small" @click="fetchEvents">刷新</a-button>
          </template>
          <div class="keyword-row">
            <a-tag v-for="k in eventData?.keywords || []" :key="k">{{ k }}</a-tag>
            <span v-if="!(eventData?.keywords || []).length" class="muted">先选择一个场景</span>
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
          />
        </a-card>
      </a-col>
    </a-row>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, reactive, ref } from 'vue';
import { message, Modal } from 'ant-design-vue';
import {
  CodeOutlined,
  ExperimentOutlined,
  QuestionCircleOutlined,
  UnorderedListOutlined,
} from '@ant-design/icons-vue';
import {
  applyRpaPatch,
  getRpaPatchEvents,
  getRpaPatchScenarios,
  getRpaPatchStatus,
  removeRpaPatch,
  type RpaPatchEvent,
  type RpaPatchEvents,
  type RpaPatchRisk,
  type RpaPatchScenario,
  type RpaPatchStatus,
} from '@/api/fault/patch';

const EVENT_COLUMNS = [
  { title: '时间', dataIndex: 'time', width: 180 },
  { title: '关键词', dataIndex: 'keyword', width: 200 },
  { title: '日志', dataIndex: 'line', ellipsis: true },
];

const scenarios = ref<RpaPatchScenario[]>([]);
const status = ref<RpaPatchStatus | null>(null);
const eventData = ref<RpaPatchEvents | null>(null);
const selectedKey = ref('');
const draft = reactive<Record<string, number | string>>({});
const pidChoice = ref(0);
const applying = ref(false);
const removing = ref(false);
const feedback = ref('');
const feedbackOk = ref(true);

const active = computed(() => status.value?.active ?? null);
const injected = computed(() => active.value?.mode === 'always' && !active.value?.stale);
const statusText = computed(() => {
  if (!active.value || active.value.mode !== 'always') return '未注入';
  return active.value.stale ? '已失效' : '已注入';
});
const replacing = computed(
  () => injected.value && !!active.value?.key && active.value.key !== selectedKey.value,
);

const groups = computed(() => {
  const order: string[] = [];
  for (const s of scenarios.value) if (!order.includes(s.group)) order.push(s.group);
  return order.map((name) => ({ name, items: scenarios.value.filter((s) => s.group === name) }));
});

const eventRows = computed(() =>
  (eventData.value?.events || []).map((e: RpaPatchEvent, i: number) => ({
    ...e,
    key: `${i}-${e.time}-${e.keyword}`,
  })),
);

function riskColor(risk: RpaPatchRisk) {
  return risk === 'high' ? 'red' : risk === 'medium' ? 'orange' : 'green';
}

function loadDraft(params: Record<string, number | string>) {
  Object.keys(draft).forEach((k) => delete draft[k]);
  Object.assign(draft, params);
}

function selectScenario(s: RpaPatchScenario) {
  if (!s.available || selectedKey.value === s.key) return;
  selectedKey.value = s.key;
  feedback.value = '';
  loadDraft(s.params);
  fetchEvents();
}

function chosenPid(): number | null {
  return pidChoice.value > 0 ? pidChoice.value : null;
}

function errMsg(e: any, fallback: string) {
  return e?.response?.data?.message || e?.message || fallback;
}

function buildParams(s: RpaPatchScenario) {
  const out: Record<string, number | string> = {};
  for (const [name, sample] of Object.entries(s.params)) {
    const value = draft[name];
    if (typeof sample === 'number') {
      const n = typeof value === 'number' ? value : Number(value);
      if (!Number.isInteger(n)) throw new Error(`${name} 须为整数`);
      out[name] = n;
    } else {
      out[name] = value == null ? '' : String(value);
    }
  }
  return out;
}

async function fetchStatus() {
  try {
    status.value = await getRpaPatchStatus();
  } catch (e) {
    console.error('获取补丁状态失败:', e);
  }
}

async function fetchEvents() {
  if (!selectedKey.value) return;
  try {
    eventData.value = await getRpaPatchEvents(selectedKey.value);
  } catch (e) {
    console.error('获取日志事件失败:', e);
  }
}

function confirmReplace(current: string, next: string) {
  return new Promise<boolean>((resolve) => {
    Modal.confirm({
      title: '同时只能有一个补丁',
      content: `将先还原「${current}」，再注入「${next}」。两个场景不会一起生效。`,
      okText: '替换',
      cancelText: '取消',
      onOk: () => resolve(true),
      onCancel: () => resolve(false),
    });
  });
}

async function handleApply() {
  const s = scenarios.value.find((item) => item.key === selectedKey.value);
  if (!s) return;
  let params: Record<string, number | string>;
  try {
    params = buildParams(s);
  } catch (e: any) {
    feedback.value = e?.message || '参数不正确';
    feedbackOk.value = false;
    return;
  }
  if (replacing.value && active.value) {
    const ok = await confirmReplace(
      `${active.value.no}. ${active.value.title}`,
      `${s.no}. ${s.title}`,
    );
    if (!ok) return;
  }
  applying.value = true;
  feedback.value = '';
  try {
    const res = await applyRpaPatch({ key: s.key, params, pid: chosenPid() });
    feedback.value = res.message;
    feedbackOk.value = res.success;
    res.success ? message.success(res.message) : message.error({ content: res.message, duration: 8 });
  } catch (e: any) {
    feedback.value = errMsg(e, '注入失败');
    feedbackOk.value = false;
    message.error({ content: feedback.value, duration: 8 });
  } finally {
    applying.value = false;
    await Promise.all([fetchStatus(), fetchEvents()]);
  }
}

async function handleRemove() {
  removing.value = true;
  try {
    const res = await removeRpaPatch(chosenPid());
    feedback.value = res.message;
    feedbackOk.value = true;
    message.success(res.message);
  } catch (e: any) {
    feedback.value = errMsg(e, '移除失败');
    feedbackOk.value = false;
    message.error({ content: feedback.value, duration: 8 });
  } finally {
    removing.value = false;
    await Promise.all([fetchStatus(), fetchEvents()]);
  }
}

let timer: number | null = null;
onMounted(async () => {
  try {
    scenarios.value = await getRpaPatchScenarios();
  } catch (e) {
    console.error('获取场景失败:', e);
  }
  await fetchStatus();
  const prefer = status.value?.active?.key;
  const first =
    scenarios.value.find((s) => s.key === prefer && s.available) ||
    scenarios.value.find((s) => s.available);
  if (first) {
    selectedKey.value = first.key;
    loadDraft(first.params);
    await fetchEvents();
  }
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
.patch-container {
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

.ml {
  margin-left: 8px;
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

.status-log {
  margin: 12px 0 0;
  max-height: 140px;
  overflow: auto;
  padding: 8px 10px;
  border-radius: 6px;
  background: var(--bg-card-alt, #fafafa);
  border: 1px solid var(--border-color, #e5e5e5);
  font-size: 12px;
  line-height: 1.5;
  white-space: pre-wrap;
  word-break: break-all;
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

.group {
  margin-bottom: 8px;
}

.group-title {
  margin: 8px 0;
  font-size: 13px;
  font-weight: 600;
  color: var(--text-secondary, #60646c);
}

.scenario {
  margin-bottom: 8px;
  padding: 10px 12px;
  border: 1px solid var(--border-color, #e5e5e5);
  border-radius: 8px;
  cursor: pointer;

  &.on {
    border-color: #e5484d;
  }

  &.live {
    background: rgba(229, 72, 77, 0.06);
  }

  &.off {
    cursor: default;
    opacity: 0.72;
  }
}

.scenario-head {
  display: flex;
  align-items: center;
  gap: 8px;
}

.no {
  color: #888;
  font-variant-numeric: tabular-nums;
}

.title {
  font-weight: 600;
}

.desc {
  margin: 4px 0 0 24px;
  color: #666;
  font-size: 12px;
  line-height: 1.5;
}

.params {
  margin: 10px 0 0 24px;
}

.replace-hint {
  margin-top: 8px;
  color: #ad5700;
  font-size: 12px;
  line-height: 1.5;
}

.feedback {
  margin-top: 8px;
  font-size: 12px;
  white-space: pre-wrap;

  &.ok {
    color: #30a46c;
  }

  &.bad {
    color: #e5484d;
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
