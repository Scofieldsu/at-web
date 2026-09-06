<template>
  <div class="env-grid">
      <!-- 安装 RPA（左上） -->
      <a-card class="theme-card env-cell env-install">
        <template #title><span class="sec-title tint-blue"><DownloadOutlined />安装 RPA</span></template>
        <a-form label-align="left" :label-col="{ style: { width: '96px' } }">
          <a-form-item label="平台">
            <a-select v-model:value="rpa.platform" placeholder="选择平台" style="width: 100%">
              <a-select-option value="platform_a">平台A (platform_a)</a-select-option>
              <a-select-option value="platform_b">平台B (platform_b)</a-select-option>
              <a-select-option value="platform_c">平台C (platform_c)</a-select-option>
              <a-select-option value="platform_d">平台D (platform_d)</a-select-option>
            </a-select>
          </a-form-item>
          <a-form-item label="版本">
            <a-auto-complete
              v-model:value="rpa.version"
              :options="versionOptions"
              :filter-option="false"
              placeholder="选择或输入版本，如 2.0.1.2"
              style="width: 100%"
              @dropdownVisibleChange="onVersionDropdown"
            >
              <template #notFoundContent>
                <span v-if="versionsLoading">加载中...</span>
                <span v-else>无可用版本，可直接输入</span>
              </template>
            </a-auto-complete>
          </a-form-item>
          <a-form-item label="安装类型">
            <a-select v-model:value="rpa.install_type" placeholder="选择安装类型" style="width: 100%">
              <a-select-option value="main">main</a-select-option>
              <a-select-option value="full">full</a-select-option>
            </a-select>
          </a-form-item>
          <a-form-item label="下载地址">
            <a-input v-model:value="rpa.download_url" placeholder="可选，留空则按照平台及版本下载" />
          </a-form-item>
          <a-form-item label="目标机器">
            <a-input v-model:value="rpa.target_machine" placeholder="可选" />
          </a-form-item>
          <a-button type="primary" :loading="installing" @click="installRpa">安装 RPA</a-button>
        </a-form>
        <pre v-if="rpaResult" class="json">{{ rpaResult }}</pre>
      </a-card>

      <!-- Agent 上线（左下） -->
      <a-card class="theme-card env-cell env-agent">
        <template #title><span class="sec-title tint-green"><PoweroffOutlined />Agent 上线</span></template>
        <a-form label-align="left" :label-col="{ style: { width: '96px' } }">
          <a-form-item label="平台">
            <a-select v-model:value="agent.platform" placeholder="选择平台" style="width: 100%">
              <a-select-option value="platform_a">平台A (platform_a)</a-select-option>
              <a-select-option value="platform_b">平台B (platform_b)</a-select-option>
              <a-select-option value="platform_c">平台C (platform_c)</a-select-option>
              <a-select-option value="platform_d">平台D (platform_d)</a-select-option>
            </a-select>
          </a-form-item>
          <a-form-item label="店铺">
            <a-select
              v-model:value="agent.shop"
              show-search
              allow-clear
              placeholder="选择或输入店铺"
              style="width: 100%"
              :options="agentShopList.map((s) => ({ label: s, value: s }))"
              @change="onAgentShopChange"
            />
          </a-form-item>
          <a-form-item label="Agent">
            <a-select
              v-model:value="agent.agent"
              show-search
              allow-clear
              placeholder="选择或输入 agent"
              style="width: 100%"
              :options="agentAgentList.map((a) => ({ label: a, value: a }))"
            />
          </a-form-item>
          <a-button type="primary" :loading="onlining" @click="onlineAgent">上线</a-button>
        </a-form>
        <pre v-if="agentResult" class="json">{{ agentResult }}</pre>
      </a-card>

      <!-- 创建浏览器用户（右上） -->
      <a-card class="theme-card env-cell env-create">
        <template #title>
          <div class="hdr">
            <span class="sec-title tint-orange"><UserAddOutlined />创建浏览器用户</span>
          </div>
        </template>
        <a-alert type="info" :closable="false" show-icon style="margin-bottom: 14px" message="启动 Chrome 浏览器实例并自动登录（凭证模式读 accounts.yaml 的端口+密码自动填入；扫码模式弹二维码人工扫码）。">
          <template #icon>
            <!-- 与模拟中控页提示同款：info 蓝感叹号（conn-tip-icon 视觉） -->
            <ExclamationCircleOutlined style="color: var(--info-color, #0090ff); font-size: 13px" />
          </template>
        </a-alert>

        <a-form label-align="left" :label-col="{ style: { width: '100px' } }">
          <a-form-item label="平台">
            <a-select v-model:value="form.platform" style="width: 100%">
              <a-select-option value="platform_a">平台A (platform_a)</a-select-option>
              <a-select-option value="platform_b">平台B (platform_b)</a-select-option>
              <a-select-option value="platform_c">平台C (platform_c)</a-select-option>
              <a-select-option value="platform_d">平台D (platform_d)</a-select-option>
            </a-select>
          </a-form-item>
          <a-form-item label="数量">
            <a-input-number v-model:value="form.count" :min="1" :max="50" style="width: 100%" />
          </a-form-item>
          <a-form-item label="登录模式">
            <a-radio-group v-model:value="form.login_mode">
              <a-radio value="credential">凭证自动登录</a-radio>
              <a-radio value="qr">扫码登录</a-radio>
            </a-radio-group>
          </a-form-item>
          <a-form-item v-if="form.login_mode === 'qr'" label="起始端口">
            <a-input-number v-model:value="form.start_port" :min="7000" :max="65535" style="width: 100%" />
            <div class="muted" style="font-size: 12px; margin-top: 4px">
              从该端口起连续分配 count 个端口
            </div>
          </a-form-item>
          <a-form-item>
            <a-button
              type="primary"
              :loading="creating"
              :disabled="!form.platform || !form.count"
              @click="createUsers"
            >
              创建用户
            </a-button>
          </a-form-item>
        </a-form>

        <pre v-if="createResult" class="json">{{ createResult }}</pre>
      </a-card>

      <!-- 分隔竖线 -->
      <div class="env-vline"></div>

      <!-- 已创建用户列表（右下） -->
      <a-card class="theme-card env-cell env-users">
        <template #title>
          <div class="hdr">
            <span class="sec-title tint-purple"><UsergroupAddOutlined />已创建的用户</span>
            <div>
              <a-select
                v-model:value="userFilterPlatform"
                style="width: 130px; margin-right: 8px"
                placeholder="全部平台"
                allow-clear
                @change="loadUsers"
              >
                <a-select-option value="platform_a">平台A</a-select-option>
                <a-select-option value="platform_b">平台B</a-select-option>
                <a-select-option value="platform_c">平台C</a-select-option>
                <a-select-option value="platform_d">平台D</a-select-option>
              </a-select>
              <a-button :loading="loadingUsers" size="small" @click="loadUsers">刷新</a-button>
            </div>
          </div>
        </template>

        <a-table
          :data-source="users"
          :columns="userColumns"
          :pagination="false"
          row-key="port"
          size="small"
          class="theme-table"
          :locale="{ emptyText: '暂无已创建的用户' }"
        >
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'logged_in'">
              <a-tag :class="record.logged_in ? 'tag-online' : 'tag-offline'">
                {{ record.logged_in ? '在线' : '离线' }}
              </a-tag>
            </template>
            <template v-else-if="column.key === 'platform'">
              {{ platformLabel(record.platform_type) }}
            </template>
          </template>
        </a-table>
      </a-card>
  </div>
