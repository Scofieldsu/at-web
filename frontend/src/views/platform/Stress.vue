<template>
  <div class="stress-page">
    <!-- ① 快速预设 -->
    <a-card class="theme-card">
      <template #title>
        <div class="hdr">
          <span class="sec-title tint-indigo"><ThunderboltOutlined />快速预设</span>
          <span class="muted">点击套用参数，可继续微调</span>
        </div>
      </template>
      <a-row :gutter="[16, 16]">
        <a-col v-for="p in presets" :key="p.key" :xs="24" :sm="12" :lg="6">
          <div
            class="preset-card"
            :class="{ recommended: p.recommended, active: presetKey === p.key }"
            @click="applyPreset(p)"
          >
            <div class="preset-title">
              {{ p.name }}
              <a-tag v-if="p.recommended" color="success" style="margin-left: 6px">推荐</a-tag>
            </div>
            <div class="preset-desc">{{ p.description }}</div>
            <a-divider style="margin: 10px 0" />
            <div class="preset-params">
              <div class="pp"><DashboardOutlined />并发 {{ p.config.concurrency }}</div>
              <div class="pp"><FireOutlined />{{ MODEL_TEXT[p.config.model] }}</div>
              <div class="pp"><ClockCircleOutlined />时长 {{ fmtDur(p.config.duration) }}</div>
            </div>
          </div>
        </a-col>
      </a-row>
    </a-card>

    <!-- ② 压测参数 -->
    <a-card class="theme-card" style="margin-top: 16px">
      <template #title>
        <div class="hdr">
          <span class="sec-title tint-indigo"><ControlOutlined />压测参数</span>
          <div>
            <a-input
              v-model:value="form.scenario"
              placeholder="场景名称"
              size="small"
              style="width: 160px"
              :disabled="running"
            />
          </div>
        </div>
      </template>

      <a-row :gutter="24">
        <!-- 左：目标设置 -->
        <a-col :xs="24" :md="10">
          <div class="form-sec-title">测试目标</div>
          <a-form layout="vertical" :disabled="running">
            <a-form-item label="目标接口">
              <a-select v-model:value="form.target_api" @change="onTargetApiChange">
                <a-select-option value="send-text">消息发送（/api/ui/send-text）</a-select-option>
                <a-select-option value="order-fetch">拉取订单（/api/ui/order-fetch）</a-select-option>
                <a-select-option value="query-msg">消息查询（/api/ui/messages）</a-select-option>
                <a-select-option value="custom">自定义 URL</a-select-option>
              </a-select>
            </a-form-item>
            <a-form-item v-if="form.target_api === 'custom'" label="自定义 URL">
              <a-input v-model:value="form.target_url" placeholder="https://.../api/xxx" />
            </a-form-item>
            <a-form-item label="协议">
              <a-radio-group v-model:value="protocol">
                <a-radio value="http">HTTP/HTTPS</a-radio>
                <a-radio value="ws">WebSocket</a-radio>
              </a-radio-group>
            </a-form-item>
            <a-form-item label="连接方式">
              <a-space>
                <a-checkbox v-model:checked="form.keep_alive">Keep-Alive 连接复用</a-checkbox>
                <a-checkbox v-model:checked="form.parameterized">数据集参数化</a-checkbox>
              </a-space>
            </a-form-item>
          </a-form>
        </a-col>

        <!-- 右：负载模型 + 时长 -->
        <a-col :xs="24" :md="14">
          <div class="form-sec-title">负载模型</div>
          <a-form layout="vertical" :disabled="running">
            <a-form-item>
              <a-radio-group v-model:value="form.model" button-style="solid">
                <a-radio-button value="constant">恒并发</a-radio-button>
                <a-radio-button value="ramp">爬坡</a-radio-button>
                <a-radio-button value="step">阶梯</a-radio-button>
                <a-radio-button value="spike">尖峰脉冲</a-radio-button>
              </a-radio-group>
            </a-form-item>

            <a-row :gutter="12">
              <a-col :xs="24" :sm="8">
                <a-form-item label="目标并发数">
                  <a-input-number v-model:value="form.concurrency" :min="1" :max="500" style="width: 100%" />
                </a-form-item>
              </a-col>
              <a-col v-if="form.model === 'ramp'" :xs="24" :sm="8">
                <a-form-item label="爬坡时间 (s)">
                  <a-input-number v-model:value="form.ramp_up" :min="1" style="width: 100%" />
                </a-form-item>
              </a-col>
              <a-col v-if="form.model === 'step'" :xs="24" :sm="8">
                <a-form-item label="阶梯数">
                  <a-input-number v-model:value="form.steps" :min="2" :max="10" style="width: 100%" />
                </a-form-item>
              </a-col>
              <a-col v-if="form.model === 'step'" :xs="24" :sm="8">
                <a-form-item label="阶梯间隔 (s)">
                  <a-input-number v-model:value="form.step_interval" :min="5" style="width: 100%" />
                </a-form-item>
              </a-col>
              <a-col v-if="form.model === 'spike'" :xs="24" :sm="8">
                <a-form-item label="峰值并发">
                  <a-input-number v-model:value="form.peak" :min="2" :max="500" style="width: 100%" />
                </a-form-item>
              </a-col>
              <a-col v-if="form.model === 'spike'" :xs="24" :sm="8">
                <a-form-item label="尖峰持续 (s)">
                  <a-input-number v-model:value="form.peak_duration" :min="5" style="width: 100%" />
                </a-form-item>
              </a-col>
            </a-row>

            <a-row :gutter="12">
              <a-col :xs="24" :sm="8">
                <a-form-item label="总时长">
                  <div class="dur-input">
                    <a-input-number v-model:value="form.duration" :min="1" style="width: 100%" />
                    <a-select :value="durUnit" style="width: 84px" @change="onDurUnit">
                      <a-select-option :value="1">秒</a-select-option>
                      <a-select-option :value="60">分钟</a-select-option>
                      <a-select-option :value="3600">小时</a-select-option>
                    </a-select>
                  </div>
                </a-form-item>
              </a-col>
              <a-col :xs="24" :sm="8">
                <a-form-item label="总请求数">
                  <a-input-number v-model:value="form.total_requests" :min="0" placeholder="0 = 到时止" style="width: 100%" />
                </a-form-item>
              </a-col>
              <a-col :xs="24" :sm="8">
                <a-form-item label="思考时间 (ms)">
                  <a-input-number v-model:value="form.think_time" :min="0" style="width: 100%" />
                </a-form-item>
              </a-col>
            </a-row>

            <a-row :gutter="12">
              <a-col :xs="24" :sm="8">
                <a-form-item label="请求超时 (s)">
                  <a-input-number v-model:value="form.timeout" :min="1" :max="300" style="width: 100%" />
                </a-form-item>
              </a-col>
            </a-row>
          </a-form>

          <a-collapse v-model:activeKey="advKeys" :bordered="false" class="adv-collapse" :disabled="running">
            <a-collapse-panel key="adv" header="高级设置 · 断言阈值">
              <a-row :gutter="12">
                <a-col :xs="24" :sm="8">
                  <a-form-item label="最小成功率 (%)">
                    <a-input-number v-model:value="form.assertions.min_success_rate" :min="0" :max="100" style="width: 100%" />
                  </a-form-item>
                </a-col>
                <a-col :xs="24" :sm="8">
                  <a-form-item label="P95 上限 (ms)">
                    <a-input-number v-model:value="form.assertions.max_p95" :min="0" placeholder="不限制" style="width: 100%" />
                  </a-form-item>
                </a-col>
                <a-col :xs="24" :sm="8">
                  <a-form-item label="最大错误率 (%)">
                    <a-input-number v-model:value="form.assertions.max_error_rate" :min="0" :max="100" placeholder="不限制" style="width: 100%" />
                  </a-form-item>
                </a-col>
              </a-row>
              <a-form-item :wrapper-col="{ offset: 0 }">
                <a-checkbox v-model:checked="form.assertions.stop_on_fail">任一断言失败时自动停止</a-checkbox>
              </a-form-item>
            </a-collapse-panel>
          </a-collapse>
        </a-col>
      </a-row>
    </a-card>

    <!-- ③ 执行监控 -->
    <a-card class="theme-card" style="margin-top: 16px">
      <template #title>
        <div class="hdr">
          <span class="sec-title tint-green"><LineChartOutlined />执行监控</span>
          <div class="run-actions">
            <a-tag :color="statusColor" class="status-tag">{{ statusText }}</a-tag>
            <span v-if="status.stop_reason" class="muted" style="margin-right: 12px">{{ status.stop_reason }}</span>
            <a-button
              v-if="!running"
              type="primary"
              :loading="starting"
              size="small"
              @click="startStress"
            >
              <PlayCircleOutlined /> 开始压测
            </a-button>
            <a-button v-else danger :loading="stopping" size="small" @click="stopStress">
              <StopOutlined /> 停止
            </a-button>
          </div>
        </div>
      </template>

      <div v-if="running" class="progress-row">
        <a-progress :percent="progressPct" :stroke-color="{ '0%': '#818cf8', '100%': '#6366f1' }" style="flex: 1" />
        <span class="muted" style="font-size: 12px; white-space: nowrap; margin-left: 12px">
          {{ fmtDur(status.elapsed_seconds) }} / {{ fmtDur(status.config?.duration || 0) }}
        </span>
      </div>

      <!-- 实时指标卡 -->
      <a-row :gutter="[12, 12]" class="metric-row">
        <a-col :xs="12" :sm="8" :md="4">
          <div class="metric-card">
            <div class="metric-label">实时 RPS</div>
            <div class="metric-value">
              {{ running && last ? last.rps : '--' }}
            </div>
            <div class="metric-sub">并发 {{ last?.concurrency ?? 0 }} / {{ status.target_concurrency }}</div>
          </div>
        </a-col>
        <a-col :xs="12" :sm="8" :md="4">
          <div class="metric-card">
            <div class="metric-label">平均响应</div>
            <div class="metric-value" :class="latencyTone(last?.avg)">
              {{ running && last ? `${last.avg} ms` : '--' }}
            </div>
            <div class="metric-sub">超时阈值 {{ form.timeout }}s</div>
          </div>
        </a-col>
        <a-col :xs="12" :sm="8" :md="4">
          <div class="metric-card">
            <div class="metric-label">P95 响应</div>
            <div class="metric-value" :class="latencyTone(last?.p95)">
              {{ running && last ? `${last.p95} ms` : '--' }}
            </div>
            <div class="metric-sub">P99 {{ running && last ? `${last.p99} ms` : '--' }}</div>
          </div>
        </a-col>
        <a-col :xs="12" :sm="8" :md="4">
          <div class="metric-card">
            <div class="metric-label">错误率</div>
            <div class="metric-value" :class="errorTone(running ? 100 - (last?.success_rate ?? 100) : null)">
              {{ running && last ? `${(100 - last.success_rate).toFixed(2)}%` : '--' }}
            </div>
            <div class="metric-sub">失败 {{ status.failed }}</div>
          </div>
        </a-col>
        <a-col :xs="12" :sm="8" :md="4">
          <div class="metric-card">
            <div class="metric-label">已完成请求</div>
            <div class="metric-value">{{ status.completed || '--' }}</div>
            <div class="metric-sub">
              {{ form.total_requests ? `目标 ${form.total_requests}` : '到时止' }}
            </div>
          </div>
        </a-col>
        <a-col :xs="12" :sm="8" :md="4">
          <div class="metric-card">
            <div class="metric-label">成功率</div>
            <div class="metric-value" :class="successTone(running ? last?.success_rate : null)">
              {{ running && last ? `${last.success_rate}%` : '--' }}
            </div>
            <div class="metric-sub">断言 {{ form.assertions.stop_on_fail ? '开启' : '关闭' }}</div>
          </div>
        </a-col>
      </a-row>

      <!-- 实时曲线 -->
      <a-row :gutter="[16, 16]" class="chart-row">
        <a-col :xs="24" :lg="12">
          <div class="chart-title">TPS / 并发</div>
          <div ref="tpsChartRef" class="chart-box"></div>
        </a-col>
        <a-col :xs="24" :lg="12">
          <div class="chart-title">响应时间（avg / p95 / p99）</div>
          <div ref="latencyChartRef" class="chart-box"></div>
        </a-col>
      </a-row>
    </a-card>

    <!-- ④ 执行报告 -->
    <a-card v-if="report" class="theme-card" style="margin-top: 16px">
      <template #title>
        <div class="hdr">
          <span class="sec-title tint-orange"><FileTextOutlined />执行报告</span>
          <span class="muted">
            {{ report.scenario }} · {{ report.started_at }} · {{ report.stop_reason || '正常完成' }}
          </span>
        </div>
      </template>

      <a-row :gutter="[12, 12]">
        <a-col v-for="c in reportCards" :key="c.label" :xs="12" :sm="8" :md="4" :lg="3">
          <div class="metric-card">
            <div class="metric-label">{{ c.label }}</div>
            <div class="metric-value" :class="c.tone">{{ c.value }}</div>
          </div>
        </a-col>
      </a-row>

      <div class="chart-title" style="margin-top: 16px">响应时间分布</div>
      <div ref="histChartRef" class="chart-box"></div>
    </a-card>

    <!-- ⑤ 历史记录 -->
    <a-card class="theme-card" style="margin-top: 16px">
      <template #title>
        <div class="hdr">
          <span class="sec-title tint-blue"><HistoryOutlined />历史记录</span>
          <a-button size="small" :loading="loadingHistory" @click="loadHistory">刷新</a-button>
        </div>
      </template>
      <a-table
        :data-source="history"
        :columns="historyColumns"
        :pagination="false"
        row-key="task_id"
        class="theme-table"
        size="small"
        :locale="{ emptyText: '暂无历史记录' }"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'status'">
            <a-tag :color="record.status === 'completed' ? 'success' : 'warning'">
              {{ record.status === 'completed' ? '完成' : '停止' }}
            </a-tag>
          </template>
          <template v-else-if="column.key === 'success_rate'">
            <span :class="record.success_rate >= 99 ? 'tone-green' : 'tone-orange'">
              {{ record.success_rate }}%
            </span>
          </template>
          <template v-else-if="column.key === 'duration'">
            {{ fmtDur(record.duration_seconds) }}
          </template>
        </template>
      </a-table>
    </a-card>
  </div>
