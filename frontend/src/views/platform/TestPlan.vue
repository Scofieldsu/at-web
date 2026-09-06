<template>
  <a-card class="theme-card">
    <template #title>
      <div class="hdr">
        <div>
          <span class="sec-title tint-blue"><SlidersOutlined />测试参数 — 各平台执行参数</span>
          <a-tag v-if="currentEnv" :color="currentEnv === 'dev' ? 'blue' : 'orange'" style="margin-left: 8px">
            {{ currentEnv === 'dev' ? '开发环境' : '生产环境' }}
          </a-tag>
        </div>
        <div>
          <a-button :loading="loading" size="small" @click="load">重新加载</a-button>
          <a-button type="primary" size="small" :loading="saving" @click="save">保存计划</a-button>
        </div>
      </div>
    </template>

    <!-- 顶部提示：与「消息注入」页目标连接提示一致（蓝感叹号 + 12px 字号） -->
    <div class="conn-tip">
      <div class="conn-tip-line">
        <ExclamationCircleOutlined class="conn-tip-icon" />
        <span class="conn-tip-body">
          此处填写 4 个平台的执行参数。执行用例时，按勾选的平台读取对应参数注入用例（覆盖用例默认值，留空则用用例自带默认）。
        </span>
      </div>
    </div>

    <!-- 4 平台参数：2×2 平铺展示，不再用 tab 切换 -->
    <div class="plan-grid">
      <a-card v-for="p in PLATFORMS" :key="p.value" class="theme-card plan-cell">
        <template #title>
          <span class="sec-title" :class="p.tint">
            <span class="pf-mark" :class="p.mark">{{ p.markChar }}</span>
            {{ p.label }} · 执行参数
          </span>
        </template>
        <a-form layout="horizontal" :label-col="{ style: { width: '96px' } }">
          <a-form-item label="版本">
            <a-auto-complete
              v-model:value="plan[p.value].version"
              :options="versionOptions[p.value] || []"
              :filter-option="false"
              placeholder="选择或输入版本，如 2.0.1.2，留空用用例默认"
              @dropdownVisibleChange="(open) => onVersionDropdown(p.value, open)"
            >
              <template #notFoundContent>
                <span v-if="versionsLoading[p.value]">加载中...</span>
                <span v-else>无可用版本，可直接输入</span>
              </template>
            </a-auto-complete>
          </a-form-item>
          <a-form-item label="安装类型">
            <a-select v-model:value="plan[p.value].install_type">
              <a-select-option value="main">main</a-select-option>
              <a-select-option value="full">full</a-select-option>
            </a-select>
          </a-form-item>
          <a-form-item label="下载地址">
            <a-input v-model:value="plan[p.value].download_url" placeholder="可选，留空则按平台及版本下载" />
          </a-form-item>
          <a-form-item label="目标机器">
            <a-input v-model:value="plan[p.value].target_machine" placeholder="可选，留空为本机" />
          </a-form-item>
          <a-form-item label="店铺">
            <a-select
              v-model:value="plan[p.value].shop"
              show-search
              allow-clear
              placeholder="选择或输入店铺"
              :options="shopList(p.value).map((s) => ({ label: s, value: s }))"
              @change="onShopChange(p.value)"
            />
          </a-form-item>
          <a-form-item label="Agent">
            <a-select
              v-model:value="plan[p.value].agent"
              show-search
              allow-clear
              placeholder="选择或输入 agent"
              :options="agentList(p.value).map((a) => ({ label: a, value: a }))"
            />
          </a-form-item>
        </a-form>
      </a-card>
    </div>
  </a-card>
</template>

