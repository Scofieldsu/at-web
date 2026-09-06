<template>
  <div class="page">
    <!-- 步骤 ① 执行位置 + 测试任务名称 + ④ 执行选中 -->
    <a-card class="theme-card">
      <div class="toolbar">
        <span class="sec-title tint-blue"><FormOutlined />① 任务信息</span>
        <a-input
          v-model:value="taskName"
          placeholder="可选，留空自动按平台-版本-日期生成"
          style="width: 260px"
        />

        <a-divider type="vertical" />

        <!-- 执行位置：本机 / 远程机器（统一执行入口） -->
        <a-radio-group v-model:value="runScope">
          <a-radio value="local">本机</a-radio>
          <a-radio value="remote">远程机器</a-radio>
        </a-radio-group>
        <a-select
          v-if="runScope === 'remote'"
          v-model:value="targetMachine"
          placeholder="选择空闲的执行机器"
          style="width: 240px"
        >
          <a-select-option
            v-for="m in machines"
            :key="m.ip"
            :value="m.ip"
            :disabled="!m.idle"
          >
            {{ m.label || m.hostname }} - {{ m.ip }} - {{ m.current_task ? '运行中' : m.available ? '空闲' : '离线' }}
          </a-select-option>
        </a-select>

        <a-divider type="vertical" />

        <a-button
          type="primary"
          :loading="running"
          :disabled="!checkedCases.length || (runScope === 'remote' && !targetMachine)"
          @click="run"
        >
          ④ 执行选中（{{ checkedCases.length }} 用例 / {{ platformLabel(selPlatform) }}）
        </a-button>
        <span class="hint">
          {{ runScope === 'local'
            ? '本机：勾选用例后自动按其所属平台分组执行，并应用对应测试计划参数。'
            : `远程：按平台逐个下发到 ${machineLabel(targetMachine)} 执行，子场景级过滤仅本机生效。` }}
        </span>
      </div>

      <!-- 当前平台的测试计划参数预览（选择平台后自动带出，带主题色） -->
      <div v-if="selPlatform" class="plan-preview">
        <div class="plan-row">
          <span class="plan-platform">{{ platformLabel(selPlatform) }}</span>
          <template v-if="planChips.length">
            <span
              v-for="c in planChips"
              :key="c.key"
              class="plan-chip"
              :class="c.cls"
              :title="`${c.label}：${c.value}`"
            >
              {{ c.label }}：{{ c.value }}
            </span>
          </template>
          <span v-else class="plan-params">未配置测试计划参数（将用用例默认参数）</span>
        </div>
      </div>
    </a-card>

    <!-- 步骤 ② 过滤栏 -->
    <a-card class="theme-card filter-card">
      <template #title><span class="sec-title tint-blue"><FilterOutlined />② 筛选条件</span></template>
      <div class="filter-bar">
        <!-- 平台过滤（单选，切换后只展示该平台用例并带出测试参数） -->
        <div class="filter-group">
          <span class="filter-label">平台</span>
          <a-select v-model:value="selPlatform" style="width: 160px" @change="onPlatformChange">
            <a-select-option v-for="p in PLATFORMS" :key="p.value" :value="p.value">
              {{ p.label }}
            </a-select-option>
          </a-select>
        </div>

        <!-- Mark 过滤 -->
        <div class="filter-group">
          <span class="filter-label">Mark</span>
          <a-checkbox-group v-model:value="filterMarks" @change="onFilterChange" class="mark-checkbox-group">
            <a-checkbox
              v-for="m in displayMarks"
              :key="m.mark"
              :value="m.mark"
            >
              {{ m.mark }}<span v-if="m.desc" class="mark-desc">（{{ m.desc }}）</span>
            </a-checkbox>
          </a-checkbox-group>
        </div>

        <!-- 策略切换 + 批量操作 -->
        <div class="filter-actions">
          <a-radio-group v-model:value="filterMode" size="small" @change="onFilterChange">
            <a-radio-button value="AND" class="radio-and">交集(AND)</a-radio-button>
            <a-radio-button value="OR" class="radio-or">并集(OR)</a-radio-button>
          </a-radio-group>

          <span class="hit-count">命中 <strong>{{ filteredCases.length }}</strong> 个用例</span>

          <a-button size="small" type="primary" @click="checkAllFiltered">全部勾选</a-button>
          <a-button size="small" @click="uncheckAllFiltered">全部取消</a-button>
        </div>
      </div>
    </a-card>

    <!-- 步骤 ③ 选择用例 -->
    <a-card class="theme-card grow">
      <template #title>
        <div class="hdr">
          <span class="sec-title tint-blue"><AppstoreOutlined />③ 选择用例</span>
          <a-button :loading="loadingCases" size="small" @click="reload"> 刷新 </a-button>
        </div>
      </template>

      <a-tree
        v-if="treeData.length"
        :tree-data="treeData"
        checkable
        v-model:checked-keys="checkedKeys"
        v-model:expanded-keys="expandedKeys"
        :field-names="{ title: 'label', key: 'id', children: 'children' }"
        class="case-tree"
        @check="onCheck"
        @expand="onExpand"
      >
        <template #title="node">
          <span class="tree-node" :class="node.type">
            <span class="node-label">{{ node.label }}</span>
            <a-tag
              v-if="node.type === 'platform' && !node.children?.length"
              color="default"
            >
              暂无用例
            </a-tag>
            <template v-if="node.type === 'case'">
              <a-tag
                v-for="m in (node.marks || [])"
                :key="m"
                color="blue"
                size="small"
                class="mark-tag"
              >{{ m }}</a-tag>
              <span v-if="node.doc" class="node-doc" :title="node.doc">
                {{ firstLine(node.doc) }}
              </span>
              <a-button v-if="!node.scenariosLoaded" size="small" type="link" @click.stop="loadScenarios(node)">
                展开子场景
              </a-button>
            </template>
            <template v-if="node.type === 'scenario'">
              <a-tag color="green" size="small">子场景</a-tag>
            </template>
          </span>
        </template>
      </a-tree>
      <div v-else class="muted pad">点「刷新」扫描 tests 目录</div>
    </a-card>

    <!-- 已选汇总 -->
    <a-card v-if="checkedCases.length" class="theme-card grow-fill">
      <template #title>
        <div class="hdr">
          <span class="sec-title tint-blue"><CheckSquareOutlined />已选用例（{{ checkedCases.length }}）</span>
          <a-button size="small" @click="clearChecked">清空</a-button>
        </div>
      </template>
      <a-table
        :data-source="checkedCases"
        :columns="summaryColumns"
        :pagination="false"
        row-key="path"
        bordered
        class="theme-table"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'marks'">
            <a-tag
              v-for="m in (record.marks || [])"
              :key="m"
              color="blue"
              size="small"
            >{{ m }}</a-tag>
          </template>
          <template v-else-if="column.key === 'doc'">
            <span v-if="record.doc" class="doc">{{ record.doc }}</span>
            <span v-else class="muted">（无注释）</span>
          </template>
        </template>
      </a-table>
    </a-card>
  </div>
