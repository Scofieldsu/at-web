<template>
  <a-card class="theme-card">
    <div class="toolbar">
      <div class="mode-tabs">
        <span
          class="mode-tab tab-local"
          :class="{ 'is-active': mode === 'local' }"
          @click="mode = 'local'"
        >
          <DesktopOutlined /> 本机任务
        </span>
        <span
          class="mode-tab tab-remote"
          :class="{ 'is-active': mode === 'remote' }"
          @click="mode = 'remote'"
        >
          <CloudServerOutlined /> 远程任务
        </span>
      </div>
      <a-button :loading="loading" @click="refresh">刷新</a-button>

      <template v-if="mode === 'local'">
        <a-select
          v-model:value="filterStatus"
          placeholder="按状态筛选"
          allow-clear
          style="width: 150px"
          @change="refresh"
        >
          <a-select-option value="pending">pending</a-select-option>
          <a-select-option value="running">running</a-select-option>
          <a-select-option value="success">success</a-select-option>
          <a-select-option value="failed">failed</a-select-option>
        </a-select>
        <span class="hint">本机（控制台所在机器）执行的任务记录</span>
      </template>
      <span v-else class="hint">本控制台提交 / 定时触发的各执行机任务记录</span>

      <a-checkbox v-model:checked="autoRefresh">自动刷新 (3s)</a-checkbox>
    </div>

    <!-- 本机任务（原任务监控，详情走 TaskMonitor） -->
    <a-table
      v-if="mode === 'local'"
      :data-source="tasks"
      :columns="columns"
      :pagination="false"
      row-key="id"
      size="small"
      bordered
      class="theme-table"
      style="margin-top: 12px"
      :scroll="{ y: 280 }"
      :custom-row="(record) => ({ onClick: () => openDetail(record, 'local') })"
      :locale="{ emptyText: '暂无任务' }"
    >
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'id'">
          <code>{{ record.id.slice(0, 8) }}…</code>
        </template>
        <template v-else-if="column.key === 'status'">
          <a-tag :color="tagType(record.status)" size="small">{{ record.status }}</a-tag>
        </template>
        <template v-else-if="column.key === 'created_at'">
          {{ fmtTime(record.created_at) }}
        </template>
        <template v-else-if="column.key === 'action'">
          <a-button
            v-if="record.status === 'pending' || record.status === 'running'"
            size="small"
            danger
            @click.stop="cancel(record.id)"
          >
            取消
          </a-button>
          <a-button size="small" @click.stop="openDetail(record, 'local')">详情</a-button>
        </template>
      </template>
    </a-table>

    <!-- 远程任务（分页展示，避免滚动条） -->
    <a-table
      v-else
      :data-source="remoteTasks"
      :columns="remoteColumns"
      :pagination="remotePagination"
      row-key="task_id"
      size="small"
      bordered
      class="theme-table"
      style="margin-top: 12px"
      :locale="{ emptyText: '暂无远程任务（在本控制台提交任务 / 定时触发后会记录在这里）' }"
    >
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'task_id'">
          <code>{{ shortId(record.task_id) }}</code>
        </template>
        <template v-else-if="column.key === 'name'">
          <span :title="record.name || ''">{{ record.name || '-' }}</span>
        </template>
        <template v-else-if="column.key === 'platform'">
          {{ platformLabel(record.platform) }}
        </template>
        <template v-else-if="column.key === 'machine'">
          <code>{{ record.machine }}</code>
        </template>
        <template v-else-if="column.key === 'cases'">
          {{ record.case_count ?? '-' }}
        </template>
        <template v-else-if="column.key === 'status'">
          <a-tag :color="tagType(record.status)" size="small">{{ record.status }}</a-tag>
          <div v-if="record.error" class="text-xs text-danger" :title="String(record.error)">
            {{ String(record.error).slice(0, 80) }}
          </div>
        </template>
        <template v-else-if="column.key === 'created_at'">
          {{ fmtTime(record.created_at) }}
        </template>
        <template v-else-if="column.key === 'action'">
          <a-space :size="4">
            <a-button size="small" @click.stop="openDetail(record, 'remote')">详情</a-button>
            <a-popconfirm
              v-if="record.status === 'running' || record.status === 'pending'"
              title="停止该远程任务？将终止执行机上的任务进程。"
              @confirm="cancel(record.task_id)"
            >
              <a-button size="small" danger>停止</a-button>
            </a-popconfirm>
            <a-popconfirm
              title="仅从列表移除记录，不会停止执行机上的真实任务。"
              @confirm="removeRemoteRecord(record)"
            >
              <a-button size="small" type="text">移除记录</a-button>
            </a-popconfirm>
          </a-space>
        </template>
      </template>
    </a-table>
  </a-card>

  <!-- 详情抽屉：本机用 TaskMonitor，远程用 RemoteTaskView（含停止/完整详情） -->
  <a-drawer
    v-model:open="drawerOpen"
    :title="drawerTitle"
    :width="drawerWidth"
    :footer="null"
  >
    <template v-if="detailKind === 'local'">
      <TaskMonitor :task-id="drawerId" />
    </template>
    <RemoteTaskView v-else-if="detailKind === 'remote' && drawerId" :task-id="drawerId" />
  </a-drawer>
