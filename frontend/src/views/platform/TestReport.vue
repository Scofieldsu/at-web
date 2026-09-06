<template>
  <!-- 报告列表 -->
  <a-card class="theme-card fill-card">
    <template #title>
      <div class="hdr">
        <span class="sec-title tint-indigo"><FileTextOutlined />测试报告</span>
        <div class="hdr-tools">
          <a-input v-model:value="keyword" placeholder="搜索任务名" size="small" allow-clear style="width:200px" />
          <a-select v-model:value="filterResult" size="small" style="width:120px">
            <a-select-option value="">全部结果</a-select-option>
            <a-select-option value="pass">仅通过</a-select-option>
            <a-select-option value="fail">仅失败</a-select-option>
          </a-select>
          <a-button :loading="loading" size="small" @click="load">刷新</a-button>
          <a-popconfirm title="清理 7 天前的报告日志和录屏？" @confirm="clean">
            <a-button size="small" danger>清理过期</a-button>
          </a-popconfirm>
        </div>
      </div>
    </template>

    <div class="table-wrap">
      <vxe-table
        :data="pageData"
        border
        resizable
        row-key="file"
        size="small"
        class="theme-table"
        auto-resize
      >
        <vxe-column field="case_name" title="测试任务名" width="400" show-overflow="tooltip" />
        <vxe-column field="created" title="时间">
          <template #default="{ row }">{{ fmtTime(row.created) }}</template>
        </vxe-column>
        <vxe-column field="result" title="结果" width="220">
          <template #default="{ row }">
            <div class="result-cell">
              <span
                v-for="seg in resultSegments(row.summary)"
                :key="seg.key"
                class="status-badge"
                :class="seg.cls"
              >
                {{ seg.text }}
              </span>
              <span v-if="!segmentsText(row.summary)" class="muted">无数据</span>
            </div>
          </template>
        </vxe-column>
        <vxe-column field="tests_count" title="用例数" width="80">
          <template #default="{ row }">
            <span class="col-num">{{ row.tests_count ?? '-' }}</span>
          </template>
        </vxe-column>
        <vxe-column field="duration" title="耗时" width="120">
          <template #default="{ row }">
            <span class="col-num">{{ fmtDuration(row.duration) }}</span>
          </template>
        </vxe-column>
        <vxe-column title="操作" width="280">
          <template #default="{ row }">
            <a-button size="small" type="primary" @click="openDetail(row)">报告</a-button>
            <a-button size="small" type="primary" ghost style="margin-left:8px" @click="openLog(row)">日志</a-button>
            <a-button size="small" type="warning" ghost style="margin-left:8px" @click="openVideos(row)" :disabled="!row.task_id">录屏</a-button>
          </template>
        </vxe-column>
      </vxe-table>
    </div>
    <div v-if="!reports.length" class="muted pad">暂无测试报告，先在「测试任务」中跑用例。</div>
    <div v-else class="pagination-bar">
      <a-pagination
        v-model:current="page"
        :total="filteredReports.length"
        :page-size="pageSize"
        show-quick-jumper
        show-total
        size="small"
        @change="page = $event"
      />
    </div>
  </a-card>

  <!-- 报告详情抽屉 -->
  <a-drawer v-model:open="detailVisible" :title="detailTitle" width="60%">
    <template v-if="detail">
      <!-- 摘要卡片 -->
      <div class="r-summary">
        <div class="r-summary-item rate">
          <div class="num">{{ passRate(detail) }}%</div>
          <div class="label">通过率</div>
        </div>
        <div class="r-summary-item passed">
          <div class="num">{{ detail.summary?.passed || 0 }}</div>
          <div class="label">通过</div>
        </div>
        <div class="r-summary-item failed">
          <div class="num">{{ detail.summary?.failed || 0 }}</div>
          <div class="label">失败</div>
        </div>
        <div class="r-summary-item error">
          <div class="num">{{ detail.summary?.error || 0 }}</div>
          <div class="label">错误</div>
        </div>
        <div class="r-summary-item skipped">
          <div class="num">{{ detail.summary?.skipped || 0 }}</div>
          <div class="label">跳过</div>
        </div>
        <div class="r-summary-item">
          <div class="num">{{ detail.summary?.total || (detail.tests?.length ?? 0) }}</div>
          <div class="label">总计</div>
          <div class="sub">{{ detail.duration ? detail.duration.toFixed(2) + 's' : '-' }}</div>
        </div>
      </div>

      <!-- 用例表格：按套件分组 -->
      <div class="r-table-wrap">
        <table class="r-table">
          <thead>
            <tr>
              <th style="width:55%">测试套件 / 用例</th>
              <th style="width:50px">总计</th>
              <th style="width:50px">通过</th>
              <th style="width:50px">失败</th>
              <th style="width:50px">错误</th>
              <th style="width:50px">跳过</th>
              <th style="width:70px">耗时</th>
            </tr>
          </thead>
          <tbody>
            <template v-for="(suite, si) in suiteData" :key="si">
              <tr :class="['r-suite', suite.cls]" @click="toggleSuite(si)">
                <td class="r-suite-name"><span class="icon">{{ suite.open ? '▼' : '▶' }}</span> {{ suite.name }}</td>
                <td class="num">{{ suite.total }}</td>
                <td class="num passed">{{ suite.passed }}</td>
                <td class="num failed">{{ suite.failed }}</td>
                <td class="num error-c">{{ suite.error }}</td>
                <td class="num skipped">{{ suite.skipped }}</td>
                <td class="num">{{ suite.duration }}s</td>
              </tr>
              <tr v-for="(tc, ti) in suite.cases" :key="ti"
                  v-show="suite.open"
                  :class="['r-case', tc.outcome]">
                <td class="r-case-name">
                  <span class="r-icon">{{ outcomeIcon(tc.outcome) }}</span>
                  {{ tc.shortName }}
                  <span class="r-time">{{ tc.duration ? tc.duration.toFixed(3) + 's' : '' }}</span>
                  <div v-if="tc.message" class="r-detail">
                    {{ tc.messageLine }}
                    <pre v-if="tc.messageBody">{{ tc.messageBody }}</pre>
                  </div>
                </td>
                <td></td><td></td><td></td><td></td><td></td><td></td>
              </tr>
            </template>
          </tbody>
        </table>
      </div>
    </template>
    <div v-else class="muted pad">加载中…</div>
  </a-drawer>

  <!-- 日志抽屉 -->
  <a-drawer v-model:open="logVisible" :title="logTitle" width="60%">
    <pre class="log-view">{{ logContent || '加载中…' }}</pre>
  </a-drawer>

  <!-- 录屏抽屉 -->
  <a-drawer v-model:open="videoVisible" :title="videoTitle" width="50%">
    <div v-if="videos.length === 0" class="muted pad">暂无误屏文件</div>
    <div v-for="(v, i) in videos" :key="i" class="video-item">
      <div class="video-name">🎬 {{ v.name }}</div>
      <div class="video-meta">{{ fmtSize(v.size) }} · {{ fmtTime(v.mtime) }}</div>
      <video
        :src="v.url"
        controls
        preload="metadata"
        class="video-preview"
        @error="$event.target.style.display='none'"
      >
        您的浏览器不支持视频播放，<a :href="v.url" download>下载</a>
      </video>
    </div>
  </a-drawer>
