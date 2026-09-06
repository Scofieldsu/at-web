<template>
  <div class="page">
    <a-card class="theme-card">
      <template #title><span class="sec-title tint-indigo"><RocketOutlined />提交测试任务</span></template>

      <!-- 顶部提示：与机器管理页一致，展示远程仓库（origin/main）最新提交与时间 -->
      <a-alert
        v-if="remoteVersion && remoteVersion.commit_hash"
        type="info"
        show-icon
        class="mb-3"
      >
        <template #message>
          <span class="strong">远程仓库（origin/main）最新版本：</span>
          <a-tag color="blue" class="ml-2">{{ remoteVersion.commit_hash }}</a-tag>
          <span class="text-muted ml-2">{{ remoteVersion.commit_date }}</span>
        </template>
      </a-alert>

      <a-form :label-col="{ span: 4 }" :wrapper-col="{ span: 18 }">
        <!-- 执行机器 -->
        <a-form-item label="执行机器" required>
          <a-radio-group v-model:value="form.targetMachine">
            <a-space direction="vertical" style="width: 100%">
              <a-radio
                v-for="m in machines"
                :key="m.id"
                :value="m.ip"
                :disabled="!m.idle"
              >
                <div
                  class="machine-card"
                  :class="{
                    'machine-card-checked': form.targetMachine === m.ip,
                    'machine-card-off': !m.idle,
                  }"
                >
                  <!-- 头部：机器名 / IP / 状态（右对齐） -->
                  <div class="mc-row">
                    <span
                      class="mc-name"
                      :class="{ 'machine-outdated': versionOutdated(m) }"
                    >
                      {{ m.hostname }}
                    </span>
                    <span class="mc-ip">{{ m.ip }}:{{ m.port }}</span>
                    <span class="mc-status">
                      <a-tag v-if="m.current_task" color="warning">运行中</a-tag>
                      <a-tag v-else-if="!m.available" color="default">离线</a-tag>
                      <a-tag v-else color="success">空闲</a-tag>
                    </span>
                  </div>
                  <!-- 元信息：版本（落后远程标黄）+ 备注（红色） -->
                  <div class="mc-sub">
                    <span
                      class="mc-version"
                      :class="{ 'machine-outdated': versionOutdated(m) }"
                    >
                      版本 {{ machineVersion(m) }}
                    </span>
                    <span v-if="m.label" class="mc-remark">备注：{{ m.label }}</span>
                  </div>
                  <!-- 负载：仅选中时展示，便于对比挑选空闲机器 -->
                  <div v-if="form.targetMachine === m.ip" class="mc-res">
                    <span class="mc-meter">
                      <span class="mc-meter-label">CPU</span>
                      <a-progress
                        class="mc-meter-bar"
                        :percent="clampPercent(m.cpu_percent)"
                        size="small"
                        :show-info="false"
                        :stroke-color="loadColor(m.cpu_percent)"
                      />
                      <span
                        class="mc-meter-pct"
                        :style="{ color: loadColor(m.cpu_percent) }"
                      >
                        {{ m.cpu_percent }}%
                      </span>
                    </span>
                    <span class="mc-meter">
                      <span class="mc-meter-label">内存</span>
                      <a-progress
                        class="mc-meter-bar"
                        :percent="clampPercent(m.memory_percent)"
                        size="small"
                        :show-info="false"
                        :stroke-color="loadColor(m.memory_percent)"
                      />
                      <span
                        class="mc-meter-pct"
                        :style="{ color: loadColor(m.memory_percent) }"
                      >
                        {{ m.memory_percent }}%
                      </span>
                    </span>
                  </div>
                </div>
              </a-radio>
            </a-space>
          </a-radio-group>
        </a-form-item>

        <!-- 测试平台 -->
        <a-form-item label="测试平台" required>
          <a-select v-model:value="form.platform" @change="onPlatformChange">
            <a-select-option value="platform_a">平台A</a-select-option>
            <a-select-option value="platform_b">平台B</a-select-option>
            <a-select-option value="platform_d">平台D</a-select-option>
            <a-select-option value="platform_c">平台C</a-select-option>
          </a-select>
        </a-form-item>

        <!-- 测试用例 -->
        <a-form-item label="测试用例" required>
          <div class="mb-2">
            <a-button size="small" :loading="loadingCases" @click="loadCases">
              刷新用例列表
            </a-button>
            <span class="ml-2 hint">已选择 {{ form.cases.length }} 个用例</span>
          </div>
          <a-tree
            v-if="caseTree.length"
            checkable
            :tree-data="caseTree"
            :checked-keys="form.cases"
            :field-names="{ title: 'name', key: 'path', children: 'children' }"
            @check="handleCaseCheck"
          />
          <a-empty v-else description="暂无用例" />
        </a-form-item>

        <!-- 测试计划：选择平台后自动带出对应参数，可修改后仅本次任务生效 -->
        <a-divider>测试计划参数 {{ platformName(form.platform) }}</a-divider>
        <div class="plan-hint">
          已按「测试参数」的{{ envLabel }}默认值带出，可修改（仅对本次任务生效）
        </div>

        <a-form-item label="RPA 版本">
          <a-auto-complete
            v-model:value="form.plan.version"
            :options="versionOptions"
            :filter-option="false"
            placeholder="选择或输入版本，留空使用 latest"
            @dropdown-visible-change="onVersionDropdown"
          >
            <template #notFoundContent>
              <span v-if="versionsLoading">版本加载中...</span>
              <span v-else>无可用版本，可直接输入</span>
            </template>
          </a-auto-complete>
        </a-form-item>

        <a-form-item label="店铺">
          <a-select
            v-model:value="form.plan.shop"
            show-search
            allow-clear
            placeholder="选择店铺，可留空"
            :options="shopOptions"
            @change="clearAgentIfInvalid"
          />
        </a-form-item>

        <a-form-item label="Agent">
          <a-select
            v-model:value="form.plan.agent"
            show-search
            allow-clear
            placeholder="选择客服 Agent，可留空"
            :options="agentOptions"
          />
        </a-form-item>

        <!-- 高级选项 -->
        <a-divider>高级选项</a-divider>

        <a-form-item label="执行选项">
          <a-space direction="vertical">
            <a-checkbox v-model:checked="form.skipInstall">
              跳过 RPA 安装（RPA_SKIP_INSTALL=1）
            </a-checkbox>
            <a-checkbox v-model:checked="form.keepAlive">
              保持 RPA 运行（RPA_KEEP_ALIVE=1）
            </a-checkbox>
          </a-space>
        </a-form-item>

        <a-form-item label="任务名称">
          <a-input
            v-model:value="form.name"
            placeholder="留空自动生成（平台-日期）"
          />
        </a-form-item>

        <!-- 提交 -->
        <a-form-item :wrapper-col="{ offset: 4 }">
          <a-space>
            <a-button type="primary" :loading="submitting" size="large" @click="handleSubmit">
              提交任务
            </a-button>
            <a-button @click="resetForm">重置</a-button>
          </a-space>
        </a-form-item>
      </a-form>
    </a-card>
  </div>
