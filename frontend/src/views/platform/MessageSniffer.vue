<template>
  <a-card class="theme-card fill-card">
    <template #title>
      <div class="hdr">
        <span class="sec-title tint-orange"><RadarChartOutlined />消息嗅探</span>
        <div class="hdr-tools">
          <a-select
            v-model:value="filter.direction"
            style="width: 160px"
            placeholder="方向"
            allow-clear
            @change="onFilterChange"
          >
            <a-select-option value="client_to_server">↑ 客户端→服务端</a-select-option>
            <a-select-option value="server_to_client">↓ 服务端→客户端</a-select-option>
          </a-select>
          <a-select
            v-model:value="filter.type"
            style="width: 200px"
            placeholder="消息类型"
            allow-clear
            show-search
            @change="onFilterChange"
          >
            <a-select-option v-for="t in typeOptions" :key="t" :value="t">
              {{ t }}
            </a-select-option>
          </a-select>
          <a-select
            v-model:value="filter.flow_id"
            style="width: 160px"
            placeholder="Flow ID"
            allow-clear
            @change="onFilterChange"
          >
            <a-select-option v-for="f in activeFlows" :key="f.flow_id" :value="f.flow_id">
              {{ String(f.flow_id).slice(0, 8) }}
            </a-select-option>
          </a-select>

          <a-switch v-model:checked="realTimeMode" checked-children="实时" un-checked-children="轮询" @change="onModeChange" />
          <a-badge v-if="realTimeMode" :count="liveCount" :overflow-count="999" style="margin: 0 8px">
            <a-tag color="processing">LIVE</a-tag>
          </a-badge>
          <a-button :loading="loading" size="small" @click="fetchMessages">刷新</a-button>
          <a-button size="small" danger @click="clearMessages">清空</a-button>
        </div>
      </div>
    </template>

    <div class="table-wrap">
      <a-table
        :data-source="filteredMessages"
        :columns="msgColumns"
        row-key="idx"
        size="small"
        bordered
        class="theme-table"
        :scroll="{ y: 'calc(100vh - 280px)' }"
        :pagination="{ pageSize: 50, size: 'small', showTotal: (t) => `共 ${filteredMessages.length} 条` }"
        :locale="{ emptyText: realTimeMode ? '等待实时消息中…' : '暂无消息，点「刷新」获取' }"
        @expand="onExpand"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'direction'">
            <a-tag :color="isReport(record) ? 'blue' : 'green'" size="small">
              {{ isReport(record) ? '↑ 客户端→服务端' : '↓ 服务端→客户端' }}
            </a-tag>
          </template>
          <template v-if="column.key === 'time'">
            {{ fmtTime(record.time) }}
          </template>
          <template v-if="column.key === 'type'">
            <code class="msg-type">{{ extractType(record) }}</code>
          </template>
          <template v-if="column.key === 'flow_id'">
            <code class="flow-id">{{ record.flow_id ? String(record.flow_id).slice(0, 8) + '…' : '-' }}</code>
          </template>
          <template v-if="column.key === 'preview'">
            <span class="preview" :title="extractPreview(record)">{{ extractPreview(record) }}</span>
          </template>
          <template v-if="column.key === 'action'">
            <a-button size="small" @click="copyRaw(record)">复制</a-button>
            <a-button size="small" style="margin-left: 4px" @click="sendToInject(record)">注入</a-button>
          </template>
        </template>
        <template #expandedRowRender="{ record }">
          <pre class="raw-json" v-html="highlightJson(formatContent(record))"></pre>
        </template>
      </a-table>
    </div>
  </a-card>
</template>

