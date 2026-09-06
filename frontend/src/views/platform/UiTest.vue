<template>
  <!-- 可用操作 -->
  <a-card class="theme-card">
    <template #title>
      <div class="hdr">
        <span class="sec-title tint-indigo"><ThunderboltOutlined />可用操作 (/api/ui/actions)</span>
        <div>
          <a-button :loading="loadingActions" size="small" @click="loadActions">刷新</a-button>
          <a-button type="primary" ghost size="small" style="margin-left: 8px" @click="loadDemo">
            <MonitorOutlined /> 屏幕信息
          </a-button>
        </div>
      </div>
    </template>

    <a-table
      :data-source="actions"
      :columns="actionColumns"
      :pagination="false"
      row-key="name"
      class="theme-table"
      :scroll="{ y: 300 }"
      :locale="{ emptyText: '点「刷新」加载可用 UI 操作' }"
    >
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'params'">
          {{ Object.keys(record.params || {}).length }} 个
        </template>
        <template v-else-if="column.key === 'action'">
          <a-button size="small" type="primary" @click="selectAction(record.name)">选用</a-button>
        </template>
      </template>
    </a-table>
    <pre v-if="demoResult" class="json">{{ demoResult }}</pre>
  </a-card>

  <!-- 执行操作 -->
  <a-card class="theme-card" style="margin-top: 16px">
    <template #title><span class="sec-title tint-green"><PlayCircleOutlined />执行操作 (/api/ui/execute)</span></template>

    <a-form :label-col="{ style: { width: '170px' } }" label-align="left" layout="horizontal">
      <a-form-item label="操作 (action)">
        <a-select
          v-model:value="selectedAction"
          placeholder="选择操作"
          style="width: 280px"
          @change="onActionChange"
        >
          <a-select-option v-for="a in actions" :key="a.name" :value="a.name">
            {{ a.name }}
          </a-select-option>
        </a-select>
        <span v-if="currentDesc" class="desc">{{ currentDesc }}</span>
      </a-form-item>

      <!-- 动态参数表单：参数名完整展示 + 悬浮 tooltip（浅 info 蓝）提示 schema，输入框收窄 -->
      <template v-if="paramFields.length">
        <a-form-item v-for="f in paramFields" :key="f.key">
          <template #label>
            <a-tooltip
              :title="f.schema"
              placement="top"
              :overlay-inner-style="tooltipStyle"
            >
              <span class="param-label">{{ f.key }}</span>
            </a-tooltip>
          </template>
          <div class="param-row">
            <a-input v-model:value="paramValues[f.key]" :placeholder="f.key" class="param-input" />
            <a-button
              v-if="f.key === 'task_id' && lastTaskId"
              size="small"
              title="填入最近 task_id"
              @click="paramValues[f.key] = lastTaskId"
            >
              填入最近
            </a-button>
          </div>
        </a-form-item>
      </template>
      <div v-else-if="selectedAction" class="muted pad">该操作无参数</div>

      <a-form-item v-if="selectedAction">
        <a-button type="primary" :loading="executing" @click="execute">执行</a-button>
        <a-button :disabled="!selectedAction" @click="resetParams">重置参数</a-button>
        <span v-if="lastTaskId" class="muted" style="margin-left: 12px">
          最近 task_id: <code>{{ lastTaskId }}</code>
        </span>
      </a-form-item>
    </a-form>

    <pre v-if="execResult" class="json" :class="{ err: execError }">{{ execResult }}</pre>
  </a-card>
</template>