</template>

<script lang="ts" setup>
  defineOptions({ name: 'DistributedSubmit' });
  import { ref, reactive, computed, onMounted } from 'vue';
  import { RocketOutlined } from '@ant-design/icons-vue';
  import { useRouter, useRoute } from 'vue-router';
  import { message } from 'ant-design-vue';
  import { getMachinesList, submitTask } from '@/api/platform/distributed';
  import type { Machine, RemoteVersion, TestPlan } from '@/api/platform/distributed';
  import http from '@/api/platform/http';

  const router = useRouter();
  const route = useRoute();

  const machines = ref<Machine[]>([]);
  const caseTree = ref<any[]>([]);
  // 远程仓库（origin/main）最新版本：顶部提示展示，同时作为机器版本比对基准
  const remoteVersion = ref<RemoteVersion | null>(null);
  // ── 测试计划参数：随平台自动带出，可修改 ──
  // /plan/ 各平台已保存的参数（版本/店铺/agent），及当前环境
  const platformPlans = ref<Record<string, any>>({});
  const planEnv = ref('');
  // /plan/options：各平台「店铺 -> agent 列表」候选
  const planOptions = ref<Record<string, Record<string, string[]>>>({});
  const versionOptions = ref<{ value: string }[]>([]);
  const versionsLoading = ref(false);

  const envLabel = computed(() => {
    if (planEnv.value === 'dev') return '开发环境';
    if (planEnv.value === 'prod') return '生产环境';
    return planEnv.value || '当前';
  });
  const shopOptions = computed(() =>
    Object.keys(planOptions.value[form.platform] || {}).map((s) => ({
      label: s,
      value: s,
    })),
  );
  // Agent 候选：优先当前店铺下配置的 agent，无则汇总该平台全部 agent
  const agentOptions = computed(() => {
    const shops = planOptions.value[form.platform] || {};
    const list = form.plan.shop && shops[form.plan.shop]
      ? shops[form.plan.shop]
      : [...new Set(Object.values(shops).flat())];
    return list.map((a) => ({ label: a, value: a }));
  });
  // 当前平台下真实存在的用例文件路径，用于过滤 a-tree 勾选结果里的分组节点 key
  const caseFiles = ref<Set<string>>(new Set());
  const loadingCases = ref(false);
  const submitting = ref(false);

  const form = reactive<{
    targetMachine: string;
    platform: string;
    cases: string[];
    plan: TestPlan;
    skipInstall: boolean;
    keepAlive: boolean;
    name: string;
  }>({
    targetMachine: '',
    platform: 'platform_a',
    cases: [],
    plan: { version: '', shop: '', agent: '' },
    skipInstall: false,
    keepAlive: false,
    name: '',
  });

  async function loadMachines() {
    try {
      const res = await getMachinesList();
      machines.value = res.data.data || [];
      remoteVersion.value = res.data.summary?.remote_version || null;

      // URL 参数预选
      const paramMachine = route.query.machine as string;
      if (paramMachine) {
        const target = machines.value.find((m) => m.ip === paramMachine && m.idle);
        if (target) form.targetMachine = target.ip;
      }

      // 未预选则自动选第一台空闲
      if (!form.targetMachine) {
        const idle = machines.value.find((m) => m.idle);
        if (idle) form.targetMachine = idle.ip;
      }
    } catch (e: any) {
      message.error('加载机器列表失败');
    }
  }

  async function loadCases() {
    loadingCases.value = true;
    try {
      const res = await http.get('/cases/', {
        params: { directory: 'cases', marks: form.platform },
      });

      const cases = res.data || [];
      const tree: any[] = [];
      const platformMap: Record<string, any> = {};
      const files = new Set<string>();

      cases.forEach((c: any) => {
        const platform = c.platform || 'other';
        if (!platformMap[platform]) {
          platformMap[platform] = {
            name: platformName(platform),
            path: platform,
            children: [],
            selectable: false,
          };
          tree.push(platformMap[platform]);
        }
        platformMap[platform].children.push({ name: c.name, path: c.file });
        files.add(c.file);
      });

      caseTree.value = tree;
      caseFiles.value = files;
      // 切换平台后原有勾选可能已不在新列表里，丢掉避免提交幽灵路径
      form.cases = form.cases.filter((f) => files.has(f));
    } catch (e: any) {
      message.error('加载用例列表失败');
    } finally {
      loadingCases.value = false;
    }
  }

  function platformName(p: string) {
    return (
      { platform_a: '平台A', platform_b: '平台B', platform_d: '平台D', platform_c: '平台C' }[p] ||
      p
    );
  }

  // 机器当前版本展示：优先 version（{hash}-{date}），缺失时退回 git commit
  function machineVersion(m: Machine): string {
    if (m.version && m.version !== 'unknown') return m.version;
    if (m.git_info?.commit_hash) return m.git_info.commit_hash;
    return '未知';
  }

  // 与远程 origin/main 比对：commit hash 不一致即视为版本落后（标黄提醒）。
  // 远程或本地拿不到时不做判定，避免误报一片黄。
  function versionOutdated(m: Machine): boolean {
    const remoteHash = remoteVersion.value?.commit_hash;
    const localHash = m.git_info?.commit_hash;
    return (
      !!remoteHash &&
      remoteHash !== 'unknown' &&
      !!localHash &&
      localHash !== remoteHash
    );
  }

  // 进度条 percent 兜底（旧版 agent 可能缺字段）
  function clampPercent(v: number | undefined): number {
    return Math.max(0, Math.min(100, Math.round(v ?? 0)));
  }

  // 负载阈值颜色，与机器管理页一致：<60 正常、60~79 偏高、>=80 过高
  function loadColor(percent: number | undefined): string {
    const p = percent ?? 0;
    if (p < 60) return 'var(--success-color)';
    if (p < 80) return 'var(--warning-color)';
    return 'var(--error-color)';
  }

  // ── 测试计划参数联动 ────────────────────────────────────
  // 平台切换/初始化时，把 /plan/ 里该平台已保存的 版本/店铺/agent 带出到表单
  function applyPlatformPlan() {
    const saved = platformPlans.value[form.platform] || {};
    form.plan = {
      version: saved.version || '',
      shop: saved.shop || '',
      agent: saved.agent || '',
    };
    // 版本候选按平台重新懒加载
    versionOptions.value = [];
    clearAgentIfInvalid();
  }

  // 店铺变化后若当前 agent 不在新店铺候选里则清空，便于重选；选项缺失时不清理
  function clearAgentIfInvalid() {
    const shops = planOptions.value[form.platform];
    if (!shops || !Object.keys(shops).length) return;
    const agents =
      form.plan.shop && shops[form.plan.shop]
        ? shops[form.plan.shop]
        : [...new Set(Object.values(shops).flat())];
    if (form.plan.agent && !agents.includes(form.plan.agent)) form.plan.agent = '';
  }

  // 拉取 /plan/ 已保存参数与 /plan/options 候选，完成后带出当前平台默认值
  async function loadPlanDefaults() {
    try {
      const { data } = await http.get('/plan/');
      platformPlans.value = data.plan || {};
      planEnv.value = data.env || '';
    } catch (e) {
      platformPlans.value = {};
    }
    try {
      const { data } = await http.get('/plan/options');
      // 后端返回 {options, env}；兼容旧结构（直接返回映射）
      planOptions.value = data.options ?? data ?? {};
    } catch (e) {
      planOptions.value = {};
    }
    applyPlatformPlan();
  }

  async function onVersionDropdown(open: boolean) {
    if (open && !versionOptions.value.length) await loadVersions();
  }

  async function loadVersions() {
    versionsLoading.value = true;
    try {
      const { data } = await http.get('/env/versions', {
        params: { platform: form.platform },
      });
      versionOptions.value = (data.versions || []).map((v: string) => ({
        value: v,
      }));
    } catch (e) {
      // 拉取失败不阻断，仍可手填
      versionOptions.value = [];
    } finally {
      versionsLoading.value = false;
    }
  }

  // 平台切换：带出该平台的计划参数，并重新加载用例
  function onPlatformChange() {
    applyPlatformPlan();
    loadCases();
  }

  function handleCaseCheck(checkedKeys: any) {
    const keys: string[] = checkedKeys.checked || checkedKeys;
    // 只保留真实用例文件：checkStrictly=false 时 rc-tree 会在某平台下全部子节点
    // 被勾选后把「平台分组节点」的 key（如 platform_a）也放进 checkedKeys，
    // 它不是文件路径，提交给 pytest 会直接报「找不到用例」。
    form.cases = keys.filter((k) => caseFiles.value.has(k));
  }

  async function handleSubmit() {
    if (!form.targetMachine) {
      message.error('请选择执行机器');
      return;
    }
    if (!form.cases.length) {
      message.error('请选择测试用例');
      return;
    }

    submitting.value = true;
    try {
      const res = await submitTask({
        target_machine: form.targetMachine,
        platform: form.platform,
        cases: form.cases,
        plan: form.plan,
        skip_install: form.skipInstall,
        keep_alive: form.keepAlive,
        name: form.name || `${form.platform} 测试`,
      });

      if (res.data.success && res.data.task_id) {
        message.success('任务已提交');
        router.push(`/test/monitor/${res.data.task_id}`);
      } else {
        message.error(res.data.error || '提交失败');
      }
    } catch (e: any) {
      const err = e?.response?.data?.error || e.message;
      message.error(`提交失败：${err}`);
    } finally {
      submitting.value = false;
    }
  }

  function resetForm() {
    form.cases = [];
    form.skipInstall = false;
    form.keepAlive = false;
    form.name = '';
    // 参数回到当前平台默认（已保存的计划值或留空）
    applyPlatformPlan();
  }

  onMounted(() => {
    loadMachines();
    loadCases();
    loadPlanDefaults();
  });
