<template>
  <div v-if="taskId" class="remote-view">
    <!-- 任务概要 -->
    <a-descriptions :column="2" bordered size="small">
      <a-descriptions-item label="状态">
        <a-tag :color="statusColor">{{ statusText }}</a-tag>
        <span v-if="errorText" class="err-hint" :title="errorText">{{ shortErr }}</span>
      </a-descriptions-item>
      <a-descriptions-item label="执行机器">{{ targetMachine }}</a-descriptions-item>
      <a-descriptions-item label="平台">{{ platformLabel(taskInfo.platform) }}</a-descriptions-item>
      <a-descriptions-item label="用例数">{{ taskInfo.cases?.length ?? '-' }}</a-descriptions-item>
      <a-descriptions-item label="开始时间">
        {{ taskInfo.started_at ? fmtTime(taskInfo.started_at) : '-' }}
      </a-descriptions-item>
      <a-descriptions-item label="耗时">{{ durationText }}</a-descriptions-item>
      <a-descriptions-item label="进度" :span="2">
        <a-progress :percent="taskInfo.progress || 0" :status="progressStatus" size="small" />
      </a-descriptions-item>
    </a-descriptions>

    <a-alert v-if="errorText" type="error" show-icon class="mt-2" :message="shortErr" />

    <!-- 实时日志（浅色背景） -->
    <div class="log-wrap">
      <div class="log-head">
        <span class="log-title">实时日志</span>
        <a-space :size="6" wrap>
          <a-checkbox v-model:checked="autoScroll">自动滚动</a-checkbox>
          <a-checkbox v-model:checked="autoPoll">自动刷新 (2s)</a-checkbox>
          <a-button size="small" :disabled="!logLines.length" @click="downloadLog">
            下载日志
          </a-button>
          <a-button size="small" type="primary" :disabled="!isFinished" @click="viewResult">
            查看结果
          </a-button>
          <a-button size="small" :loading="downloadingVideo" :disabled="!isFinished" @click="handleDownloadVideo">
            下载录屏
          </a-button>
          <a-button size="small" danger :loading="stopping" :disabled="!active" @click="stopTask">
            {{ stopping ? '停止中…' : '停止任务' }}
          </a-button>
          <a-button size="small" :loading="loadingLog" @click="fetchLog(true)">刷新</a-button>
        </a-space>
      </div>
      <div ref="logBox" class="log-body">
        <pre class="log-content">{{ logText || '暂无日志输出…' }}</pre>
      </div>
      <div class="log-foot">
        <span>已加载 {{ logLines.length }} / {{ logTotal }} 行</span>
        <span v-if="logFinished" class="text-success">（任务已结束）</span>
        <span v-if="logError" class="err-hint">{{ logError }}</span>
      </div>
    </div>

    <!-- 测试结果弹窗（与任务详情页一致） -->
    <a-modal v-model:open="resultVisible" title="测试结果" width="80%" :footer="null">
      <template v-if="testResult">
        <a-descriptions bordered :column="3" size="small" class="mb-3">
          <a-descriptions-item label="总用例">{{ resultSummary.total }}</a-descriptions-item>
          <a-descriptions-item label="通过">
            <span class="text-success">{{ resultSummary.passed }}</span>
          </a-descriptions-item>
          <a-descriptions-item label="失败">
            <span class="text-danger">{{ resultSummary.failed }}</span>
          </a-descriptions-item>
          <a-descriptions-item label="错误">{{ resultSummary.error }}</a-descriptions-item>
          <a-descriptions-item label="跳过">{{ resultSummary.skipped }}</a-descriptions-item>
          <a-descriptions-item label="总耗时">
            {{ (testResult.duration || 0).toFixed(2) }}s
          </a-descriptions-item>
        </a-descriptions>
        <a-table
          :columns="resultColumns"
          :data-source="testResult.tests || []"
          :pagination="false"
          row-key="nodeid"
          size="small"
          bordered
        >
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'outcome'">
              <a-tag :color="outcomeColor(record.outcome)">{{ record.outcome }}</a-tag>
            </template>
            <template v-else-if="column.key === 'duration'">
              {{ (record.duration || 0).toFixed(2) }}s
            </template>
          </template>
        </a-table>
      </template>
    </a-modal>
  </div>
</template>

