<template>
  <a-row :gutter="16">
    <!-- 左侧：消息发送配置 -->
    <a-col :span="14">
      <a-card class="theme-card">
        <template #title>
          <div class="hdr">
            <div style="display: inline-flex; align-items: center; gap: 8px">
              <span class="sec-title tint-indigo"><SendOutlined />消息发送配置</span>
              <a-tag v-if="currentEnv" :color="currentEnv === 'dev' ? 'blue' : 'orange'">
                {{ currentEnv === 'dev' ? '开发环境' : '生产环境' }}
              </a-tag>
            </div>
            <a-button size="small" @click="loadPhrases">刷新话术</a-button>
          </div>
        </template>

        <!-- 选择平台 → 联系人（按平台默认带出） → 浏览器买家 -->
        <a-form :label-col="{ style: { width: '110px' } }" label-align="left">
          <!-- 平台（先选平台） -->
          <a-form-item label="平台">
            <a-select
              v-model:value="form.platform_type"
              style="width: 340px"
              @change="onPlatformChange"
            >
              <a-select-option :value="1">平台B</a-select-option>
              <a-select-option :value="2">平台A</a-select-option>
              <a-select-option :value="3">平台D</a-select-option>
              <a-select-option :value="4">平台C</a-select-option>
            </a-select>
            <div v-if="form.mode === 'auto' && mixedPlatform" class="muted" style="margin-top: 4px; font-size: 12px">
              所选浏览器买家平台不一致，按各自平台发送（此处仅作缺省值）
            </div>
          </a-form-item>

          <!-- 联系人：切换平台后按配置的默认值带出，可修改 -->
          <a-form-item label="联系人">
            <a-input v-model:value="form.contact" placeholder="如：演示店铺A" style="width: 340px" />
          </a-form-item>

          <!-- 浏览器买家（原“用户（端口）”，排在最下方） -->
          <!-- 手动模式：单个浏览器买家 -->
          <a-form-item v-if="form.mode === 'manual'" label="浏览器买家">
            <a-select
              v-model:value="form.port"
              placeholder="先创建浏览器买家，然后刷新"
              style="width: 340px"
              @change="onPortChange"
            >
              <a-select-option v-for="u in platformUsers" :key="u.port" :value="u.port">
                端口 {{ u.port }} · {{ u.username }} · {{ platformLabel(u.platform_type) }}
                <a-tag v-if="!u.logged_in" color="error" size="small">离线</a-tag>
              </a-select-option>
            </a-select>
          </a-form-item>

          <!-- 自动模式：多选浏览器买家，每个端口一条独立发送线程 -->
          <a-form-item v-else label="浏览器买家">
            <a-select
              v-model:value="form.ports"
              mode="multiple"
              placeholder="可多选，每个浏览器买家独立发送"
              style="width: 340px"
              :max-tag-count="4"
              @change="onPortsChange"
            >
              <a-select-option v-for="u in platformUsers" :key="u.port" :value="u.port">
                端口 {{ u.port }} · {{ u.username }} · {{ platformLabel(u.platform_type) }}
                <a-tag v-if="!u.logged_in" color="error" size="small">离线</a-tag>
              </a-select-option>
            </a-select>
            <div class="muted" style="margin-top: 4px; font-size: 12px">
              <a @click.prevent="selectAllPorts">全选</a>
              <a-divider type="vertical" />
              <a @click.prevent="form.ports = []">清空</a>
              <span v-if="form.ports.length" style="margin-left: 8px">
                已选 {{ form.ports.length }} 个浏览器买家
              </span>
            </div>
          </a-form-item>

          <!-- 发送模式 -->
          <a-divider style="margin: 4px 0; font-size: 13px">发送模式</a-divider>

          <a-form-item label="发送模式">
            <a-radio-group v-model:value="form.mode">
              <a-radio value="manual">手动发送</a-radio>
              <a-radio value="auto">自动发送</a-radio>
            </a-radio-group>
          </a-form-item>

          <!-- 手动模式：消息输入 -->
          <template v-if="form.mode === 'manual'">
            <a-form-item label="消息类型">
              <a-radio-group v-model:value="form.message_type">
                <a-radio value="text">文本</a-radio>
                <a-radio value="image">图片</a-radio>
                <a-radio value="video">视频</a-radio>
                <a-radio value="card">商品卡片</a-radio>
                <a-radio value="order">订单（仅平台A）</a-radio>
              </a-radio-group>
            </a-form-item>

            <!-- 文本消息 -->
            <a-form-item v-if="form.message_type === 'text'" label="消息内容">
              <a-textarea
                v-model:value="form.manual_message"
                placeholder="输入要发送的消息"
                :rows="3"
                style="width: 100%"
              />
            </a-form-item>
            <a-form-item v-if="form.message_type === 'text'" label=" ">
              <a-button @click="fillRandomPhrase" size="small">从 FAQ 随机填充</a-button>
            </a-form-item>

            <!-- 图片消息 -->
            <a-form-item v-if="form.message_type === 'image'" label="选择图片">
              <a-select v-model:value="form.image_path" placeholder="选择图片资产" style="width: 100%">
                <a-select-option v-for="img in assets.images" :key="img" :value="img">
                  {{ img.split('/').pop() }}
                </a-select-option>
              </a-select>
              <div class="muted" style="margin-top: 4px; font-size: 12px">
                来自 var/data/pictures/*.png（与 platform_a case 一致）
              </div>
            </a-form-item>

            <!-- 视频消息 -->
            <a-form-item v-if="form.message_type === 'video'" label="选择视频">
              <a-select v-model:value="form.video_path" placeholder="选择视频资产" style="width: 100%">
                <a-select-option v-for="vid in assets.videos" :key="vid" :value="vid">
                  {{ vid.split('/').pop() }}
                </a-select-option>
              </a-select>
              <div class="muted" style="margin-top: 4px; font-size: 12px">
                来自 var/data/videos/*.{mp4,avi,mkv}（与 platform_a case 一致）
              </div>
            </a-form-item>

            <!-- 商品卡片 -->
            <a-form-item v-if="form.message_type === 'card'" label="商品链接">
              <a-select
                v-model:value="form.card_url"
                placeholder="选择商品链接"
                style="width: 100%"
                show-search
              >
                <a-select-opt-group v-for="(urls, pf) in assets.cards" :key="pf" :label="pf">
                  <a-select-option v-for="(url, idx) in urls" :key="url" :value="url">
                    {{ url.substring(0, 60) }}{{ url.length > 60 ? '...' : '' }}
                  </a-select-option>
                </a-select-opt-group>
              </a-select>
              <div class="muted" style="margin-top: 4px; font-size: 12px">
                来自 config/phrases/shopping_faq.json card_url_*（与 platform_a case 一致）
              </div>
            </a-form-item>

            <!-- 订单消息 -->
            <a-form-item v-if="form.message_type === 'order'" label="订单备注">
              <a-input
                v-model:value="form.order_text"
                placeholder="可选，订单备注文本"
                style="width: 100%"
              />
              <div class="muted" style="margin-top: 4px; font-size: 12px">
                仅平台A平台支持，点订单面板发送当前订单
              </div>
            </a-form-item>

            <a-form-item label=" ">
              <a-button type="primary" :loading="sendingManual" @click="sendManual">
                发送
              </a-button>
            </a-form-item>
          </template>

          <!-- 自动模式：批量参数 -->
          <template v-if="form.mode === 'auto'">
            <a-form-item label="消息类型">
              <a-radio-group v-model:value="form.auto_message_type">
                <a-radio value="text">文本</a-radio>
                <a-radio value="image">图片</a-radio>
                <a-radio value="video">视频</a-radio>
                <a-radio value="card">商品卡片</a-radio>
                <a-radio value="random">随机混合</a-radio>
              </a-radio-group>
              <div v-if="form.auto_message_type === 'random'" class="muted" style="margin-top: 4px; font-size: 12px">
                随机混合：每条消息从 文本/图片/视频/商品卡片 中随机选择
              </div>
            </a-form-item>

            <!-- 文本类型 -->
            <template v-if="form.auto_message_type === 'text'">
              <a-form-item label="消息来源">
                <a-radio-group v-model:value="form.message_source">
                  <a-radio value="faq">FAQ 随机</a-radio>
                  <a-radio value="custom">自定义列表</a-radio>
                </a-radio-group>
              </a-form-item>

              <a-form-item v-if="form.message_source === 'custom'" label="消息列表">
                <a-textarea
                  v-model:value="form.custom_messages"
                  placeholder="每行一条消息"
                  :rows="4"
                  style="width: 100%"
                />
              </a-form-item>
            </template>

            <!-- 图片类型 -->
            <a-form-item v-if="form.auto_message_type === 'image'" label="图片池">
              <a-checkbox-group v-model:value="form.auto_images" style="width: 100%">
                <a-row>
                  <a-col v-for="img in assets.images" :key="img" :span="24" style="margin-bottom: 4px">
                    <a-checkbox :value="img">{{ img.split('/').pop() }}</a-checkbox>
                  </a-col>
                </a-row>
              </a-checkbox-group>
              <a-button size="small" @click="form.auto_images = assets.images.slice()" style="margin-top: 8px">
                全选
              </a-button>
              <a-button size="small" @click="form.auto_images = []" style="margin-left: 8px">清空</a-button>
              <div class="muted" style="margin-top: 4px; font-size: 12px">
                每条消息从勾选的图片中随机选一张
              </div>
            </a-form-item>

            <!-- 视频类型 -->
            <a-form-item v-if="form.auto_message_type === 'video'" label="视频池">
              <a-checkbox-group v-model:value="form.auto_videos" style="width: 100%">
                <a-row>
                  <a-col v-for="vid in assets.videos" :key="vid" :span="24" style="margin-bottom: 4px">
                    <a-checkbox :value="vid">{{ vid.split('/').pop() }}</a-checkbox>
                  </a-col>
                </a-row>
              </a-checkbox-group>
              <a-button size="small" @click="form.auto_videos = assets.videos.slice()" style="margin-top: 8px">
                全选
              </a-button>
              <a-button size="small" @click="form.auto_videos = []" style="margin-left: 8px">清空</a-button>
              <div class="muted" style="margin-top: 4px; font-size: 12px">
                每条消息从勾选的视频中随机选一个
              </div>
            </a-form-item>

            <!-- 商品卡片类型 -->
            <a-form-item v-if="form.auto_message_type === 'card'" label="商品链接池">
              <a-select
                v-model:value="form.auto_card_platform"
                placeholder="选择平台"
                style="width: 150px; margin-bottom: 8px"
              >
                <a-select-option v-for="(urls, pf) in assets.cards" :key="pf" :value="pf">
                  {{ pf }}
                </a-select-option>
              </a-select>
              <div class="muted" style="margin-top: 4px; font-size: 12px">
                每条消息从该平台的商品链接中随机选一条（共 {{
                  (assets.cards[form.auto_card_platform] || []).length
                }} 条）
              </div>
            </a-form-item>

            <a-form-item label="每轮条数">
              <a-input-number v-model:value="form.messages_per_round" :min="1" :max="20" style="width: 120px" />
            </a-form-item>
            <a-form-item label="发送间隔">
              <a-input-number v-model:value="form.send_interval" :min="0" :max="300" style="width: 120px" />
              <span class="muted" style="margin-left: 8px">秒（条与条之间）</span>
            </a-form-item>
            <a-form-item label="每轮间隔">
              <a-input-number v-model:value="form.round_interval" :min="0" :max="3600" style="width: 120px" />
              <span class="muted" style="margin-left: 8px">秒（轮与轮之间）</span>
            </a-form-item>
            <a-form-item label="总轮数">
              <a-input-number v-model:value="form.total_rounds" :min="-1" :max="9999" style="width: 120px" />
              <span class="muted" style="margin-left: 8px">-1 为无限循环</span>
            </a-form-item>

            <!-- 压测模式折叠面板 -->
            <a-collapse v-model:activeKey="stressActiveKey" style="margin-top: 16px; margin-bottom: 16px">
              <a-collapse-panel key="stress" header="⚡ 压测模式（动态进线调度）">
                <a-form-item label="启用压测模式">
                  <a-switch v-model:checked="form.dynamic_interval" />
                  <span class="muted" style="margin-left: 8px">
                    开启后按真实进线规律分批启动用户（模拟高峰/平时波动）
                  </span>
                </a-form-item>

                <template v-if="form.dynamic_interval">
                  <a-form-item label="最大并发数">
                    <a-input-number v-model:value="form.max_concurrent" :min="1" :max="100" style="width: 120px" />
                    <span class="muted" style="margin-left: 8px">同时在线的最大用户数</span>
                  </a-form-item>

                  <a-form-item label="平时进线间隔">
                    <a-input-number v-model:value="form.normal_interval[0]" :min="1" :max="3600" style="width: 100px" />
                    <span style="margin: 0 8px">~</span>
                    <a-input-number v-model:value="form.normal_interval[1]" :min="1" :max="3600" style="width: 100px" />
                    <span class="muted" style="margin-left: 8px">秒（随机区间）</span>
                  </a-form-item>

                  <a-form-item label="高峰周期">
                    <a-input-number v-model:value="form.peak_every_minutes" :min="1" :max="120" style="width: 120px" />
                    <span class="muted" style="margin-left: 8px">分钟（多久触发一次高峰）</span>
                  </a-form-item>

                  <a-form-item label="高峰进线数量">
                    <a-input-number v-model:value="form.peak_count[0]" :min="1" :max="50" style="width: 100px" />
                    <span style="margin: 0 8px">~</span>
                    <a-input-number v-model:value="form.peak_count[1]" :min="1" :max="50" style="width: 100px" />
                    <span class="muted" style="margin-left: 8px">用户（一次性启动数）</span>
                  </a-form-item>

                  <a-form-item label="高峰内间隔">
                    <a-input-number v-model:value="form.peak_gap[0]" :min="0" :max="60" style="width: 100px" />
                    <span style="margin: 0 8px">~</span>
                    <a-input-number v-model:value="form.peak_gap[1]" :min="0" :max="60" style="width: 100px" />
                    <span class="muted" style="margin-left: 8px">秒（高峰内用户间启动间隔）</span>
                  </a-form-item>

                  <a-alert
                    message="压测模式说明"
                    description="开启后，用户不会立即全部并发，而是按「平时间隔」逐个进线，每隔「高峰周期」分钟触发一次「高峰进线」（短时间内批量启动）。用于模拟真实业务的进线波动，测试系统在高峰/低谷下的表现。"
                    type="info"
                    show-icon
                    style="margin-top: 8px"
                  />
                </template>
              </a-collapse-panel>
            </a-collapse>

            <a-form-item label=" " style="margin-top: 8px">
              <a-button
                v-if="!batchTaskId"
                type="primary"
                :disabled="!form.ports.length || !form.contact"
                @click="startBatch"
              >
                ▶ 开始自动发送{{ form.ports.length > 1 ? `（${form.ports.length} 个用户）` : '' }}
              </a-button>
              <a-button v-else danger @click="stopBatch">
                ⏹ 停止发送
              </a-button>
            </a-form-item>
          </template>

          <pre v-if="manualResult" class="json">{{ manualResult }}</pre>
        </a-form>
      </a-card>
    </a-col>

    <!-- 右侧：话术预览 + 任务状态 -->
    <a-col :span="10">
      <a-card class="theme-card" style="margin-bottom: 16px">
        <template #title>
          <div class="hdr">
            <span class="sec-title tint-orange"><BookOutlined />FAQ 话术预览</span>
            <span class="muted">{{ faqCount }} 条</span>
          </div>
        </template>
        <div class="phrase-list">
          <div v-for="(phrase, index) in faqList" :key="index" class="phrase-item" @click="copyPhrase(phrase.a)">
            <span class="phrase-key">Q: {{ phrase.q }}</span>
            <span class="phrase-text">A: {{ phrase.a }}</span>
          </div>
          <div v-if="!faqCount" class="muted pad">点「刷新话术」加载</div>
        </div>
      </a-card>

      <!-- 自动发送任务状态 -->
      <a-card v-if="batchTaskId" class="theme-card">
        <template #title>
          <span class="sec-title tint-green">
            <SyncOutlined />
            自动发送状态
            <a-tag v-if="batchStatus" :color="batchStatusColor" style="margin-left: 8px">
              {{ batchStatus }}
            </a-tag>
          </span>
        </template>
        <a-descriptions :column="2" size="small" bordered>
          <a-descriptions-item label="轮次">{{ batchState.round || 0 }}</a-descriptions-item>
          <a-descriptions-item label="发送成功">{{ batchState.sent || 0 }}</a-descriptions-item>
          <a-descriptions-item label="发送失败">{{ batchState.failed || 0 }}</a-descriptions-item>
          <a-descriptions-item label="错误信息" :span="2">
            {{ batchState.error || '-' }}
          </a-descriptions-item>
        </a-descriptions>

        <!-- 多用户时按端口展开各自进度 -->
        <a-table
          v-if="portRows.length > 1"
          :columns="portColumns"
          :data-source="portRows"
          :pagination="false"
          size="small"
          row-key="port"
          style="margin-top: 12px"
        >
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'status'">
              <a-tag :color="statusColor(record.status)">{{ record.status }}</a-tag>
            </template>
          </template>
        </a-table>
      </a-card>
    </a-col>
  </a-row>
</template>

<script lang="ts" setup>
  defineOptions({ name: 'MessageSend' });
  import { ref, reactive, computed, onMounted, onUnmounted } from 'vue';
  import { SendOutlined, BookOutlined, SyncOutlined } from '@ant-design/icons-vue';
  import { message } from 'ant-design-vue';
  import http from '@/api/platform/http';

  const PLATFORM_LABELS: Record<number, string> = {
    1: '平台B', 2: '平台A', 3: '平台D', 4: '平台C',
  };

  const PLATFORM_DEFAULT_CONTACT: Record<number, string> = {
    1: '演示店铺A',
    2: 'Yuyuan187509小店',
  };

  /** MessageSend 数字平台号 → shop_agent_name.json 平台名 */
  const NUM_TO_PLATFORM: Record<number, string> = {
    1: 'platform_b', 2: 'platform_a', 3: 'platform_d', 4: 'platform_c',
  };

  // 当前环境 + 各平台账号配置（来自 /env/accounts ← shop_agent_name.json，按 env.json current）
  const currentEnv = ref('');
  const accounts = ref<Record<string, any>>({});

  // ── 用户列表 ──
  const userList = ref<any[]>([]);
  /** 浏览器买家下拉只展示当前所选平台的账号（随平台过滤） */
  const platformUsers = computed(() =>
    userList.value.filter((u) => u.platform_type === form.platform_type),
  );
  const faqList = ref<Record<string, string>>({});
  const faqCount = computed(() => Object.keys(faqList.value).length);

  // ── 资产列表（图片/视频/商品链接） ──
  const assets = ref<any>({ images: [], videos: [], cards: {} });

  // ── 表单 ──
  const form = reactive<any>({
    port: undefined,       // 手动模式：单个端口
    ports: [] as number[], // 自动模式：多个端口
    platform_type: 2,
    contact: 'Yuyuan187509小店',
    mode: 'manual',
    message_type: 'text',  // 手动模式：text/image/video/card/order
    manual_message: '',
    image_path: '',
    video_path: '',
    card_url: '',
    order_text: '',
    auto_message_type: 'text',  // 自动模式：text/image/video/card/random
    message_source: 'faq',
    custom_messages: '',
    auto_images: [] as string[],      // 自动模式图片池
    auto_videos: [] as string[],      // 自动模式视频池
    auto_card_platform: 'platform_a',   // 自动模式商品卡片平台
    messages_per_round: 1,
    send_interval: 15,
    round_interval: 15,
    total_rounds: 20,

    // 压测参数
    dynamic_interval: false,
    max_concurrent: 10,
    normal_interval: [30, 90],
    peak_every_minutes: 10,
    peak_count: [5, 10],
    peak_gap: [3, 5],
  });

  const stressActiveKey = ref<string[]>([]);

  const sendingManual = ref(false);
  const manualResult = ref('');
  const batchTaskId = ref('');
  const batchStatus = ref('');
  const batchState = ref<any>({});

  let pollTimer: any = null;

  function statusColor(status: string) {
    const m: Record<string, string> = {
      running: 'processing', completed: 'success', stopped: 'warning', failed: 'error',
    };
    return m[status] || 'default';
  }

  const batchStatusColor = computed(() => statusColor(batchStatus.value));

  // ── 多用户进度表 ──
  const portColumns = [
    { title: '端口', dataIndex: 'port', key: 'port', width: 72 },
    { title: '状态', dataIndex: 'status', key: 'status', width: 88 },
    { title: '轮次', dataIndex: 'round', key: 'round', width: 60 },
    { title: '成功', dataIndex: 'sent', key: 'sent', width: 60 },
    { title: '失败', dataIndex: 'failed', key: 'failed', width: 60 },
  ];

  /** 把后端 ports 字典摊成表格行（key 走 JSON 是字符串，转回数字排序）。 */
  const portRows = computed(() => {
    const ports = batchState.value?.ports;
    if (!ports) return [];
    return Object.entries(ports)
      .map(([port, s]: [string, any]) => ({ port: Number(port), ...s }))
      .sort((a, b) => a.port - b.port);
  });

  function platformLabel(type: number) {
    return PLATFORM_LABELS[type] || `平台${type}`;
  }

  /**
   * 平台切换时同步默认联系人。
   * 优先取 shop_agent_name.json 当前环境下该平台的 target_contact（/env/accounts），
   * 取不到再退回内置默认表；仅当当前值还是某个默认值（说明用户没手改过）时才覆盖，
   * 避免冲掉手输内容。
   */
  function defaultContactOf(platformType: number): string {
    const key = NUM_TO_PLATFORM[platformType];
    return accounts.value[key]?.target_contact || PLATFORM_DEFAULT_CONTACT[platformType] || '';
  }

  function syncDefaultContact(platformType: number) {
    const next = defaultContactOf(platformType);
    if (!next) return;
    const known = new Set<string>([
      ...Object.values(accounts.value).map((a: any) => a?.target_contact).filter(Boolean),
      ...Object.values(PLATFORM_DEFAULT_CONTACT),
    ]);
    if (!form.contact || known.has(form.contact)) {
      form.contact = next;
    }
  }

  function onPlatformChange(platformType: number) {
    syncDefaultContact(platformType);
    // 切平台后，浏览器买家的已选账号只保留属于该平台的
    const samePlatform = (p: number) =>
      userList.value.find((u) => u.port === p)?.platform_type === platformType;
    if (form.port && !samePlatform(form.port)) form.port = undefined;
    if (form.ports?.length) form.ports = form.ports.filter(samePlatform);
  }

  function onPortChange(port: number) {
    const u = userList.value.find((x) => x.port === port);
    if (u && u.platform_type) {
      form.platform_type = u.platform_type;
      syncDefaultContact(u.platform_type);
    }
  }

  /** 所选端口对应的用户（保持选择顺序）。 */
  const selectedUsers = computed(() =>
    form.ports
      .map((p: number) => userList.value.find((x) => x.port === p))
      .filter(Boolean),
  );

  /** 所选用户是否跨了多个平台 —— 此时按端口分别下发 platform_type。 */
  const mixedPlatform = computed(() => {
    const types = new Set(selectedUsers.value.map((u: any) => u.platform_type).filter(Boolean));
    return types.size > 1;
  });

  function onPortsChange(ports: number[]) {
    // 平台一致时同步到 platform_type，方便用户看到当前生效平台
    const types = new Set(
      ports
        .map((p) => userList.value.find((x) => x.port === p)?.platform_type)
        .filter(Boolean),
    );
    if (types.size === 1) {
      form.platform_type = [...types][0] as number;
      syncDefaultContact(form.platform_type);
    }
  }

  function selectAllPorts() {
    // 只全选当前平台下的浏览器买家（与下拉过滤一致）
    form.ports = platformUsers.value.map((u) => u.port);
    onPortsChange(form.ports);
  }

  function copyPhrase(text: string) {
    form.manual_message = text;
    message.success('已填入消息框');
  }

  function fillRandomPhrase() {
    http.get('/ui/random-phrase').then(({ data }) => {
      // 后端返回 { q, a } 对象，取 a（回答话术）填入消息框
      const p = data?.phrase;
      if (p && p.a) {
        form.manual_message = p.a;
      } else if (typeof p === 'string') {
        form.manual_message = p;
      } else {
        message.warning('获取随机话术失败');
      }
    }).catch(() => {
      message.warning('获取随机话术失败');
    });
  }

  // ── 加载用户和话术 ──
  async function loadUsers() {
    try {
      const { data } = await http.get('/env/users');
      userList.value = Array.isArray(data?.users) ? data.users : [];
    } catch { /* 忽略 */ }
  }

  async function loadPhrases() {
    try {
      const { data } = await http.get('/ui/phrases');
      // 后端返回 [{ q, a }, ...] 话术对象数组
      faqList.value = Array.isArray(data) ? data : [];
    } catch { /* 忽略 */ }
  }

  async function loadAssets() {
    try {
      const { data } = await http.get('/ui/assets');
      assets.value = data || { images: [], videos: [], cards: {} };
    } catch { /* 忽略 */ }
  }

  // ── 手动发送 ──
  async function sendManual() {
    if (!form.port) { message.warning('请先选择用户'); return; }
    if (!form.contact.trim()) { message.warning('请输入联系人'); return; }

    // 根据消息类型验证必填字段
    if (form.message_type === 'text' && !form.manual_message.trim()) {
      message.warning('请输入文本消息内容');
      return;
    }
    if (form.message_type === 'image' && !form.image_path) {
      message.warning('请选择图片');
      return;
    }
    if (form.message_type === 'video' && !form.video_path) {
      message.warning('请选择视频');
      return;
    }
    if (form.message_type === 'card' && !form.card_url) {
      message.warning('请选择商品链接');
      return;
    }

    sendingManual.value = true;
    manualResult.value = '';
    try {
      let endpoint = '/ui/send-message';
      let payload: any = {
        port: form.port,
        platform_type: form.platform_type,
        contact: form.contact.trim(),
        safe_mode: true,
      };

      // 根据消息类型选择不同的端点和参数
      if (form.message_type === 'text') {
        payload.message = form.manual_message.trim();
      } else if (form.message_type === 'image') {
        endpoint = '/ui/send-image';
        payload.image_path = form.image_path;
      } else if (form.message_type === 'video') {
        endpoint = '/ui/send-video';
        payload.video_path = form.video_path;
      } else if (form.message_type === 'card') {
        endpoint = '/ui/send-card';
        payload.card_url = form.card_url;
      } else if (form.message_type === 'order') {
        endpoint = '/ui/send-order';
        if (form.order_text.trim()) {
          payload.order_text = form.order_text.trim();
        }
      }

      const { data } = await http.post(endpoint, payload);
      manualResult.value = JSON.stringify(data, null, 2);
      if (data.success) {
        message.success('发送成功');
      } else {
        message.error(data.error || '发送失败');
      }
    } catch (e: any) {
      manualResult.value = JSON.stringify(e.response?.data || { error: String(e) }, null, 2);
      message.error(e.response?.data?.error || '发送请求失败');
    } finally {
      sendingManual.value = false;
    }
  }

  // ── 自动批量发送（多用户并发）──
  async function startBatch() {
    if (!form.ports.length) { message.warning('请先选择至少一个用户'); return; }
    if (!form.contact.trim()) { message.warning('请输入联系人'); return; }

    const payload: any = {
      ports: form.ports,
      platform_type: form.platform_type,
      contact: form.contact.trim(),
      messages_per_round: form.messages_per_round,
      send_interval: form.send_interval,
      round_interval: form.round_interval,
      total_rounds: form.total_rounds,
      safe_mode: true,
      message_type: form.auto_message_type,  // 新增：消息类型

      // 压测参数
      dynamic_interval: form.dynamic_interval,
      max_concurrent: form.max_concurrent,
      normal_interval: form.normal_interval,
      peak_every_minutes: form.peak_every_minutes,
      peak_count: form.peak_count,
      peak_gap: form.peak_gap,
    };

    // 混平台时按端口下发各自的 platform_type，避免用错平台的选择器
    if (mixedPlatform.value) {
      payload.port_platforms = Object.fromEntries(
        selectedUsers.value.map((u: any) => [u.port, u.platform_type]),
      );
    }

    // 根据消息类型添加对应参数
    if (form.auto_message_type === 'text') {
      if (form.message_source === 'custom') {
        const lines = form.custom_messages.split('\n').map((s: string) => s.trim()).filter(Boolean);
        if (!lines.length) { message.warning('自定义消息列表为空'); return; }
        payload.message_list = lines;
      }
    } else if (form.auto_message_type === 'image') {
      if (!form.auto_images.length) { message.warning('请至少选择一张图片'); return; }
      payload.image_pool = form.auto_images;
    } else if (form.auto_message_type === 'video') {
      if (!form.auto_videos.length) { message.warning('请至少选择一个视频'); return; }
      payload.video_pool = form.auto_videos;
    } else if (form.auto_message_type === 'card') {
      const cardUrls = assets.value.cards[form.auto_card_platform] || [];
      if (!cardUrls.length) { message.warning('所选平台无可用商品链接'); return; }
      payload.card_pool = cardUrls;
    } else if (form.auto_message_type === 'random') {
      // 随机混合模式：准备所有类型的资源池
      payload.image_pool = assets.value.images;
      payload.video_pool = assets.value.videos;
      payload.card_pool = assets.value.cards[form.auto_card_platform] || [];
    }

    try {
      const { data } = await http.post('/ui/send-batch', payload);
      if (data.success) {
        batchTaskId.value = data.task_id;
        batchStatus.value = 'running';
        batchState.value = {};
        message.success(`自动发送已启动（${form.ports.length} 个用户）`);
        startPolling();
      } else {
        message.error(data.error || '启动失败');
      }
    } catch (e: any) {
      message.error(e.response?.data?.error || '启动失败');
    }
  }

  async function stopBatch() {
    if (!batchTaskId.value) return;
    try {
      const { data } = await http.post(`/ui/send-batch/${batchTaskId.value}/cancel`);
      if (data.success) {
        message.success('已停止');
        batchStatus.value = 'stopped';
      } else {
        message.error(data.error || '取消失败');
      }
    } catch (e: any) {
      message.error(e.response?.data?.error || '取消失败');
    }
  }

  async function pollBatchStatus() {
    if (!batchTaskId.value) return;
    try {
      const { data } = await http.get(`/ui/send-batch/${batchTaskId.value}/status`);
      if (data.error) {
        batchStatus.value = 'completed';
        stopPolling();
        return;
      }
      batchStatus.value = data.status;
      batchState.value = data;
      if (data.status !== 'running') {
        stopPolling();
        const scope = portRows.value.length > 1 ? `${portRows.value.length} 个用户共` : '';
        if (data.failed > 0) {
          message.warning(`发送完成：${scope}成功 ${data.sent} 条，失败 ${data.failed} 条`);
        } else {
          message.success(`发送完成：${scope}成功 ${data.sent} 条`);
        }
      }
    } catch {
      batchStatus.value = 'completed';
      stopPolling();
    }
  }

  function startPolling() {
    stopPolling();
    pollTimer = setInterval(pollBatchStatus, 2000);
  }
  function stopPolling() {
    if (pollTimer) { clearInterval(pollTimer); pollTimer = null; }
  }

  /** 拉取当前环境的平台账号配置（/env/accounts）→ 环境标签 + 联系人默认值 */
  async function loadAccounts() {
    try {
      const { data } = await http.get('/env/accounts');
      currentEnv.value = data?.env || '';
      accounts.value = data?.accounts || {};
      // 就绪后带出当前平台的默认联系人（仅未手改时覆盖）
      syncDefaultContact(form.platform_type);
    } catch {
      // 拉取失败不阻断，仍用内置默认值
    }
  }

  onMounted(() => {
    loadUsers();
    loadPhrases();
    loadAssets();
    loadAccounts();
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
}
.pad {
  padding: 12px;
}
.json {
  background: #0d0f13;
  color: var(--text-secondary);
  padding: 12px;
  border-radius: 6px;
  max-height: 280px;
  overflow: auto;
  font-size: var(--vben-font-size-sm);
  white-space: pre-wrap;
  margin: 12px 0 0 0;
  line-height: 1.6;
}
.phrase-list {
  max-height: 420px;
  overflow-y: auto;
}
.phrase-item {
  display: flex;
  align-items: baseline;
  gap: 8px;
  padding: 6px 8px;
  border-bottom: 1px solid var(--border-color);
  cursor: pointer;
  font-size: var(--vben-font-size-base);
  transition: background 0.15s;
}
.phrase-item:hover {
  background: rgba(255, 255, 255, 0.04);
}
.phrase-key {
  color: var(--accent);
  font-weight: 600;
  font-size: var(--vben-font-size-sm);
  min-width: 32px;
  flex-shrink: 0;
}
.phrase-text {
  color: var(--text-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