</template>

<script lang="ts" setup>
  defineOptions({ name: 'EnvUsers' });
  import { ref, reactive, computed, watch, onMounted } from 'vue';
  import { message } from 'ant-design-vue';
  import { DownloadOutlined, ExclamationCircleOutlined, PoweroffOutlined, UserAddOutlined, UsergroupAddOutlined } from '@ant-design/icons-vue';
  import http from '@/api/platform/http';

  // ── RPA 安装 ──────────────────────────────────────────
  const rpa = ref<any>({
    platform: 'platform_a',
    version: '',
    install_type: 'main',
    download_url: '',
    target_machine: '',
  });
  const installing = ref(false);
  const rpaResult = ref('');

  const versionOptions = ref<{ value: string }[]>([]);
  const versionsLoading = ref(false);

  async function loadVersions() {
    if (!rpa.value.platform) return;
    versionsLoading.value = true;
    try {
      const { data } = await http.get('/env/versions', {
        params: { platform: rpa.value.platform },
      });
      const versions: string[] = data.versions || [];
      versionOptions.value = versions.map((v) => ({ value: v }));
    } catch (e: any) {
      versionOptions.value = [];
      message.error(e.response?.data?.error || '获取版本列表失败');
    } finally {
      versionsLoading.value = false;
    }
  }

  function onVersionDropdown(open: boolean) {
    if (open && versionOptions.value.length === 0) loadVersions();
  }

  watch(
    () => rpa.value.platform,
    () => {
      rpa.value.version = '';
      versionOptions.value = [];
      loadVersions();
    },
  );

  async function installRpa() {
    if (!rpa.value.platform || !rpa.value.version) {
      message.warning('平台和版本为必填');
      return;
    }
    installing.value = true;
    try {
      const { data } = await http.post('/env/install-rpa', rpa.value);
      rpaResult.value = JSON.stringify(data, null, 2);
      data.success ? message.success('RPA 安装成功') : message.error(data.error || '安装失败');
    } catch (e: any) {
      rpaResult.value = JSON.stringify(e.response?.data || { error: String(e) }, null, 2);
      message.error(e.response?.data?.error || '安装请求失败');
    } finally {
      installing.value = false;
    }
  }

  // ── Agent 上线 ────────────────────────────────────────
  const agent = ref<any>({ platform: 'platform_a', shop: '', agent: '' });
  const onlining = ref(false);
  const agentResult = ref('');
  const planOptions = ref<any>({});

  const agentShopList = computed(() =>
    Object.keys(planOptions.value[agent.value.platform] || {}),
  );
  const agentAgentList = computed(() => {
    const shops = planOptions.value[agent.value.platform] || {};
    const shop = agent.value.shop;
    if (shop && shops[shop]) return shops[shop];
    return [...new Set(Object.values(shops).flat())] as string[];
  });

  function onAgentShopChange() {
    if (agent.value.agent && !agentAgentList.value.includes(agent.value.agent)) {
      agent.value.agent = '';
    }
  }

  async function loadAgentOptions() {
    try {
      const { data } = await http.get('/plan/options');
      planOptions.value = data.options ?? data ?? {};
    } catch (e) {
      planOptions.value = {};
    }
  }

  watch(
    () => agent.value.platform,
    () => {
      agent.value.shop = '';
      agent.value.agent = '';
    },
  );

  async function onlineAgent() {
    if (!agent.value.platform || !agent.value.shop || !agent.value.agent) {
      message.warning('平台、店铺、Agent 为必填');
      return;
    }
    onlining.value = true;
    try {
      const { data } = await http.post('/env/online-agent', agent.value);
      agentResult.value = JSON.stringify(data, null, 2);
      data.success ? message.success('上线成功') : message.error(data.error || '上线失败');
    } catch (e: any) {
      agentResult.value = JSON.stringify(e.response?.data || { error: String(e) }, null, 2);
      message.error(e.response?.data?.error || '上线请求失败');
    } finally {
      onlining.value = false;
    }
  }

  // ── 创建浏览器用户 ────────────────────────────────────
  const PLATFORM_LABELS: Record<number, string> = {
    1: '平台B', 2: '平台A', 3: '平台D', 4: '平台C',
  };

  const form = reactive<any>({
    platform: 'platform_a',
    count: 1,
    login_mode: 'credential',
    start_port: 7000,
  });

  const creating = ref(false);
  const createResult = ref('');

  const users = ref<any[]>([]);
  const loadingUsers = ref(false);
  const userFilterPlatform = ref('');

  const userColumns = [
    {
      title: '端口', dataIndex: 'port', key: 'port', width: 90,
      sorter: (a: any, b: any) => Number(a.port) - Number(b.port),
    },
    { title: '用户名', dataIndex: 'username', key: 'username', width: 200, ellipsis: true },
    {
      title: '平台', key: 'platform', width: 90,
      sorter: (a: any, b: any) =>
        String(platformLabel(a.platform_type)).localeCompare(String(platformLabel(b.platform_type))),
    },
    {
      title: '在线状态', key: 'logged_in', width: 100,
      sorter: (a: any, b: any) => Number(!!b.logged_in) - Number(!!a.logged_in),
    },
  ];

  function platformLabel(type: number) {
    return PLATFORM_LABELS[type] || `平台${type}`;
  }

  async function createUsers() {
    if (!form.platform || !form.count) {
      message.warning('请填写平台和数量');
      return;
    }
    creating.value = true;
    createResult.value = '';
    try {
      const payload: any = {
        platform: form.platform,
        count: form.count,
        login_mode: form.login_mode,
      };
      if (form.login_mode === 'qr') payload.start_port = form.start_port;

      const { data } = await http.post('/env/create-users', payload, { timeout: 900000 });
      createResult.value = JSON.stringify(data, null, 2);
      if (data.success) {
        message.success(`成功创建 ${data.users?.length || 0} 个用户`);
        await loadUsers();
      } else {
        message.error(data.error || '创建失败');
      }
    } catch (e: any) {
      const body = e.response?.data || { error: String(e) };
      createResult.value = JSON.stringify(body, null, 2);
      message.error(body.error || '创建请求失败');
    } finally {
      creating.value = false;
    }
  }

  async function loadUsers() {
    loadingUsers.value = true;
    try {
      await http.post('/env/users/rescan').catch(() => {
        // 扫描失败不阻塞列表加载
      });

      const params: any = {};
      if (userFilterPlatform.value) params.platform = userFilterPlatform.value;
      const { data } = await http.get('/env/users', { params });
      users.value = Array.isArray(data?.users) ? data.users : [];
    } catch (e: any) {
      message.error('加载用户列表失败');
    } finally {
      loadingUsers.value = false;
    }
  }

  onMounted(() => {
    loadVersions();
    loadAgentOptions();
    loadUsers();
  });
