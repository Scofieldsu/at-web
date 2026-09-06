<template>
  <div class="page">
    <!-- 选择栏 -->
    <a-card class="theme-card">
      <div class="toolbar">
        <span class="label">平台</span>
        <a-select v-model:value="platform" placeholder="选择平台" style="width: 160px" @change="onPlatformChange">
          <a-select-option v-for="p in platforms" :key="p" :value="p">{{ platformLabel(p) }}</a-select-option>
        </a-select>

        <a-divider type="vertical" />

        <span class="label">版本</span>
        <a-select
          v-model:value="version"
          placeholder="选择版本"
          style="width: 200px"
          :disabled="!platform"
          @change="onVersionChange"
        >
          <a-select-option v-for="v in versions" :key="v.version" :value="v.version">{{ v.version }}</a-select-option>
        </a-select>

        <a-button :disabled="!platform" @click="loadVersions" style="margin-left: 8px">刷新</a-button>
      </div>
    </a-card>

    <!-- 用例表格 -->
    <a-card v-if="version" class="theme-card grow">
      <template #title>
        <div class="hdr">
          <span class="sec-title tint-purple"><HistoryOutlined />{{ platformLabel(platform) }} · {{ version }} · 共 {{ cases.length }} 条用例</span>
        </div>
      </template>

      <a-table
        :data-source="cases"
        :columns="caseColumns"
        :pagination="false"
        row-key="case_name"
        class="theme-table status-table"
        :custom-row="caseRowEvents"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'execution_steps'">
            <span v-if="record.execution_steps" class="step-cell" :title="record.execution_steps">
              {{ firstLine(record.execution_steps) }}
            </span>
            <span v-else class="muted">—</span>
          </template>
          <template v-else-if="column.key === 'passed'">
            <span :class="['status-badge', record.passed ? 'passed' : 'failed']">
              {{ record.passed ? '通过' : '失败' }}
            </span>
          </template>
          <template v-else-if="column.key === 'latest_passed_report'">
            <a
              v-if="record.latest_passed_report"
              href="javascript:void(0)"
              class="report-link"
              @click.stop="openReport(record.latest_passed_report)"
            >
              {{ record.latest_passed_report }}
            </a>
            <span v-else class="muted">—</span>
          </template>
          <template v-else-if="column.key === 'latest_report'">
            <a
              v-if="record.latest_report"
              href="javascript:void(0)"
              class="report-link"
              @click.stop="openReport(record.latest_report)"
            >
              {{ record.latest_report }}
            </a>
            <span v-else class="muted">—</span>
          </template>
        </template>
      </a-table>
    </a-card>

    <!-- 未选择时的占位 -->
    <div v-if="!version" class="muted pad" style="text-align: center; padding: 60px">
      请先选择平台和版本查看记录
    </div>
  </div>

  <!-- 报告详情抽屉（复用 TestReport 的查看逻辑） -->
  <a-drawer v-model:open="detailVisible" :title="detailTitle" width="56%">
    <template v-if="detail">
      <a-descriptions :column="2" bordered size="small" style="margin-bottom: 16px">
        <a-descriptions-item label="通过">{{ detail.summary?.passed || 0 }}</a-descriptions-item>
        <a-descriptions-item label="失败">{{ detail.summary?.failed || 0 }}</a-descriptions-item>
        <a-descriptions-item label="错误">{{ detail.summary?.error || 0 }}</a-descriptions-item>
        <a-descriptions-item label="跳过">{{ detail.summary?.skipped || 0 }}</a-descriptions-item>
        <a-descriptions-item label="总数">{{ detail.summary?.total || (detail.tests?.length ?? 0) }}</a-descriptions-item>
        <a-descriptions-item label="总耗时(s)">{{ detail.duration ? detail.duration.toFixed(2) : '-' }}</a-descriptions-item>
      </a-descriptions>

      <a-table
        :data-source="detail.tests || []"
        :columns="detailColumns"
        :pagination="false"
        row-key="nodeid"
        size="small"
        class="theme-table"
      >
        <template #expandedRowRender="{ record }">
          <pre v-if="record.message" class="fail-detail">{{ record.message }}</pre>
          <span v-else class="muted" style="padding: 8px">无额外信息</span>
        </template>
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'outcome'">
            <a-tag :color="outcomeTag(record.outcome)">{{ record.outcome }}</a-tag>
          </template>
          <template v-else-if="column.key === 'duration'">
            {{ record.duration ? record.duration.toFixed(2) : '-' }}
          </template>
        </template>
      </a-table>
    </template>
    <div v-else class="muted pad">加载中…</div>
  </a-drawer>
</template>