</template>

<script lang="ts" setup>
  defineOptions({ name: 'Cases' });
  import { ref, computed, onMounted } from 'vue';
  import { useRoute, useRouter } from 'vue-router';
  import { message } from 'ant-design-vue';
  import { FilterOutlined, CheckSquareOutlined, AppstoreOutlined, FormOutlined } from '@ant-design/icons-vue';
  import http from '@/api/platform/http';
  import { getMachinesList, submitTask } from '@/api/platform/distributed';
  import type { Machine } from '@/api/platform/distributed';

  const router = useRouter();
  const route = useRoute();

  const PLATFORMS = [
    { value: 'platform_a', label: '平台A' },
    { value: 'platform_b', label: '平台B' },
    { value: 'platform_c', label: '平台C' },
    { value: 'platform_d', label: '平台D' },
  ];

  // ── 数据源 ──────────────────────────────────────────
  const allCases = ref<any[]>([]);          // 全部用例
  const modules = ref<any[]>([]);           // 模块
  const availableMarks = ref<any[]>([]);    // 可用 mark 列表（含描述+计数）
  const loadingCases = ref(false);
  const loadingModules = ref(false);

  // ── 子场景缓存 ────────────────────────────────────
  // { [casePath]: { scenarios: [{param_id, nodeid}], loaded: bool } }
  const scenariosCache = ref<Record<string, any>>({});
  const loadingScenarios = ref<Record<string, boolean>>({});
  // 按 mark 过滤时，缓存匹配的文件列表
  const markedFiles = ref<Record<string, string[]>>({});
  const loadingMarkedFiles = ref(false);

  // ── 勾选状态 ────────────────────────────────────────
  const checkedCases = ref<any[]>([]);      // 当前勾选的用例对象
  const checkedKeys = ref<any[]>([]);
  const expandedKeys = ref<any[]>([]);

  // ── 过滤状态 ────────────────────────────────────────
  // 平台单选：默认平台A，切换后用例树与测试参数只针对该平台
  const selPlatform = ref('platform_a');
  const filterMarks = ref<string[]>([]);
  const filterMode = ref<'AND' | 'OR'>('AND');

  // ── 执行状态 ────────────────────────────────────────
  const running = ref(false);
  const taskName = ref('');
  const plan = ref<any>({});

  // ── 执行位置：本机 / 远程机器（统一执行入口）──────────────
  const runScope = ref<'local' | 'remote'>('remote'); // 默认远程执行
  const machines = ref<Machine[]>([]);
  const targetMachine = ref('');

  const summaryColumns = [
    { title: '用例', dataIndex: 'name', key: 'name', width: 160 },
    { title: '所属模块', dataIndex: 'directory', key: 'directory', width: 160 },
    { title: 'Mark', key: 'marks', width: 200 },
    { title: '用例执行步骤（文件头部注释）', key: 'doc' },
  ];

  // 可展示的 mark 列表（排除平台 mark，平台已由独立过滤栏处理）
  const displayMarks = computed(() => {
    const platformValues = new Set(PLATFORMS.map((p) => p.value));
    return availableMarks.value.filter((m) => !platformValues.has(m.mark));
  });
  const filteredCases = computed(() => {
    // 未选平台且无 mark 时显示 0 个用例，避免初进页面误以为全部选中
    if (!selPlatform.value && filterMarks.value.length === 0) {
      return [];
    }

    let result = [...allCases.value];

    // 平台过滤（单选：只保留当前平台用例）
    if (selPlatform.value) {
      result = result.filter((c) => c.platform === selPlatform.value);
    }

    // Mark 过滤：先按类级别 mark 过滤，再结合子场景 mark
    if (filterMarks.value.length > 0) {
      // 收集所有已加载的 mark 文件列表
      const allMarkFiles = new Set<string>();
      for (const mark of filterMarks.value) {
        for (const fp of (markedFiles.value[mark] || [])) {
          allMarkFiles.add(fp);
        }
      }

      result = result.filter((c) => {
        const cMarks: string[] = c.marks || [];
        // 类级别 mark 匹配
        const classMatch = filterMode.value === 'AND'
          ? filterMarks.value.every((m) => cMarks.includes(m))
          : filterMarks.value.some((m) => cMarks.includes(m));
        if (classMatch) return true;
        // 类级别不匹配时，检查子场景级别的 mark（通过 markedFiles 判断）
        if (allMarkFiles.size > 0) {
          return allMarkFiles.has(c.path);
        }
        return false;
      });
    }

    return result;
  });

  // 过滤命中的用例 ID 集合（用于批量勾选）
  const filteredCaseIds = computed(() => {
    const ids = new Set<string>();
    for (const c of filteredCases.value) {
      ids.add(`case:${c.path}`);
    }
    return ids;
  });

  // ── 构建树（仅显示过滤命中的用例）─────────────────────
  const treeData = computed(() => {
    const byPlatform: any = {};
    for (const c of allCases.value) {
      const pf = c.platform || 'debug';
      (byPlatform[pf] = byPlatform[pf] || []).push(c);
    }

    const KNOWN = PLATFORMS.map((p) => p.value);
    // 平台单选：只构建当前平台的节点（含未注册平台的兜底名）
    const platformKeys = selPlatform.value
      ? [selPlatform.value].filter((p) => byPlatform[p])
      : [
          ...KNOWN.filter((p) => byPlatform[p]),
          ...Object.keys(byPlatform).filter((p) => !KNOWN.includes(p)),
        ];

    return platformKeys.map((pf) => {
      const childCases = (byPlatform[pf] || [])
        .filter((c: any) => filteredCaseIds.value.has(`case:${c.path}`))
        .map((c: any) => {
          const caseId = `case:${c.path}`;
          const cache = scenariosCache.value[caseId];
          const children: any[] = [];
          if (cache?.loaded && cache.scenarios?.length) {
            for (const s of cache.scenarios) {
              if (s.param_id) {
                children.push({
                  id: `scenario:${c.path}:${s.param_id}`,
                  label: s.param_id,
                  type: 'scenario',
                  casePath: c.path,
                  paramId: s.param_id,
                });
              }
            }
          }
          return {
            id: caseId,
            label: c.name,
            type: 'case',
            doc: c.doc,
            directory: c.directory,
            marks: c.marks,
            caseRef: c,
            scenariosLoaded: !!cache?.loaded,
            children: children.length ? children : undefined,
          };
        });
      return {
        id: `plat:${pf}`,
        label: pf,
        type: 'platform',
        children: childCases,
      };
    });
  });

  function platformLabel(value: any) {
    return PLATFORMS.find((p) => p.value === value)?.label || value;
  }

  function machineLabel(ip: string) {
    const m = machines.value.find((m) => m.ip === ip);
    return m?.label || m?.hostname || ip || '未选择';
  }

  // 测试参数展示字段与主题色（与系统语义色一致，半透明底不突兀）
  const PLAN_FIELDS: { key: string; label: string; cls: string }[] = [
    { key: 'version', label: '版本', cls: 'pp-version' },
    { key: 'install_type', label: '类型', cls: 'pp-install' },
    { key: 'shop', label: '店铺', cls: 'pp-shop' },
    { key: 'agent', label: 'Agent', cls: 'pp-agent' },
    { key: 'download_url', label: '下载地址', cls: 'pp-download' },
    { key: 'target_machine', label: '目标机', cls: 'pp-other' },
  ];
  // 当前平台已填写的参数（转成彩色 chips 展示）
  const planChips = computed(() => {
    const cfg = plan.value[selPlatform.value];
    if (!cfg) return [];
    const out: { key: string; label: string; value: string; cls: string }[] = [];
    for (const f of PLAN_FIELDS) {
      const v = cfg[f.key];
      if (v) out.push({ key: f.key, label: f.label, value: String(v), cls: f.cls });
    }
    return out;
  });

  function firstLine(doc: any) {
    if (!doc) return '';
    const line = doc.split('\n')[0].trim();
    return line.length > 40 ? line.slice(0, 40) + '…' : line;
  }

  // ── 子场景加载 ──────────────────────────────────────
  async function loadScenarios(node: any) {
    if (!node.caseRef?.path) return;
    const caseId = node.id;
    if (scenariosCache.value[caseId]?.loaded) return;
    loadingScenarios.value[caseId] = true;
    try {
      const { data } = await http.get('/cases/collect', {
        params: { case: node.caseRef.path },
      });
      if (data?.success && data.scenarios) {
        scenariosCache.value[caseId] = {
          scenarios: data.scenarios,
          loaded: true,
        };
        // 触发树重建
        node.scenariosLoaded = true;
      }
    } catch (e) {
      console.error('加载子场景失败', e);
    } finally {
      loadingScenarios.value[caseId] = false;
    }
  }

  function onExpand(expandedKeys: any[], info: any) {
    // 展开文件节点时自动加载子场景
    if (info?.expanded && info.node?.type === 'case') {
      loadScenarios(info.node);
    }
  }

  // ── 勾选变化 ────────────────────────────────────────
  function onCheck(_keys: any, info: any) {
    const nodes = info?.checkedNodes || [];
    // 收集勾选的用例文件
    checkedCases.value = nodes.filter((n: any) => n.type === 'case').map((n: any) => n.caseRef);
    // 收集勾选的子场景 param_id，按文件分组
    const scenarioMap: Record<string, string[]> = {};
    for (const n of nodes) {
      if (n.type === 'scenario' && n.casePath && n.paramId) {
        (scenarioMap[n.casePath] = scenarioMap[n.casePath] || []).push(n.paramId);
      }
    }
    // 缓存到 checkedCases 上，供执行时拼 -k 参数
    for (const c of checkedCases.value) {
      const ids = scenarioMap[c.path];
      c._selectedScenarios = ids?.length ? ids : undefined;
    }
  }

  function checkAllFiltered() {
    // 收集当前过滤命中的所有用例 ID
    const ids = filteredCases.value.map((c) => `case:${c.path}`);
    // 合并已有勾选（保留已勾但不在当前过滤中的用例）
    const existing = new Set(checkedKeys.value.filter((k: string) => !filteredCaseIds.value.has(k)));
    checkedKeys.value = [...existing, ...ids];
    // 刷新 checkedCases
    updateCheckedFromKeys();
  }

  function uncheckAllFiltered() {
    // 仅移除当前过滤命中的用例勾选，保留已勾但不在过滤中的
    const remaining = checkedKeys.value.filter((k: string) => !filteredCaseIds.value.has(k));
    checkedKeys.value = remaining;
    updateCheckedFromKeys();
  }

  function updateCheckedFromKeys() {
    // 从 checkedKeys 反查 caseRef
    const allNodes: any[] = [];
    for (const pf of Object.values(allCases.value)) {
      // allCases.value 是扁平的，直接匹配
    }
    // 改用 tree 遍历方式重建 checkedCases
    const pathToCase = new Map<string, any>();
    for (const c of allCases.value) {
      pathToCase.set(`case:${c.path}`, c);
    }
    checkedCases.value = checkedKeys.value
      .filter((k: string) => k.startsWith('case:'))
      .map((k: string) => pathToCase.get(k))
      .filter(Boolean);
  }

  function clearChecked() {
    checkedKeys.value = [];
    checkedCases.value = [];
  }

  function onFilterChange() {
    // 过滤条件变化时自动展开所有平台节点
    expandedKeys.value = treeData.value.map((n: any) => n.id);
    // 如果有 mark 过滤，异步加载包含该 mark 的文件列表
    if (filterMarks.value.length > 0) {
      fetchMarkedFiles();
    }
  }

  // 平台切换：只保留该平台的勾选并自动展开，避免跨平台残留选中项
  function onPlatformChange() {
    const keep = new Set(
      (allCases.value || [])
        .filter((c) => c.platform === selPlatform.value)
        .map((c) => `case:${c.path}`),
    );
    checkedKeys.value = checkedKeys.value.filter(
      (k: string) => !k.startsWith('case:') || keep.has(k),
    );
    updateCheckedFromKeys();
    expandedKeys.value = treeData.value.map((n: any) => n.id);
  }

  async function fetchMarkedFiles() {
    loadingMarkedFiles.value = true;
    for (const mark of filterMarks.value) {
      if (markedFiles.value[mark]) continue; // 已缓存
      try {
        const { data } = await http.get('/cases/with-mark', { params: { mark } });
        if (data?.files) {
          markedFiles.value[mark] = data.files;
        }
      } catch (e) {
        console.error(`获取 mark ${mark} 文件列表失败`, e);
      }
    }
    loadingMarkedFiles.value = false;
  }

  // ── 数据加载 ────────────────────────────────────────
  async function reload() {
    loadingCases.value = true;
    loadingModules.value = true;
    try {
      const [casesRes, modulesRes, marksRes] = await Promise.all([
        http.get('/cases/'),
        http.get('/cases/modules'),
        http.get('/cases/marks'),
      ]);
      allCases.value = Array.isArray(casesRes.data) ? casesRes.data : [];
      modules.value = Array.isArray(modulesRes.data) ? modulesRes.data : [];
      availableMarks.value = Array.isArray(marksRes.data) ? marksRes.data : [];
    } catch (e) {
      message.error('加载用例失败');
    } finally {
      loadingCases.value = false;
      loadingModules.value = false;
    }
  }

  async function run() {
    if (!checkedCases.value.length) {
      message.warning('请先勾选用例');
      return;
    }
    if (runScope.value === 'remote') {
      if (!targetMachine.value) {
        message.warning('请选择执行机器');
        return;
      }
      running.value = true;
      try {
        await runRemote();
      } finally {
        running.value = false;
      }
      return;
    }
    running.value = true;
    try {
      const targets = checkedCases.value.map((c) => c.path);
      const payload: any = { targets };

      // 如果选中有子场景，按文件分组拼接 -k 参数
      const hasScenario = checkedCases.value.some((c) => c._selectedScenarios?.length);
      if (hasScenario) {
        const argsMap: Record<string, string[]> = {};
        for (const c of checkedCases.value) {
          if (c._selectedScenarios?.length) {
            (argsMap[c.path] = argsMap[c.path] || []).push(
              ...c._selectedScenarios.map((id: string) => `"${id}"`),
            );
          }
        }
        // 每个文件一个 -k 参数
        payload.args = [];
        for (const [path, ids] of Object.entries(argsMap)) {
          payload.args.push('-k', ids.join(' or '));
        }
      }

      if (taskName.value.trim()) payload.name = taskName.value.trim();
      const { data } = await http.post('/cases/execute-batch', payload);
      message.success(
        `已提交本机执行（任务 ${data.task_id.slice(0, 8)}…），请到「任务记录」查看进度`,
      );
    } catch (e: any) {
      message.error(e.response?.data?.error || '提交执行失败');
    } finally {
      running.value = false;
    }
  }

  // 远程执行：按平台分组后逐个下发到目标机器，计划参数用「测试参数」该平台的默认值
  async function runRemote() {
    const groups: Record<string, string[]> = {};
    for (const c of checkedCases.value) {
      const p = c.platform || 'other';
      (groups[p] = groups[p] || []).push(c.path);
    }
    if (checkedCases.value.some((c) => c._selectedScenarios?.length)) {
      message.info('远程执行按整个用例文件下发（子场景级过滤仅本机生效）');
    }

    const submitted: string[] = [];
    for (const [p, paths] of Object.entries(groups)) {
      const cfg = plan.value[p] || {};
      try {
        const res = await submitTask({
          target_machine: targetMachine.value,
          platform: p,
          cases: paths,
          plan: { version: cfg.version || '', shop: cfg.shop || '', agent: cfg.agent || '' },
          name: taskName.value.trim() || undefined,
        });
        if (res.data.success && res.data.task_id) {
          submitted.push(res.data.task_id);
        } else {
          message.error(`平台 ${platformLabel(p)} 下发失败：${res.data.error || '未知错误'}`);
        }
      } catch (e: any) {
        message.error(`平台 ${platformLabel(p)} 下发失败：${e?.response?.data?.error || e.message}`);
      }
    }

    if (submitted.length) {
      message.success(`已下发 ${submitted.length} 个远程任务到 ${machineLabel(targetMachine.value)}`);
      // 单任务直达详情，多任务到「任务记录」统一查看
      if (submitted.length === 1) {
        router.push(`/test/monitor/${submitted[0]}`);
      } else {
        router.push('/test/monitor');
      }
    }
  }

  // 加载执行机器（远程作用域用），支持 URL ?machine=<ip> 预选（机器管理「执行任务」跳转）
  async function loadMachines() {
    try {
      const res = await getMachinesList();
      machines.value = res.data.data || [];
    } catch (e: any) {
      machines.value = [];
    }
    const q = route.query.machine as string | undefined;
    if (q && machines.value.some((m) => m.ip === q)) {
      targetMachine.value = q;
      runScope.value = 'remote';
      return;
    }
    targetMachine.value = machines.value.find((m) => m.idle)?.ip || '';
  }

  async function loadPlan() {
    try {
      const { data } = await http.get('/plan/');
      plan.value = data.plan || {};
    } catch (e) {
      plan.value = {};
    }
  }

  onMounted(() => {
    reload();
    loadPlan();
    loadMachines();
  });
