<template>
  <div class="page">
    <!-- 任务信息 -->
    <a-card class="theme-card">
      <div class="task-header">
        <span class="task-title">{{ taskInfo.name || taskId }}</span>
        <a-tag :color="statusColor">{{ statusText }}</a-tag>
      </div>

      <a-descriptions :column="3" bordered size="small" class="mt-3">
        <a-descriptions-item label="任务 ID">{{ taskId }}</a-descriptions-item>
        <a-descriptions-item label="执行机器">{{ targetMachine }}</a-descriptions-item>
        <a-descriptions-item label="平台">
          {{ taskInfo.platform || '-' }}
        </a-descriptions-item>
        <a-descriptions-item label="开始时间">
          {{ taskInfo.started_at ? formatTime(taskInfo.started_at) : '-' }}
        </a-descriptions-item>
        <a-descriptions-item label="结束时间">
          {{ taskInfo.finished_at ? formatTime(taskInfo.finished_at) : '-' }}
        </a-descriptions-item>
        <a-descriptions-item label="耗时">{{ duration }}</a-descriptions-item>
        <a-descriptions-item label="退出码">
          {{ taskInfo.exit_code === null ? '-' : taskInfo.exit_code }}
        </a-descriptions-item>
        <a-descriptions-item label="用例数">
          {{ taskInfo.cases?.length ?? 0 }}
        </a-descriptions-item>
        <a-descriptions-item label="进度">
          <a-progress :percent="taskInfo.progress || 0" :status="progressStatus" />
        </a-descriptions-item>
      </a-descriptions>

      <a-alert
        v-if="taskInfo.error"
        type="error"
        show-icon
        class="mt-3"
        :message="taskInfo.error"
      />
    </a-card>

    <!-- 实时日志 -->
    <a-card class="theme-card">
      <template #title><span class="sec-title tint-blue"><FileSearchOutlined />实时日志</span></template>
      <template #extra>
        <a-space>
          <a-checkbox v-model:checked="autoScroll">自动滚动</a-checkbox>
          <a-checkbox v-model:checked="autoPoll">自动刷新 (2s)</a-checkbox>
          <a-button size="small" :loading="loadingLog" @click="fetchLog">
            刷新
          </a-button>
        </a-space>
      </template>

      <div ref="logBox" class="log-container">
        <pre class="log-content">{{ logText || '暂无日志输出…' }}</pre>
      </div>

      <div class="log-footer">
        已加载 {{ logLines.length }} / {{ logTotal }} 行
        <span v-if="logFinished" class="text-success">（任务已结束）</span>
      </div>
    </a-card>

    <!-- 操作 -->
    <a-card class="theme-card">
      <a-space wrap>
        <a-button :disabled="!logLines.length" @click="downloadLog">
          下载日志
        </a-button>
        <a-button
          type="primary"
          :disabled="!isFinished"
          @click="viewResult"
        >
          查看结果
        </a-button>
        <a-button
          :loading="downloadingVideo"
          :disabled="!isFinished"
          @click="handleDownloadVideo"
        >
          下载录屏
        </a-button>
        <a-button @click="router.push('/prepare/machines')">
          返回机器列表
        </a-button>
      </a-space>
    </a-card>

    <!-- 结果详情 -->
    <a-modal v-model:open="resultVisible" title="测试结果" width="80%" :footer="null">
      <template v-if="testResult">
        <a-descriptions bordered :column="3" size="small" class="mb-3">
          <a-descriptions-item label="总用例">
            {{ resultSummary.total }}
          </a-descriptions-item>
          <a-descriptions-item label="通过">
            <span class="text-success">{{ resultSummary.passed }}</span>
          </a-descriptions-item>
          <a-descriptions-item label="失败">
            <span class="text-danger">{{ resultSummary.failed }}</span>
          </a-descriptions-item>
          <a-descriptions-item label="错误">
            {{ resultSummary.error }}
          </a-descriptions-item>
          <a-descriptions-item label="跳过">
            {{ resultSummary.skipped }}
          </a-descriptions-item>
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
  defineOptions({ name: 'DistributedMonitor' });
  import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue';
  import { FileSearchOutlined } from '@ant-design/icons-vue';
  import { useRouter, useRoute } from 'vue-router';
  import { message } from 'ant-design-vue';
  import {
    getTaskStatus,
    getTaskLog,
    getTaskResult,
    downloadVideo,
  } from '@/api/platform/distributed';
  import type { TaskStatus } from '@/api/platform/distributed';

  const router = useRouter();
  const route = useRoute();
  const taskId = route.params.id as string;

  const taskInfo = ref<Partial<TaskStatus>>({
    task_id: taskId,
    status: 'pending',
    progress: 0,
    exit_code: null,
    cases: [],
  });

  const logLines = ref<string[]>([]);
  const logOffset = ref(0);
  const logTotal = ref(0);
  const logFinished = ref(false);
  const autoScroll = ref(true);
  const autoPoll = ref(true);
  const loadingLog = ref(false);
  const logBox = ref<HTMLElement | null>(null);

  const resultVisible = ref(false);
  const testResult = ref<any>(null);
  const downloadingVideo = ref(false);

  let timer: ReturnType<typeof setInterval> | null = null;

  const resultColumns = [
    { title: '用例', dataIndex: 'nodeid', key: 'nodeid', ellipsis: true },
    { title: '结果', key: 'outcome', width: 100 },
    { title: '耗时', key: 'duration', width: 100 },
  ];

  // task_1724582400_10_0_0_20 → 10.0.0.20
  const targetMachine = computed(() => {
    const parts = taskId.split('_');
    return parts.length >= 6 ? parts.slice(2, 6).join('.') : '未知';
  });

  const isFinished = computed(() =>
    ['success', 'failed', 'stopped'].includes(taskInfo.value.status || ''),
  );

  const statusText = computed(
    () =>
      ({
        pending: '等待中',
        running: '运行中',
        success: '成功',
        failed: '失败',
        stopped: '已停止',
      })[taskInfo.value.status || ''] || taskInfo.value.status,
  );

  const statusColor = computed(
    () =>
      ({
        pending: 'default',
        running: 'processing',
        success: 'success',
        failed: 'error',
        stopped: 'warning',
      })[taskInfo.value.status || ''] || 'default',
  );

  const progressStatus = computed(() => {
    if (taskInfo.value.status === 'success') return 'success';
    if (taskInfo.value.status === 'failed') return 'exception';
    if (taskInfo.value.status === 'running') return 'active';
    return 'normal';
  });

  const duration = computed(() => {
    if (!taskInfo.value.started_at) return '-';
    const end = taskInfo.value.finished_at || Date.now() / 1000;
    const total = Math.max(0, Math.floor(end - taskInfo.value.started_at));
    const m = Math.floor(total / 60);
    const h = Math.floor(m / 60);
    if (h > 0) return `${h}h ${m % 60}m ${total % 60}s`;
    if (m > 0) return `${m}m ${total % 60}s`;
    return `${total}s`;
  });

  const logText = computed(() => logLines.value.join(''));

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

  // ── 轮询 ──────────────────────────────────────────────────

  async function fetchStatus() {
    try {
      const res = await getTaskStatus(taskId);
      taskInfo.value = res.data;
    } catch {
      // 网络抖动不打断轮询，下一拍会重试
    }
  }

  async function fetchLog() {
    loadingLog.value = true;
    try {
      const res = await getTaskLog(taskId, logOffset.value);
      const { lines, offset, total, finished } = res.data;
      if (lines?.length) logLines.value.push(...lines);
      logOffset.value = offset;
      logTotal.value = total;
      logFinished.value = finished;

      if (autoScroll.value && lines?.length) {
        await nextTick();
        if (logBox.value) logBox.value.scrollTop = logBox.value.scrollHeight;
      }

      // 后端只在「日志读完 + 任务终态」时才返回 finished，此时停止轮询不会丢尾部
      if (finished) autoPoll.value = false;
    } catch {
      // 同上：静默重试
    } finally {
      loadingLog.value = false;
    }
  }

  function startPolling() {
    if (timer) return;
    timer = setInterval(async () => {
      if (!autoPoll.value) return;
      await fetchStatus();
      await fetchLog();
    }, 2000);
  }

  // ── 操作 ──────────────────────────────────────────────────

  function downloadLog() {
    const blob = new Blob([logText.value], { type: 'text/plain;charset=utf-8' });
    triggerDownload(blob, `${taskId}.log`);
  }

  async function viewResult() {
    try {
      const res = await getTaskResult(taskId);
      testResult.value = res.data;
      resultVisible.value = true;
    } catch (e: any) {
      message.error(e?.response?.data?.error || '获取结果失败');
    }
  }

  async function handleDownloadVideo() {
    downloadingVideo.value = true;
    try {
      const res = await downloadVideo(taskId);
      triggerDownload(new Blob([res.data], { type: 'video/mp4' }), `${taskId}.mp4`);
      message.success('开始下载');
    } catch (e: any) {
      message.error('下载失败，可能该任务未录屏');
    } finally {
      downloadingVideo.value = false;
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

  function formatTime(ts: number) {
    return new Date(ts * 1000).toLocaleString();
  }

  function outcomeColor(outcome: string) {
    return (
      { passed: 'success', failed: 'error', error: 'error', skipped: 'warning' }[
        outcome
      ] || 'default'
    );
  }

  onMounted(async () => {
    await fetchStatus();
    await fetchLog();
    startPolling();
  });

  onUnmounted(() => {
    if (timer) clearInterval(timer);
  });
</script>

<style lang="less" scoped>
  .page {
    padding: 16px;
  }

  .theme-card {
    margin-bottom: 16px;
  }

  .task-header {
    display: flex;
    gap: 12px;
    align-items: center;
  }

  .task-title {
    font-size: 18px;
    font-weight: 600;
  }

  .log-container {
    height: 560px;
    padding: 12px;
    overflow-y: auto;
    background: #1e1e1e;
    border-radius: 4px;
  }

  .log-content {
    margin: 0;
    font-family: Consolas, Monaco, 'Courier New', monospace;
    font-size: 12.5px;
    line-height: 1.6;
    color: #d4d4d4;
    white-space: pre-wrap;
    word-break: break-all;
  }

  .log-footer {
    margin-top: 10px;
    font-size: var(--vben-font-size-sm);
    color: var(--text-secondary);
  }

  .text-success {
    color: var(--success-color);
  }

  .text-danger {
    color: var(--error-color);
  }

  .mt-3 {
    margin-top: 12px;
  }

  .mb-3 {
    margin-bottom: 12px;
  }
</style>