<script lang="ts" setup>
  defineOptions({ name: 'VersionRecords' });
  import { ref, onMounted } from 'vue';
  import { HistoryOutlined } from '@ant-design/icons-vue';
  import { message } from 'ant-design-vue';
  import http from '@/api/platform/http';

  const PLATFORM_LABELS: Record<string, string> = {
    platform_a: '平台A',
    platform_b: '平台B',
    platform_c: '平台C',
    platform_d: '平台D',
  };

  const platforms = ref<any[]>([]);
  const versions = ref<any[]>([]);
  const cases = ref<any[]>([]);
  const platform = ref('');
  const version = ref('');

  // 报告详情
  const detailVisible = ref(false);
  const detail = ref<any>(null);
  const detailTitle = ref('');

  const caseColumns = [
    { title: '用例名', dataIndex: 'case_name', key: 'case_name', ellipsis: true, minWidth: 180 },
    { title: '所属模块', dataIndex: 'module', key: 'module', ellipsis: true, minWidth: 140 },
    { title: '用例执行步骤', key: 'execution_steps', minWidth: 240 },
    { title: '测试结果', key: 'passed', width: 110 },
    { title: '通过的最新报告', key: 'latest_passed_report', minWidth: 200 },
    { title: '最新报告', key: 'latest_report', minWidth: 180 },
  ];

  const detailColumns = [
    { title: '结果', key: 'outcome', width: 90 },
    { title: '测试函数 (nodeid)', dataIndex: 'nodeid', key: 'nodeid', ellipsis: true, minWidth: 320 },
    { title: '耗时(s)', key: 'duration', width: 100 },
  ];

  function caseRowEvents(record: any) {
    return {
      onClick: () => openCaseReport(record),
    };
  }

  function platformLabel(value: string) {
    return PLATFORM_LABELS[value] || value;
  }

  function firstLine(text: string) {
    if (!text) return '';
    const line = text.split('\n')[0].trim();
    return line.length > 60 ? line.slice(0, 60) + '…' : line;
  }

  function outcomeTag(o: string) {
    return { passed: 'success', failed: 'error', error: 'error', skipped: 'default' }[o] || 'default';
  }

  async function loadPlatforms() {
    try {
      const { data } = await http.get('/version-records/platforms');
      platforms.value = Array.isArray(data) ? data : [];
      // 如果当前 platform 不再有效，自动清除
      if (platform.value && !platforms.value.includes(platform.value)) {
        platform.value = '';
        versions.value = [];
        cases.value = [];
        version.value = '';
      }
      // 首次进入：默认选中第一个平台，并自动加载其最新版本（版本列表按更新时间倒序，取第一条）
      if (!platform.value && platforms.value.length) {
        platform.value = platforms.value[0];
        await loadVersions();
        if (versions.value.length) {
          version.value = versions.value[0].version;
          await onVersionChange();
        }
      }
    } catch (e) {
      message.error('加载平台列表失败');
    }
  }

  async function onPlatformChange() {
    version.value = '';
    cases.value = [];
    await loadVersions();
  }

  async function loadVersions() {
    if (!platform.value) return;
    try {
      const { data } = await http.get(`/version-records/${platform.value}/versions`);
      versions.value = Array.isArray(data) ? data : [];
    } catch (e) {
      message.error('加载版本列表失败');
    }
  }

  async function onVersionChange() {
    if (!platform.value || !version.value) return;
    try {
      const { data } = await http.get(`/version-records/${platform.value}/${version.value}`);
      cases.value = data.cases || [];
    } catch (e) {
      message.error('加载版本用例失败');
    }
  }

  async function openReport(filename: string) {
    if (!filename) return;
    detailTitle.value = filename;
    detail.value = null;
    detailVisible.value = true;
    try {
      const { data } = await http.get(`/cases/history/${filename}`);
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

  function openCaseReport(row: any) {
    // 点击行时打开最新报告（优先打开通过的，否则打开最近的）
    const target = row.latest_passed_report || row.latest_report;
    if (target) openReport(target);
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

  onMounted(loadPlatforms);
</script>

<style scoped>
.page {
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.toolbar {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}
.label {
  color: var(--text-secondary);
  font-size: var(--vben-font-size-lg);
  font-weight: 600;
}
.grow {
  flex: 1;
  display: flex;
  flex-direction: column;
}
.grow :deep(.el-card__body) {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
}
.grow :deep(.el-table) {
  flex: 1;
}
.hdr {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.muted {
  color: var(--text-muted);
}
.pad {
  padding: 12px;
}
.report-link {
  color: var(--accent);
  text-decoration: none;
  font-size: var(--vben-font-size-sm);
  word-break: break-all;
}
.report-link:hover {
  text-decoration: underline;
  opacity: 0.8;
}
.step-cell {
  font-size: var(--vben-font-size-sm);
  color: var(--text-secondary);
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.status-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 2px 12px;
  border-radius: 12px;
  font-size: var(--vben-font-size-sm);
  font-weight: 600;
  letter-spacing: 0.5px;
  min-width: 52px;
}
.status-badge.passed {
  background: rgba(48, 164, 108, 0.12);
  color: var(--success-color);
  border: 1px solid rgba(48, 164, 108, 0.35);
}
.status-badge.passed::before {
  content: "✓ ";
  font-weight: 700;
}
.status-badge.failed {
  background: rgba(248, 113, 113, 0.12);
  color: var(--error-color);
  border: 1px solid rgba(248, 113, 113, 0.25);
}
.status-badge.failed::before {
  content: "✗ ";
  font-weight: 700;
}
.step-detail {
  padding: 12px 16px;
}
.step-detail strong {
  color: var(--text-secondary);
  font-size: var(--vben-font-size-base);
}
.step-detail pre {
  background: rgba(0,0,0,0.3);
  color: var(--text-secondary);
  padding: 10px;
  border-radius: 6px;
  font-size: var(--vben-font-size-sm);
  line-height: 1.6;
  white-space: pre-wrap;
  margin: 6px 0 0;
  overflow: auto;
  max-height: 200px;
}
.fail-detail {
  background: #0d0f13;
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
</style>
