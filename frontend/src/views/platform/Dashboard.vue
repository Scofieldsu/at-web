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

      <!-- 测试版本：按当前环境显示测试参数里各平台版本，与最新版本不一致时高亮提示；点击进测试参数页 -->
      <div class="stat-card theme-card version-card" @click="go('/test/params')">
        <div class="stat-icon neutral">
          <TagOutlined :style="{ fontSize: '22px' }" />
        </div>
        <div class="ver-body">
          <div class="stat-label">测试版本</div>
          <div class="ver-cols">
            <div
              v-for="p in platformRows"
              :key="p.value"
              class="ver-col"
              :class="{ stale: p.stale }"
            >
              <span class="pf-mark" :class="p.mark">{{ p.markChar }}</span>
              <span class="ver-col-name">{{ p.label }}</span>
              <a-tooltip
                v-if="p.stale"
                :title="`${p.label} 最新版本为 ${p.latest}`"
                placement="top"
              >
                <span class="ver-col-ver">{{ p.version || '—' }}</span>
              </a-tooltip>
              <span v-else class="ver-col-ver" :title="`${p.label} ${p.version || '未配置'}`">
                {{ p.version || '—' }}
              </span>
            </div>
          </div>
          <div v-if="stalePlatforms.length" class="ver-stale-tip">
            <ExclamationCircleOutlined />
            <span>{{ staleText }}</span>
          </div>
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

    <!-- 中部：需要关注的失败 + 最近任务 + 最近报告（两列栅格，失败卡与"最近测试任务"同宽） -->
    <div class="mid">
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

      <!-- 定时任务速览（启用中的定时计划：名称/周期/下次执行/最近结果） -->
      <a-card class="theme-card" :body-style="{ padding: '0 4px 4px' }">
        <template #title>
          <div class="hdr">
            <span class="sec-title tint-cyan"><FieldTimeOutlined />定时任务速览</span>
            <a-button type="link" size="small" @click="go('/test/schedule')">全部 →</a-button>
          </div>
        </template>
        <a-table
          v-if="enabledSchedules.length"
          :data-source="enabledSchedules"
          :columns="scheduleColumns"
          :pagination="false"
          row-key="id"
          size="small"
          :scroll="{ y: 220 }"
        >
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'name'">
              <span class="fail-name">{{ record.name }}</span>
            </template>
            <template v-else-if="column.key === 'spec'">
              {{ specText(record.spec) }}
            </template>
            <template v-else-if="column.key === 'next_run_at'">
              {{ fmtTime(record.next_run_at) }}
            </template>
            <template v-else-if="column.key === 'last'">
              <a-tag v-if="record.last_run" :color="lastRunColor(record.last_run.status)">
                {{ lastRunText(record.last_run.status) }}
              </a-tag>
              <span v-else class="muted">未运行</span>
            </template>
          </template>
        </a-table>
        <div v-else class="empty">暂无启用的定时任务</div>
      </a-card>

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
  import { ApiOutlined, BarChartOutlined, ClusterOutlined, CarryOutOutlined, FileDoneOutlined, AuditOutlined, FieldTimeOutlined, TagOutlined, ExclamationCircleOutlined } from '@ant-design/icons-vue';
  import http from '@/api/platform/http';
  import { getMachinesList } from '@/api/platform/distributed';
  import type { Machine } from '@/api/platform/distributed';
  import { getSchedules } from '@/api/platform/schedules';
  import type { Schedule } from '@/api/platform/schedules';
  import { useTasksStore } from '@/store/modules/tasks';

  const router = useRouter();
  const tasksStore = useTasksStore();

  const proxy = ref<any>({});
  const recentReports = ref<any[]>([]);
  const versionOverview = ref<any[]>([]);
  const machines = ref<Machine[]>([]);
  const schedules = ref<Schedule[]>([]);
  // 测试版本卡：各平台（当前环境测试参数版本 + 最新版本；环境在页面左上角已显示，卡片内不重复）
  const planVersions = ref<Record<string, string>>({});
  const latestVersions = ref<Record<string, string>>({});
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
  const scheduleColumns = [
    { title: '名称', key: 'name', ellipsis: true },
    { title: '周期', key: 'spec', width: 110 },
    { title: '下次执行', key: 'next_run_at', width: 120 },
    { title: '最近', key: 'last', width: 84 },
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

  // 定时任务速览：启用中的计划（最多 5 条，按下次执行时间升序）
  const enabledSchedules = computed(() => {
    return schedules.value
      .filter((s) => s.enabled)
      .sort((a, b) => String(a.next_run_at).localeCompare(String(b.next_run_at)))
      .slice(0, 5);
  });

  const WEEKDAYS = ['一', '二', '三', '四', '五', '六', '日'];

  // 测试版本卡：平台展示顺序与测试参数页一致（颜色/徽标对齐该页）
  const DASH_PLATFORMS = [
    { value: 'platform_a', label: '平台A', mark: 'pf-jd', markChar: 'A' },
    { value: 'platform_b', label: '平台B', mark: 'pf-qn', markChar: 'B' },
    { value: 'platform_c', label: '平台C', mark: 'pf-pdd', markChar: 'C' },
    { value: 'platform_d', label: '平台D', mark: 'pf-dy', markChar: 'D' },
  ];
  const platformRows = computed(() =>
    DASH_PLATFORMS.map((p) => {
      const version = planVersions.value[p.value] || '';
      const latest = latestVersions.value[p.value] || '';
      return { ...p, version, latest, stale: !!(version && latest && version !== latest) };
    }),
  );
  const stalePlatforms = computed(() => platformRows.value.filter((p) => p.stale));
  const staleText = computed(() =>
    stalePlatforms.value.map((p) => `${p.label} 最新版本为 ${p.latest}`).join('；'),
  );

  function specText(spec: any) {
    if (!spec || !spec.type) return '-';
    switch (spec.type) {
      case 'daily':
        return `每天 ${spec.time || ''}`.trim();
      case 'weekly':
        return (
          `每周${(spec.weekdays || []).map((d: number) => WEEKDAYS[(d % 7) - 1] || '?').join('')}` +
          (spec.time ? ` ${spec.time}` : '')
        ).trim();
      case 'monthly':
        return `${spec.day_of_month || '?'}日 ${spec.time || ''}`.trim();
      case 'interval':
        return `每 ${spec.interval_hours || 1}h`;
      default:
        return spec.type;
    }
  }
  function lastRunColor(s: string) {
    return ({ success: 'success', failed: 'error', running: 'processing' } as any)[s] || 'default';
  }
  function lastRunText(s: string) {
    return ({ success: '成功', failed: '失败', running: '运行中' } as any)[s] || s;
  }

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
      const { data: st } = await http.get('/proxy/status');
      proxy.value = st || {};
    } catch {
      /* 忽略 */
    }
  }

  // 测试版本：当前环境测试参数里的各平台版本 + 最新版本（与测试参数页同源接口）
  async function loadRpaVersions() {
    try {
      const { data } = await http.get('/plan/');
      const p = data.plan || {};
      const vers: Record<string, string> = {};
      for (const { value } of DASH_PLATFORMS) {
        vers[value] = (p[value] && p[value].version) || '';
      }
      planVersions.value = vers;
    } catch {
      /* 忽略 */
    }
    const latest: Record<string, string> = {};
    await Promise.all(
      DASH_PLATFORMS.map(async ({ value }) => {
        try {
          const { data } = await http.get('/env/versions', { params: { platform: value } });
          const vs: string[] = data.versions || [];
          if (vs.length) latest[value] = vs[0];
        } catch {
          /* 该平台无版本/接口不可用时留空 */
        }
      }),
    );
    latestVersions.value = latest;
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

  async function loadSchedules() {
    try {
      const { data } = await getSchedules();
      schedules.value = Array.isArray(data?.schedules) ? data.schedules : [];
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
    loadSchedules(); // 定时任务速览
    loadRpaVersions(); // 测试版本（环境版本 + 最新）
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
    /* 机器在线卡（第 1 位）加宽容纳两列机器明细；代理状态（第 2 位）加宽、测试版本（第 3 位）收窄，其余统计卡收窄，行高保持一致 */
    grid-template-columns: 2fr 1.6fr 0.9fr 0.9fr 0.9fr;
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
  /* 测试版本卡：左侧图标，右侧两列平台版本 */
  .version-card {
    gap: 12px;
    padding: 12px 14px;
  }
  .ver-body {
    flex: 1;
    min-width: 0;
  }
  .ver-cols {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 4px 10px;
    margin-top: 6px;
  }
  .ver-col {
    display: flex;
    align-items: center;
    gap: 6px;
    min-width: 0;
    padding: 2px 6px;
    border-radius: 6px;
    border: 1px solid transparent;
    line-height: 20px;
    font-size: 12px;
    white-space: nowrap;
  }
  .ver-col .pf-mark {
    width: 18px;
    height: 18px;
    border-radius: 5px;
    font-size: 11px;
  }
  /* 平台徽标：基础样式与四色背景，与测试参数页（TestPlan.vue）保持完全一致 */
  .pf-mark {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    color: #fff;
  }
  .pf-jd {
    background: #e5484d;
  }
  .pf-qn {
    background: #0090ff;
  }
  .pf-pdd {
    background: #f76b15;
  }
  .pf-dy {
    background: #30a46c;
  }
  .ver-col-name {
    font-weight: 600;
    color: var(--text-secondary);
    flex-shrink: 0;
  }
  .ver-col-ver {
    margin-left: auto;
    font-weight: 600;
    color: var(--text-primary);
    overflow: hidden;
    text-overflow: ellipsis;
  }
  /* 与最新版本不一致：整行高亮 + 提示最新版本 */
  .ver-col.stale {
    background: rgba(247, 107, 21, 0.1);
    border-color: rgba(247, 107, 21, 0.45);
  }
  .ver-col.stale .ver-col-ver {
    color: var(--warning-color);
  }
  /* 悬浮提示内的版本文本：保持可被 tooltip 捕获（display:inline 兜底） */
  .ver-col.stale :deep(.ant-tooltip) {
    z-index: 1050;
  }
  .ver-stale-tip {
    display: flex;
    align-items: center;
    gap: 6px;
    margin-top: 6px;
    font-size: 12px;
    line-height: 16px;
    color: var(--warning-color);
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
  .muted {
    color: var(--text-muted);
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
  /* 失败报告卡片（与最近任务/报告同宽：栅格内不再额外留底边距） */
  .fail-card {
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
