<template>
  <div class="dash">
    <!-- 顶部 5 张状态卡片 -->
    <div class="cards">
      <!-- 机器在线（最左，加高展示机器明细） -->
      <div class="stat-card theme-card machine-card" @click="go('/prepare/machines')">
        <!-- 左侧：统计数字 -->
        <div class="mc-head">
          <div class="stat-icon" :class="machineStatus.color">
            <ClusterOutlined :style="{ fontSize: '22px' }" />
          </div>
          <div class="stat-body">
            <div class="stat-label">机器在线</div>
            <div class="stat-value">{{ machineStatus.online }} / {{ machineStatus.total }}</div>
            <div class="stat-sub">{{ machineStatus.text }}</div>
          </div>
        </div>
        <!-- 右侧：机器明细，每行一台（备注 + 当前任务），非空闲在上 -->
        <div class="mc-list">
          <div v-for="m in machineRows" :key="m.id" class="mc-item">
            <span class="mc-name" :title="m.label || m.hostname">{{ m.label || m.hostname || m.ip || '-' }}</span>
            <a-tag v-if="m.current_task" color="processing" class="mc-tag">{{ m.current_task.name }}</a-tag>
            <a-tag v-else-if="m.idle" color="success" class="mc-tag">空闲</a-tag>
            <span v-else class="mc-offline">未就绪</span>
          </div>
          <div v-if="!machines.length" class="mc-empty">暂无机器</div>
        </div>
      </div>

      <div class="stat-card theme-card" @click="go('/prepare/proxy')">
        <div class="stat-icon" :class="proxy.running ? 'ok' : 'off'">
          <ApiOutlined :style="{ fontSize: '22px' }" />
        </div>
        <div class="stat-body">
          <div class="stat-label">代理状态</div>
          <div class="stat-value">{{ proxy.running ? '运行中' : '已停止' }}</div>
          <div class="stat-sub">PID {{ proxy.pid ?? '-' }} · 规则 {{ proxy.rules_count ?? 0 }}</div>
        </div>
      </div>

      <div class="stat-card theme-card" @click="go('/prepare/proxy')">
        <div class="stat-icon neutral">
          <ShareAltOutlined :style="{ fontSize: '22px' }" />
        </div>
        <div class="stat-body">
          <div class="stat-label">抓包流量</div>
          <div class="stat-value">{{ flowsCount }}</div>
          <div class="stat-sub">HTTP 流</div>
        </div>
      </div>

      <div class="stat-card theme-card" @click="go('/test/monitor')">
        <div class="stat-icon" :class="taskStat.running ? 'busy' : 'neutral'">
          <BarChartOutlined :style="{ fontSize: '22px' }" />
        </div>
        <div class="stat-body">
          <div class="stat-label">运行中任务</div>
          <div class="stat-value">{{ taskStat.running }}</div>
          <div class="stat-sub">待执行 {{ taskStat.pending }} · 今日完成 {{ taskStat.doneToday }}</div>
        </div>
      </div>

      <div class="stat-card theme-card" @click="go('/test/report')">
        <div class="ring" :style="ringStyle">
          <span class="ring-num">{{ passRate === null ? '—' : passRate + '%' }}</span>
        </div>
        <div class="stat-body">
          <div class="stat-label">最近通过率</div>
          <div class="stat-value">{{ passRate === null ? '暂无' : passRate + '%' }}</div>
          <div class="stat-sub">{{ passedCount }} / {{ recentReports.length }} 次通过</div>
        </div>
      </div>
    </div>

    <!-- 失败报告（仅在有失败时显示，优先级最高） -->
    <a-card v-if="failedReports.length" class="theme-card fail-card">
      <template #title>
        <div class="hdr">
          <span class="fail-title sec-title tint-red">
            <span class="fail-x">✗</span>
            需要关注的失败（{{ failedReports.length }}）
          </span>
          <a-button type="link" size="small" @click="go('/test/report')">全部报告 →</a-button>
        </div>
      </template>
      <a-table
        :data-source="failedReports"
        :columns="failColumns"
        :pagination="false"
        row-key="file"
        size="small"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'case_name'">
            <span class="fail-name">{{ record.case_name || '未命名' }}</span>
          </template>
          <template v-else-if="column.key === 'detail'">
            <span class="status-badge failed">{{ failDetail(record.summary) }}</span>
          </template>
          <template v-else-if="column.key === 'time'">
            {{ fmtTime(record.created_at || record.timestamp) }}
          </template>
          <template v-else-if="column.key === 'action'">
            <a-button type="link" size="small" @click="go(`/test/report?open=${record.file}`)">
              看报告
            </a-button>
          </template>
        </template>
      </a-table>
    </a-card>

    <!-- 中部：最近任务 + 最近报告 -->
    <div class="mid">
      <a-card class="theme-card" :body-style="{ padding: '0 4px 4px' }">
        <template #title>
          <div class="hdr">
            <span class="sec-title tint-indigo"><CarryOutOutlined />最近测试任务</span>
            <a-button type="link" size="small" @click="go('/test/monitor')">全部 →</a-button>
          </div>
        </template>
        <a-table
          :data-source="recentTasks"
          :columns="taskColumns"
          :pagination="false"
          row-key="id"
          size="small"
          :scroll="{ y: 220 }"
          :locale="{ emptyText: '暂无任务' }"
        >
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'name'">
              {{ record.name || record.id.slice(0, 8) + '…' }}
            </template>
            <template v-else-if="column.key === 'status'">
              <a-tag :color="tagColor(record.status)">{{ record.status }}</a-tag>
            </template>
            <template v-else-if="column.key === 'created_at'">
              {{ fmtTime(record.created_at) }}
            </template>
            <template v-else-if="column.key === 'action'">
              <a-button type="link" size="small" @click="go(`/test/monitor?focus=${record.id}`)">
                详情
              </a-button>
            </template>
          </template>
        </a-table>
      </a-card>

      <a-card class="theme-card" :body-style="{ padding: '0 4px 4px' }">
        <template #title>
          <div class="hdr">
            <span class="sec-title tint-blue"><FileDoneOutlined />最近测试报告</span>
            <a-button type="link" size="small" @click="go('/test/report')">全部 →</a-button>
          </div>
        </template>
        <a-table
          :data-source="recentReports"
          :columns="reportColumns"
          :pagination="false"
          row-key="file"
          size="small"
          :scroll="{ y: 220 }"
          :locale="{ emptyText: '暂无报告' }"
        >
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'result'">
              <div class="result-badges">
                <span
                  v-for="seg in resultSegments(record.summary)"
                  :key="seg.key"
                  class="status-badge"
                  :class="seg.cls"
                >{{ seg.text }}</span>
                <span v-if="!resultHasData(record.summary)" class="muted">无数据</span>
              </div>
            </template>
            <template v-else-if="column.key === 'duration'">
              {{ record.duration ? record.duration.toFixed(1) + 's' : '-' }}
            </template>
            <template v-else-if="column.key === 'action'">
              <a-button type="link" size="small" @click="go(`/test/report?open=${record.file}`)">
                报告
              </a-button>
            </template>
          </template>
        </a-table>
      </a-card>
    </div>

    <!-- 底部：版本质量概览（默认展开） -->
    <a-collapse v-model:activeKey="verActiveKeys" class="theme-card ver-collapse" :bordered="false">
      <a-collapse-panel key="versions">
        <template #header>
          <span class="sec-title tint-purple"><AuditOutlined />版本质量概览</span>
        </template>
        <template #extra>
          <a-button type="link" size="small" @click.stop="go('/quality/versions')">详情 →</a-button>
        </template>
        <div v-if="versionOverview.length" class="ver-grid">
          <span v-for="v in versionOverview" :key="v.platform" class="ver-item">
            <span class="ver-platform">{{ v.platform }}</span>
            <span class="ver-ver">{{ v.version || '—' }}</span>
            <span
              v-if="v.passed !== null"
              class="status-badge"
              :class="v.passed ? 'passed' : 'failed'"
            >{{ v.passed ? '通过' : '失败' }}</span>
            <span v-else class="status-badge skipped">未测</span>
          </span>
        </div>
        <div v-else class="empty">暂无版本记录</div>
      </a-collapse-panel>
    </a-collapse>
  </div>
