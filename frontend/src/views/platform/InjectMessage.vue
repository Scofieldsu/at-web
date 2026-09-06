<template>
  <a-row :gutter="16">
    <!-- 左侧：注入配置 -->
    <a-col :span="11">
      <a-card class="theme-card">
        <template #title>
          <div class="hdr">
            <span class="sec-title tint-indigo"><EnterOutlined />消息注入</span>
            <a-button :loading="loadingFlows" size="small" @click="loadFlows">刷新连接</a-button>
          </div>
        </template>

        <a-form :label-col="{ style: { width: '110px' } }" label-align="left">
          <!-- 目标连接提示（整行置于字段上方，不与字段同行） -->
          <div class="conn-tip">
            <div class="conn-tip-line">
              <ExclamationCircleOutlined class="conn-tip-icon" />
              <span class="conn-tip-body">
                注入命令会经 Mock 服务下发到选中的活跃连接（演示环境为模拟连接）；不选连接时广播给所有活跃连接。
              </span>
            </div>
          </div>

          <!-- 目标连接 -->
          <a-form-item label="目标连接">
            <a-select
              v-model:value="form.flow_id"
              placeholder="留空则广播给所有活跃连接"
              allow-clear
              style="width: 100%"
            >
              <a-select-option v-for="f in flows" :key="f.flow_id" :value="f.flow_id">
                {{ f.flow_id }} · {{ truncateUrl(f.url) }}
              </a-select-option>
            </a-select>
          </a-form-item>

          <!-- 选择会话（自动带出买家信息，命令参数随之精简） -->
          <a-form-item label="选择会话">
            <a-select
              v-model:value="form.conversation_id"
              placeholder="从活跃会话中选择（自动带出 user_name / conversation_id）"
              allow-clear
              style="width: 100%"
              :options="conversationOptions"
              @change="onConversationChange"
            />
          </a-form-item>

          <!-- 命令模板 -->
          <a-form-item label="命令模板">
            <a-select
              v-model:value="form.command_type"
              placeholder="选择预制命令（选后自动填充模板）"
              style="width: 100%"
              @change="onCommandChange"
            >
              <a-select-option v-for="c in availableCommands" :key="c.type" :value="c.type">
                {{ c.type }}
                <span class="muted" style="margin-left: 8px; font-size: 12px">{{ c.description }}</span>
              </a-select-option>
            </a-select>
          </a-form-item>

          <!-- 已选会话信息（只读展示，注入时自动带入报文） -->
          <template v-if="currentConversation">
            <a-divider style="margin: 4px 0; font-size: 13px">会话信息（自动带入报文）</a-divider>
            <a-descriptions size="small" bordered :column="1" class="conv-info">
              <a-descriptions-item label="user_name">
                <a-typography-text copyable :content="currentConversation.user_name">
                  {{ currentConversation.user_name || '-' }}
                </a-typography-text>
              </a-descriptions-item>
              <a-descriptions-item label="nick_name">
                {{ currentConversation.nick_name || '-' }}
              </a-descriptions-item>
              <a-descriptions-item label="conversation_id">
                <a-typography-text copyable :content="currentConversation.conversation_id">
                  {{ currentConversation.conversation_id || '-' }}
                </a-typography-text>
              </a-descriptions-item>
              <a-descriptions-item label="platform">
                <a-tag :color="getPlatformColor(currentConversation.platform)">
                  {{ currentConversation.platform }}
                </a-tag>
              </a-descriptions-item>
            </a-descriptions>
          </template>

          <!-- 命令参数（精简：会话字段 / 自动生成的 id 已由后端处理，只渲染需手填项） -->
          <template v-if="quickParams.length">
            <a-divider style="margin: 4px 0; font-size: 13px">命令参数</a-divider>
            <!-- 说明只以悬浮 tooltip 展示（鼠标移到字段名才出现），字段下不留常驻小字 -->
            <a-form-item v-for="key in quickParams" :key="key">
              <template #label>
                <a-tooltip :title="currentCommand?.params?.[key] || ''" placement="top">
                  <span class="param-label">{{ key === 'text' ? '回复内容' : key }}</span>
                </a-tooltip>
              </template>
              <a-textarea
                v-if="key === 'text'"
                v-model:value="commandParams[key]"
                :rows="3"
              />
              <a-input
                v-else
                v-model:value="commandParams[key]"
                :style="{ width: paramWidth(key) }"
              />
            </a-form-item>
          </template>

          <!-- 方向 -->
          <a-divider style="margin: 4px 0; font-size: 13px">注入方向</a-divider>
          <a-form-item label="方向">
            <a-radio-group v-model:value="form.from_client">
              <a-radio :value="true">模拟买家发（client→server）</a-radio>
              <a-radio :value="false">模拟服务端回（server→client）</a-radio>
            </a-radio-group>
          </a-form-item>

          <!-- 同步 / 异步 -->
          <a-form-item label="模式">
            <a-radio-group v-model:value="form.wait">
              <a-radio :value="true">同步等待（确认注入完成）</a-radio>
              <a-radio :value="false">异步（fire-and-forget，压测用）</a-radio>
            </a-radio-group>
          </a-form-item>

          <!-- 原始报文输入（仅 raw_message 命令需要；模板命令只展示命令参数） -->
          <template v-if="form.command_type === 'raw_message'">
            <a-divider style="margin: 4px 0; font-size: 13px">原始报文（JSON）</a-divider>
            <a-form-item label=" ">
              <a-textarea
                v-model:value="rawJson"
                :rows="10"
                placeholder="{&#10;  &quot;type&quot;: &quot;...&quot;,&#10;  &quot;data&quot;: {}&#10;}"
                class="json-editor"
                @keydown.tab.prevent="insertTab"
              />
            </a-form-item>
          </template>

          <a-form-item label=" ">
            <a-button type="primary" :loading="injecting" :disabled="!canInject" @click="doInject">
              ▶ 注入
            </a-button>
            <a-button
              v-if="form.command_type !== 'raw_message'"
              style="margin-left: 8px"
              :loading="previewing"
              @click="previewJson"
            >
              📝 预览 JSON 报文
            </a-button>
          </a-form-item>
        </a-form>

        <pre v-if="injectResult" class="json">{{ injectResult }}</pre>
      </a-card>

      <!-- 报文预览弹窗（与 Mock websocket 页同款：后端 dry_run 组装 + JSON 高亮） -->
      <a-modal v-model:open="previewOpen" title="报文预览" width="640px" :footer="null" centered>
        <div class="preview-hint">
          按当前命令模板、命令参数与所选会话构造的完整报文；
          <code>request_id</code> / <code>record_id</code> 每次预览/注入都会重新生成。
        </div>
        <pre class="preview-json" v-html="previewHtml"></pre>
      </a-modal>
    </a-col>

    <!-- 右侧：活跃会话 + 活跃连接 + RPA 上报消息 -->
    <a-col :span="13">
      <!-- 活跃会话列表 -->
      <a-card class="theme-card">
        <template #title>
          <div class="hdr">
            <span class="sec-title tint-green"><TeamOutlined />活跃会话</span>
            <a-button :loading="loadingConversations" size="small" @click="loadActiveConversations">刷新会话</a-button>
          </div>
        </template>
        <a-table
          :data-source="conversations"
          :columns="conversationColumns"
          row-key="conversation_id"
          :pagination="false"
          size="small"
          class="theme-table"
          :scroll="{ y: 200 }"
          :locale="{ emptyText: '暂无活跃会话' }"
        >
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'platform'">
              <a-tag :color="getPlatformColor(record.platform)">{{ record.platform }}</a-tag>
            </template>
            <template v-if="column.key === 'action'">
              <a-button size="small" type="link" @click="selectConversation(record)">选用</a-button>
            </template>
          </template>
        </a-table>
      </a-card>

      <!-- 活跃 WebSocket 连接 -->
      <a-card class="theme-card" style="margin-top: 16px">
        <template #title>
          <div class="hdr">
            <span class="sec-title tint-blue"><ApiOutlined />活跃 WebSocket 连接</span>
            <span class="muted">{{ flows.length }} 个</span>
          </div>
        </template>
        <a-table
          :data-source="flows"
          :columns="flowColumns"
          row-key="flow_id"
          :pagination="false"
          size="small"
          class="theme-table"
          :scroll="{ y: 400 }"
          :locale="{ emptyText: '暂无活跃连接' }"
        >
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'url'">
              <span :title="record.url">{{ truncateUrl(record.url) }}</span>
            </template>
            <template v-if="column.key === 'action'">
              <a-button size="small" type="primary" @click="selectFlow(record)">选用</a-button>
            </template>
          </template>
        </a-table>
      </a-card>

      <!-- 上报消息（注入后可查看回执/上报，每行一条可展开结构化） -->
      <a-card class="theme-card" style="margin-top: 16px">
        <template #title>
          <div class="hdr">
            <span class="sec-title tint-orange"><ArrowUpOutlined />上报消息</span>
            <div class="hdr-tools">
              <a-select
                v-model:value="reportedTypeFilter"
                placeholder="全部类型"
                style="width: 160px"
                size="small"
                allow-clear
                :options="reportedTypeOptions"
              />
              <a-button :loading="loadingReported" size="small" @click="loadReportedMessages">刷新</a-button>
            </div>
          </div>
        </template>
        <div class="reported-hint muted">仅展示 client→server（上报服务端）方向；点击行可展开完整报文。</div>
        <a-collapse ghost :bordered="false" class="reported-collapse">
          <a-collapse-panel v-for="(m, i) in filteredReportedMessages" :key="i">
            <template #header>
              <span class="reported-row">
                <span class="reported-time">{{ fmtMsgTime(m.timestamp) }}</span>
                <code class="reported-type">{{ msgType(m.content) }}</code>
                <span class="reported-flow muted">{{ m.flow_id || '' }}</span>
              </span>
            </template>
            <pre class="json reported-json" v-html="highlightJson(m.content)"></pre>
          </a-collapse-panel>
          <a-empty
            v-if="!filteredReportedMessages.length"
            :image="simpleImage"
            description="暂无匹配消息（注入后自动刷新）"
          />
        </a-collapse>
      </a-card>
    </a-col>
  </a-row>
