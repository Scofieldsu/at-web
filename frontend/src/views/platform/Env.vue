<template>
  <a-row :gutter="16">
    <a-col :span="12">
      <a-card class="theme-card">
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
    </a-col>

    <a-col :span="12">
      <a-card class="theme-card">
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
    </a-col>
  </a-row>
</template>

<script lang="ts" setup>
  defineOptions({ name: 'Env' });
  import { ref, computed, watch, onMounted } from 'vue';
  import { message } from 'ant-design-vue';
  import { DownloadOutlined, PoweroffOutlined } from '@ant-design/icons-vue';
  import http from '@/api/platform/http';

  const rpa = ref<any>({
    platform: 'platform_a',
    version: '',
    install_type: 'main',
    download_url: '',
    target_machine: '',
  });
  const installing = ref(false);
  const rpaResult = ref('');

  // 版本下拉框（支持输入）：选项从 MinIO 对应 bucket 动态获取
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

  // 首次进入下拉时若未加载则拉取，避免每次展开都请求
  function onVersionDropdown(open: boolean) {
    if (open && versionOptions.value.length === 0) loadVersions();
  }

  // 切换平台时清空已选版本并重新拉取
  watch(
    () => rpa.value.platform,
    () => {
      rpa.value.version = '';
      versionOptions.value = [];
      loadVersions();
    },
  );

  const agent = ref<any>({ platform: 'platform_a', shop: '', agent: '' });
  const onlining = ref(false);
  const agentResult = ref('');

  // agent 上线：店铺/agent 下拉选项，来自 rpa_settings 的 console 配置（/plan/options）
  const planOptions = ref<any>({});

  const agentShopList = computed(() =>
    Object.keys(planOptions.value[agent.value.platform] || {}),
  );
  const agentAgentList = computed(() => {
    const shops = planOptions.value[agent.value.platform] || {};
    const shop = agent.value.shop;
    // 选中店铺有对应 agents 则返回之；否则汇总该平台所有 agents 作为候选
    if (shop && shops[shop]) return shops[shop];
    return [...new Set(Object.values(shops).flat())] as string[];
  });

  function onAgentShopChange() {
    // 切店铺后，若当前 agent 不在新店铺候选里则清空，便于重选
    if (agent.value.agent && !agentAgentList.value.includes(agent.value.agent)) {
      agent.value.agent = '';
    }
  }

  async function loadAgentOptions() {
    try {
      const { data } = await http.get('/plan/options');
      // 后端返回 {options, env}；兼容旧结构（直接返回映射）
      planOptions.value = data.options ?? data ?? {};
    } catch (e) {
      // 拉取失败不阻断，仍可手填
      planOptions.value = {};
    }
  }

  // 切换平台时清空已选店铺/agent
  watch(
    () => agent.value.platform,
    () => {
      agent.value.shop = '';
      agent.value.agent = '';
    },
  );

  onMounted(() => {
    loadVersions();
    loadAgentOptions();
  });

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
</script>

<style scoped>
.hdr {
  display: flex;
  align-items: center;
  justify-content: space-between;
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
</style>