</script>

<style lang="less" scoped>
  .page {
    padding: 16px;
  }

  .theme-card {
    max-width: 960px;
  }

  .machine-card {
    border: 1px solid var(--border-color);
    border-radius: 6px;
    padding: 8px 12px;
    transition:
      border-color 0.2s,
      background-color 0.2s;
  }

  /* 选中卡片：accent 描边 + 浅色底，与系统主题色一致 */
  .machine-card-checked {
    border-color: var(--accent);
    background: var(--accent-bg);
  }

  /* 忙碌/离线机器弱化，避免干扰选择 */
  .machine-card-off {
    opacity: 0.55;
  }

  .mc-row {
    display: flex;
    gap: 8px;
    align-items: center;
  }

  .mc-name {
    font-weight: 500;
  }

  .mc-ip {
    font-size: var(--vben-font-size-sm);
    color: var(--text-secondary);
  }

  .mc-status {
    margin-left: auto;
    display: inline-flex;
  }

  .mc-sub {
    display: flex;
    flex-wrap: wrap;
    gap: 2px 16px;
    align-items: center;
    margin-top: 3px;
    font-size: var(--vben-font-size-sm);
  }

  .mc-version {
    color: var(--text-secondary);
  }

  /* 备注：红色字体 */
  .mc-remark {
    color: var(--error-color);
  }

  /* 版本与远程仓库不一致的机器：黄色字体 */
  .machine-outdated {
    color: var(--warning-color);
    font-weight: 600;
  }

  /* 选中机器才展示的负载概览 */
  .mc-res {
    display: flex;
    flex-wrap: wrap;
    gap: 8px 24px;
    align-items: center;
    margin-top: 6px;
    padding-top: 6px;
    border-top: 1px dashed var(--border-color);
    font-size: var(--vben-font-size-sm);
  }

  .mc-meter {
    display: flex;
    align-items: center;
    gap: 8px;
    width: 210px;
  }

  .mc-meter-label {
    width: 34px;
    flex-shrink: 0;
    color: var(--text-secondary);
  }

  .mc-meter-bar {
    flex: 1;
    min-width: 80px;
    margin: 0;
  }

  .mc-meter-pct {
    width: 44px;
    text-align: right;
    font-weight: 500;
  }

  .hint {
    font-size: var(--vben-font-size-sm);
    color: var(--text-secondary);
  }

  /* 测试计划参数区提示：说明默认值来源与生效范围 */
  .plan-hint {
    margin-bottom: 8px;
    font-size: var(--vben-font-size-sm);
    color: var(--text-secondary);
  }

  .strong {
    font-weight: 500;
  }

  .text-muted {
    color: var(--text-secondary);
  }

  .mb-2 {
    margin-bottom: 8px;
  }

  .mb-3 {
    margin-bottom: 12px;
  }

  .ml-2 {
    margin-left: 8px;
  }
</style>
