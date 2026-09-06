<template>
  <a-row :gutter="16">
    <!-- 左列：下发消息（Mock 服务启停合并到标题区；与右侧活跃连接 + 消息流各占一半） -->
    <a-col :span="12">
      <a-card class="theme-card">
        <template #title>
          <div class="hdr">
            <span class="sec-title tint-orange"><DownCircleOutlined />下发消息</span>
            <div class="hdr-tools">
              <a-button size="small" type="primary" :loading="actingMock" :disabled="status.running" @click="actMock('start')">
                启动
              </a-button>
              <a-button size="small" danger :loading="actingMock" :disabled="!status.running" @click="actMock('stop')">
                停止
              </a-button>
              <a-tag :color="status.running ? 'success' : 'default'">
                {{ status.running ? '运行中' : '已停止' }}
              </a-tag>
              <span class="muted" style="font-size: 12px">
                {{ (status.rpa_connections || []).length }} 连接 · {{ mockWsUrl }}
              </span>
              <a-button :loading="loadingStatus" size="small" @click="loadStatus">刷新</a-button>
            </div>
          </div>
        </template>

        <a-alert
          type="info"
          show-icon
          :closable="false"
          style="margin-bottom: 12px"
          message="演示模式：Mock 服务运行期间周期性模拟客户端连接与消息帧；下发会广播给所有活跃连接，未运行时仅记录日志。"
        >
          <template #icon>
            <!-- 与创建浏览器用户页提示同款：info 蓝感叹号 -->
            <ExclamationCircleOutlined style="color: var(--info-color, #0090ff); font-size: 13px" />
          </template>
        </a-alert>

        <a-form label-align="left" :label-col="{ style: { width: '110px' } }">
          <a-form-item label="发送模式">
            <a-radio-group v-model:value="mode">
              <a-radio value="template">模板模式</a-radio>
              <a-radio value="raw">原始报文</a-radio>
            </a-radio-group>
          </a-form-item>

          <a-form-item label="连接ID">
            <a-select v-model:value="target" :options="targetOptions" style="width: 100%" />
          </a-form-item>

          <template v-if="mode === 'template'">
            <a-form-item label="选择会话">
              <a-select
                v-model:value="sessionKey"
                :options="sessionOptions"
                allow-clear
                placeholder="从最近收发记录选择（自动带出 user_name / conversation_id）"
                style="width: 100%"
                @change="onSessionChange"
              />
            </a-form-item>

            <!-- 会话信息（选中后只读展示，并自动带入报文参数） -->
            <a-form-item v-if="currentSession" label="会话信息">
              <a-descriptions size="small" bordered :column="1" class="mock-conv-info">
                <a-descriptions-item label="user_name">
                  <a-typography-text copyable :content="currentSession.user_name">
                    {{ currentSession.user_name }}
                  </a-typography-text>
                </a-descriptions-item>
                <a-descriptions-item label="conversation_id">
                  <a-typography-text copyable :content="currentSession.conversation_id || ''">
                    {{ currentSession.conversation_id || '-' }}
                  </a-typography-text>
                </a-descriptions-item>
              </a-descriptions>
            </a-form-item>

            <a-form-item label="消息模板">
              <a-select
                v-model:value="templateKey"
                :options="templateOptions"
                placeholder="请选择模板"
                style="width: 100%"
                @change="onTemplateChange"
              />
            </a-form-item>

            <template v-if="currentTemplate">
              <a-divider style="margin: 4px 0; font-size: 13px">消息参数</a-divider>
              <!-- 字段 label 在输入框左侧，统一英文 key；中文说明悬浮展示 -->
              <div v-for="p in currentTemplate.params" :key="p.key" class="mock-param-row">
                <a-tooltip :title="p.label || p.key" placement="top">
                  <span class="mock-param-label">{{ p.key }}</span>
                </a-tooltip>
                <a-auto-complete
                  v-if="isImageUrlField(p.key)"
                  v-model:value="params[p.key]"
                  :options="imageUrlOptions"
                  :filter-option="filterImageUrl"
                  placeholder="从预置图片链接中选择，或直接输入其他链接"
                  allow-clear
                  class="mock-param-input"
                />
                <a-textarea
                  v-else-if="p.key === 'content' || p.key === 'order_text'"
                  v-model:value="params[p.key]"
                  :rows="3"
                  :placeholder="p.label"
                  class="mock-param-input"
                />
                <a-input v-else v-model:value="params[p.key]" :placeholder="p.key" class="mock-param-input" />
              </div>
            </template>
          </template>

          <a-form-item v-else label="完整报文 JSON">
            <a-textarea
              v-model:value="rawMessage"
              :rows="8"
              style="max-width: 520px"
              placeholder='{"type":"reply-message","request_id":"...","task_id":"...","priority":2,"data":{...}}'
            />
          </a-form-item>

          <a-form-item label=" " style="margin-top: 14px">
            <a-space>
              <a-button type="primary" :loading="sending" @click="send">发送</a-button>
              <a-button :loading="previewing" @click="openPreview">预览 JSON 报文</a-button>
            </a-space>
          </a-form-item>
        </a-form>
      </a-card>

      <!-- 报文预览（模板 + 当前参数构造结果，不下发） -->
      <a-modal v-model:open="previewOpen" title="报文预览" width="640px" :footer="null" centered>
        <div class="preview-hint">
          按当前模板与参数构造的完整报文。<code>request_id</code> / <code>task_id</code> /
          <code>record_id</code> 每次生成都是新 UUID，实际下发时会重新生成。
        </div>
        <pre class="preview-json" v-html="highlightJson(previewText)"></pre>
      </a-modal>
    </a-col>

    <!-- 右列（半宽）：活跃 WebSocket 连接 + 消息流 -->
    <a-col :span="12">
      <!-- 活跃 WebSocket 连接（「选用」即设为下发目标） -->
      <a-card class="theme-card">
        <template #title>
          <div class="hdr">
            <span class="sec-title tint-blue"><ApiOutlined />活跃 WebSocket 连接</span>
            <div class="hdr-tools">
              <span class="muted" style="font-size: 12px">{{ (status.rpa_connections || []).length }} 个</span>
              <a-button size="small" :loading="loadingStatus" @click="loadStatus">刷新</a-button>
            </div>
          </div>
        </template>
        <a-table
          :data-source="status.rpa_connections || []"
          :columns="connColumns"
          row-key="cid"
          :pagination="false"
          :scroll="{ y: 200 }"
          size="small"
          class="theme-table"
          :locale="{ emptyText: '暂无活跃连接（先启动 Mock 服务，演示连接会周期性接入）' }"
        >
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'action'">
              <a-button size="small" type="link" @click="selectTarget(record)">选用</a-button>
            </template>
          </template>
        </a-table>
      </a-card>

      <!-- 消息流（双 Tab + 类型过滤 + 折叠 JSON 高亮） -->
      <a-card class="theme-card" style="margin-top: 16px">
        <template #title>
          <div class="hdr">
            <span class="sec-title tint-purple"><SwapOutlined />消息流</span>
            <div class="hdr-tools">
              <a-select
                v-model:value="flowTypeFilter"
                placeholder="全部类型"
                style="width: 190px"
                size="small"
                allow-clear
                :options="flowTypeOptions"
              />
              <a-button size="small" @click="refreshFlow">刷新</a-button>
            </div>
          </div>
        </template>
        <a-tabs v-model:activeKey="flowTab" size="small" @change="onFlowTabChange">
          <a-tab-pane key="recv">
            <template #tab>
              <span style="color: var(--success-color)">客户端上报（{{ flowRecvCount }}）</span>
            </template>
          </a-tab-pane>
          <a-tab-pane key="send">
            <template #tab>
              <span style="color: var(--info-color)">服务端下发（{{ flowSendCount }}）</span>
            </template>
          </a-tab-pane>
        </a-tabs>
        <div class="flow-scroll">
          <a-collapse ghost :bordered="false" class="flow-collapse">
            <a-collapse-panel v-for="(m, i) in filteredFlowMessages" :key="i">
              <template #header>
                <span class="flow-row">
                  <span class="flow-time">{{ m.ts }}</span>
                  <code class="flow-type">{{ m.type }}</code>
                  <span class="flow-meta muted">{{ m.channel || '' }}</span>
                </span>
              </template>
              <pre class="json flow-json" v-html="highlightJson(m.raw || m.summary || '')"></pre>
            </a-collapse-panel>
            <a-empty v-if="!filteredFlowMessages.length" description="暂无消息（Mock 服务运行后自动产生，每 2s 轮询）" />
          </a-collapse>
        </div>
      </a-card>
    </a-col>
  </a-row>
