<template>
  <div class="intercept-container">
    <a-row :gutter="[16, 16]">
      <!-- 拦截状态 -->
      <a-col :xs="24" :lg="12">
        <a-card :class="['theme-card', 'status-card', { running: status?.running }]">
          <template #title>
            <span class="sec-title" :class="status?.running ? 'tint-red' : 'tint-gray'">
              <StopOutlined />拦截状态
            </span>
          </template>
          <div class="status-header">
            <a-badge
              :status="status?.running ? 'processing' : 'default'"
              :text="status?.running ? '拦截中' : '未启动'"
            />
            <a-button
              v-if="status?.running"
              danger
              :loading="stopping"
              style="margin-left: auto"
              @click="handleStop"
            >
              停止拦截
            </a-button>
          </div>
          <a-descriptions :column="{ xs: 1, sm: 2 }" size="small" bordered>
            <a-descriptions-item label="当前模式">
              <a-tag v-if="status?.control" color="red">{{ modeLabel(status.control.mode) }}</a-tag>
              <span v-else>-</span>
            </a-descriptions-item>
            <a-descriptions-item label="拦截进程 PID">{{ status?.pid ?? '-' }}</a-descriptions-item>
            <a-descriptions-item label="被测客户端" :span="2">
              <template v-if="target">
                <a-tag color="blue">{{ target.version || '版本未知' }}</a-tag>
                <a-tag v-if="target.uses_system_proxy !== null && target.uses_system_proxy !== undefined">{{
                  target.uses_system_proxy ? '走系统代理' : '直连'
                }}</a-tag>
                <code>{{ target.install_path }}</code>
              </template>
              <span v-else class="muted">-</span>
            </a-descriptions-item>
            <a-descriptions-item label="系统代理" :span="2">
              <template v-if="sysProxy">
                <code>{{ sysProxy.enabled ? sysProxy.server || '(空)' : '未启用' }}</code>
                <a-tag :color="sysProxy.bypass_active ? 'red' : 'default'" class="ml">
                  {{ sysProxy.bypass_active ? '样式域名已加入绕过列表' : '绕过列表未含样式域名' }}
                </a-tag>
              </template>
              <span v-else>-</span>
            </a-descriptions-item>
            <a-descriptions-item label="外部抓包工具">
              <a-tag :color="status?.external_capture?.active ? 'orange' : 'default'">
                {{ status?.external_capture?.active ? `运行中（${status.external_capture.port}）` : '未运行' }}
              </a-tag>
            </a-descriptions-item>
            <a-descriptions-item label="服务权限">
              <a-tag :color="status?.is_admin ? 'green' : 'default'">{{
                status?.is_admin ? '管理员' : '普通'
              }}</a-tag>
            </a-descriptions-item>
          </a-descriptions>
          <a-alert v-if="status?.external_capture?.active" type="warning" show-icon class="mt">
            <template #message>外部抓包工具正在运行，不能开启拦截</template>
            <template #description>
              外部抓包工具持有系统代理。此时改绕过列表会让它退出时不恢复系统代理，请先停止外部抓包工具。
            </template>
          </a-alert>
          <a-alert v-else-if="leftoverBypass" type="warning" show-icon class="mt">
            <template #message>拦截已停止，但绕过列表里还有样式域名</template>
            <template #description>
              点「停止拦截」移除；否则被测客户端的样式会一直直连，不经过本机代理。
            </template>
          </a-alert>
        </a-card>
      </a-col>

      <!-- 使用说明 -->
      <a-col :xs="24" :lg="12">
        <a-card class="theme-card">
          <template #title>
            <span class="sec-title tint-purple"><QuestionCircleOutlined />使用说明</span>
          </template>
          <div class="tips-grid">
            <div class="tips-item">只拦被测客户端<strong>渲染进程</strong>的样式（CSS），HTML/JS 照常加载</div>
            <div class="tips-item">开启期间样式域名加入系统代理<strong>绕过列表</strong>，停止时撤掉；代理地址不改</div>
            <div class="tips-item">外部抓包工具运行时<strong>不能开启</strong>，两者别同时测</div>
            <div class="tips-item">开启时默认重启被测客户端并清缓存，服务会自动重新拉起</div>
            <div class="tips-item">演示环境全部为模拟数据，不真实改系统代理</div>
            <div class="tips-item">测试结束<strong>务必停止拦截</strong></div>
          </div>
        </a-card>
      </a-col>

      <!-- 目标面板 · 样式未加载 -->
      <a-col :span="24">
        <a-card class="theme-card">
          <template #title>
            <span class="sec-title tint-orange"><BgColorsOutlined />目标面板 · 样式未加载</span>
          </template>
          <a-radio-group v-model:value="form.mode" class="mode-group">
            <a-radio-button v-for="m in MODE_OPTIONS" :key="m.value" :value="m.value">{{
              m.label
            }}</a-radio-button>
          </a-radio-group>
          <div class="muted mode-desc">{{ currentModeDesc }}</div>
          <a-form layout="inline" class="mt">
            <a-form-item v-if="form.mode === 'once'" label="拦截次数">
              <a-input-number v-model:value="form.count" :min="1" :max="100" />
            </a-form-item>
            <a-form-item v-if="form.mode === 'delay'" label="延迟（秒）">
              <a-input-number v-model:value="form.delay" :min="1" :max="120" />
            </a-form-item>
            <a-form-item label="路径过滤">
              <a-input
                v-model:value="form.path"
                allow-clear
                placeholder="留空拦全部，如 next.min.css"
                style="width: 240px"
              />
            </a-form-item>
            <a-form-item>
              <a-checkbox v-model:checked="form.restart_client">重启被测客户端并清缓存</a-checkbox>
            </a-form-item>
            <a-form-item>
              <a-button
                type="primary"
                danger
                :loading="starting"
                :disabled="status?.external_capture?.active"
                @click="handleStart"
              >
                {{ status?.running ? '切换模式' : '开始拦截' }}
              </a-button>
            </a-form-item>
          </a-form>
        </a-card>
      </a-col>

      <!-- 命中记录 -->
      <a-col :span="24">
        <a-card class="theme-card">
          <template #title>
            <span class="sec-title tint-blue"
              ><UnorderedListOutlined />命中记录（{{ hits.length }}）</span
            >
          </template>
          <template #extra>
            <a-button size="small" @click="fetchHits">刷新</a-button>
          </template>
          <a-table
            :data-source="hits"
            :columns="HIT_COLUMNS"
            size="small"
            :pagination="{ pageSize: 20 }"
            row-key="key"
          />
        </a-card>
      </a-col>
    </a-row>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, reactive, ref } from 'vue';