</template>

<script lang="ts" setup>
  defineOptions({ name: 'DashboardIndex' });
  import { ref, computed, onMounted, onUnmounted } from 'vue';
  import { useRouter } from 'vue-router';
  import { ApiOutlined, ShareAltOutlined, BarChartOutlined, ClusterOutlined, CarryOutOutlined, FileDoneOutlined, AuditOutlined } from '@ant-design/icons-vue';
  import http from '@/api/platform/http';
  import { getMachinesList } from '@/api/platform/distributed';
  import type { Machine } from '@/api/platform/distributed';
  import { useTasksStore } from '@/store/modules/tasks';

  const router = useRouter();
  const tasksStore = useTasksStore();

  const proxy = ref<any>({});
  const flowsCount = ref(0);
  const recentReports = ref<any[]>([]);
  const versionOverview = ref<any[]>([]);
  const machines = ref<Machine[]>([]);
  // 版本质量概览默认展开
  const verActiveKeys = ref<string[]>(['versions']);
  let timer: ReturnType<typeof setInterval> | null = null;

  const taskColumns = [
    { title: '名称', key: 'name', ellipsis: true },
    { title: '状态', key: 'status', width: 96 },
    { title: '创建时间', key: 'created_at', width: 150 },
    { title: '', key: 'action', width: 70 },
  ];
  const reportColumns = [
    { title: '任务名', dataIndex: 'case_name', key: 'case_name', ellipsis: true },
    { title: '结果', key: 'result', width: 150 },
    { title: '耗时', key: 'duration', width: 80 },
    { title: '', key: 'action', width: 70 },
  ];
  const failColumns = [
    { title: '任务名', key: 'case_name', ellipsis: true },
    { title: '失败情况', key: 'detail', width: 160 },
    { title: '时间', key: 'time', width: 150 },
    { title: '', key: 'action', width: 90 },
  ];

  function go(path: string) {
    router.push(path);
  }
  function tagColor(s: string) {
    return (
      { success: 'success', failed: 'error', running: 'warning', pending: 'default' }[s] || 'default'
    );
  }
  function reportPassed(row: any) {
    const s = row.summary || {};
    return !s.failed && !s.error;
  }
  /** 结果列分段徽标（与 TestReport 一致：✓/✗ + 颜色 + 数字） */
  function resultSegments(s: any) {
    if (!s || typeof s !== 'object') return [];
    const segs: Array<{ key: string; cls: string; text: string }> = [];
    if (s.passed) segs.push({ key: 'passed', cls: 'passed', text: `通过 ${s.passed}` });
    if (s.failed) segs.push({ key: 'failed', cls: 'failed', text: `失败 ${s.failed}` });
    if (s.error) segs.push({ key: 'error', cls: 'error', text: `错误 ${s.error}` });
    if (s.skipped) segs.push({ key: 'skipped', cls: 'skipped', text: `跳过 ${s.skipped}` });
    return segs;
  }
  function resultHasData(s: any) {
    return resultSegments(s).length > 0;
  }

  const recentTasks = computed(() => tasksStore.tasks.slice(0, 6));

  const taskStat = computed(() => {
    const list = tasksStore.tasks;
    const startOfToday = new Date();
    startOfToday.setHours(0, 0, 0, 0);
    const todayTs = startOfToday.getTime() / 1000;
    return {
      running: list.filter((t: any) => t.status === 'running').length,
      pending: list.filter((t: any) => t.status === 'pending').length,
      doneToday: list.filter(
        (t: any) =>
          (t.status === 'success' || t.status === 'failed') &&
          (t.finished_at || t.created_at) >= todayTs,
      ).length,
    };
  });

  const passRate = computed(() => {
    const list = recentReports.value;
    if (!list.length) return null;
    const ok = list.filter(reportPassed).length;
    return Math.round((ok / list.length) * 100);
  });

  const passedCount = computed(() => {
    return recentReports.value.filter(reportPassed).length;
  });

  // 机器在线状态
  const machineStatus = computed(() => {
    const total = machines.value.length;
    const online = machines.value.filter((m) => m.status === 'online').length;
    let color = 'neutral';
    let text = '分布式执行节点';
    if (total === 0) {
      text = '暂无机器';
    } else if (online === 0) {
      color = 'off';
      text = '全部离线';
    } else if (online < total) {
      color = 'busy';
      text = `${total - online} 台离线`;
    } else {
      color = 'ok';
      text = '全部在线';
    }
    return { total, online, color, text };
  });

  // 机器明细排序：非空闲（有当前任务）在前，空闲在后，离线垫底
  const machineRows = computed(() => {
    const rank = (m: any) => (m.current_task ? 0 : m.idle ? 1 : 2);
    return [...machines.value].sort((a, b) => rank(a) - rank(b));
  });

  // 失败的报告（最多 5 条，按时间倒序）
  const failedReports = computed(() => {
    return recentReports.value.filter((r) => !reportPassed(r)).slice(0, 5);
  });

  // 失败明细文本（失败 2 / 错误 1）
  function failDetail(s: any) {
    if (!s || typeof s !== 'object') return '未知';
    const parts: string[] = [];
    if (s.failed) parts.push(`失败 ${s.failed}`);
    if (s.error) parts.push(`错误 ${s.error}`);
    return parts.length ? parts.join(' / ') : '未知';
  }

  // 时间格式化（MM-DD HH:mm）
  function fmtTime(ts: number | string | undefined) {
    if (!ts) return '-';
    const d = new Date(typeof ts === 'number' ? ts * 1000 : ts);
    const m = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    const h = String(d.getHours()).padStart(2, '0');
    const min = String(d.getMinutes()).padStart(2, '0');
    return `${m}-${day} ${h}:${min}`;
  }

  const ringStyle = computed(() => {
    const pct = passRate.value === null ? 0 : passRate.value;
    const color = pct >= 90 ? 'var(--success-color)' : pct >= 60 ? 'var(--warning-color)' : '#ef4444';
    return { background: `conic-gradient(${color} ${pct * 3.6}deg, var(--border-color) 0deg)` };
  });

  async function loadProxy() {
    try {
      const [{ data: st }, { data: fl }] = await Promise.all([
        http.get('/proxy/status'),
        http.get('/proxy/flows'),
      ]);
      proxy.value = st || {};
      flowsCount.value = Array.isArray(fl) ? fl.length : 0;
    } catch {
      /* 忽略 */
    }
  }

  async function loadReports() {
    try {
      const { data } = await http.get('/cases/history', { params: { limit: 20 } });
      recentReports.value = Array.isArray(data) ? data : [];
    } catch {
      /* 忽略 */
    }
  }

  async function loadMachines() {
    try {
      const res = await getMachinesList();
      // 响应体为 { data: Machine[], summary }，与 machines.vue/submit.vue 一致
      machines.value = res.data.data || [];
    } catch {
      /* 忽略 */
    }
  }

  async function loadVersions() {
    try {
      const { data: platforms } = await http.get('/version-records/platforms');
      if (!Array.isArray(platforms)) return;

      // 并发请求所有平台的版本和详情
      const rows = await Promise.all(
        platforms.map(async (p) => {
          try {
            const { data: vers } = await http.get(`/version-records/${p}/versions`);
            const latest = Array.isArray(vers) && vers.length ? vers[0] : null;
            let passed: boolean | null = null;
            if (latest) {
              const { data: detail } = await http.get(`/version-records/${p}/${latest.version}`);
              passed = deriveVersionPassed(detail);
            }
            return { platform: p, version: latest?.version || '', passed };
          } catch {
            return { platform: p, version: '', passed: null };
          }
        })
      );
      versionOverview.value = rows;
    } catch {
      /* 忽略 */
    }
  }

  function deriveVersionPassed(detail: any): boolean | null {
    const cases = (detail && (detail.cases || detail.case_records)) || null;
    if (!cases) return null;
    const vals = Array.isArray(cases) ? cases : Object.values(cases);
    if (!vals.length) return null;
    return vals.every((c: any) => c && c.passed === true);
  }

  /** 当前环境（dev / prod），与测试参数页取自同一个 /plan/options 接口 */
  function refreshAll() {
    loadProxy();
    loadReports();
    loadVersions(); // 版本概览也纳入刷新（之前只加载一次）
    loadMachines(); // 机器状态
  }

  // 页面不可见时暂停轮询，避免后台标签页持续打接口
  function startPolling() {
    if (timer) return;
    timer = setInterval(refreshAll, 10_000); // 4s → 10s
  }

  function stopPolling() {
    if (timer) {
      clearInterval(timer);
      timer = null;
    }
  }

  function onVisibilityChange() {
    if (document.visibilityState === 'visible') {
      refreshAll(); // 切回来先立即刷一次
      startPolling();
    } else {
      stopPolling();
    }
  }

  onMounted(() => {
    tasksStore.start();
    refreshAll();
    startPolling();
    document.addEventListener('visibilitychange', onVisibilityChange);
  });
  onUnmounted(() => {
    tasksStore.stop();
    stopPolling();
    document.removeEventListener('visibilitychange', onVisibilityChange);
  });