</template>

<script lang="ts" setup>
  import {
    computed,
    onBeforeUnmount,
    onMounted,
    reactive,
    ref,
  } from 'vue';
  import { message, Modal } from 'ant-design-vue';
  import {
    ApiOutlined,
    DownCircleOutlined,
    ExclamationCircleOutlined,
    SwapOutlined,
  } from '@ant-design/icons-vue';
  import {
    getMockLogs,
    getMockStatus,
    getMockTemplates,
    getServerInfo,
    getImageUrls,
    previewMockMessage,
    sendMockMessage,
    stopMock,
    startMock,
  } from '@/api/platform/mock-server';
  import { highlightJson } from '@/utils/jsonHighlight';

  defineOptions({ name: 'MockServer' });

  const mockWsUrl = ref('');

  // ─── Mock 服务状态 ───
  const status = ref<any>({
    running: false,
    rpa_connections: [],
    image_urls: [],
  });
  const loadingStatus = ref(false);
  const actingMock = ref(false);

  async function loadStatus() {
    loadingStatus.value = true;
    try {
      const { data } = await getMockStatus();
      status.value = data;
      // 首次加载取 ws 地址（后端返回演示 ip + port）
      if (!mockWsUrl.value) {
        try {
          const { data: info } = await getServerInfo();
          mockWsUrl.value = `ws://${info.ip}:${info.port}/ws`;
        } catch {
          mockWsUrl.value = 'ws://127.0.0.1:8765/ws';
        }
      }
    } finally {
      loadingStatus.value = false;
    }
  }

  // 预置图片链接（图片回复模板的下拉候选）
  async function loadImageUrls() {
    try {
      const { data } = await getImageUrls();
      status.value.image_urls = data?.images || [];
    } catch {
      /* 忽略 */
    }
  }

  async function actMock(action: 'start' | 'stop') {
    actingMock.value = true;
    try {
      if (action === 'start') {
        await startMock();
        message.success('Mock 服务已启动');
        await loadStatus();
      } else {
        Modal.confirm({
          title: '停止 Mock 服务',
          content: '停止后所有活跃连接将断开，确认停止？',
          onOk: async () => {
            await stopMock();
            message.success('Mock 服务已停止');
            loadStatus();
          },
        });
      }
    } finally {
      actingMock.value = false;
    }
  }

  // ─── 活跃连接表 ───
  const connColumns = [
    { title: '连接ID', dataIndex: 'cid', key: 'cid' },
    { title: '昵称', dataIndex: 'nick', key: 'nick' },
    { title: '平台', dataIndex: 'channel', key: 'channel' },
    { title: '操作', key: 'action' },
  ];
  function selectTarget(rec: any) {
    target.value = rec.cid;
    message.success(`下发目标已设为 ${rec.cid}`);
  }

  // ─── 下发消息 ───
  const mode = ref<'template' | 'raw'>('template');
  const target = ref<string>('*');
  // 下发目标：默认广播给所有活跃连接，可选具体连接（启动后从活跃连接表「选用」）
  const targetOptions = computed(() => [
    { label: '所有活跃连接（广播）', value: '*' },
    ...(status.value.rpa_connections || []).map((c: any) => ({ label: c.cid, value: c.cid })),
  ]);
  const templateKey = ref('text_reply');
  const params = reactive<Record<string, any>>({});
  const rawMessage = ref(
    JSON.stringify(
      {
        type: 'reply-message',
        request_id: 'demo-req-0001',
        task_id: 'demo-task-0001',
        priority: 2,
        data: { msg_list: [{ record_id: 'r001', type: 'TEXT', content: '你好，很高兴为您服务' }] },
      },
      null,
      2,
    ),
  );
  const templates = ref<any[]>([]);
  const sending = ref(false);
  const previewing = ref(false);
  const previewOpen = ref(false);
  const previewText = ref('');

  const sessionKey = ref('');
  const currentSession = computed(() => sessions.value.find((s) => s.key === sessionKey.value));

  async function loadTemplates() {
    const { data } = await getMockTemplates();
    templates.value = data?.templates || [];
    if (templates.value.length) {
      if (!templates.value.find((t: any) => t.key === templateKey.value)) {
        templateKey.value = templates.value[0].key;
      }
      onTemplateChange();
    }
  }

  const templateOptions = computed(() =>
    templates.value.map((t: any) => ({ label: t.name, value: t.key })),
  );
  const currentTemplate = computed(() =>
    templates.value.find((t: any) => t.key === templateKey.value),
  );

  // 图片链接字段：模板 params 中 label 含「图片」（at-web 演示模板为「图片地址」）
  function isImageUrlField(key: string) {
    const p = currentTemplate.value?.params?.find((x: any) => x.key === key);
    return p ? /图片/.test(p.label || '') : false;
  }

  const imageUrlOptions = computed(() =>
    (status.value.image_urls || []).map((u: string) => ({ value: u })),
  );
  function filterImageUrl(input: string, option: any) {
    return String(option.value).toLowerCase().includes(String(input).toLowerCase());
  }

  function onTemplateChange() {
    const t = currentTemplate.value;
    if (!t) return;
    for (const p of t.params || []) {
      if (params[p.key] === undefined) params[p.key] = p.default ?? '';
    }
  }

  // 会话记录（从消息流里收集最近收发，自动带出 user_name / conversation_id）
  interface SessionItem {
    key: string;
    user_name: string;
    conversation_id?: string;
    msg_type: string;
    ts: string;
  }
  const sessions = ref<SessionItem[]>([]);
  const sessionOptions = computed(() =>
    sessions.value.map((s) => ({
      label: `${s.msg_type} · ${s.user_name} · ${s.ts}`,
      value: s.key,
    })),
  );

  function harvestSessions(logs: any[]) {
    const seen = new Map<string, SessionItem>();
    for (const l of logs) {
      const p = l.payload || {};
      const userName =
        p.user_name ||
        p.user_nick_name ||
        p.data?.user_name ||
        p.data?.user_nick_name ||
        p.conversation?.user_name;
      const convId = p.conversation_id || p.conversation?.conversation_id;
      if (!userName) continue;
      const key = `${p.user_id || ''}_${convId || userName}`;
      const prev = seen.get(key);
      seen.set(key, {
        key,
        user_name: userName,
        conversation_id: convId || prev?.conversation_id,
        msg_type: l.msg_type || l.type || 'message',
        ts: l.time || l.ts || '',
      });
    }
    const list = [...seen.values()].sort((a, b) => (a.ts < b.ts ? 1 : -1));
    if (list.length) sessions.value = list.slice(0, 20);
  }

  function onSessionChange() {
    const s = currentSession.value;
    if (!s) return;
    const t = currentTemplate.value;
    if (!t) return;
    for (const p of t.params || []) {
      if (p.key === 'user_name') params.user_name = s.user_name;
      if (p.key === 'conversation_id') params.conversation_id = s.conversation_id || '';
    }
  }

  // 构造完整报文（raw 模式本地校验；template 模式由后端按模板渲染）
  function buildMessage(): any {
    if (mode.value === 'raw') {
      try {
        const obj = JSON.parse(rawMessage.value || '{}');
        if (!obj.type) throw new Error('缺少 type');
        return obj;
      } catch (e: any) {
        message.error(`报文 JSON 解析失败：${e.message}`);
        throw e;
      }
    }
    return null;
  }

  async function send() {
    sending.value = true;
    try {
      if (mode.value === 'raw') {
        const msg = buildMessage();
        await sendMockMessage({ message: msg, target: target.value });
      } else {
        await sendMockMessage({ template: templateKey.value, params: { ...params } });
      }
      message.success('下发成功（广播给所有活跃连接）');
    } catch (e: any) {
      if (e?.message !== 'no template') message.error(e?.message || '下发失败');
    } finally {
      sending.value = false;
    }
  }

  async function openPreview() {
    previewing.value = true;
    try {
      if (mode.value === 'raw') {
        previewText.value = JSON.stringify(buildMessage(), null, 2);
      } else {
        // 走后端渲染保证与下发报文一致
        const { data: res } = await previewMockMessage({ template: templateKey.value, params: { ...params } });
        previewText.value = JSON.stringify(res?.message, null, 2);
      }
      previewOpen.value = true;
    } catch (e: any) {
      message.error(e?.message || '预览失败');
    } finally {
      previewing.value = false;
    }
  }

  // ─── 消息流（双 Tab + 类型过滤） ───
  const flowTab = ref<'recv' | 'send'>('recv');
  // 切换 Tab 时重置类型过滤，避免旧过滤条件导致空列表
  function onFlowTabChange() {
    flowTypeFilter.value = undefined;
  }
  const flowTypeFilter = ref<string | undefined>();
  const flowMessages = ref<any[]>([]);
  const flowRecvCount = ref(0);
  const flowSendCount = ref(0);

  const flowTypeOptions = computed(() => {
    const set = new Set<string>();
    for (const m of flowMessages.value) if (m.type) set.add(m.type);
    return [...set].map((t) => ({ label: t, value: t }));
  });

  const filteredFlowMessages = computed(() =>
    flowMessages.value.filter((m) => {
      const isRecv = flowTab.value === 'recv';
      const dirOk = isRecv ? m.direction === 'client' : m.direction === 'server';
      const typeOk = !flowTypeFilter.value || m.type === flowTypeFilter.value;
      return dirOk && typeOk;
    }),
  );

  async function refreshFlow() {
    try {
      const { data: res } = await getMockLogs(0, 200);
      const logs: any[] = res?.logs || [];
      // 适配后端字段：ts / direction(recv|send) / kind(frame|lifecycle|dispatch) / payload
      flowMessages.value = logs
        .filter((l) => l.kind === 'frame')
        .map((l) => ({
          ts: l.ts,
          type: l.payload?.type || l.summary || 'message',
          direction: l.direction === 'recv' ? 'client' : l.direction === 'send' ? 'server' : l.direction,
          channel: l.channel || '',
          raw: JSON.stringify(l.payload ?? l.summary ?? ''),
          summary: l.summary || '',
        }))
        .reverse(); // 后端按 seq 升序，展示最新在上
      flowRecvCount.value = flowMessages.value.filter((m) => m.direction === 'client').length;
      flowSendCount.value = flowMessages.value.filter((m) => m.direction === 'server').length;
      harvestSessions(logs);
    } catch {
      /* 轮询失败静默 */
    }
  }

  let timer: any = null;
  onMounted(async () => {
    await Promise.all([loadStatus(), loadTemplates(), loadImageUrls()]);
    await refreshFlow();
    timer = setInterval(async () => {
      await refreshFlow();
      if (status.value.running) loadStatus();
    }, 2000);
  });
  onBeforeUnmount(() => {
    if (timer) clearInterval(timer);
  });