</script>

<style scoped>
/* 左右功能区布局：左列略窄（安装/Agent），右列略宽（创建/列表），中间 1px 分隔线贯穿到底 */
.env-grid {
  display: grid;
  grid-template-columns: minmax(0, 5fr) 1px minmax(0, 7fr);
  grid-template-rows: auto auto;
  column-gap: 24px;
  row-gap: 16px;
  align-items: start;
}
/* 中间竖向分隔线：作为独立列贯穿两行，直达底部 */
.env-vline {
  grid-area: 1 / 2 / 3 / 3;
  width: 1px;
  height: 100%;
  background: var(--border-color);
}
.env-install { grid-area: 1 / 1; }
.env-agent   { grid-area: 2 / 1; }
.env-create  { grid-area: 1 / 3; }
.env-users   { grid-area: 2 / 3; }
/* 表单控件宽度收窄：下拉/输入/数字框等以适合尺寸为主，不撑满整卡 */
.env-cell :deep(.ant-form-item-control-input-content) {
  max-width: 340px;
}
/* 已创建用户的筛选下拉保持窄宽度 */
.env-users .ant-select {
  max-width: 160px;
}
.hdr {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  row-gap: 6px;
  column-gap: 12px;
}
/* 标题不收缩不换行：避免右侧筛选/刷新控件变宽时挤压标题导致左移/截断 */
.hdr .sec-title {
  flex-shrink: 0;
  white-space: nowrap;
  min-width: 0;
}
/* 右侧操作区（筛选下拉 + 刷新）整体不收缩 */
.hdr > div {
  display: inline-flex;
  align-items: center;
  flex-shrink: 0;
  min-width: 0;
}
.muted {
  color: var(--text-muted);
}
/* 在线/离线状态：与全系统语义色一致（绿 success / 红 error，浅色底不突兀） */
.tag-online {
  color: var(--success-color);
  background: rgba(48, 164, 108, 0.12);
  border-color: rgba(48, 164, 108, 0.35);
}
.tag-offline {
  color: var(--error-color);
  background: rgba(229, 72, 77, 0.12);
  border-color: rgba(229, 72, 77, 0.35);
}
.json {
  background: #f5f6f8;
  color: var(--text-primary);
  padding: 12px;
  border-radius: 6px;
  border: 1px solid var(--border-color);
  max-height: 280px;
  overflow: auto;
  font-size: var(--vben-font-size-sm);
  white-space: pre-wrap;
  margin: 12px 0 0 0;
  line-height: 1.6;
}
</style>