</template>

<script lang="ts" setup>
  defineOptions({ name: 'Tasks' });
  import { ref, computed, watch, onMounted, onUnmounted } from 'vue';
  import { useRoute } from 'vue-router';
  import { message } from 'ant-design-vue';
  import { DesktopOutlined, CloudServerOutlined } from '@ant-design/icons-vue';
  import http from '@/api/platform/http';
  import TaskMonitor from '@/components/platform/TaskMonitor.vue';
  import RemoteTaskView from '@/components/platform/RemoteTaskView.vue';

  const route = useRoute();

  // 记录维度：本机任务 / 远程任务
  const mode = ref<'local' | 'remote'>('local');

  // ── 本机任务 ─────────────────────────────────────────
  const tasks = ref<any[]>([]);

  // ── 详情抽屉 ─────────────────────────────────────────
  const drawerOpen = ref(false);
  const drawerId = ref('');
  const detailKind = ref<'local' | 'remote'>('local');
  // 抽屉宽度：按窗口自适应（上限 1280），保证远程详情完整展示
  const drawerWidth = ref(1280);
  const drawerTitle = computed(() =>
    detailKind.value === 'local' ? '本机任务详情' : '远程任务详情',
  );

  // ── 远程任务（Master 索引）───────────────────────────
  const remoteTasks = ref<any[]>([]);

  const loading = ref(false);
  const filterStatus = ref('');
  const autoRefresh = ref(false);
  let timer: any = null;

  const PLATFORMS: Record<string, string> = {
    platform_a: '平台A',
    platform_b: '平台B',
    platform_d: '平台D',
    platform_c: '平台C',
  };
  function platformLabel(v: string) {
    return PLATFORMS[v] || v || '通用';
  }

  const columns = [
    { title: 'ID', key: 'id', width: 120 },
    { title: '名称', dataIndex: 'name', key: 'name', minWidth: 240, ellipsis: true },
    { title: '状态', key: 'status', width: 110 },
    { title: '创建时间', key: 'created_at', width: 170 },
    { title: '操作', key: 'action', width: 180, fixed: 'right' },
  ];

  const remoteColumns = [
    { title: 'ID', key: 'task_id', width: 110 },
    { title: '名称', dataIndex: 'name', key: 'name', width: 150, ellipsis: true },
    { title: '平台', key: 'platform', width: 70 },
    { title: '执行机', key: 'machine', width: 120 },
    { title: '用例数', key: 'cases', width: 60 },
    { title: '状态', key: 'status', width: 110 },
    { title: '创建时间', key: 'created_at', width: 150 },
    { title: '操作', key: 'action', width: 180, fixed: 'right' },
  ];

  // 远程任务分页（每页 10 条，避免滚动条）
  const remotePagination = {
    pageSize: 10,
    showSizeChanger: false,
    size: 'small' as const,
    showTotal: (total: number) => `共 ${total} 条`,
  };

  function shortId(id: string) {
    return id.length > 16 ? id.slice(0, 8) + '…' : id;
  }

  function tagType(s: string) {
    return (
      { success: 'success', failed: 'error', running: 'warning', pending: 'default', stopped: 'default' }[s] || 'default'
    );
  }
  function fmtTime(ts: number) {
    if (!ts) return '-';
    return new Date(ts * 1000).toLocaleString('zh-CN', { hour12: false });
  }

  async function loadTasks() {
    loading.value = true;
    try {
      const params: any = { limit: 50 };
      if (filterStatus.value) params.status = filterStatus.value;
      const { data } = await http.get('/tasks/', { params });
      tasks.value = Array.isArray(data) ? data : [];
    } catch (e) {
      message.error('加载本机任务失败');
    } finally {
      loading.value = false;
    }
  }

  async function loadRemoteTasks() {
    loading.value = true;
    try {
      const { data } = await http.get('/tasks/remote-list');
      remoteTasks.value = Array.isArray(data) ? data : [];
    } catch (e) {
      message.error('加载远程任务失败');
    } finally {
      loading.value = false;
    }
  }

  function refresh() {
    if (mode.value === 'local') loadTasks();
    else loadRemoteTasks();
  }

  // 打开详情抽屉（本机用 TaskMonitor，远程用 RemoteTaskView；完整详情在抽屉内跳转）
  function openDetail(record: any, kind: 'local' | 'remote') {
    drawerId.value = kind === 'local' ? record.id : record.task_id;
    detailKind.value = kind;
    // 宽度随窗口自适应，保证远程详情完整展示
    if (typeof window !== 'undefined') {
      drawerWidth.value = Math.min(1280, Math.floor(window.innerWidth * 0.96));
    }
    drawerOpen.value = true;
  }

  async function cancel(id: string) {
    try {
      const { data } = await http.post(`/tasks/${id}/cancel`);
      if (data.success) {
        message.success('任务已停止');
        await refresh(); // 本机/远程按当前 tab 刷新
      } else {
        message.error(data.error || '取消失败');
      }
    } catch (e: any) {
      message.error(e.response?.data?.error || '取消失败');
    }
  }

  // 仅清理 Master 索引记录（机器已下架/不可达、状态卡住的远程任务）
  async function removeRemoteRecord(record: any) {
    try {
      const { data } = await http.post('/tasks/remote-remove', {
        task_id: record.task_id,
      });
      if (data.success) {
        message.success('已移除记录');
        await loadRemoteTasks();
      } else {
        message.error(data.error || '移除失败');
      }
    } catch (e: any) {
      message.error(e?.response?.data?.error || '移除失败');
    }
  }

  watch(autoRefresh, (on) => {
    if (on) {
      timer = setInterval(refresh, 3000);
    } else if (timer) {
      clearInterval(timer);
      timer = null;
    }
  });

  onMounted(async () => {
    await Promise.all([loadTasks(), loadRemoteTasks()]);
    // 从 Dashboard / 顶栏 / 通知跳转带 ?focus=<id>：自动打开该本机任务的详情抽屉
    const focus = route.query.focus;
    if (focus && tasks.value.some((t) => t.id === focus)) {
      openDetail({ id: focus as string }, 'local');
    }
  });
  onUnmounted(() => {
    if (timer) clearInterval(timer);
  });