<script lang="ts" setup>
  defineOptions({ name: 'MessageSniffer' });
  import { ref, computed, reactive, onMounted, onUnmounted } from 'vue';
  import { message } from 'ant-design-vue';
  import { RadarChartOutlined } from '@ant-design/icons-vue';
  import { useRouter } from 'vue-router';
  import http from '@/api/platform/http';
  import { highlightJson } from '@/utils/jsonHighlight';

  const router = useRouter();

  const messages = ref<any[]>([]);
  const loading = ref(false);
  const realTimeMode = ref(false);
  const liveCount = ref(0);
  const activeFlows = ref<any[]>([]);
  const eventSource = ref<EventSource | null>(null);
  const expandedRows = ref<string[]>([]);

  let idxCounter = 0;
  let pollTimer: any = null;

  const filter = reactive<any>({
    direction: undefined,
    type: undefined,
    flow_id: undefined,
  });

  const msgColumns = [
    { title: '时间', key: 'time', width: 160 },
    { title: '方向', key: 'direction', width: 110 },
    { title: 'Flow', key: 'flow_id', width: 100 },
    { title: '类型', key: 'type', width: 160 },
    { title: '内容预览', key: 'preview', ellipsis: true },
    { title: '操作', key: 'action', width: 130, fixed: 'right' },
  ];

  /** 消息类型下拉候选：从嗅探到的所有消息的类型中去重展示（随新消息实时更新） */
  const typeOptions = computed(() => {
    const set = new Set<string>();
    for (const m of messages.value) {
      const t = m.type || extractType(m) || '';
      if (t) set.add(t);
    }
    return [...set].sort();
  });

  const filteredMessages = computed(() => {
    let list = messages.value;
    if (filter.direction) {
      // addon 记录用 direction 字段（client_to_server = RPA 上报 / server_to_client = 下发）
      list = list.filter((m) => m.direction === filter.direction);
    }
    if (filter.type) {
      const kw = filter.type.toLowerCase();
      list = list.filter((m) => {
        const t = (m.type || extractType(m) || '').toLowerCase();
        return t === kw;
      });
    }
    if (filter.flow_id) {
      list = list.filter((m) => String(m.flow_id) === String(filter.flow_id));
    }
    return list;
  });

  function fmtTime(ts: number | string) {
    if (!ts) return '-';
    const d = typeof ts === 'number' ? new Date(ts * 1000) : new Date(ts);
    return d.toLocaleTimeString('zh-CN', { hour12: false }) + '.' + String(d.getMilliseconds()).padStart(3, '0');
  }

  /** 是否 RPA→服务端 上报方向（client_to_server） */
  function isReport(record: any) {
    return record.direction === 'client_to_server';
  }

  function extractType(record: any) {
    if (record.type) return record.type;
    if (record.message_data && record.message_data.type) return record.message_data.type;
    const raw = record.content || record.raw || record.message_data;
    if (raw && typeof raw === 'object') {
      // addon 记录 content 是已解析对象时，直接取 type
      return raw.type || '';
    }
    if (typeof raw === 'string') {
      try {
        const parsed = JSON.parse(raw);
        return parsed.type || '';
      } catch { /* */ }
    }
    return '';
  }

  function extractPreview(record: any) {
    const raw = record.content || record.raw || record.message_data;
    if (typeof raw === 'object' && raw !== null) {
      const str = JSON.stringify(raw);
      return str.length > 120 ? str.slice(0, 120) + '…' : str;
    }
    const s = String(raw || '');
    return s.length > 120 ? s.slice(0, 120) + '…' : s;
  }

  function formatContent(record: any) {
    const raw = record.content || record.raw || record.message_data;
    if (typeof raw === 'object' && raw !== null) return JSON.stringify(raw, null, 2);
    if (typeof raw === 'string') {
      try {
        return JSON.stringify(JSON.parse(raw), null, 2);
      } catch { /* */ }
    }
    return String(raw || '');
  }

  function onExpand(expanded: boolean, record: any) {
    const id = String(record.idx);
    if (expanded) {
      if (!expandedRows.value.includes(id)) expandedRows.value.push(id);
    } else {
      expandedRows.value = expandedRows.value.filter((x) => x !== id);
    }
  }

  function onFilterChange() {
    // 展开的自动收起，没啥特别处理
  }

  function copyRaw(record: any) {
    const text = formatContent(record);
    navigator.clipboard.writeText(text).then(() => {
      message.success('已复制到剪贴板');
    }).catch(() => {
      message.warning('复制失败，请手动选择复制');
    });
  }

  function sendToInject(record: any) {
    // 跳转到注入页面，把消息内容通过 query 传递
    try {
      const raw = record.content || record.raw || record.message_data;
      const jsonStr = typeof raw === 'object' ? JSON.stringify(raw) : raw;
      // 存到 sessionStorage 让注入页面读取
      sessionStorage.setItem('_inject_payload', jsonStr);
      if (record.flow_id) {
        sessionStorage.setItem('_inject_flow_id', String(record.flow_id));
      }
      message.success('已跳转到注入页面');
      router.push('/message/inject');
    } catch { /* */ }
  }

  // ── 轮询模式 ──
  async function fetchMessages() {
    loading.value = true;
    try {
      const { data } = await http.get('/ui/messages', { params: { limit: 200 } });
      if (Array.isArray(data)) {
        // 保留已有的展开状态
        messages.value = data.map((m, i) => ({
          ...m,
          idx: ++idxCounter,
          _key: `msg-${idxCounter}-${Date.now()}`,
        }));
      }
    } catch (e: any) {
      if (!realTimeMode.value) message.error('获取消息失败');
    } finally {
      loading.value = false;
    }
  }

  // ── 实时 SSE 模式 ──
  function connectSSE() {
    const proto = window.location.protocol === 'https:' ? 'https' : 'http';
    const host = window.location.host;
    const url = `${proto}://${host}/api/ui/events`;
    const es = new EventSource(url);
    eventSource.value = es;

    es.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        const record = {
          ...data,
          idx: ++idxCounter,
          from_client: data.direction === 'client_to_server',
          time: Date.now() / 1000,
        };
        messages.value.unshift(record);
        if (messages.value.length > 500) messages.value.length = 500;
        liveCount.value = messages.value.length;
      } catch { /* */ }
    };

    es.onerror = () => {
      // EventSource 会自动重连
    };
  }

  function disconnectSSE() {
    if (eventSource.value) {
      eventSource.value.close();
      eventSource.value = null;
    }
    if (pollTimer) {
      clearInterval(pollTimer);
      pollTimer = null;
    }
  }

  // ── 模式切换 ──
  function onModeChange(mode: boolean) {
    disconnectSSE();
    if (mode) {
      // 实时模式：先用 SSE，若不行回退到轮询
      try {
        connectSSE();
        // 5s 后检查 SSE 是否真的连上了
        setTimeout(() => {
          if (eventSource.value?.readyState !== EventSource.OPEN) {
            // fallback to polling
            pollTimer = setInterval(fetchMessages, 3000);
            message.warning('SSE 连接失败，已切换到轮询模式');
          }
        }, 5000);
      } catch {
        pollTimer = setInterval(fetchMessages, 3000);
      }
    } else {
      fetchMessages();
    }
  }

  function clearMessages() {
    messages.value = [];
    liveCount.value = 0;
    message.success('已清空');
  }

  async function loadFlows() {
    try {
      const { data } = await http.get('/proxy/flows');
      activeFlows.value = Array.isArray(data) ? data : [];
    } catch { /* 忽略 */ }
  }

  onMounted(() => {
    fetchMessages();
    loadFlows();
  });

  onUnmounted(() => {
    disconnectSSE();
  });