</template>

<script lang="ts" setup>
  defineOptions({ name: 'Stress' });
  import { ref, reactive, computed, onMounted, onUnmounted, nextTick } from 'vue';
  import {
    ThunderboltOutlined,
    ControlOutlined,
    LineChartOutlined,
    FileTextOutlined,
    HistoryOutlined,
    PlayCircleOutlined,
    StopOutlined,
    ClockCircleOutlined,
    FireOutlined,
    DashboardOutlined,
  } from '@ant-design/icons-vue';
  import { message } from 'ant-design-vue';
  import { useECharts } from '@/hooks/web/useECharts';
  import http from '@/api/platform/http';

  const MODEL_TEXT: Record<string, string> = {
    constant: '恒并发',
    ramp: '爬坡',
    step: '阶梯',
    spike: '尖峰脉冲',
  };

  // ---- 预设 ----
  const presets = ref<any[]>([]);
  const presetKey = ref('');

  async function loadPresets() {
    try {
      const { data } = await http.get('/stress/presets');
      presets.value = Array.isArray(data) ? data : [];
    } catch {
      /* 演示：忽略 */
    }
  }

  function applyPreset(p: any) {
    presetKey.value = p.key;
    const c = p.config;
    Object.assign(form, {
      scenario: c.scenario || p.name,
      model: c.model,
      concurrency: c.concurrency,
      ramp_up: c.ramp_up ?? 10,
      steps: c.steps ?? 3,
      step_interval: c.step_interval ?? 60,
      peak: c.peak ?? c.concurrency * 2,
      peak_duration: c.peak_duration ?? 30,
      duration: c.duration,
      total_requests: c.total_requests ?? 0,
      think_time: c.think_time ?? 0,
    });
    durUnit.value = c.duration >= 3600 ? 3600 : c.duration >= 60 ? 60 : 1;
    message.success(`已套用预设「${p.name}」`);
  }

  // ---- 表单 ----
  const form = reactive({
    scenario: '标准负载',
    target_api: 'send-text' as string,
    target_url: '',
    keep_alive: true,
    parameterized: false,
    model: 'ramp' as 'constant' | 'ramp' | 'step' | 'spike',
    concurrency: 20,
    ramp_up: 10,
    steps: 3,
    step_interval: 60,
    peak: 40,
    peak_duration: 30,
    duration: 300,
    total_requests: 0,
    think_time: 0,
    timeout: 5,
    assertions: {
      min_success_rate: 99,
      max_p95: 800,
      max_error_rate: 1,
      stop_on_fail: false,
    } as {
      min_success_rate?: number;
      max_p95?: number;
      max_error_rate?: number;
      stop_on_fail: boolean;
    },
  });
  const protocol = ref<'http' | 'ws'>('http');
  const advKeys = ref<string[]>([]);
  const durUnit = ref(1);

  function onTargetApiChange(v: string) {
    if (v !== 'custom') form.target_url = '';
  }

  // 切换时长单位：保持总秒数不变，换算显示值
  function onDurUnit(unit: number) {
    const seconds = form.duration * durUnit.value;
    durUnit.value = unit;
    form.duration = Math.max(1, Math.round(seconds / unit));
  }

  function fmtDur(s: number | undefined | null): string {
    if (!s) return '-';
    s = Math.floor(s);
    if (s >= 3600) return `${Math.floor(s / 3600)}h ${Math.floor((s % 3600) / 60)}m`;
    if (s >= 60) return `${Math.floor(s / 60)}m ${s % 60}s`;
    return `${s}s`;
  }

  // ---- 运行状态 ----
  const status = ref<any>({});
  const starting = ref(false);
  const stopping = ref(false);
  const running = computed(() => status.value.running === true);
  const last = computed(() => status.value.last_point || null);
  const progressPct = computed(() => Math.round((status.value.progress || 0) * 100));
  const statusText = computed(() =>
    running.value ? '运行中' : status.value.status === 'stopped' ? '已停止' : status.value.status === 'completed' ? '已完成' : '未开始',
  );
  const statusColor = computed(() =>
    running.value ? 'processing' : status.value.status === 'completed' ? 'success' : status.value.status === 'stopped' ? 'warning' : 'default',
  );

  // 指标卡配色阈值（绿/橙/红，走项目语义色）
  function latencyTone(v?: number) {
    if (v == null) return '';
    if (v >= 1000) return 'tone-red';
    if (v >= 400) return 'tone-orange';
    return 'tone-green';
  }
  function errorTone(v?: number) {
    if (v == null) return '';
    if (v >= 5) return 'tone-red';
    if (v >= 1) return 'tone-orange';
    return 'tone-green';
  }
  function successTone(v?: number) {
    if (v == null) return '';
    if (v < 95) return 'tone-red';
    if (v < 99) return 'tone-orange';
    return 'tone-green';
  }

  let pollTimer: ReturnType<typeof setInterval> | null = null;
  let lastAfter = 0;
  const points = ref<any[]>([]);

  async function pollOnce() {
    try {
      const { data } = await http.get('/stress/status');
      status.value = data;
      const { data: pts } = await http.get('/stress/metrics', { params: { after: lastAfter } });
      if (Array.isArray(pts) && pts.length) {
        points.value = points.value.concat(pts);
        lastAfter += pts.length;
        updateCharts();
      }
      // 运行中 → 拉报告与历史；刚结束 → 清理
      if (!data.running) {
        if (data.status === 'completed' || data.status === 'stopped') {
          await loadReport();
          await loadHistory();
        }
        stopPolling();
      }
    } catch {
      /* 轮询失败忽略，下轮重试 */
    }
  }

  function startPolling() {
    stopPolling();
    pollOnce();
    pollTimer = setInterval(pollOnce, 1500);
  }
  function stopPolling() {
    if (pollTimer) {
      clearInterval(pollTimer);
      pollTimer = null;
    }
  }

  async function startStress() {
    starting.value = true;
    try {
      points.value = [];
      lastAfter = 0;
      report.value = null;
      const cfg = {
        scenario: form.scenario,
        target_api: form.target_api,
        target_url: form.target_api === 'custom' ? form.target_url : '',
        keep_alive: form.keep_alive,
        model: form.model,
        concurrency: form.concurrency,
        ramp_up: form.ramp_up,
        steps: form.steps,
        step_interval: form.step_interval,
        peak: form.peak,
        peak_duration: form.peak_duration,
        duration: form.duration * durUnit.value,
        total_requests: form.total_requests,
        think_time: form.think_time,
        timeout: form.timeout,
        assertions: { ...form.assertions },
      };
      const { data } = await http.post('/stress/start', { config: cfg });
      if (!data.success) {
        message.error(data.error || '启动失败');
        return;
      }
      message.success(data.message);
      startPolling();
    } catch (e: any) {
      message.error(e.response?.data?.error || '启动请求失败');
    } finally {
      starting.value = false;
    }
  }

  async function stopStress() {
    stopping.value = true;
    try {
      const { data } = await http.post('/stress/stop', {});
      if (!data.success) message.error(data.error || '停止失败');
    } catch {
      message.error('停止请求失败');
    } finally {
      stopping.value = false;
    }
  }

  // ---- 报告 ----
  const report = ref<any>(null);
  const reportCards = computed(() => {
    const r = report.value;
    if (!r) return [];
    return [
      { label: '总请求数', value: r.total?.toLocaleString() ?? '-' },
      { label: '成功 / 失败', value: `${(r.success ?? 0).toLocaleString()} / ${r.failed}` },
      { label: '成功率', value: `${r.success_rate}%`, tone: successTone(r.success_rate) },
      { label: '平均 RPS', value: r.avg_rps },
      { label: '峰值 RPS', value: r.max_rps },
      { label: '平均响应', value: `${r.avg} ms`, tone: latencyTone(r.avg) },
      { label: 'Min / Max', value: `${r.min} / ${r.max} ms` },
      { label: 'P50', value: `${r.p50} ms` },
      { label: 'P90', value: `${r.p90} ms` },
      { label: 'P95', value: `${r.p95} ms`, tone: latencyTone(r.p95) },
      { label: 'P99', value: `${r.p99} ms`, tone: latencyTone(r.p99) },
      { label: '最大并发', value: r.max_concurrency },
    ];
  });

  async function loadReport() {
    try {
      const { data } = await http.get('/stress/report');
      if (data.available) {
        report.value = data;
        await nextTick();
        renderHist();
      }
    } catch {
      /* 忽略 */
    }
  }

  // ---- 历史 ----
  const history = ref<any[]>([]);
  const loadingHistory = ref(false);
  const historyColumns = [
    { title: '开始时间', dataIndex: 'started_at', key: 'started_at', width: 150 },
    { title: '场景', dataIndex: 'scenario', key: 'scenario' },
    { title: '模型', dataIndex: 'model', key: 'model', width: 90 },
    { title: '并发', dataIndex: 'concurrency', key: 'concurrency', width: 70 },
    { title: '时长', key: 'duration', width: 80 },
    { title: '平均 RPS', dataIndex: 'avg_rps', key: 'avg_rps', width: 90 },
    { title: '平均响应', dataIndex: 'avg_ms', key: 'avg_ms', width: 90 },
    { title: 'P95', dataIndex: 'p95_ms', key: 'p95_ms', width: 80 },
    { title: '成功率', key: 'success_rate', width: 80 },
    { title: '状态', key: 'status', width: 70 },
  ];

  async function loadHistory() {
    loadingHistory.value = true;
    try {
      const { data } = await http.get('/stress/history');
      history.value = Array.isArray(data) ? data : [];
    } catch {
      /* 忽略 */
    } finally {
      loadingHistory.value = false;
    }
  }

  // ---- 图表 ----
  const tpsChartRef = ref<HTMLDivElement | null>(null);
  const latencyChartRef = ref<HTMLDivElement | null>(null);
  const histChartRef = ref<HTMLDivElement | null>(null);
  const { setOptions: setTpsOptions } = useECharts(tpsChartRef, 'default');
  const { setOptions: setLatencyOptions } = useECharts(latencyChartRef, 'default');
  const { setOptions: setHistOptions } = useECharts(histChartRef, 'default');

  function chartColors() {
    return { indigo: '#6366f1', blue: '#0090ff', orange: '#f76b15', red: '#e5484d', green: '#30a46c' };
  }

  function updateCharts() {
    const pts = points.value.slice(-300);
    if (!pts.length) return;
    const x = pts.map((p) => `${p.t}s`);
    const c = chartColors();
    setTpsOptions({
      grid: { left: 44, right: 16, top: 30, bottom: 24 },
      tooltip: { trigger: 'axis' },
      legend: { data: ['RPS', '并发'], top: 0, textStyle: { fontSize: 11 } },
      xAxis: { type: 'category', data: x, axisLabel: { fontSize: 10, color: '#9ca3af' } },
      yAxis: [
        { type: 'value', name: 'RPS', axisLabel: { fontSize: 10, color: '#9ca3af' }, splitLine: { lineStyle: { color: '#eef0f3' } } },
        { type: 'value', name: '并发', axisLabel: { fontSize: 10, color: '#9ca3af' }, splitLine: { show: false } },
      ],
      series: [
        {
          name: 'RPS', type: 'line', data: pts.map((p) => p.rps), smooth: true, symbol: 'none',
          lineStyle: { width: 2, color: c.indigo },
          areaStyle: { color: 'rgba(99,102,241,0.12)' },
        },
        {
          name: '并发', type: 'line', yAxisIndex: 1, data: pts.map((p) => p.concurrency),
          step: 'middle', symbol: 'none', lineStyle: { width: 1.5, type: 'dashed', color: c.blue },
        },
      ],
    });
    setLatencyOptions({
      grid: { left: 44, right: 16, top: 30, bottom: 24 },
      tooltip: { trigger: 'axis', valueFormatter: (v: any) => `${v} ms` },
      legend: { data: ['avg', 'p95', 'p99'], top: 0, textStyle: { fontSize: 11 } },
      xAxis: { type: 'category', data: x, axisLabel: { fontSize: 10, color: '#9ca3af' } },
      yAxis: { type: 'value', name: 'ms', axisLabel: { fontSize: 10, color: '#9ca3af' }, splitLine: { lineStyle: { color: '#eef0f3' } } },
      series: [
        { name: 'avg', type: 'line', data: pts.map((p) => p.avg), smooth: true, symbol: 'none', lineStyle: { width: 2, color: c.indigo } },
        { name: 'p95', type: 'line', data: pts.map((p) => p.p95), smooth: true, symbol: 'none', lineStyle: { width: 1.5, color: c.orange } },
        { name: 'p99', type: 'line', data: pts.map((p) => p.p99), smooth: true, symbol: 'none', lineStyle: { width: 1.5, color: c.red } },
      ],
    });
  }

  function renderHist() {
    const r = report.value;
    if (!r?.histogram?.length) return;
    const c = chartColors();
    const p95 = Number(r.p95) || 0;
    // 上限超过 P95 的分档标红，直观展示长尾
    const edges: Record<string, number> = {
      '50-100': 100, '100-200': 200, '200-400': 400, '400-800': 800, '800-1500': 1500, '1500+': 1e9,
    };
    setHistOptions({
      grid: { left: 44, right: 16, top: 30, bottom: 24 },
      tooltip: {
        trigger: 'axis',
        formatter: (params: any) => {
          const p = Array.isArray(params) ? params[0] : params;
          return `${p.name}<br/>请求数 ${p.value}（占比见柱高）`;
        },
      },
      xAxis: { type: 'category', data: r.histogram.map((h: any) => h.label), axisLabel: { fontSize: 10, color: '#9ca3af' } },
      yAxis: { type: 'value', name: '请求数', axisLabel: { fontSize: 10, color: '#9ca3af' }, splitLine: { lineStyle: { color: '#eef0f3' } } },
      series: [
        {
          name: '分布', type: 'bar', barWidth: '55%',
          data: r.histogram.map((h: any) => ({
            value: h.count,
            itemStyle: {
              color: (edges[h.label] || 0) > p95 ? c.red : c.indigo,
              borderRadius: [3, 3, 0, 0],
            },
          })),
        },
      ],
    });
  }

  // ---- 生命周期：进入页面恢复运行中任务状态 ----
  onMounted(async () => {
    loadPresets();
    loadHistory();
    loadReport();
    try {
      const { data } = await http.get('/stress/status');
      status.value = data;
      if (data.running) {
        lastAfter = 0;
        startPolling();
      }
    } catch {
      /* 忽略 */
    }
  });

  onUnmounted(stopPolling);