</script>

<style scoped>
  .dash {
    display: flex;
    flex-direction: column;
    gap: 16px;
    padding: 16px;
  }

  /* 环境标签：右上角，不占额外行高（负边距贴合卡片区上沿） */
  .cards {
    display: grid;
    /* 机器在线卡（第 1 位）加宽容纳两列机器明细，其余统计卡收窄，行高保持一致 */
    grid-template-columns: 2fr 0.9fr 0.9fr 0.9fr 0.9fr;
    gap: 12px;
    align-items: stretch;
  }
  .stat-card {
    display: flex;
    align-items: center;
    gap: 14px;
    padding: 16px;
    border-radius: 4px;
    cursor: pointer;
    background: var(--bg-card);
    border: 1px solid var(--border-color);
    transition: border-color 0.15s, background 0.15s;
  }
  .stat-card:hover {
    border-color: var(--accent);
    background: var(--bg-hover);
  }
  .stat-icon {
    width: 46px;
    height: 46px;
    border-radius: 10px;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
  }
  .stat-icon.ok {
    background: rgba(48, 164, 108, 0.12);
    color: var(--success-color);
  }
  .stat-icon.off {
    background: rgba(156, 163, 175, 0.14);
    color: var(--text-muted);
  }
  .stat-icon.busy {
    background: rgba(247, 107, 21, 0.12);
    color: var(--warning-color);
  }
  .stat-icon.neutral {
    background: rgba(99, 102, 241, 0.12);
    color: var(--accent);
  }
  .stat-body {
    min-width: 0;
  }
  .stat-label {
    font-size: var(--vben-font-size-sm);
    color: var(--text-muted);
  }
  .stat-value {
    font-size: 22px;
    font-weight: 700;
    color: var(--text-primary);
    line-height: 1.3;
  }
  .stat-value .unit {
    font-size: var(--vben-font-size-sm);
    font-weight: 400;
    color: var(--text-muted);
  }
  .stat-sub {
    font-size: var(--vben-font-size-sm);
    color: var(--text-secondary);
  }
  /* 机器在线卡：左侧统计，右侧机器明细（每行一台：备注 + 当前任务） */
  .machine-card {
    flex-direction: row;
    align-items: center;
    gap: 12px;
    padding: 12px 14px;
    min-width: 0;
    height: 100%;
  }
  .mc-head {
    display: flex;
    align-items: center;
    gap: 12px;
    flex-shrink: 0;
  }
  .mc-head .stat-value {
    font-size: 20px;
  }
  /* 两列 4×2 展示：8 台 = 4 行 × 2 列，高度约 4 行，无需滚动条 */
  .mc-list {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    column-gap: 10px;
    row-gap: 3px;
    flex: 1;
    min-width: 0;
    max-height: 96px;
    overflow-y: auto;
    border-left: 1px solid var(--border-color);
    padding-left: 12px;
  }
  .mc-item {
    display: flex;
    align-items: center;
    gap: 6px;
    min-width: 0;
    line-height: 18px;
    font-size: 12px;
    white-space: nowrap;
  }
  .mc-name {
    font-size: 12px;
    font-weight: 600;
    color: var(--text-primary);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    max-width: 45%;
    flex-shrink: 0;
  }
  .mc-tag {
    font-size: 12px;
    margin: 0;
    height: 18px;
    line-height: 16px;
    padding: 0 6px;
    border-radius: 4px;
    max-width: 55%;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .mc-offline {
    color: var(--text-muted);
    font-size: 12px;
  }
  .mc-empty {
    color: var(--text-muted);
    font-size: var(--vben-font-size-sm);
    text-align: center;
  }
  .ring {
    width: 52px;
    height: 52px;
    border-radius: 50%;
    flex-shrink: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    position: relative;
  }
  .ring::after {
    content: '';
    position: absolute;
    width: 40px;
    height: 40px;
    border-radius: 50%;
    background: var(--bg-card);
  }
  .ring-num {
    position: relative;
    z-index: 1;
    font-size: var(--vben-font-size-sm);
    font-weight: 700;
    color: var(--text-primary);
  }
  .mid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 16px;
  }
  .hdr {
    display: flex;
    align-items: center;
    justify-content: space-between;
  }
  .empty {
    color: var(--text-muted);
    padding: 12px;
    text-align: center;
  }
  .ver-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
    gap: 12px;
  }
  .ver-item {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 10px 12px;
    border: 1px solid var(--border-color);
    border-radius: 8px;
  }
  .ver-platform {
    font-weight: 600;
    color: var(--accent);
  }
  .ver-ver {
    color: var(--text-secondary);
    font-size: var(--vben-font-size-base);
    margin-right: auto;
  }
  /* 结果列：分段 status-badge（✓/✗ + 颜色 + 数字） */
  .result-badges {
    display: flex;
    flex-wrap: wrap;
    gap: 4px 8px;
  }
  /* 失败报告卡片 */
  .fail-card {
    margin-bottom: 16px;
    border-left: 3px solid var(--error-color);
  }
  .fail-title {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    font-weight: 600;
    color: var(--error-color);
  }
  /* 与失败徽标 status-badge.failed 的 ✗ 保持一致 */
  .fail-x {
    font-weight: 700;
    font-size: 14px;
    color: var(--error-color);
    line-height: 1;
  }
  .fail-icon {
    font-size: 18px;
  }
  .fail-name {
    font-weight: 500;
  }
  /* 版本折叠面板 */
  .ver-collapse {
    background: var(--bg-card);
    border: 1px solid var(--border-color);
    border-radius: 4px;
  }
  .ver-collapse :deep(.ant-collapse-item) {
    border: none;
  }
  .ver-collapse :deep(.ant-collapse-header) {
    font-weight: 500;
    color: var(--text-primary);
  }
  @media (max-width: 1600px) {
    .cards {
      grid-template-columns: repeat(3, 1fr);
    }
  }
  @media (max-width: 1100px) {
    .cards {
      grid-template-columns: repeat(2, 1fr);
    }
    .mid {
      grid-template-columns: 1fr;
    }
  }
</style>