<script lang="ts" setup>
  defineOptions({ name: 'UiTest' });
  import { ref, computed, reactive, onMounted } from 'vue';
  import { ThunderboltOutlined, PlayCircleOutlined, MonitorOutlined } from '@ant-design/icons-vue';
  import { message } from 'ant-design-vue';
  import http from '@/api/platform/http';

  const actions = ref<any[]>([]);
  const loadingActions = ref(false);
  const demoResult = ref('');

  // 参数名悬浮提示样式：浅 info 蓝背景 + 深色小字（与目标连接提示同风格）
  const tooltipStyle = {
    background: 'rgba(0, 144, 255, 0.06)',
    color: '#1c2024',
    border: '1px solid rgba(0, 144, 255, 0.25)',
    borderRadius: '6px',
    fontSize: '12px',
    lineHeight: '1.6',
  };

  const selectedAction = ref('');
  const paramValues = reactive<any>({});
  const executing = ref(false);
  const execResult = ref('');
  const execError = ref(false);
  const lastTaskId = ref('');

  const actionColumns = [
    { title: '操作名', dataIndex: 'name', key: 'name', width: 160 },
    { title: '说明', dataIndex: 'description', key: 'description', minWidth: 280 },
    { title: '参数', key: 'params', width: 100 },
    { title: '操作', key: 'action', width: 100, fixed: 'right' },
  ];

  const currentAction = computed(() => actions.value.find((a) => a.name === selectedAction.value));
  const currentDesc = computed(() => currentAction.value?.description || '');
  const paramFields = computed(() => {
    const p = currentAction.value?.params || {};
    return Object.entries(p).map(([key, schema]) => ({ key, schema }));
  });

  async function loadActions() {
    loadingActions.value = true;
    try {
      const { data } = await http.get('/ui/actions');
      actions.value = Array.isArray(data) ? data : [];
    } catch (e) {
      message.error('加载操作列表失败');
    } finally {
      loadingActions.value = false;
    }
  }

  async function loadDemo() {
    try {
      const { data } = await http.get('/ui/demo');
      demoResult.value = JSON.stringify(data, null, 2);
    } catch (e) {
      message.error('获取屏幕信息失败');
    }
  }

  function selectAction(name: string) {
    selectedAction.value = name;
    onActionChange();
  }

  function onActionChange() {
    // 清空并按当前 action 的默认参数重新初始化（无默认值则留空，由用户填）
    Object.keys(paramValues).forEach((k) => delete paramValues[k]);
    const defaults = currentAction.value?.defaults || {};
    for (const f of paramFields.value) {
      const d = defaults[f.key];
      paramValues[f.key] = d === undefined || d === null ? '' : String(d);
    }
  }

  function resetParams() {
    onActionChange();
  }

  // 智能解析：纯数字 → number，JSON → 对象/数组，其余 → 字符串；空值忽略
  function coerce(raw: any) {
    if (raw === '' || raw == null) return undefined;
    const s = String(raw).trim();
    if (/^-?\d+(\.\d+)?$/.test(s)) return Number(s);
    if (/^[[{]/.test(s)) {
      try {
        return JSON.parse(s);
      } catch {
        /* fall through */
      }
    }
    return raw;
  }

  async function execute() {
    const params: any = {};
    for (const [k, v] of Object.entries(paramValues)) {
      const val = coerce(v);
      if (val !== undefined) params[k] = val;
    }
    executing.value = true;
    execError.value = false;
    try {
      const { data } = await http.post('/ui/execute', { action: selectedAction.value, params });
      execResult.value = JSON.stringify(data, null, 2);
      execError.value = data && data.success === false;
      // 记住返回的 task_id，方便后续 stop_test / test_status 复用
      if (data && data.task_id) lastTaskId.value = data.task_id;
      if (data && data.success === false) {
        message.error(data.error || '执行返回失败');
      } else {
        message.success('执行完成');
      }
    } catch (e: any) {
      execError.value = true;
      execResult.value = JSON.stringify(e.response?.data || { error: String(e) }, null, 2);
      message.error(e.response?.data?.error || '执行请求失败');
    } finally {
      executing.value = false;
    }
  }

  onMounted(loadActions);
</script>

<style scoped>
.hdr {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.desc {
  margin-left: 12px;
  color: var(--text-muted);
  font-size: var(--vben-font-size-base);
}
.param-row {
  display: flex;
  gap: 8px;
  width: 100%;
  align-items: center;
}
/* 参数名：完整展示 + 悬浮提示光标 */
.param-label {
  display: inline-block;
  white-space: nowrap;
  cursor: help;
  color: var(--text-primary);
}
/* 输入框收窄：参数多为数字/短字符串，无需超长输入框 */
.param-input {
  width: 260px;
}
.muted {
  color: var(--text-muted);
}
.pad {
  padding: 12px;
}
code {
  color: var(--accent);
}
.json {
  background: #f5f6f8;
  color: var(--text-primary);
  padding: 12px;
  border-radius: 6px;
  border: 1px solid var(--border-color);
  max-height: 320px;
  overflow: auto;
  font-size: var(--vben-font-size-sm);
  white-space: pre-wrap;
  margin: 12px 0 0 0;
  line-height: 1.6;
}
.json.err {
  color: var(--error-color);
}
</style>
