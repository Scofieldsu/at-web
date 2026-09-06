<template>
  <div class="page">
    <a-card class="theme-card">
      <template #title>
        <div class="hdr">
          <span class="sec-title tint-indigo"><ClockCircleOutlined />定时任务</span>
          <div class="tools">
            <a-button type="primary" size="small" @click="openCreate">新建定时任务</a-button>
            <a-button size="small" @click="loadSchedules">刷新</a-button>
          </div>
        </div>
      </template>

      <a-table
        :data-source="schedules"
        :columns="columns"
        row-key="id"
        size="middle"
        :loading="loading"
        :pagination="{ pageSize: 10 }"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'spec'">{{ formatSpec(record.spec) }}</template>
          <template v-else-if="column.key === 'enabled'">
            <a-tag :color="record.enabled ? 'success' : 'default'">{{ record.enabled ? '启用' : '停用' }}</a-tag>
          </template>
          <template v-else-if="column.key === 'cases'">{{ (record.cases || []).length }} 个</template>
          <template v-else-if="column.key === 'last_run'">
            <template v-if="record.last_run">
              <a-tag :color="lastRunColor(record.last_run.status)">{{ lastRunText(record.last_run.status) }}</a-tag>
              <a
                v-if="record.last_run.task_id"
                :href="`#/test/monitor/${record.last_run.task_id}`"
                class="ml-2"
              >{{ shortId(record.last_run.task_id) }}</a>
            </template>
            <span v-else class="muted">未执行</span>
          </template>
          <template v-else-if="column.key === 'action'">
            <a-space>
              <a-button size="small" @click="openEdit(record)">编辑</a-button>
              <a-button size="small" @click="toggleEnabled(record)">{{ record.enabled ? '停用' : '启用' }}</a-button>
              <a-popconfirm title="立即执行该定时任务？" @confirm="runNow(record)">
                <a-button size="small">立即执行</a-button>
              </a-popconfirm>
              <a-popconfirm title="确定删除该定时任务？" @confirm="removeSchedule(record)">
                <a-button size="small" danger>删除</a-button>
              </a-popconfirm>
            </a-space>
          </template>
          <template v-else>{{ record[column.key] }}</template>
        </template>
      </a-table>
    </a-card>

    <!-- 新建 / 编辑弹窗 -->
    <a-modal
      v-model:open="modalOpen"
      :title="editing ? '编辑定时任务' : '新建定时任务'"
      width="640"
      :confirm-loading="saving"
      @ok="save"
    >
      <a-form :label-col="{ span: 5 }" :wrapper-col="{ span: 18 }">
        <a-form-item label="名称" required>
          <a-input v-model:value="form.name" placeholder="如：每日回归" />
        </a-form-item>

        <a-form-item label="调度周期" required>
          <a-radio-group v-model:value="form.spec.type">
            <a-radio value="daily">每天</a-radio>
            <a-radio value="weekly">每周</a-radio>
            <a-radio value="monthly">每月</a-radio>
            <a-radio value="interval">间隔</a-radio>
          </a-radio-group>
        </a-form-item>

        <a-form-item v-if="form.spec.type === 'daily'" label="执行时间" required>
          <a-time-picker v-model:value="dailyTime" format="HH:mm" :minute-step="5" @change="syncDailyTime" />
        </a-form-item>
        <template v-else-if="form.spec.type === 'weekly'">
          <a-form-item label="星期" required>
            <a-select v-model:value="form.spec.weekdays" mode="multiple" placeholder="选择星期" style="width: 100%">
              <a-select-option v-for="(label, i) in weekdayLabels" :key="i + 1" :value="i + 1">{{ label }}</a-select-option>
            </a-select>
          </a-form-item>
          <a-form-item label="执行时间" required>
            <a-time-picker v-model:value="weeklyTime" format="HH:mm" @change="syncWeeklyTime" />
          </a-form-item>
        </template>
        <template v-else-if="form.spec.type === 'monthly'">
          <a-form-item label="几号" required>
            <a-input-number v-model:value="form.spec.day_of_month" :min="1" :max="31" />
          </a-form-item>
          <a-form-item label="执行时间" required>
            <a-time-picker v-model:value="monthlyTime" format="HH:mm" @change="syncMonthlyTime" />
          </a-form-item>
        </template>
        <a-form-item v-else label="间隔（小时）" required>
          <a-input-number v-model:value="form.spec.interval_hours" :min="1" />
        </a-form-item>

        <a-form-item label="目标机器" required>
          <a-select v-model:value="form.target_machine" placeholder="选择执行机器" style="width: 100%">
            <a-select-option v-for="m in machines" :key="m.id" :value="m.ip">
              {{ m.hostname }} ({{ m.ip }})
            </a-select-option>
          </a-select>
        </a-form-item>

        <a-form-item label="测试平台" required>
          <a-select v-model:value="form.platform" @change="loadCases">
            <a-select-option value="platform_a">平台A</a-select-option>
            <a-select-option value="platform_b">平台B</a-select-option>
            <a-select-option value="platform_d">平台D</a-select-option>
            <a-select-option value="platform_c">平台C</a-select-option>
          </a-select>
        </a-form-item>

        <a-form-item label="测试用例" required>
          <div class="mb-2">
            <a-button size="small" :loading="loadingCases" @click="loadCases">刷新用例列表</a-button>
            <span class="hint ml-2">已选择 {{ form.cases.length }} 个用例</span>
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

        <a-divider>测试计划参数</a-divider>
        <a-form-item label="测试版本">
          <a-input v-model:value="form.plan.version" placeholder="留空使用 latest" />
        </a-form-item>
        <a-form-item label="店铺">
          <a-input v-model:value="form.plan.shop" placeholder="如：测试店铺A" />
        </a-form-item>
        <a-form-item label="Agent">
          <a-input v-model:value="form.plan.agent" placeholder="如：客服1" />
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script lang="ts" setup>
  defineOptions({ name: 'SchedulePage' });
  import { ref, reactive, onMounted } from 'vue';
  import { message } from 'ant-design-vue';
  import { ClockCircleOutlined } from '@ant-design/icons-vue';
  import dayjs from 'dayjs';
  import type { Dayjs } from 'dayjs';
  import {
    getSchedules,
    createSchedule,
    updateSchedule,
    deleteSchedule,
    runSchedule,
  } from '@/api/platform/schedules';
  import type { Schedule, ScheduleSpec } from '@/api/platform/schedules';
  import { getMachinesList } from '@/api/platform/distributed';
  import type { Machine } from '@/api/platform/distributed';
  import http from '@/api/platform/http';

  const schedules = ref<Schedule[]>([]);
  const machines = ref<Machine[]>([]);
  const caseTree = ref<any[]>([]);
  // 当前平台下真实存在的用例文件路径，用于过滤 a-tree 勾选结果里的分组节点 key
  const caseFiles = ref<Set<string>>(new Set());
  const loadingCases = ref(false);
  const loading = ref(false);
  const saving = ref(false);
  const modalOpen = ref(false);
  const editing = ref<Schedule | null>(null);

  const weekdayLabels = ['周一', '周二', '周三', '周四', '周五', '周六', '周日'];

  function emptyForm() {
    return {
      name: '',
      spec: {
        type: 'daily',
        time: '02:00',
        weekdays: [1],
        day_of_month: 1,
        interval_hours: 6,
      } as ScheduleSpec,
      target_machine: '',
      platform: 'platform_a',
      cases: [] as string[],
      plan: { version: '', shop: '', agent: '' } as Record<string, any>,
    };
  }
  const form = reactive(emptyForm());

  const dailyTime = ref<Dayjs>(dayjs('02:00', 'HH:mm'));
  const weeklyTime = ref<Dayjs>(dayjs('02:00', 'HH:mm'));
  const monthlyTime = ref<Dayjs>(dayjs('02:00', 'HH:mm'));

  const columns = [
    { title: '名称', key: 'name', width: 140 },
    { title: '调度周期', key: 'spec', width: 180 },
    { title: '目标机器', key: 'target_machine', width: 130 },
    { title: '平台', key: 'platform', width: 80 },
    { title: '用例', key: 'cases', width: 60 },
    { title: '状态', key: 'enabled', width: 70 },
    { title: '下次执行', key: 'next_run_at', width: 160 },
    { title: '最近执行', key: 'last_run', width: 180 },
    { title: '操作', key: 'action', width: 230 },
  ];

  function formatSpec(spec: ScheduleSpec): string {
    if (spec.type === 'daily') return `每天 ${spec.time}`;
    if (spec.type === 'weekly') {
      const days = (spec.weekdays || []).map((d) => weekdayLabels[d - 1]).join('、');
      return `每周${days} ${spec.time}`;
    }
    if (spec.type === 'monthly') return `每月${spec.day_of_month}号 ${spec.time}`;
    return `每${spec.interval_hours}小时`;
  }

  function lastRunText(s: string): string {
    const map: Record<string, string> = { success: '成功', failed: '失败', running: '执行中' };
    return map[s] || s;
  }

  function lastRunColor(s: string): string {
    if (s === 'success') return 'success';
    if (s === 'failed') return 'error';
    return 'processing';
  }

  function shortId(id: string): string {
    return id.length > 20 ? `${id.slice(0, 12)}…` : id;
  }

  async function loadSchedules() {
    loading.value = true;
    try {
      const res = await getSchedules();
      schedules.value = res.data.schedules || [];
    } catch {
      message.error('加载定时任务失败');
    } finally {
      loading.value = false;
    }
  }

  async function loadMachines() {
    try {
      const res = await getMachinesList();
      machines.value = res.data.data || [];
    } catch {
      /* 忽略 */
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
      const map: Record<string, any> = {};
      const files = new Set<string>();
      cases.forEach((c: any) => {
        const p = c.platform || 'other';
        if (!map[p]) {
          map[p] = { name: platformName(p), path: p, children: [], selectable: false };
          tree.push(map[p]);
        }
        map[p].children.push({ name: c.name, path: c.file });
        files.add(c.file);
      });
      caseTree.value = tree;
      caseFiles.value = files;
      // 用例列表变了（切换平台、用例文件被删）时丢掉已不存在的勾选，避免提交幽灵路径。
      // 编辑已有任务时这会改动用户原本保存的选择，所以要提示，不能默默丢。
      const kept = form.cases.filter((f) => files.has(f));
      if (kept.length !== form.cases.length) {
        const dropped = form.cases.length - kept.length;
        if (editing.value) {
          message.warning(`已忽略 ${dropped} 个在当前平台下不存在的用例，保存后将不再包含`);
        }
        form.cases = kept;
      }
    } catch {
      message.error('加载用例列表失败');
    } finally {
      loadingCases.value = false;
    }
  }

  function platformName(p: string) {
    return (
      { platform_a: '平台A', platform_b: '平台B', platform_d: '平台D', platform_c: '平台C' }[p] || p
    );
  }

  function handleCaseCheck(checkedKeys: any) {
    const keys: string[] = checkedKeys.checked || checkedKeys;
    // 只保留真实用例文件：checkStrictly=false 时 rc-tree 会在某平台下全部子节点
    // 被勾选后把「平台分组节点」的 key（如 platform_a）也放进 checkedKeys，
    // 它不是文件路径，提交给 pytest 会直接报「找不到用例」。
    form.cases = keys.filter((k) => caseFiles.value.has(k));
  }

  function syncTimeToSpec(t: Dayjs | null) {
    if (t) form.spec.time = t.format('HH:mm');
  }

  function syncDailyTime(t: Dayjs | null) {
    if (form.spec.type === 'daily') syncTimeToSpec(t);
  }

  function syncWeeklyTime(t: Dayjs | null) {
    if (form.spec.type === 'weekly') syncTimeToSpec(t);
  }

  function syncMonthlyTime(t: Dayjs | null) {
    if (form.spec.type === 'monthly') syncTimeToSpec(t);
  }

  function openCreate() {
    editing.value = null;
    Object.assign(form, emptyForm());
    dailyTime.value = dayjs('02:00', 'HH:mm');
    weeklyTime.value = dayjs('02:00', 'HH:mm');
    monthlyTime.value = dayjs('02:00', 'HH:mm');
    modalOpen.value = true;
    if (machines.value.length && !form.target_machine) {
      form.target_machine = machines.value[0].ip;
    }
    loadCases();
  }

  function openEdit(s: Schedule) {
    editing.value = s;
    Object.assign(form, {
      name: s.name,
      spec: { ...s.spec },
      target_machine: s.target_machine,
      platform: s.platform,
      cases: [...(s.cases || [])],
      plan: { ...(s.plan || {}) },
    });
    const t = s.spec.time || '02:00';
    dailyTime.value = dayjs(t, 'HH:mm');
    weeklyTime.value = dayjs(t, 'HH:mm');
    monthlyTime.value = dayjs(t, 'HH:mm');
    modalOpen.value = true;
    loadCases();
  }

  async function save() {
    if (!form.name) {
      message.error('请填写名称');
      return;
    }
    if (!form.target_machine) {
      message.error('请选择目标机器');
      return;
    }
    if (!form.cases.length) {
      message.error('请选择测试用例');
      return;
    }
    if (form.spec.type === 'weekly' && !(form.spec.weekdays || []).length) {
      message.error('请选择星期');
      return;
    }

    saving.value = true;
    try {
      const payload = { ...form };
      if (editing.value) {
        await updateSchedule(editing.value.id, payload);
      } else {
        await createSchedule(payload);
      }
      message.success('已保存');
      modalOpen.value = false;
      await loadSchedules();
    } catch (e: any) {
      message.error(e?.response?.data?.error || '保存失败');
    } finally {
      saving.value = false;
    }
  }

  async function toggleEnabled(s: Schedule) {
    try {
      await updateSchedule(s.id, { enabled: !s.enabled });
      s.enabled = !s.enabled;
    } catch {
      message.error('操作失败');
    }
  }

  async function runNow(s: Schedule) {
    try {
      const res = await runSchedule(s.id);
      if (res.data.success) {
        message.success('已触发执行');
        await loadSchedules();
      } else {
        message.error(res.data.error || '触发失败');
      }
    } catch (e: any) {
      message.error(e?.response?.data?.error || '触发失败');
    }
  }

  async function removeSchedule(s: Schedule) {
    try {
      await deleteSchedule(s.id);
      message.success('已删除');
      await loadSchedules();
    } catch (e: any) {
      message.error(e?.response?.data?.error || '删除失败');
    }
  }

  onMounted(() => {
    loadSchedules();
    loadMachines();
  });
</script>

<style lang="less" scoped>
  .page {
    padding: 16px;
  }

  .hdr {
    display: flex;
    align-items: center;
    justify-content: space-between;
  }

  .tools {
    display: flex;
    gap: 8px;
  }

  .muted {
    color: var(--text-muted);
  }

  .mb-2 {
    margin-bottom: 8px;
  }

  .ml-2 {
    margin-left: 8px;
  }

  .hint {
    color: var(--text-secondary);
    font-size: var(--vben-font-size-sm);
  }
</style>
