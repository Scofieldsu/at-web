<template>
  <a-card v-if="taskId" class="monitor-card theme-card">
    <template #title>
      <div class="card-header">
        <span>任务 <code>{{ taskId.slice(0, 8) }}…</code></span>
        <a-tag :color="tagType" size="small">{{ status || '...' }}</a-tag>
        <span v-if="name" class="task-name">{{ name }}</span>
      </div>
    </template>

    <!-- 步骤进度 -->
    <div v-if="steps.length" class="steps">
      <div v-for="(s, i) in steps" :key="i" class="step">
        <a-tag :color="stepTag(s.status)" size="small" class="step-tag">
          {{ s.status }}
        </a-tag>
        <span class="step-name">{{ s.name }}</span>
      </div>
    </div>

    <!-- 错误信息 -->
    <pre v-if="error" class="logs error">{{ error }}</pre>

    <!-- 结果摘要 -->
    <pre v-if="result" class="logs">{{ resultText }}</pre>

    <div v-if="!steps.length && !error && !result" class="empty">
      等待任务进度…
    </div>

    <!-- 服务端日志 -->
    <div v-if="taskId" class="server-log-section">
      <div class="log-header" @click="logExpanded = !logExpanded">
        <span class="log-title">📋 服务端日志 (app.log)</span>
        <a-tag color="default" size="small" class="log-line-count">{{ logLines }} 行</a-tag>
        <DownOutlined :class="{ rotated: logExpanded }" class="log-toggle" />
      </div>
      <div v-show="logExpanded" class="log-body-wrap">
        <pre ref="logContainerRef" class="logs server-log">{{ logContent || '等待日志…' }}</pre>
      </div>
    </div>
  </a-card>
</template>

<script lang="ts" setup>
  import { ref, watch, onUnmounted, computed, nextTick } from 'vue';
  import { DownOutlined } from '@ant-design/icons-vue';
  import http from '@/api/platform/http';

  const props = defineProps({ taskId: String });
  const status = ref('');
  const name = ref('');
  const steps = ref<any[]>([]);
  const result = ref<any>(null);
  const error = ref('');

  // 服务端日志状态
  const logContent = ref('');
  const logLines = ref(0);
  const logExpanded = ref(true);
  const logContainerRef = ref<any>(null);

  let timer: any = null;
  let logTimer: any = null;

  const tagType = computed(
    () =>
      ({ success: 'success', failed: 'error', running: 'warning', pending: 'default' }[
        status.value
      ] || 'default'),
  );

  const resultText = computed(() => {
    if (result.value == null) return '';
    try {
      return typeof result.value === 'string'
        ? result.value
        : JSON.stringify(result.value, null, 2);
    } catch {
      return String(result.value);
    }
  });

  function stepTag(s: string) {
    return (
      { success: 'success', failed: 'error', running: 'warning', skipped: 'default' }[s] || 'default'
    );
  }

  async function poll() {
    if (!props.taskId) return;
    try {
      const { data } = await http.get(`/tasks/${props.taskId}`);
      status.value = data.status;
      name.value = data.name || '';
      steps.value = data.steps || [];
      result.value = data.result ?? null;
      error.value = data.error || '';
      if (data.status === 'success' || data.status === 'failed') stop();
    } catch {
      /* 忽略轮询错误 */
    }
  }

  async function pollAppLog() {
    if (!props.taskId) return;
    try {
      const { data } = await http.get(`/cases/live-log/${props.taskId}`, {
        params: { tail: 200 },
        responseType: 'text',
      });
      const text = typeof data === 'string' ? data : JSON.stringify(data);
      logContent.value = text;
      logLines.value = text ? text.split('\n').length : 0;
      // 自动滚到底部
      await nextTick();
      if (logContainerRef.value) {
        logContainerRef.value.scrollTop = logContainerRef.value.scrollHeight;
      }
    } catch {
      /* 忽略日志轮询错误 */
    }
  }

  function stop() {
    if (timer) {
      clearInterval(timer);
      timer = null;
    }
    if (logTimer) {
      clearInterval(logTimer);
      logTimer = null;
    }
  }

  watch(
    () => props.taskId,
    (id) => {
      stop();
      steps.value = [];
      result.value = null;
      error.value = '';
      status.value = '';
      name.value = '';
      logContent.value = '';
      logLines.value = 0;
      logExpanded.value = true;
      if (id) {
        poll();
        pollAppLog();
        timer = setInterval(poll, 2000);
        logTimer = setInterval(pollAppLog, 3000);
      }
    },
    { immediate: true },
  );

  onUnmounted(stop);
</script>

<style scoped>
.monitor-card {
  margin-top: 16px;
  background: var(--bg-card-alt);
  border: 1px solid var(--border-color);
  color: var(--text-primary);
}
.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
}
.card-header code {
  color: var(--accent);
  font-size: 13px;
}
.task-name {
  color: var(--text-muted);
  font-size: 12px;
  margin-left: auto;
}
.steps {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-bottom: 10px;
}
.step {
  display: flex;
  align-items: center;
  gap: 8px;
}
.step-tag {
  min-width: 64px;
  text-align: center;
}
.step-name {
  color: var(--text-secondary);
  font-size: 13px;
}
.logs {
  background: #0d0f13;
  color: var(--text-secondary);
  padding: 12px;
  border-radius: 6px;
  max-height: 360px;
  overflow: auto;
  font-size: 12px;
  white-space: pre-wrap;
  margin: 0 0 8px 0;
  line-height: 1.6;
}
.logs.error {
  color: #f87171;
}
.empty {
  color: var(--text-muted);
  font-size: 13px;
}
.server-log-section {
  margin-top: 16px;
  border-top: 1px solid var(--border-color);
  padding-top: 8px;
}
.log-header {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  user-select: none;
  padding: 4px 0;
}
.log-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
}
.log-line-count {
  font-size: 11px;
}
.log-toggle {
  margin-left: auto;
  font-size: 14px;
  transition: transform 0.2s ease;
  color: var(--text-muted);
}
.log-toggle.rotated {
  transform: rotate(-180deg);
}
.log-body-wrap {
  margin-top: 4px;
}
.server-log {
  max-height: 480px;
  font-family: 'Cascadia Code', 'Fira Code', 'Consolas', monospace;
  font-size: 11px;
  line-height: 1.5;
}
</style>