</script>

<style scoped>
.toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}
/* 记录维度 tab：仿区块标题 tint 风格的两个邻接 tab，默认各自着色、字号更大 */
.mode-tabs {
  display: inline-flex;
  align-items: stretch;
  overflow: hidden;
  border: 1px solid var(--border-color);
  border-radius: 8px;
  line-height: 1;
}
.mode-tab {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 22px;
  font-size: 15px;
  cursor: pointer;
  user-select: none;
  transition: background-color 0.2s, color 0.2s;
}
.mode-tab + .mode-tab {
  border-left: 1px solid var(--border-color);
}
/* 默认即带 tint 着色（同 InjectMessage 区块标题风格），两色不撞 */
.tab-local {
  color: var(--accent);
  background: rgba(99, 102, 241, 0.12);
}
.tab-remote {
  color: #06b6d4;
  background: rgba(6, 182, 212, 0.12);
}
.mode-tab.is-active {
  font-weight: 600;
}
.tab-local.is-active {
  background: rgba(99, 102, 241, 0.24);
}
.tab-remote.is-active {
  background: rgba(6, 182, 212, 0.24);
}
.hint {
  font-size: var(--vben-font-size-sm);
  color: var(--text-secondary);
}
.text-xs {
  font-size: var(--vben-font-size-sm);
}
.text-danger {
  color: var(--error-color);
}
.empty {
  color: var(--text-muted);
  padding: 12px;
}
code {
  color: var(--accent);
}
</style>