</script>

<style scoped>
.hdr {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.hdr-tools {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.muted {
  color: var(--text-muted);
}
.table-wrap {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}
.table-wrap :deep(.ant-table) {
  flex: 1;
}
.preview {
  font-size: var(--vben-font-size-sm);
  color: var(--text-secondary);
  font-family: 'SF Mono', 'Consolas', monospace;
}
.raw-json {
  background: #f5f6f8;
  color: var(--text-primary);
  padding: 12px;
  border-radius: 6px;
  border: 1px solid var(--border-color);
  font-size: var(--vben-font-size-sm);
  white-space: pre-wrap;
  line-height: 1.6;
  text-align: left;
  max-height: 400px;
  overflow: auto;
  margin: 0;
}
/* JSON 高亮着色（系统色板） */
.raw-json :deep(.jv-key) {
  color: var(--accent);
  font-weight: 500;
}
.raw-json :deep(.jv-string) {
  color: var(--success-color);
}
.raw-json :deep(.jv-number) {
  color: var(--warning-color);
}
.raw-json :deep(.jv-bool) {
  color: var(--info-color);
}
.raw-json :deep(.jv-null) {
  color: var(--error-color);
}
.msg-type {
  font-size: var(--vben-font-size-sm);
  color: var(--accent);
}
.flow-id {
  font-size: var(--vben-font-size-sm);
  color: var(--text-muted);
}
/* 卡片撑满页面 */
.fill-card {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  flex-direction: column;
}
.fill-card > .ant-card-head { flex-shrink: 0; }
.fill-card > .ant-card-body {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
  padding-bottom: 8px;
  overflow: hidden;
}
</style>