</script>

<style scoped>
  .hdr {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
    flex-wrap: wrap;
  }
  .hdr-tools {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-wrap: wrap;
  }

  .muted {
    color: var(--text-color-3, rgba(0, 0, 0, 0.45));
  }

  .sec-title {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    font-weight: 600;
    font-size: 14px;
  }
  .tint-orange {
    color: var(--warning-color, #f76b15);
  }
  .tint-blue {
    color: var(--info-color, #0090ff);
  }
  .tint-purple {
    color: var(--primary-color, #6366f1);
  }

  /* 消息参数行 */
  .mock-param-row {
    display: flex;
    align-items: flex-start;
    gap: 8px;
    margin-bottom: 10px;
  }
  .mock-param-label {
    width: 110px;
    flex-shrink: 0;
    padding-top: 6px;
    font-size: 13px;
    color: var(--text-color-2, rgba(0, 0, 0, 0.65));
    word-break: break-all;
  }
  .mock-param-input {
    flex: 1;
    max-width: 520px;
  }

  .mock-conv-info {
    max-width: 560px;
  }

  /* 报文预览 */
  .preview-hint {
    margin-bottom: 10px;
    font-size: 12px;
    color: var(--text-color-3, rgba(0, 0, 0, 0.45));
  }
  .preview-hint :deep(code) {
    background: rgba(99, 102, 241, 0.08);
    padding: 1px 5px;
    border-radius: 4px;
    font-size: 12px;
  }
  .preview-json {
    max-height: 60vh;
    overflow: auto;
    padding: 12px;
    background: rgba(0, 0, 0, 0.03);
    border-radius: 8px;
    font-size: 13px;
    line-height: 1.6;
    white-space: pre-wrap;
    word-break: break-all;
  }

  /* 消息流 */
  .flow-scroll {
    max-height: 420px;
    overflow: auto;
  }
  .flow-collapse :deep(.ant-collapse-header) {
    padding: 6px 0 !important;
  }
  .flow-row {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    min-width: 0;
  }
  .flow-time {
    font-family: var(--font-mono, monospace);
    font-size: 12px;
    color: var(--text-color-3, rgba(0, 0, 0, 0.45));
  }
  .flow-type {
    font-size: 12px;
    background: rgba(99, 102, 241, 0.1);
    padding: 1px 6px;
    border-radius: 4px;
    color: var(--primary-color, #6366f1);
  }
  .flow-meta {
    font-size: 12px;
  }
  .flow-json {
    max-height: 300px;
    overflow: auto;
    margin: 4px 0 8px;
  }

  /* JSON 高亮着色（系统色板） */
  :deep(.jv-key) {
    color: var(--primary-color, #6366f1);
    font-weight: 500;
  }
  :deep(.jv-string) {
    color: var(--success-color, #30a46c);
  }
  :deep(.jv-number) {
    color: var(--warning-color, #f76b15);
  }
  :deep(.jv-bool) {
    color: var(--info-color, #0090ff);
  }
  :deep(.jv-null) {
    color: var(--error-color, #e5484d);
  }
</style>