<script lang="ts" setup>
  defineOptions({ name: 'RemoteTaskView' });
  import { ref, computed, watch, onUnmounted, nextTick } from 'vue';
  import { message } from 'ant-design-vue';
  import { getTaskStatus, getTaskLog, getTaskResult, downloadVideo } from '@/api/platform/distributed';
  import http from '@/api/platform/http';

  const props = defineProps({ taskId: { type: String, default: '' } });

  const PLATFORMS: Record<string, string> = {
    platform_a: '平台A',
    platform_b: '平台B',
    platform_d: '平台D',
    platform_c: '平台C',
  };
  function platformLabel(v?: string) {
    return (v && PLATFORMS[v]) || v || '-';
  }

  // ── 状态 ─────────────────────────────────────────────
  const taskInfo = ref<any>({ status: 'pending', progress: 0 });
  const errorText = ref('');
  const logError = ref('');

  // ── 日志 ─────────────────────────────────────────────
  const logLines = ref<string[]>([]);
  const logOffset = ref(0);
  const logTotal = ref(0);
  const logFinished = ref(false);
  const loadingLog = ref(false);
  const autoScroll = ref(true);
  const autoPoll = ref(true);
  const logBox = ref<HTMLElement | null>(null);

  // ── 结果 / 录屏 / 停止 ──────────────────────────────
  const resultVisible = ref(false);
  const testResult = ref<any>(null);
  const downloadingVideo = ref(false);
  const stopping = ref(false);

  let timer: ReturnType<typeof setInterval> | null = null;

  const active = computed(() => ['pending', 'running'].includes(taskInfo.value.status || ''));
  const isFinished = computed(() =>
    ['success', 'failed', 'stopped'].includes(taskInfo.value.status || ''),
  );
  const targetMachine = computed(() => {
    const parts = props.taskId.split('_');
    return parts.length >= 6 ? parts.slice(2, 6).join('.') : '未知';
  });
  const statusText = computed(
    () =>
      ({ pending: '等待中', running: '运行中', success: '成功', failed: '失败', stopped: '已停止' })[
        taskInfo.value.status || ''
      ] || taskInfo.value.status || '…',
  );
  const statusColor = computed(
    () =>
      ({ pending: 'default', running: 'processing', success: 'success', failed: 'error', stopped: 'warning' })[
        taskInfo.value.status || ''
      ] || 'default',
  );
  const progressStatus = computed(() => {
    if (taskInfo.value.status === 'success') return 'success';
    if (taskInfo.value.status === 'failed') return 'exception';
    if (taskInfo.value.status === 'running') return 'active';
    return 'normal';
  });
  const shortErr = computed(() => (errorText.value || '').slice(0, 120));
  const durationText = computed(() => {
    const s = taskInfo.value.started_at;
    if (!s) return '-';
    const end = taskInfo.value.finished_at || Date.now() / 1000;
    const t = Math.max(0, Math.floor(end - s));
    const m = Math.floor(t / 60);
    return m > 0 ? `${m}m ${t % 60}s` : `${t}s`;
  });
  const logText = computed(() => logLines.value.join(''));

  const resultColumns = [
    { title: '用例', dataIndex: 'nodeid', key: 'nodeid', ellipsis: true },
    { title: '结果', key: 'outcome', width: 100 },
    { title: '耗时', key: 'duration', width: 100 },
  ];
  const resultSummary = computed(() => {
    const s = testResult.value?.summary || {};
    return {
      total: s.total ?? 0,
      passed: s.passed ?? 0,
      failed: s.failed ?? 0,
      error: s.error ?? 0,
      skipped: s.skipped ?? 0,
    };
  });

  function fmtTime(ts: number) {
    if (!ts) return '-';
    return new Date(ts * 1000).toLocaleString('zh-CN', { hour12: false });
  }
  function outcomeColor(outcome: string) {
    return (
      { passed: 'success', failed: 'error', error: 'error', skipped: 'warning' }[outcome] ||
      'default'
    );
  }

  // ── 拉取（与任务详情页同构：状态 + 日志增量）────────────
  async function fetchStatus() {
    if (!props.taskId) return;
    try {
      const { data } = await getTaskStatus(props.taskId);
      taskInfo.value = data || {};
      errorText.value = data?.error || '';
    } catch (e: any) {
      errorText.value = e?.response?.data?.error || e?.message || '获取任务状态失败';
    }
  }

  async function fetchLog(reset = false) {
    if (!props.taskId || loadingLog.value) return;
    loadingLog.value = true;
    logError.value = '';
    try {
      if (reset) {
        logLines.value = [];
        logOffset.value = 0;
        logTotal.value = 0;
      }
      const res = await getTaskLog(props.taskId, logOffset.value, 500);
      const { lines, offset, total, finished } = res.data;
      if (lines?.length) logLines.value.push(...lines);
      logOffset.value = offset;
      logTotal.value = total;
      logFinished.value = finished;
      // 日志读完且任务结束：停止自动刷新
      if (finished) autoPoll.value = false;
      if (autoScroll.value && lines?.length) {
        await nextTick();
        if (logBox.value) logBox.value.scrollTop = logBox.value.scrollHeight;
      }
    } catch (e: any) {
      logError.value = e?.response?.data?.error || e?.message || '拉取日志失败';
    } finally {
      loadingLog.value = false;
    }
  }

  function startPolling() {
    if (timer) {
      clearInterval(timer);
      timer = null;
    }
    if (!autoPoll.value || !props.taskId) return;
    timer = setInterval(async () => {
      if (!autoPoll.value) return;
      await fetchStatus();
      await fetchLog();
    }, 2000);
  }

  function stopPolling() {
    if (timer) {
      clearInterval(timer);
      timer = null;
    }
  }

  // ── 操作：下载日志 / 查看结果 / 下载录屏 / 停止 ─────────
  function downloadLog() {
    const blob = new Blob([logText.value], { type: 'text/plain;charset=utf-8' });
    triggerDownload(blob, `${props.taskId}.log`);
  }

  async function viewResult() {
    try {
      const res = await getTaskResult(props.taskId);
      testResult.value = res.data;
      resultVisible.value = true;
    } catch (e: any) {
      message.error(e?.response?.data?.error || '获取结果失败');
    }
  }

  async function handleDownloadVideo() {
    downloadingVideo.value = true;
    try {
      const res = await downloadVideo(props.taskId);
      triggerDownload(new Blob([res.data], { type: 'video/mp4' }), `${props.taskId}.mp4`);
      message.success('开始下载');
    } catch {
      message.error('下载失败，可能该任务未录屏');
    } finally {
      downloadingVideo.value = false;
    }
  }

  async function stopTask() {
    stopping.value = true;
    try {
      const { data } = await http.post(`/tasks/${props.taskId}/cancel`);
      if (data.success) {
        message.success('已发送停止指令');
        await fetchStatus();
        await fetchLog();
      } else {
        message.error(data.error || '停止失败');
      }
    } catch (e: any) {
      message.error(e?.response?.data?.error || '停止失败');
    } finally {
      stopping.value = false;
    }
  }

  function triggerDownload(blob: Blob, filename: string) {
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  }

  // 任务 ID 变化：重置并立即拉取 + 启动轮询
  watch(
    () => props.taskId,
    (id) => {
      stopPolling();
      if (!id) return;
      logLines.value = [];
      logOffset.value = 0;
      logTotal.value = 0;
      logFinished.value = false;
      logError.value = '';
      autoPoll.value = true;
      fetchStatus();
      fetchLog();
      startPolling();
    },
    { immediate: true },
  );

  // 自动刷新开关：开→启动轮询，关→停表
  watch(autoPoll, (on) => {
    if (on) startPolling();
    else stopPolling();
  });

  onUnmounted(stopPolling);
</script>

<style scoped>
.remote-view {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.err-hint {
  margin-left: 8px;
  color: var(--error-color);
  font-size: 12px;
}
.mt-2 {
  margin-top: 8px;
}
.log-wrap {
  border: 1px solid var(--border-color);
  border-radius: 6px;
  overflow: hidden;
}
.log-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 8px 12px;
  border-bottom: 1px solid var(--border-color);
  flex-wrap: wrap;
}
.log-title {
  font-weight: 500;
}
/* 浅色日志背景 */
.log-body {
  max-height: 460px;
  overflow-y: auto;
  background: #f8f9fa;
}
.log-content {
  margin: 0;
  padding: 12px;
  font-family: Consolas, Monaco, 'Courier New', monospace;
  font-size: 12.5px;
  line-height: 1.6;
  color: #24292f;
  white-space: pre-wrap;
  word-break: break-all;
}
.log-foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 12px;
  border-top: 1px solid var(--border-color);
  font-size: 12px;
  color: var(--text-secondary);
}
.text-success {
  color: var(--success-color);
}
.text-danger {
  color: var(--error-color);
}
.mb-3 {
  margin-bottom: 12px;
}
</style>