</script>

<style scoped>
.page {
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.filter-card {
  flex-shrink: 0;
}
.filter-bar {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.filter-group {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  flex-wrap: wrap;
}
.filter-label {
  color: var(--accent);
  font-size: var(--vben-font-size-base);
  font-weight: 700;
  min-width: 48px;
  line-height: 22px;
}
.mark-desc {
  color: var(--text-muted);
  font-size: var(--vben-font-size-sm);
}
.mark-checkbox-group {
  display: grid;
  grid-template-columns: repeat(4, auto);
  gap: 2px 12px;
  align-items: start;
}
.filter-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  padding-top: 8px;
  border-top: 1px dashed var(--border-color);
}
.hit-count {
  color: var(--accent);
  font-size: var(--vben-font-size-base);
  font-weight: 600;
}
.hit-count strong {
  color: var(--error-color);
  font-size: var(--vben-font-size-lg);
}
.radio-and.ant-radio-button-wrapper-checked {
  border-color: var(--accent);
  color: var(--accent);
}
.radio-or.ant-radio-button-wrapper-checked {
  border-color: var(--warning-color);
  color: var(--warning-color);
}
.grow {
  display: flex;
  flex-direction: column;
}
.grow :deep(.el-card__body) {
  display: flex;
  flex-direction: column;
  max-height: 50vh;
  overflow: auto;
}
.grow-fill {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 200px;
}
.grow-fill :deep(.el-card__body) {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
}
.grow-fill :deep(.el-table) {
  flex: 1;
}
.toolbar {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}
.label {
  color: var(--text-primary);
  font-size: 16px;
  font-weight: 700;
}
.hint {
  color: var(--text-muted);
  font-size: var(--vben-font-size-base);
}
.plan-preview {
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px dashed var(--border-color);
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.plan-row {
  display: flex;
  align-items: baseline;
  gap: 8px;
  font-size: var(--vben-font-size-sm);
}
.plan-platform {
  color: var(--accent);
  font-weight: 600;
  min-width: 48px;
}
.plan-params {
  color: var(--text-muted);
}
/* 测试参数彩色 chips：字段色与系统语义色一致，浅半透明底不突兀 */
.plan-chip {
  display: inline-flex;
  align-items: center;
  padding: 1px 10px;
  border-radius: 4px;
  font-size: var(--vben-font-size-sm);
  line-height: 22px;
}
.pp-version {
  color: #0090ff;
  background: rgba(0, 144, 255, 0.12);
}
.pp-install {
  color: #f76b15;
  background: rgba(247, 107, 21, 0.12);
}
.pp-shop {
  color: #30a46c;
  background: rgba(48, 164, 108, 0.12);
}
.pp-agent {
  color: var(--accent);
  background: rgba(99, 102, 241, 0.12);
}
.pp-download {
  color: #7c3aed;
  background: rgba(124, 58, 237, 0.12);
}
.pp-other {
  color: var(--text-secondary);
  background: rgba(96, 100, 108, 0.12);
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
.case-tree {
  background: transparent;
}
.tree-node {
  display: flex;
  align-items: center;
  gap: 4px;
  flex: 1;
  overflow: hidden;
  flex-wrap: wrap;
}
.tree-node.platform .node-label {
  font-weight: 600;
  color: var(--accent);
}
.tree-node.case .node-label {
  color: var(--text-secondary);
}
.node-doc {
  color: var(--text-muted);
  font-size: var(--vben-font-size-sm);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  margin-left: 4px;
}
.doc {
  white-space: pre-wrap;
  font-size: var(--vben-font-size-sm);
  line-height: 1.5;
  color: var(--text-secondary);
}
.mark-tag {
  font-size: var(--vben-font-size-sm);
  line-height: 16px;
  padding: 0 4px;
  margin: 0 2px;
}
</style>