</script>

<style scoped>
.hdr {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.muted {
  color: var(--text-muted);
  font-size: 12px;
}

/* 预设卡（参考 WeakNet 的 preset-card 风格） */
.preset-card {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 14px;
  height: 100%;
  cursor: pointer;
  transition: all 0.2s;
}
.preset-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 4px 12px rgba(99, 102, 241, 0.14);
  border-color: rgba(99, 102, 241, 0.4);
}
.preset-card.recommended {
  border-color: rgba(48, 164, 108, 0.5);
}
.preset-card.active {
  border-color: var(--accent);
  background: var(--accent-bg);
}
.preset-title {
  font-size: 14px;
  font-weight: 600;
}
.preset-desc {
  font-size: 12px;
  color: var(--text-secondary);
  line-height: 1.6;
  min-height: 36px;
  margin-top: 4px;
}
.preset-params {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.pp {
  display: flex;
  align-items: center;
  gap: 7px;
  font-size: 12.5px;
  color: var(--text-secondary);
}
.pp .anticon {
  color: var(--accent);
}

/* 表单分区标题 */
.form-sec-title {
  font-size: 13px;
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: 12px;
  padding-left: 8px;
  border-left: 3px solid var(--accent);
}
.dur-input {
  display: flex;
  gap: 8px;
}
.adv-collapse {
  background: var(--bg-card-alt);
  border-radius: 8px;
  margin-top: 4px;
}

/* 运行区 */
.run-actions {
  display: flex;
  align-items: center;
}
.status-tag {
  margin-right: 10px;
}
.progress-row {
  display: flex;
  align-items: center;
  margin-bottom: 16px;
}

/* 指标卡 */
.metric-row {
  margin-top: 4px;
}
.metric-card {
  background: var(--bg-card-alt);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 12px 14px;
  height: 100%;
}
.metric-label {
  font-size: 12px;
  color: var(--text-muted);
}
.metric-value {
  font-size: 22px;
  font-weight: 700;
  margin-top: 4px;
  font-variant-numeric: tabular-nums;
}
.metric-sub {
  font-size: 11.5px;
  color: var(--text-muted);
  margin-top: 3px;
}
.tone-green {
  color: var(--success-color);
}
.tone-orange {
  color: var(--warning-color);
}
.tone-red {
  color: var(--error-color);
}

/* 图表 */
.chart-row {
  margin-top: 16px;
}
.chart-title {
  font-size: 12.5px;
  font-weight: 600;
  color: var(--text-secondary);
  margin-bottom: 6px;
}
.chart-box {
  height: 240px;
  width: 100%;
}
</style>