import { message } from 'ant-design-vue';
import {
  BgColorsOutlined,
  QuestionCircleOutlined,
  StopOutlined,
  UnorderedListOutlined,
} from '@ant-design/icons-vue';
import {
  getInterceptHits,
  getInterceptStatus,
  startIntercept,
  stopIntercept,
  type InterceptHit,
  type InterceptMode,
  type InterceptStatus,
} from '@/api/fault/intercept';

const MODE_OPTIONS: { value: InterceptMode; label: string; desc: string }[] = [
  {
    value: 'off',
    label: '仅记录',
    desc: '不拦截，只记录面板加载了哪些样式（先用它确认命中范围）',
  },
  {
    value: '404',
    label: '一直拦截',
    desc: '样式请求一律返回 404，刷新也恢复不了 → 测「刷新未恢复 → 重启客户端」',
  },
  {
    value: 'once',
    label: '只拦前 N 次',
    desc: '前 N 次返回 404，之后放行 → 测「检测错位 → 点刷新 → 恢复 → 重试抓取」',
  },
  { value: 'empty', label: '返回空 CSS', desc: '返回 200 空内容：请求「成功」但没有样式' },
  {
    value: 'delay',
    label: '延迟加载',
    desc: '放行但延迟 N 秒返回 → 测样式迟到时是否误判、刷新后 3s 等待是否够',
  },
];

const HIT_COLUMNS = [
  { title: '时间', dataIndex: 'time', width: 100 },
  { title: '动作', dataIndex: 'action', width: 220 },
  { title: 'URL', dataIndex: 'url', ellipsis: true },
];

const status = ref<InterceptStatus | null>(null);
const hits = ref<(InterceptHit & { key: string })[]>([]);
const starting = ref(false);
const stopping = ref(false);
const form = reactive({
  mode: '404' as InterceptMode,
  count: 1,
  delay: 10,
  path: '',
  restart_client: true,
});

const target = computed(() => status.value?.target);
const sysProxy = computed(() => status.value?.system_proxy);
// 未在拦截却仍有样式绕过项：服务异常退出或外部工具退出时恢复了带绕过项的旧值
const leftoverBypass = computed(() => !status.value?.running && !!sysProxy.value?.bypass_active);
const currentModeDesc = computed(
  () => MODE_OPTIONS.find((m) => m.value === form.mode)?.desc ?? '',
);

function modeLabel(mode: InterceptMode) {
  return MODE_OPTIONS.find((m) => m.value === mode)?.label ?? mode;
}

function errMsg(e: any, fallback: string) {
  return e?.response?.data?.message || e?.message || fallback;
}

async function fetchStatus() {
  try {
    status.value = await getInterceptStatus();
  } catch (e) {
    console.error('获取拦截状态失败:', e);
  }
}

async function fetchHits() {
  try {
    hits.value = (await getInterceptHits()).map((h, i) => ({ ...h, key: `${i}-${h.time}-${h.url}` }));
  } catch (e) {
    console.error('获取命中记录失败:', e);
  }
}

async function handleStart() {
  starting.value = true;
  try {
    const res = await startIntercept({ ...form });
    res.success
      ? message.success(res.message)
      : message.error({ content: res.message, duration: 8 });
  } catch (e: any) {
    message.error({ content: `开启失败: ${errMsg(e, '未知错误')}`, duration: 8 });
  } finally {
    starting.value = false;
    await Promise.all([fetchStatus(), fetchHits()]);
  }
}

async function handleStop() {
  stopping.value = true;
  try {
    message.success((await stopIntercept()).message);
  } catch (e: any) {
    message.error({ content: `停止失败: ${errMsg(e, '未知错误')}`, duration: 8 });
  } finally {
    stopping.value = false;
    await fetchStatus();
  }
}

let timer: number | null = null;
onMounted(async () => {
  await Promise.all([fetchStatus(), fetchHits()]);
  if (status.value?.control) Object.assign(form, status.value.control);
  timer = window.setInterval(() => {
    fetchStatus();
    if (status.value?.running) fetchHits();
  }, 3000);
});
onUnmounted(() => {
  if (timer) clearInterval(timer);
});
</script>

<style scoped lang="less">
.intercept-container {
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
}

.mode-desc {
  margin-top: 8px;
  font-size: 12px;
}

code {
  font-size: 12px;
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
</style>