<script lang="ts" setup>
  defineOptions({ name: 'TestPlan' });
  import { ref, reactive, onMounted } from 'vue';
  import { SlidersOutlined, ExclamationCircleOutlined } from '@ant-design/icons-vue';
  import { message } from 'ant-design-vue';
  import http from '@/api/platform/http';

  const PLATFORMS = [
    { value: 'platform_a', label: '平台A', tint: 'tint-red', mark: 'pf-jd', markChar: '京' },
    { value: 'platform_b', label: '平台B', tint: 'tint-blue', mark: 'pf-qn', markChar: '千' },
    { value: 'platform_c', label: '平台C', tint: 'tint-orange', mark: 'pf-pdd', markChar: '拼' },
    { value: 'platform_d', label: '平台D', tint: 'tint-green', mark: 'pf-dy', markChar: '抖' },
  ];

  const loading = ref(false);
  const saving = ref(false);
  const currentEnv = ref('');

  // 各平台参数（用 reactive，模板里按 plan[平台] 访问）
  const empty = () => ({
    version: '',
    install_type: 'main',
    download_url: '',
    target_machine: '',
    shop: '',
    agent: '',
  });
  const plan = reactive<any>({
    platform_a: empty(),
    platform_b: empty(),
    platform_c: empty(),
    platform_d: empty(),
  });

  // 版本下拉框（支持输入）：各平台选项从 MinIO 对应 bucket 动态获取
  const versionOptions = reactive<Record<string, { value: string }[]>>({});
  const versionsLoading = reactive<Record<string, boolean>>({});

  async function loadVersions(platform: string) {
    if (!platform) return;
    versionsLoading[platform] = true;
    try {
      const { data } = await http.get('/env/versions', { params: { platform } });
      const versions: string[] = data.versions || [];
      versionOptions[platform] = versions.map((v) => ({ value: v }));
    } catch (e) {
      // 拉取失败不阻断，仍可手填
      versionOptions[platform] = [];
    } finally {
      versionsLoading[platform] = false;
    }
  }

  // 首次展开某平台版本下拉时按需拉取，避免重复请求
  function onVersionDropdown(platform: string, open: boolean) {
    if (open && !versionOptions[platform]) loadVersions(platform);
  }

  // settings 里各平台的店铺→agents 选项
  const options = ref<any>({});

  function shopList(platform: string) {
    return Object.keys(options.value[platform] || {});
  }
  function agentList(platform: string) {
    const shop = plan[platform].shop;
    const shops = options.value[platform] || {};
    // 选中的店铺有对应 agents 则返回之；否则汇总该平台所有 agents 作为候选
    if (shop && shops[shop]) return shops[shop];
    return [...new Set(Object.values(shops).flat())];
  }
  function onShopChange(platform: string) {
    // 切店铺后，若当前 agent 不在新店铺候选里则清空，便于重选
    const agents = agentList(platform);
    if (plan[platform].agent && !agents.includes(plan[platform].agent)) {
      plan[platform].agent = '';
    }
  }

  async function loadOptions() {
    try {
      const { data } = await http.get('/plan/options');
      // 后端返回 {options, env}；兼容旧结构（直接返回映射）
      options.value = data.options ?? data ?? {};
      if (data.env) currentEnv.value = data.env;
    } catch (e) {
      // 选项拉取失败不阻断，仍可手填
      options.value = {};
    }
  }

  async function load() {
    loading.value = true;
    try {
      const { data } = await http.get('/plan/');
      const p = data.plan || {};
      for (const { value } of PLATFORMS) {
        Object.assign(plan[value], empty(), p[value] || {});
      }
      if (data.env) currentEnv.value = data.env;
    } catch (e) {
      message.error('读取测试计划失败');
    } finally {
      loading.value = false;
    }
  }

  async function save() {
    saving.value = true;
    try {
      const payload: any = {};
      for (const { value } of PLATFORMS) payload[value] = { ...plan[value] };
      const { data } = await http.put('/plan/', { plan: payload });
      if (data.success) {
        message.success(data.env ? `已保存 ${data.env} 环境测试计划` : '测试计划已保存');
      } else {
        message.error(data.error || '保存失败');
      }
    } catch (e: any) {
      message.error(e.response?.data?.error || '保存失败');
    } finally {
      saving.value = false;
    }
  }

  onMounted(async () => {
    await loadOptions();
    await load();
  });
</script>

<style scoped>
.hdr {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
/* 顶部提示：与消息注入页 conn-tip 同款（蓝感叹号、12px 字号） */
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
/* 4 平台参数：2×2 平铺 */
.plan-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}
.plan-cell {
  min-width: 0;
}
/* 表单控件宽度适中 */
.plan-cell :deep(.ant-form-item-control-input-content) {
  max-width: 360px;
}
/* 平台 logo 徽章：圆角色块 + 单字 */
.pf-mark {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 600;
  color: #fff;
  flex-shrink: 0;
}
.pf-jd { background: #e5484d; }
.pf-qn { background: #0090ff; }
.pf-pdd { background: #f76b15; }
.pf-dy { background: #30a46c; }
</style>