</template>

<script lang="ts" setup>
  defineOptions({ name: 'MessageInject' });
  import { ref, reactive, computed, watch, h, onMounted, onBeforeUnmount } from 'vue';
  import { message } from 'ant-design-vue';
  import { Empty } from 'ant-design-vue';
  import { ExclamationCircleOutlined, EnterOutlined, TeamOutlined, ApiOutlined, ArrowUpOutlined } from '@ant-design/icons-vue';
  import http from '@/api/platform/http';
  import { highlightJson } from '@/utils/jsonHighlight';

  const flows = ref<any[]>([]);
  const conversations = ref<any[]>([]);
  const commands = ref<any[]>([]);
  const loadingFlows = ref(false);
  const loadingConversations = ref(false);
  const injecting = ref(false);
  const injectResult = ref('');

  // RPA 上报消息（client→server），注入后轮询刷新
  const reportedMessages = ref<any[]>([]);
  const loadingReported = ref(false);
  const simpleImage = Empty.PRESENTED_IMAGE_SIMPLE;
  let reportedTimer: number | null = null;
  // 上报消息类型过滤
  const reportedTypeFilter = ref<string | undefined>(undefined);
  const reportedTypeOptions = computed(() => {
    const types = new Set<string>();
    reportedMessages.value.forEach((m: any) => {
      const t = msgType(m.content);
      if (t) types.add(t);
    });
    return Array.from(types)
      .sort()
      .map((t) => ({ label: t, value: t }));
  });
  const filteredReportedMessages = computed(() => {
    if (!reportedTypeFilter.value) return reportedMessages.value;
    return reportedMessages.value.filter((m: any) => msgType(m.content) === reportedTypeFilter.value);
  });

  const form = reactive<any>({
    flow_id: undefined,
    conversation_id: undefined,
    command_type: undefined,
    from_client: false,
    wait: true,
  });

  // raw_message 命令的原始报文输入
  const rawJson = ref('');

  const commandParams = reactive<Record<string, string>>({});
  const currentCommand = computed(() => commands.value.find((c) => c.type === form.command_type));

  // 报文预览（与 Mock websocket 页同款：后端 dry_run 组装 + JSON 高亮弹窗）
  const previewOpen = ref(false);
  const previewHtml = ref('');
  const previewing = ref(false);

  /** 当前选中的连接 flow（未选则 undefined，表示广播） */
  const selectedFlow = computed(() => flows.value.find((f) => f.flow_id === form.flow_id));

  /** 可用命令模板（演示环境：全部预制命令对任意连接可用） */
  const availableCommands = computed(() => commands.value);

  const flowColumns = [
    { title: 'Flow ID', dataIndex: 'flow_id', key: 'flow_id', width: 100 },
    { title: 'URL', key: 'url', ellipsis: true },
    { title: '', key: 'action', width: 70 },
  ];

  const conversationColumns = [
    { title: '昵称', dataIndex: 'nick_name', key: 'nick_name', width: 120, ellipsis: true },
    { title: '平台', key: 'platform', width: 80 },
    { title: '', key: 'action', width: 60 },
  ];

  const conversationOptions = computed(() =>
    conversations.value.map((c) => ({
      label: `${c.nick_name} (${c.platform})`,
      value: c.conversation_id,
    }))
  );

  function truncateUrl(url: string) {
    return url && url.length > 60 ? url.slice(0, 60) + '…' : url || '-';
  }
  function insertTab(e: KeyboardEvent) {
    const ta = e.target as HTMLTextAreaElement;
    const start = ta.selectionStart;
    const end = ta.selectionEnd;
    rawJson.value = rawJson.value.substring(0, start) + '  ' + rawJson.value.substring(end);
    setTimeout(() => ta.setSelectionRange(start + 2, start + 2));
  }

  function onCommandChange() {
    const cmd = currentCommand.value;
    if (!cmd) return;
    // 清空参数，从 defaults 预填
    Object.keys(commandParams).forEach((k) => delete commandParams[k]);
    // 设置方向
    if (cmd.from_client !== undefined) form.from_client = cmd.from_client;
    // raw_message 无模板参数
    if (cmd.type === 'raw_message') return;
    quickParams.value.forEach((k) => {
      commandParams[k] = cmd.defaults?.[k] || '';
    });
  }

  function selectFlow(record: any) {
    form.flow_id = record.flow_id;
    message.success(`已选用 Flow: ${record.flow_id}`);
  }

  function getPlatformColor(platform: string) {
    const colors: Record<string, string> = {
      platform_d: 'red',
      platform_b: 'orange',
      platform_a: 'blue',
      platform_c: 'purple',
    };
    return colors[platform] || 'default';
  }

  function selectConversation(record: any) {
    form.conversation_id = record.conversation_id;
    injectResult.value = '';
    message.success(`已选用会话: ${record.nick_name}（user_name / conversation_id 将自动带入报文）`);
  }

  function onConversationChange() {
    injectResult.value = '';
  }

  /** 当前选中会话的完整对象 */
  const currentConversation = computed(() =>
    conversations.value.find((c) => c.conversation_id === form.conversation_id),
  );

  /** 后端自动生成/自动填写的参数，不渲染输入框 */
  const QUICK_AUTO_PARAMS = ['user_name', 'nick_name', 'conversation_id', 'request_id', 'record_id', 'timestamp'];

  /** 需要手填的命令特有参数（排除会话字段与后端自动生成的 id） */
  const quickParams = computed(() => {
    const cmd = currentCommand.value;
    if (!cmd || !cmd.params) return [];
    return Object.keys(cmd.params).filter((k) => !QUICK_AUTO_PARAMS.includes(k));
  });

  /** 短值参数（枚举 / 数字 / 单号）用窄控件，避免整行空白 */
  const NARROW_PARAMS = new Set(['query_scope', 'max_orders', 'timeout_seconds']);
  const MEDIUM_PARAMS = new Set(['order_id', 'task_id', 'request_id']);

  function paramWidth(key: string): string {
    if (NARROW_PARAMS.has(key)) return '160px';
    if (MEDIUM_PARAMS.has(key)) return '280px';
    return '100%';
  }

  /** 需要选中会话的命令（与后端 _CMD_NEEDS_CONVERSATION 一致） */
  const QUICK_NEEDS_CONVERSATION = ['reply_message', 'transfer_message', 'order_fetch'];

  /** 是否满足注入前置条件 */
  const canInject = computed(() => {
    // raw_message：原始报文输入框中已有合法 JSON 即可注入
    if (form.command_type === 'raw_message') {
      const s = rawJson.value.trim();
      if (!s) return false;
      try {
        JSON.parse(s);
        return true;
      } catch {
        return false;
      }
    }
    const cmd = currentCommand.value;
    if (!cmd) return false;
    if (QUICK_NEEDS_CONVERSATION.includes(cmd.type) && !currentConversation.value) return false;
    if (cmd.type === 'reply_message' && !(commandParams.text || '').trim()) return false;
    return true;
  });

  /** 组装 quick-inject 请求体：会话字段由后端按 conversation_id 自动带入，params 只含手填项 */
  function buildQuickInjectPayload(dryRun: boolean) {
    const cmd = currentCommand.value;
    if (!cmd) return null;
    const conv = currentConversation.value;
    const params: Record<string, string> = {};
    for (const key of quickParams.value) {
      if (commandParams[key]) params[key] = commandParams[key];
    }
    return {
      command_type: cmd.type,
      conversation_id: conv?.conversation_id || '',
      platform: conv?.platform || '',
      params,
      flow_id: form.flow_id || conv?.flow_id,
      wait: form.wait,
      dry_run: dryRun,
    };
  }

  async function loadActiveConversations() {
    loadingConversations.value = true;
    try {
      const { data } = await http.get('/ui/active-conversations');
      conversations.value = Array.isArray(data) ? data.filter((c: any) => c.conversation_id) : [];
      if (!conversations.value.length) {
        // toast 用 info 蓝感叹号 + 蓝字（与目标连接提示同色）
        message.open({
          content: h('span', { style: { color: 'var(--vben-info)' } }, '暂无活跃会话，先让买家发一条消息再刷新'),
          icon: h(ExclamationCircleOutlined, { style: { color: 'var(--vben-info)' } }),
          duration: 3,
        });
      }
    } catch (e: any) {
      message.error(e.response?.data?.error || '获取会话列表失败');
    } finally {
      loadingConversations.value = false;
    }
  }

  async function loadReportedMessages() {
    loadingReported.value = true;
    try {
      const { data } = await http.get('/ui/messages', { params: { limit: 60 } });
      const all = Array.isArray(data) ? data : [];
      // 只保留 RPA 上报方向（client→server），最新在前；
      // content 若被序列化成字符串则归一化为对象，保证展开时能多行格式化
      reportedMessages.value = all
        .filter((m: any) => m.direction === 'client_to_server')
        .map((m: any) => ({ ...m, content: normalizeContent(m.content) }))
        .reverse()
        .slice(0, 30);
    } catch {
      /* 消息拉取失败不阻塞 */
    } finally {
      loadingReported.value = false;
    }
  }

  /** content 归一：字符串形态 JSON → 对象（无法解析则保持字符串，formatMsg 兜底） */
  function normalizeContent(content: any): any {
    if (content && typeof content === 'object') return content;
    const s = String(content ?? '').trim();
    if (s) {
      try {
        return JSON.parse(s);
      } catch {
        /* 非 JSON 原文 */
      }
    }
    return content;
  }

  function fmtMsgTime(ts: number) {
    if (!ts) return '-';
    return new Date(ts * 1000).toLocaleTimeString('zh-CN', { hour12: false });
  }

  function msgType(content: any) {
    if (!content || typeof content !== 'object') return 'raw';
    return content.type || 'unknown';
  }

  function formatMsg(content: any) {
    // content 可能是已解析对象或字符串形态的 JSON：统一格式化后展示
    if (content && typeof content === 'object') {
      try {
        return JSON.stringify(content, null, 2);
      } catch {
        return String(content);
      }
    }
    const s = String(content ?? '');
    if (s) {
      try {
        return JSON.stringify(JSON.parse(s), null, 2);
      } catch {
        /* 非 JSON 原文展示 */
      }
    }
    return s;
  }

  async function loadFlows() {
    loadingFlows.value = true;
    try {
      const { data } = await http.get('/proxy/flows');
      flows.value = Array.isArray(data) ? data : [];
      // 默认目标连接：未手动选择时自动选中含 client（业务链路）的那条连接
      if (!form.flow_id && flows.value.length) {
        const clientFlow = flows.value.find((f: any) => /\/v1\/ws\/client\//.test(f.url || ''));
        if (clientFlow) {
          form.flow_id = clientFlow.flow_id;
        }
      }
    } catch (e: any) {
      message.error('获取连接列表失败');
    } finally {
      loadingFlows.value = false;
    }
  }

  async function loadCommands() {
    try {
      const { data } = await http.get('/ui/inject-commands');
      commands.value = Array.isArray(data) ? data : [];
      // 默认选中一个 client 业务命令（reply_message 优先），加载后即可直接注入
      if (!form.command_type && commands.value.length) {
        const preferred =
          commands.value.find((c: any) => c.type === 'reply_message') ||
          commands.value.find((c: any) => c.type !== 'raw_message');
        if (preferred) {
          form.command_type = preferred.type;
          onCommandChange();
        }
      }
    } catch { /* 忽略 */ }
  }

  /** 预览：模板命令走后端 dry_run 组装，高亮弹窗展示（会话/参数自动带入） */
  async function previewJson() {
    const payload = buildQuickInjectPayload(true);
    if (!payload) {
      message.warning('请先选择命令模板');
      return;
    }
    previewing.value = true;
    try {
      const { data } = await http.post('/ui/quick-inject', payload, { timeout: 10000 });
      previewHtml.value = highlightJson(data.message);
      previewOpen.value = true;
    } catch (e: any) {
      message.error(e.response?.data?.error || '预览失败');
    } finally {
      previewing.value = false;
    }
  }

  /** 注入：模板命令走 quick-inject（后端组装报文）；raw_message 走通用 inject */
  async function doInject() {
    injecting.value = true;
    injectResult.value = '';
    try {
      if (form.command_type === 'raw_message') {
        let content: any;
        try {
          content = JSON.parse(rawJson.value.trim());
        } catch {
          message.error('JSON 格式错误，请检查');
          return;
        }
        const payload: any = {
          content,
          from_client: form.from_client,
          wait: form.wait,
        };
        if (form.flow_id) payload.flow_id = form.flow_id;
        const { data } = await http.post('/ui/inject', payload, { timeout: form.wait ? 45000 : 10000 });
        injectResult.value = JSON.stringify(data, null, 2);
        if (data.error) {
          message.error(data.error);
        } else {
          message.success(`已注入到 ${data.injected_to} 个连接`);
        }
        return;
      }

      const payload = buildQuickInjectPayload(false);
      if (!payload) {
        message.warning('请先选择命令模板');
        return;
      }
      const { data } = await http.post('/ui/quick-inject', payload, { timeout: form.wait ? 45000 : 10000 });
      injectResult.value = JSON.stringify(data, null, 2);
      if (data.error) {
        message.error(data.error);
      } else {
        message.success(`已注入 ${form.command_type} 到 ${data.result?.injected_to ?? 0} 个连接`);
      }
      // 注入成功/失败都刷新右侧上报消息，便于立即观察 RPA 回执
      loadReportedMessages();
    } catch (e: any) {
      const body = e.response?.data || { error: String(e) };
      injectResult.value = JSON.stringify(body, null, 2);
      message.error(body.error || '注入失败');
    } finally {
      injecting.value = false;
    }
  }

  onMounted(() => {
    loadFlows();
    loadCommands();
    loadActiveConversations();
    loadReportedMessages();
    // 每 3 秒轮询一次 RPA 上报消息，注入后无需手动刷新即可看到回执
    reportedTimer = window.setInterval(loadReportedMessages, 3000);
  });

  onBeforeUnmount(() => {
    if (reportedTimer) window.clearInterval(reportedTimer);
  });
</script>

<style scoped>
.hdr {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
/* ── 区块标题：图标 + 浅色系彩色标题块（各区块不同色，贴合系统配色）── */
.sec-title {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-weight: 600;
  font-size: var(--vben-font-size-base);
  line-height: 1;
  padding: 5px 10px;
  border-radius: 6px;
}
.tint-indigo { background: rgba(99, 102, 241, 0.12); color: var(--accent); }
.tint-green  { background: rgba(48, 164, 108, 0.12); color: var(--success-color); }
.tint-blue   { background: rgba(0, 144, 255, 0.12); color: var(--info-color); }
.tint-orange { background: rgba(247, 107, 21, 0.12); color: var(--warning-color); }
.hdr-tools {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.muted {
  color: var(--text-muted);
}
.json {
  background: #f5f6f8;
  color: var(--text-primary);
  padding: 12px;
  border-radius: 6px;
  border: 1px solid var(--border-color);
  max-height: 360px;
  overflow: auto;
  font-size: var(--vben-font-size-sm);
  white-space: pre-wrap;
  margin: 12px 0 0 0;
  line-height: 1.6;
}
.json-editor {
  font-family: 'SF Mono', 'Fira Code', 'Consolas', monospace;
  font-size: var(--vben-font-size-base);
  line-height: 1.5;
  background: #ffffff;
  color: var(--text-primary);
  border: 1px solid var(--border-color);
}
.conv-info {
  margin-bottom: 12px;
  font-size: 13px;
}
.conv-info :deep(.ant-descriptions-item-label) {
  width: 140px;
  background: var(--card);
}

/* ── 报文预览弹窗（与 Mock websocket 页同款） ── */
.preview-hint {
  margin-bottom: 10px;
  font-size: 12px;
  color: var(--text-muted);
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
/* JSON 高亮着色（系统色板） */
.preview-json :deep(.jv-key) {
  color: var(--accent);
  font-weight: 500;
}
.preview-json :deep(.jv-string) {
  color: var(--success-color);
}
.preview-json :deep(.jv-number) {
  color: var(--warning-color);
}
.preview-json :deep(.jv-bool) {
  color: var(--info-color);
}
.preview-json :deep(.jv-null) {
  color: var(--error-color);
}
/* ── 目标连接提示 ── */
.conn-tip {
  background: rgba(0, 144, 255, 0.06);
  border: 1px solid rgba(0, 144, 255, 0.25);
  border-radius: var(--vben-radius-lg);
  padding: 8px 12px;
  margin-bottom: 12px;
  font-size: 12px;
}
.conn-tip-line {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  line-height: 1.6;
}
.conn-tip-line + .conn-tip-line {
  margin-top: 6px;
}
.conn-tip-icon {
  color: var(--info-color, #0090ff);
  font-size: 13px;
  flex-shrink: 0;
  margin-top: 3px;
}
.conn-tip-body {
  flex: 1;
  color: var(--text-secondary);
}
.conn-tip-body b {
  color: var(--text-primary);
}

/* ── 命令参数 label：悬停提示，显示下划线虚线提示可交互 ── */
.param-label {
  cursor: help;
  border-bottom: 1px dashed rgba(0, 144, 255, 0.3);
}

/* ── RPA 上报消息 ── */
.reported-hint {
  font-size: var(--vben-font-size-sm);
  margin-bottom: 4px;
}
.reported-collapse :deep(.ant-collapse-item) {
  border-bottom: 1px solid var(--border-color);
}
.reported-collapse :deep(.ant-collapse-header) {
  padding: 8px 0 !important;
  font-size: var(--vben-font-size-base);
}
.reported-row {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  width: 100%;
}
.reported-time {
  color: var(--text-muted);
  font-size: var(--vben-font-size-sm);
  font-variant-numeric: tabular-nums;
  flex-shrink: 0;
}
.reported-type {
  color: var(--accent);
  font-weight: 600;
  font-size: var(--vben-font-size-base);
  flex-shrink: 0;
}
.reported-flow {
  font-size: var(--vben-font-size-sm);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.reported-json {
  margin: 0 0 4px 0;
  max-height: 280px;
  font-size: var(--vben-font-size-sm);
  text-align: left;
}
/* JSON 高亮着色（系统色板） */
.reported-json :deep(.jv-key) {
  color: var(--accent);
  font-weight: 500;
}
.reported-json :deep(.jv-string) {
  color: var(--success-color);
}
.reported-json :deep(.jv-number) {
  color: var(--warning-color);
}
.reported-json :deep(.jv-bool) {
  color: var(--info-color);
}
.reported-json :deep(.jv-null) {
  color: var(--error-color);
}
</style>