</template>

<script lang="ts" setup>
  defineOptions({ name: 'TestReport' });
  import { ref, computed, onMounted } from 'vue';
  import { useRoute } from 'vue-router';
  import { FileTextOutlined } from '@ant-design/icons-vue';
  import { message } from 'ant-design-vue';
  import http from '@/api/platform/http';

  const route = useRoute();

  const reports = ref<any[]>([]);
  const loading = ref(false);
  const keyword = ref('');       // 任务名搜索
  const filterResult = ref('');  // 结果筛选：'' | 'pass' | 'fail'

  const page = ref(1);
  const pageSize = ref(10);
  const pageData = computed(() => {
    const start = (page.value - 1) * pageSize.value;
    return filteredReports.value.slice(start, start + pageSize.value);
  });


  const filteredReports = computed(() => {
    const kw = keyword.value.trim().toLowerCase();
    return reports.value.filter((r) => {
      if (kw && !(r.case_name || '').toLowerCase().includes(kw)) return false;
      if (filterResult.value === 'pass' && !passed(r)) return false;
      if (filterResult.value === 'fail' && passed(r)) return false;
      return true;
    });
  });

  const detailVisible = ref(false);
  const detail = ref<any>(null);
  const detailTitle = ref('');

  const logVisible = ref(false);
  const logContent = ref('');
  const logTitle = ref('');

  const videoVisible = ref(false);
  const videoTitle = ref('');
  const videos = ref<any[]>([]);
  const videoTaskId = ref('');

  const suiteOpen = ref<Record<number, boolean>>({});
  const suiteData = computed(() => {
    const tests = detail.value?.tests || [];
    const groups: Record<string, any> = {};
    for (const t of tests) {
      const file = (t.nodeid || '').split('::')[0] || 'unknown';
      if (!groups[file]) groups[file] = { name: file, cases: [], total: 0, passed: 0, failed: 0, error: 0, skipped: 0, duration: 0 };
      const parts = (t.nodeid || '').split('::');
      const shortName = parts.length > 2 ? parts.slice(1).join('::') : t.nodeid;
      const msg = t.message || '';
      const lines = msg.split('\n');
      groups[file].cases.push({
        ...t,
        shortName,
        messageLine: lines[0] || '',
        messageBody: lines.slice(1).filter(Boolean).join('\n') || '',
      });
      groups[file].total++;
      if (t.outcome === 'passed') groups[file].passed++;
      else if (t.outcome === 'failed') groups[file].failed++;
      else if (t.outcome === 'error') groups[file].error++;
      else if (t.outcome === 'skipped') groups[file].skipped++;
      groups[file].duration = Math.max(groups[file].duration, t.duration || 0);
    }
    return Object.values(groups).map((g, i) => ({
      ...g,
      cls: g.failed || g.error ? 'failed' : g.skipped === g.total ? 'skipped' : 'passed',
      open: suiteOpen.value[i] !== false,
      duration: g.duration.toFixed(2),
    }));
  });

  function passRate(d: any) {
    const s = d.summary || {};
    const total = s.total || (d.tests?.length ?? 0);
    if (!total) return 0;
    return ((s.passed || 0) / total * 100).toFixed(1);
  }

  function outcomeIcon(o: string) {
    return { passed: '✅', failed: '❌', error: '❌', skipped: '⏭️' }[o] || '▪️';
  }

  function toggleSuite(idx: number) {
    suiteOpen.value[idx] = !(suiteOpen.value[idx] !== false);
  }

  function passed(row: any) {
    const s = row.summary || {};
    return !s.failed && !s.error;
  }

  function summaryText(s: any) {
    if (!s || typeof s !== 'object') return '-';
    const parts: string[] = [];
    if (s.passed) parts.push(`通过 ${s.passed}`);
    if (s.failed) parts.push(`失败 ${s.failed}`);
    if (s.error) parts.push(`错误 ${s.error}`);
    if (s.skipped) parts.push(`跳过 ${s.skipped}`);
    return parts.length ? parts.join(' / ') : '无数据';
  }

  /** 结果列分片段：每个状态单独着色 + 圆点，比纯文字更醒目（通过=绿/失败=红/错误=红/跳过=灰） */
  function resultSegments(s: any) {
    if (!s || typeof s !== 'object') return [];
    const segs: Array<{ key: string; cls: string; text: string }> = [];
    if (s.passed) segs.push({ key: 'passed', cls: 'passed', text: `通过 ${s.passed}` });
    if (s.failed) segs.push({ key: 'failed', cls: 'failed', text: `失败 ${s.failed}` });
    if (s.error) segs.push({ key: 'error', cls: 'error', text: `错误 ${s.error}` });
    if (s.skipped) segs.push({ key: 'skipped', cls: 'skipped', text: `跳过 ${s.skipped}` });
    return segs;
  }

  /** 结果列是否有可展示的片段（用于空态判定） */
  function segmentsText(s: any) {
    return resultSegments(s).length > 0;
  }

  function outcomeTag(o: string) {
    return { passed: 'success', failed: 'error', error: 'error', skipped: 'default' }[o] || 'default';
  }

  function failMsg(row: any) {
    return row.message || (row.call && row.call.longrepr) || '';
  }

  function fmtTime(ts: number) {
    if (!ts) return '-';
    return new Date(ts * 1000).toLocaleString('zh-CN', { hour12: false });
  }

  function fmtDuration(d: number) {
    if (!d || d <= 0) return '-';
    const totalSec = Math.round(d);
    if (totalSec < 60) return totalSec + 's';
    const min = Math.floor(totalSec / 60);
    const sec = totalSec % 60;
    if (min < 60) return `${min}m${sec}s`;
    const h = Math.floor(min / 60);
    return `${h}h${min % 60}m${sec}s`;
  }

  async function load() {
    loading.value = true;
    try {
      const { data } = await http.get('/cases/history', { params: { limit: 50 } });
      reports.value = Array.isArray(data) ? data : [];
    } catch (e) {
      message.error('加载报告列表失败');
    } finally {
      loading.value = false;
    }
  }

  async function openDetail(row: any) {
    detailTitle.value = `${row.case_name} · ${fmtTime(row.created)}`;
    detail.value = null;
    detailVisible.value = true;
    try {
      const { data } = await http.get(`/cases/history/${row.file}`);
      // 后端返回完整 pytest-json-report，补充摘要展示用字段
      detail.value = {
        summary: data.summary || {},
        duration: data.duration || 0,
        tests: (data.tests || []).map((t: any) => ({
          nodeid: t.nodeid,
          outcome: t.outcome,
          duration: t.duration,
          message: extractMsg(t),
        })),
      };
    } catch (e) {
      message.error('加载报告详情失败');
      detailVisible.value = false;
    }
  }

  function extractMsg(t: any) {
    const call = t.call || {};
    if (call.outcome === 'failed') {
      const lr = call.longrepr;
      if (typeof lr === 'string') return lr;
      if (lr && lr.reprcrash) return lr.reprcrash.message || '';
    }
    return '';
  }

  async function openLog(row: any) {
    if (!row.log_file) {
      message.info('该报告无关联日志文件');
      return;
    }
    logTitle.value = `日志 · ${row.case_name}`;
    logContent.value = '';
    logVisible.value = true;
    try {
      const { data } = await http.get(`/cases/log/${row.log_file}`, { responseType: 'text' });
      logContent.value = typeof data === 'string' ? data : JSON.stringify(data);
    } catch (e) {
      logContent.value = '加载日志失败';
    }
  }

  async function openVideos(row: any) {
    const tid = row.task_id;
    if (!tid) {
      message.info('该报告无关联录屏');
      return;
    }
    videoTaskId.value = tid;
    videoTitle.value = `录屏 · ${row.case_name}`;
    videos.value = [];
    videoVisible.value = true;
    try {
      const { data } = await http.get(`/cases/videos/${tid}`);
      videos.value = Array.isArray(data) ? data : [];
    } catch (e) {
      message.error('加载录屏列表失败');
    }
  }

  function fmtSize(bytes: number) {
    if (!bytes) return '0 B';
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / 1024 / 1024).toFixed(1) + ' MB';
  }

  async function clean() {
    try {
      const { data } = await http.post('/cases/clean', { keep_days: 7 });
      message.success(`已清理 ${data.deleted} 个，保留 ${data.kept} 个`);
      await load();
    } catch (e) {
      message.error('清理失败');
    }
  }

  onMounted(async () => {
    await load();
    // 从 Dashboard 跳转带 ?open=<file>：自动打开对应报告详情抽屉
    const openFile = route.query.open;
    if (openFile) {
      const row = reports.value.find((r) => r.file === openFile);
      if (row) openDetail(row);
    }
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
.pad {
  padding: 12px;
}
/* 数值列（用例数/耗时）：系统次要文字色 + 等宽数字，弱化纯数字的视觉重量 */
.col-num {
  color: var(--text-secondary);
  font-variant-numeric: tabular-nums;
}

/* ── 结果列：分段 status-badge 展示（✓/✗ logo + 颜色 + 数字，全局 .status-badge）── */
.result-cell {
  display: flex;
  flex-wrap: wrap;
  gap: 4px 8px;
}
.fail-detail {
  background: var(--bg-card-alt, #fafafa);
  border: 1px solid var(--border-color);
  color: var(--error-color);
  padding: 12px;
  border-radius: 6px;
  margin: 8px;
  font-size: var(--vben-font-size-sm);
  white-space: pre-wrap;
  line-height: 1.5;
  overflow: auto;
  max-height: 320px;
}
.log-view {
  background: #f5f6f8;
  color: var(--text-primary);
  padding: 12px;
  border-radius: 6px;
  border: 1px solid var(--border-color);
  font-size: var(--vben-font-size-sm);
  white-space: pre-wrap;
  line-height: 1.6;
  margin: 0;
  height: 100%;
  overflow: auto;
}

/* ── 报告详情样式（线性主题：浅色卡片 + 边框 + 系统配色）── */
.r-summary {
  display: flex;
  gap: 12px;
  margin-bottom: 20px;
  flex-wrap: wrap;
}
.r-summary-item {
  background: var(--bg-card-alt, #fafafa);
  border: 1px solid var(--border-color);
  border-radius: var(--vben-radius-lg);
  padding: 16px 24px;
  text-align: center;
  flex: 1;
  min-width: 100px;
}
.r-summary-item .num { font-size: 28px; font-weight: 700; }
.r-summary-item .label { font-size: var(--vben-font-size-base); color: var(--text-muted); margin-top: 2px; }
.r-summary-item .sub { font-size: var(--vben-font-size-sm); color: var(--text-muted); margin-top: 0; }
.r-summary-item.passed .num { color: var(--success-color); }
.r-summary-item.failed .num { color: var(--error-color); }
.r-summary-item.error .num { color: var(--error-color); }
.r-summary-item.skipped .num { color: var(--warning-color); }
.r-summary-item.rate .num { color: var(--info-color); }

.r-table-wrap {
  background: var(--bg-card-alt, #fafafa);
  border: 1px solid var(--border-color);
  border-radius: var(--vben-radius-lg);
  overflow: hidden;
}
.r-table { width: 100%; border-collapse: collapse; }
.r-table th {
  background: var(--bg-card-alt, #fafafa);
  text-align: left;
  padding: 10px 14px;
  font-size: var(--vben-font-size-sm);
  color: var(--text-muted);
  font-weight: 600;
  text-transform: uppercase;
}
.r-table td { padding: 8px 14px; border-top: 1px solid var(--border-color); font-size: var(--vben-font-size-lg); }
.r-table .num { text-align: center; font-variant-numeric: tabular-nums; }
.r-suite-name {
  font-weight: 600;
  cursor: pointer;
  user-select: none;
}
.r-suite-name .icon { font-size: var(--vben-font-size-sm); margin-right: 6px; color: var(--text-muted); }
/* 套件行：去状态色整行底，状态靠文字色（.passed/.failed/.error-c/.skipped）表达，
   与用例行统一为系统中性色方案 */
.r-suite.passed { background: transparent; }
.r-suite.failed { background: transparent; }
.r-suite.skipped { background: transparent; }
.r-case-name {
  padding-left: 36px !important;
  font-size: var(--vben-font-size-base);
}
/* 失败/错误用例行：不用浅红底（避免整行浓色抢眼），改为透明底仅以文字状态色
   （.failed/.error 已标红）区分；错误行保留左侧 2px 系统错误色条做弱提示 */
.r-case.failed { background: transparent; }
.r-case.error { background: transparent; box-shadow: inset 2px 0 0 var(--error-color); }
.r-case.skipped { background: transparent; }
.r-time { color: var(--text-muted); font-size: var(--vben-font-size-sm); margin-left: 8px; }
.r-icon { margin-right: 4px; }
.r-detail {
  margin-top: 6px;
  font-size: var(--vben-font-size-sm);
  color: var(--text-secondary);
}
.r-detail pre {
  background: var(--bg-card-alt, #fafafa);
  border: 1px solid var(--border-color);
  padding: 8px;
  border-radius: 6px;
  margin-top: 4px;
  font-size: var(--vben-font-size-sm);
  color: var(--text-secondary);
  max-height: 120px;
  overflow: auto;
  white-space: pre-wrap;
  word-break: break-all;
}
.passed { color: var(--success-color); }
.failed { color: var(--error-color); }
.error-c { color: var(--error-color); }
.skipped { color: var(--warning-color); }

.table-wrap { flex: 1; min-height: 0; display: flex; flex-direction: column; width: 100%; overflow: hidden; }
.table-wrap .vxe-table { flex: 1; min-height: 0; width: 100%; }
.table-wrap .vxe-table .vxe-table--body-wrapper,
.table-wrap .vxe-table .vxe-table--header-wrapper,
.table-wrap .vxe-table .vxe-table--main-wrapper,
.table-wrap .vxe-table .vxe-table--fixed-wrapper,
.table-wrap .vxe-table .vxe-body--column { overflow: hidden !important; }
.table-wrap .vxe-body--column { text-overflow: ellipsis; }
.pagination-bar {
  display: flex;
  justify-content: flex-end;
  padding-top: 12px;
  flex-shrink: 0;
}

/* 卡片撑满页面 */
.fill-card { position: absolute; top: 0; left: 0; right: 0; bottom: 0; display: flex; flex-direction: column; }
.fill-card > .ant-card-head { flex-shrink: 0; }
.fill-card > .ant-card-body { flex: 1; display: flex; flex-direction: column; min-height: 0; padding-bottom: 8px; overflow: hidden; }

/* 录屏视频样式 */
.video-item {
  margin-bottom: 20px;
  padding: 12px;
  background: var(--bg-card-alt);
  border-radius: 8px;
}
.video-name {
  font-weight: 600;
  font-size: var(--vben-font-size-lg);
  margin-bottom: 4px;
}
.video-meta {
  color: var(--text-muted);
  font-size: var(--vben-font-size-sm);
  margin-bottom: 8px;
}
.video-preview {
  width: 100%;
  max-height: 480px;
  border-radius: 4px;
  background: #000;
}
</style>
