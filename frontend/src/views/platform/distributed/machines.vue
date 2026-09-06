<template>
  <div class="page">
    <!-- 汇总 -->
    <a-card class="theme-card">
      <div class="summary-grid">
        <div class="summary-item">
          <div class="summary-label">总机器数</div>
          <div class="summary-value">{{ summary.total }}</div>
        </div>
        <div class="summary-item">
          <div class="summary-label">在线</div>
          <div class="summary-value text-success">{{ summary.online }}</div>
        </div>
        <div class="summary-item">
          <div class="summary-label">空闲</div>
          <div class="summary-value text-primary">{{ summary.idle }}</div>
        </div>
        <div class="summary-item">
          <div class="summary-label">代码版本</div>
          <div class="summary-value">
            <a-tag v-if="summary.versionConsistent" color="success">一致</a-tag>
            <a-tag v-else color="warning">不一致</a-tag>
          </div>
        </div>
      </div>

      <!-- 远程仓库版本提示：与「消息注入」目标连接提示同款（蓝感叹号 + 浅蓝底 + 12px） -->
      <div v-if="remoteVersion && remoteVersion.commit_hash" class="conn-tip mt-3">
        <div class="conn-tip-line">
          <ExclamationCircleOutlined class="conn-tip-icon" />
          <span class="conn-tip-body">
            <span class="strong">远程仓库（origin/main）最新版本：</span>
            <a-tag color="blue" class="ml-2">{{ remoteVersion.commit_hash }}</a-tag>
            <span class="text-muted ml-2">{{ remoteVersion.commit_date }}</span>
          </span>
        </div>
      </div>
    </a-card>

    <!-- 操作栏 -->
    <a-card class="theme-card">
      <div class="toolbar">
        <a-button type="primary" :loading="loading" @click="refreshMachines">
          刷新
        </a-button>
        <a-button @click="showAddModal">添加机器</a-button>
        <a-divider type="vertical" />
        <span class="hint">每 60 秒自动刷新 · 最后刷新 {{ lastRefreshTime }}</span>
      </div>
    </a-card>

    <!-- 机器列表 -->
    <a-card class="theme-card">
      <a-table
        :columns="columns"
        :data-source="machines"
        :loading="loading"
        :pagination="false"
        :scroll="{ x: 1200 }"
        row-key="id"
        size="middle"
      >
        <template #bodyCell="{ column, record }">
          <!-- 状态 -->
          <template v-if="column.key === 'status'">
            <div class="cell-flex">
              <span class="status-dot" :class="`dot-${record.status}`" />
              <a-tag :color="statusColor(record.status)">
                {{ statusText(record.status) }}
              </a-tag>
            </div>
            <div v-if="record.error" class="text-xs text-danger mt-1">
              {{ record.error }}
            </div>
          </template>

          <!-- 机器 -->
          <template v-else-if="column.key === 'machine'">
            <div class="strong" :class="{ 'text-danger': record.is_local }">
              {{ record.hostname || '-' }}
            </div>
            <div
              class="text-xs"
              :class="record.is_local ? 'text-danger' : 'text-muted'"
            >{{ record.ip }}:{{ record.port }}</div>
            <!-- 本机标记与备注标签并存：ip/hostname 自动维护，备注仍可自己改 -->
            <a-tag v-if="record.is_local" color="blue" class="mt-1">本机 · IP 自动识别</a-tag>
            <div class="label-row mt-1">
              <template v-if="editingLabelId === record.id">
                <a-input
                  v-model:value="labelDraft"
                  autofocus
                  size="small"
                  :maxlength="MAX_LABEL_LEN"
                  :disabled="savingLabel"
                  placeholder="备注，留空清除"
                  class="label-input"
                  @press-enter="confirmSaveLabel(record)"
                  @keyup.esc="cancelLabel"
                />
              </template>
              <!-- 双击标签直接修改备注：回车保存（二次确认），Esc 取消 -->
              <template v-else>
                <a-tag
                  v-if="record.label"
                  class="label-tag"
                  title="双击修改备注"
                  @dblclick="startEditLabel(record)"
                >
                  {{ record.label }}
                </a-tag>
                <span
                  v-else
                  class="text-xs text-muted label-empty"
                  title="双击添加备注"
                  @dblclick="startEditLabel(record)"
                >无备注</span>
              </template>
            </div>
          </template>

          <!-- 代码版本 -->
          <template v-else-if="column.key === 'version'">
            <template v-if="record.git_info && record.git_info.commit_hash">
              <div class="cell-flex">
                <a-tag color="blue">{{ record.git_info.commit_hash }}</a-tag>
                <span class="text-xs text-muted">{{ record.git_info.branch }}</span>
                <ExclamationCircleOutlined
                  v-if="getVersionStatus(record) === 'mismatch'"
                  class="version-icon text-danger clickable"
                  title="代码版本与远程不一致，点击查看差异"
                  @click="showDiffModal(record)"
                />
                <ExclamationCircleOutlined
                  v-else-if="getVersionStatus(record) === 'uncommitted'"
                  class="version-icon text-warning clickable"
                  title="有未提交的修改，点击查看差异"
                  @click="showDiffModal(record)"
                />
              </div>
              <div class="text-xs text-muted mt-1">
                {{ record.git_info.commit_date }}
              </div>
              <a-tag
                v-if="record.git_info.has_uncommitted_changes"
                color="warning"
                class="mt-1"
              >
                有未提交修改
              </a-tag>
            </template>
            <span v-else class="text-muted">未知</span>
          </template>

          <!-- 资源 -->
          <template v-else-if="column.key === 'resources'">
            <div
              class="resource-overview"
              :title="record.cpu_model ? `CPU 型号：${record.cpu_model}` : ''"
            >
              <span v-if="record.cpu_cores">{{ record.cpu_cores }} 核</span>
              <span v-else class="text-muted">- 核</span>
              <span v-if="record.memory_total_gb"> · {{ record.memory_total_gb }} GB</span>
              <span v-else class="text-muted"> · - GB</span>
              <span v-if="record.disk_total_gb"> · {{ record.disk_total_gb }} GB</span>
              <span v-else class="text-muted"> · - GB</span>
            </div>
            <div class="resource-row">
              <span class="resource-label">CPU</span>
              <a-progress
                :percent="record.cpu_percent"
                :stroke-color="progressColor(record.cpu_percent)"
                size="small"
              />
            </div>
            <div class="resource-row">
              <span class="resource-label">内存</span>
              <a-progress
                :percent="record.memory_percent"
                :stroke-color="progressColor(record.memory_percent)"
                size="small"
              />
            </div>
            <div class="resource-row">
              <span class="resource-label">磁盘</span>
              <a-progress
                :percent="record.disk_percent"
                :stroke-color="progressColor(record.disk_percent)"
                size="small"
              />
            </div>
          </template>

          <!-- 关键服务 -->
          <template v-else-if="column.key === 'services'">
            <div class="cell-flex">
              <span
                class="service-dot"
                :class="record.services?.mitmproxy ? 'dot-ok' : 'dot-off'"
              />
              <span class="text-xs">mitmproxy</span>
            </div>
            <!-- 只有装了 MinIO 的机器才显示 MinIO 行 -->
            <div v-if="record.services?.minio" class="cell-flex mt-1">
              <span class="service-dot dot-ok" />
              <span class="text-xs">MinIO</span>
            </div>
            <div class="text-xs text-muted mt-1">
              Python 进程: {{ record.services?.python_processes ?? '-' }}
            </div>
          </template>

          <!-- 当前任务 -->
          <template v-else-if="column.key === 'currentTask'">
            <template v-if="record.current_task">
              <a-tag color="processing">运行中</a-tag>
              <div class="text-xs mt-1">{{ record.current_task.name }}</div>
              <a-button
                type="link"
                size="small"
                @click="gotoMonitor(record.current_task.task_id)"
              >
                查看日志
              </a-button>
            </template>
            <a-tag v-else-if="record.available" color="success">空闲</a-tag>
            <span v-else class="text-muted">-</span>
          </template>

          <!-- 操作 -->
          <template v-else-if="column.key === 'action'">
            <div class="action-row">
              <a-button
                type="primary"
                size="small"
                :disabled="!record.idle"
                @click="gotoSubmit(record)"
              >
                执行任务
              </a-button>
              <a-dropdown trigger="click">
                <a-button size="small">
                  <MoreOutlined />
                </a-button>
                <template #overlay>
                  <a-menu @click="({ key }) => handleActionMenu(key, record)">
                    <a-menu-item key="update" :disabled="!record.available || !record.idle">
                      更新服务
                    </a-menu-item>
                    <a-menu-item v-if="!record.is_local" key="remove" danger>
                      移除
                    </a-menu-item>
                  </a-menu>
                </template>
              </a-dropdown>
            </div>
          </template>
        </template>
      </a-table>
    </a-card>

    <!-- 添加机器 -->
    <a-modal
      v-model:open="addVisible"
      title="添加测试机器"
      :confirm-loading="addLoading"
      @ok="handleAdd"
    >
      <a-form :label-col="{ span: 6 }">
        <a-form-item label="IP 地址" required>
          <a-input v-model:value="addForm.ip" placeholder="10.0.0.20" />
        </a-form-item>
        <a-form-item label="端口">
          <a-input-number
            v-model:value="addForm.port"
            :min="1"
            :max="65535"
            style="width: 100%"
          />
        </a-form-item>
        <a-form-item label="主机名">
          <a-input v-model:value="addForm.hostname" placeholder="留空则自动探测" />
        </a-form-item>
        <a-form-item label="标签">
          <a-input v-model:value="addForm.label" placeholder="如：物理机1" />
        </a-form-item>
      </a-form>
      <a-alert
        type="info"
        show-icon
        message="目标机器需已启动本项目服务（默认 5000 端口）并放通防火墙。"
      />
    </a-modal>

    <!-- 更新服务 -->
    <a-modal
      v-model:open="updateVisible"
      :title="`更新服务 - ${updateTarget?.hostname || updateTarget?.ip}`"
      width="800px"
      :confirm-loading="updateStarting"
      :ok-text="updateStarted ? '关闭' : '确认更新'"
      :cancel-text="updateStarted ? null : '取消'"
      @ok="updateStarted ? (updateVisible = false) : handleUpdate()"
    >
      <template v-if="!updateStarted">
        <a-alert type="warning" show-icon class="mb-3">
          <template #message>
            <div class="strong">更新操作将执行以下步骤：</div>
            <ol class="mt-2 ml-4">
              <li>停止当前服务（mitmweb + Flask）</li>
              <li>拉取最新代码（git pull）</li>
              <li>重新构建前端（web-vben）</li>
              <li>重启服务</li>
            </ol>
            <div class="mt-2 text-danger strong">
              更新期间该机器将无法响应请求，已在运行的任务会被中断。
            </div>
          </template>
        </a-alert>

        <a-alert
          v-if="updateTarget?.is_local"
          type="info"
          show-icon
          class="mb-3"
          message="本机更新说明"
        >
          <template #description>
            <div>更新进程会以孤儿模式运行，即使当前控制台断开连接也不会中断。</div>
            <div class="mt-1">
              服务重启后可通过「刷新」按钮查看更新结果，或在下方日志中查看进度。
            </div>
          </template>
        </a-alert>

        <div v-if="!updatePrivilegeOk" class="mb-3">
          <a-alert type="error" show-icon>
            <template #message>
              <div class="strong">权限不足</div>
              <div class="mt-1">
                服务未以管理员权限运行，无法执行更新操作。请以管理员身份重启服务后重试。
              </div>
            </template>
          </a-alert>
        </div>
      </template>

      <template v-else>
        <a-alert
          :type="updateStatus === 'running' ? 'info' : updateStatus === 'success' ? 'success' : 'error'"
          show-icon
          class="mb-3"
        >
          <template #message>
            <span v-if="updateStatus === 'running'">更新进行中...</span>
            <span v-else-if="updateStatus === 'success'">更新完成</span>
            <span v-else>更新失败</span>
          </template>
          <template v-if="updateError" #description>{{ updateError }}</template>
        </a-alert>

        <div class="update-log-container">
          <div class="log-header">
            <span class="strong">更新日志</span>
            <a-button
              v-if="updateStatus === 'running'"
              type="link"
              size="small"
              :loading="updateLogLoading"
              @click="fetchUpdateLog"
            >
              刷新
            </a-button>
          </div>
          <div class="log-content">
            <pre v-if="updateLogLines.length > 0">{{ updateLogLines.join('') }}</pre>
            <div v-else class="text-muted text-center">暂无日志</div>
          </div>
        </div>
      </template>
    </a-modal>

    <!-- 代码差异 -->
    <a-modal
      v-model:open="diffVisible"
      :title="`代码差异 - ${diffTarget?.hostname || diffTarget?.ip}`"
      width="900px"
      :footer="null"
    >
      <a-spin :spinning="diffLoading">
        <template v-if="!diffLoading && diffData">
          <a-alert
            v-if="diffData.local_hash && diffData.remote_hash"
            :type="diffData.behind > 0 || diffData.has_uncommitted ? 'warning' : 'info'"
            show-icon
            class="mb-3"
          >
            <template #message>
              <div class="strong">版本对比</div>
              <div class="mt-1">
                本地：<a-tag color="blue">{{ diffData.local_hash }}</a-tag>
                <span v-if="diffData.behind > 0" class="text-danger ml-2">
                  落后 origin/main {{ diffData.behind }} 个提交
                </span>
                <span v-else-if="diffData.ahead > 0" class="text-success ml-2">
                  领先 origin/main {{ diffData.ahead }} 个提交
                </span>
                <span v-else class="text-success ml-2">与 origin/main 一致</span>
              </div>
              <div class="mt-1">
                远程：<a-tag color="blue">{{ diffData.remote_hash }}</a-tag>
              </div>
            </template>
          </a-alert>

          <a-tabs v-if="diffData.commits.length > 0 || diffData.has_uncommitted">
            <a-tab-pane v-if="diffData.commits.length > 0" key="commits" tab="缺失的提交">
              <div class="commits-list">
                <div
                  v-for="commit in diffData.commits"
                  :key="commit.hash"
                  class="commit-item"
                >
                  <div class="commit-header">
                    <a-tag color="blue">{{ commit.hash }}</a-tag>
                    <span class="commit-author">{{ commit.author }}</span>
                    <span class="commit-date">{{ commit.date }}</span>
                  </div>
                  <div class="commit-message">{{ commit.message }}</div>
                </div>
              </div>
            </a-tab-pane>

            <a-tab-pane
              v-if="diffData.has_uncommitted"
              key="uncommitted"
              tab="未提交的修改"
            >
              <div v-if="diffData.untracked_files.length > 0" class="mb-3">
                <div class="strong mb-2">未跟踪的文件：</div>
                <div class="untracked-files">
                  <div
                    v-for="file in diffData.untracked_files"
                    :key="file"
                    class="untracked-file"
                  >
                    {{ file }}
                  </div>
                </div>
              </div>
              <div v-if="diffData.uncommitted_diff">
                <div class="strong mb-2">差异：</div>
                <pre class="diff-content">{{ diffData.uncommitted_diff }}</pre>
                <a-alert
                  v-if="diffData.truncated"
                  type="warning"
                  show-icon
                  class="mt-2"
                  message="差异内容过大，已截断显示"
                />
              </div>
              <div v-else class="text-muted text-center">仅有未跟踪文件，无已跟踪文件的修改</div>
            </a-tab-pane>
          </a-tabs>

          <a-empty v-else description="无代码差异" />
        </template>
      </a-spin>
    </a-modal>
  </div>
</template>

<script lang="ts" setup>
  defineOptions({ name: 'DistributedMachines' });
  import { ref, reactive, computed, onMounted, onUnmounted } from 'vue';
  import { useRouter } from 'vue-router';
  import { message, Modal } from 'ant-design-vue';
  import { MoreOutlined, ExclamationCircleOutlined } from '@ant-design/icons-vue';
  import {
    getMachinesList,
    addMachine,
    removeMachine,
    setMachineLabel,
    triggerUpdate,
    getUpdateStatus,
    getUpdateLog,
    getMachineDiff,
  } from '@/api/platform/distributed';
  import type { Machine } from '@/api/platform/distributed';

  const router = useRouter();

  const machines = ref<Machine[]>([]);
  const loading = ref(false);
  const lastRefreshTime = ref('--');
  const remoteVersion = ref<any>(null);
  let timer: ReturnType<typeof setInterval> | null = null;

  const columns = [
    { title: '状态', key: 'status', width: 130 },
    { title: '机器', key: 'machine', width: 190 },
    { title: '代码版本', key: 'version', width: 260 },
    { title: '资源占用', key: 'resources', width: 240 },
    { title: '关键服务', key: 'services', width: 140 },
    { title: '当前任务', key: 'currentTask', width: 180 },
    { title: '操作', key: 'action', width: 150, fixed: 'right' },
  ];

  // 汇总直接由后端 summary 提供；此处兜底本地计算，避免接口异常时整块空白
  const summary = computed(() => {
    const list = machines.value;
    const versions = [
      ...new Set(
        list
          .filter((m) => m.available && m.version && m.version !== 'unknown')
          .map((m) => m.version),
      ),
    ];
    return {
      total: list.length,
      online: list.filter((m) => m.available).length,
      idle: list.filter((m) => m.idle).length,
      versions,
      versionConsistent: versions.length <= 1,
    };
  });

  async function refreshMachines() {
    loading.value = true;
    try {
      const res = await getMachinesList();
      // 本机默认置顶显示在第一个（稳定排序，其余保持后端顺序）
      machines.value = (res.data.data || []).slice().sort(
        (a, b) => Number(b.is_local) - Number(a.is_local),
      );
      remoteVersion.value = res.data.summary?.remote_version || null;
      lastRefreshTime.value = new Date().toLocaleTimeString();
    } catch (e: any) {
      message.error(`刷新失败: ${e?.response?.data?.error || e.message}`);
    } finally {
      loading.value = false;
    }
  }

  // ── 版本对比 ──────────────────────────────────────────────
  // 与远程 origin/main 的 commit_hash 比对：不一致优先标红，一致但有本地
  // 未提交改动标黄；远程版本拿不到时不做判定（避免误报一片红）。
  function getVersionStatus(m: Machine): 'ok' | 'mismatch' | 'uncommitted' | 'unknown' {
    const remoteHash = remoteVersion.value?.commit_hash;
    const localHash = m.git_info?.commit_hash;
    if (!remoteHash || remoteHash === 'unknown' || !localHash) return 'unknown';
    if (localHash !== remoteHash) return 'mismatch';
    return m.git_info?.has_uncommitted_changes ? 'uncommitted' : 'ok';
  }

  const diffVisible = ref(false);
  const diffLoading = ref(false);
  const diffTarget = ref<Machine | null>(null);
  const diffData = ref<any>(null);

  async function showDiffModal(m: Machine) {
    diffTarget.value = m;
    diffData.value = null;
    diffVisible.value = true;
    diffLoading.value = true;
    try {
      const res = await getMachineDiff({ ip: m.ip, port: m.port });
      diffData.value = res.data;
    } catch (e: any) {
      message.error(e?.response?.data?.error || '获取代码差异失败');
      diffVisible.value = false;
    } finally {
      diffLoading.value = false;
    }
  }

  // ── 备注标签行内编辑 ──────────────────────────────────────
  // 双击标签进入编辑；回车弹出二次确认（确认保存 / 取消丢弃），Esc 直接取消。
  // 与后端 MAX_LABEL_LEN 保持一致，输入框直接截断，不用等接口报 400
  const MAX_LABEL_LEN = 32;
  const editingLabelId = ref<string | null>(null);
  const labelDraft = ref('');
  const savingLabel = ref(false);

  function startEditLabel(m: Machine) {
    editingLabelId.value = m.id;
    labelDraft.value = m.label || '';
  }

  function cancelLabel() {
    editingLabelId.value = null;
    labelDraft.value = '';
  }

  // 回车触发：二次确认/取消，避免误保存
  function confirmSaveLabel(m: Machine) {
    const next = labelDraft.value.trim();
    if (next === (m.label || '')) {
      // 内容无变化，直接退出编辑，不弹窗
      cancelLabel();
      return;
    }
    Modal.confirm({
      title: '确认修改备注',
      content: `将${m.label ? `「${m.label}」` : '（无备注）'}改为${next ? `「${next}」` : '（清除备注）'}？`,
      okText: '确认',
      cancelText: '取消',
      onOk: () => saveLabel(m),
      onCancel: () => cancelLabel(),
    });
  }

  async function saveLabel(m: Machine) {
    const next = labelDraft.value.trim();
    if (next === (m.label || '')) {
      cancelLabel();
      return;
    }
    savingLabel.value = true;
    try {
      await setMachineLabel({ ip: m.ip, port: m.port, label: next });
      // 就地更新，避免整表刷新把用户正在看的行抖掉
      m.label = next;
      message.success(next ? '备注已保存' : '备注已清除');
      cancelLabel();
    } catch (e: any) {
      message.error(e?.response?.data?.error || '保存备注失败');
    } finally {
      savingLabel.value = false;
    }
  }

  // ── 添加 / 移除 ────────────────────────────────────────────

  const addVisible = ref(false);
  const addLoading = ref(false);
  const addForm = reactive({ ip: '', port: 5000, hostname: '', label: '' });

  function showAddModal() {
    Object.assign(addForm, { ip: '', port: 5000, hostname: '', label: '' });
    addVisible.value = true;
  }

  async function handleAdd() {
    if (!addForm.ip.trim()) {
      message.error('请输入 IP 地址');
      return;
    }
    addLoading.value = true;
    try {
      const res = await addMachine({ ...addForm, ip: addForm.ip.trim() });
      addVisible.value = false;
      if (res.data?.status === 'online') {
        message.success('添加成功，机器在线');
      } else {
        message.warning(
          `已添加，但探测到状态为 ${res.data?.status}：${res.data?.error || ''}`,
        );
      }
      await refreshMachines();
    } catch (e: any) {
      message.error(e?.response?.data?.error || '添加失败');
    } finally {
      addLoading.value = false;
    }
  }

  // ── 操作：主按钮 + 更多下拉 ────────────────────────────────
  // 执行任务常驻；更新服务/移除收进「⋯」下拉，按机器状态/属性显示可用项
  function handleActionMenu(key: string, m: Machine) {
    if (key === 'update') {
      showUpdateModal(m);
    } else if (key === 'remove') {
      Modal.confirm({
        title: '确定移除此机器？',
        content: `${m.hostname || m.ip}（${m.ip}:${m.port}）将从机器列表中移除。`,
        okText: '移除',
        okButtonProps: { danger: true },
        cancelText: '取消',
        onOk: () => handleRemove(m),
      });
    }
  }

  async function handleRemove(m: Machine) {
    try {
      await removeMachine({ ip: m.ip, port: m.port });
      message.success('已移除');
      await refreshMachines();
    } catch (e: any) {
      message.error(e?.response?.data?.error || '移除失败');
    }
  }

  // ── 服务更新 ──────────────────────────────────────────────

  const updateVisible = ref(false);
  const updateTarget = ref<Machine | null>(null);
  const updateStarting = ref(false);
  const updateStarted = ref(false);
  const updateId = ref('');
  const updateStatus = ref<'running' | 'success' | 'failed'>('running');
  const updateError = ref('');
  const updatePrivilegeOk = ref(true);
  const updateLogLines = ref<string[]>([]);
  const updateLogOffset = ref(0);
  const updateLogLoading = ref(false);
  let updatePollTimer: ReturnType<typeof setInterval> | null = null;

  function showUpdateModal(m: Machine) {
    updateTarget.value = m;
    updateStarted.value = false;
    updateId.value = '';
    updateStatus.value = 'running';
    updateError.value = '';
    updatePrivilegeOk.value = true;
    updateLogLines.value = [];
    updateLogOffset.value = 0;
    updateVisible.value = true;
  }

  async function handleUpdate() {
    if (!updateTarget.value) return;

    updateStarting.value = true;
    try {
      const target = updateTarget.value.is_local ? 'local' : updateTarget.value.ip;
      const res = await triggerUpdate({
        target,
        port: updateTarget.value.port,
      });

      if (!res.data.success) {
        // 权限不足等错误
        if (res.data.code === 403) {
          updatePrivilegeOk.value = false;
          message.error(res.data.error || '服务未以管理员权限运行');
        } else {
          message.error(res.data.error || '启动更新失败');
        }
        return;
      }

      updateId.value = res.data.update_id!;
      updateStarted.value = true;
      message.success('更新已启动，请等待...');

      // 开始轮询状态和日志
      startUpdatePolling();
    } catch (e: any) {
      message.error(e?.response?.data?.error || '启动更新失败');
    } finally {
      updateStarting.value = false;
    }
  }

  function startUpdatePolling() {
    // 立即拉一次
    fetchUpdateStatus();
    fetchUpdateLog();

    // 每 2 秒轮询
    updatePollTimer = setInterval(() => {
      fetchUpdateStatus();
      fetchUpdateLog();
    }, 2000);
  }

  function stopUpdatePolling() {
    if (updatePollTimer) {
      clearInterval(updatePollTimer);
      updatePollTimer = null;
    }
  }

  async function fetchUpdateStatus() {
    if (!updateId.value) return;
    try {
      const res = await getUpdateStatus(updateId.value);
      updateStatus.value = res.data.status;
      updateError.value = res.data.error || '';

      // 终态则停止轮询
      if (res.data.status === 'success' || res.data.status === 'failed') {
        stopUpdatePolling();
        // 更新完成后刷新机器列表（特别是本机，IP 可能变了）
        if (res.data.status === 'success') {
          setTimeout(() => refreshMachines(), 3000);
        }
      }
    } catch (e: any) {
      // 忽略轮询失败（更新期间服务会短暂不可达）
      console.warn('fetchUpdateStatus error:', e);
    }
  }

  async function fetchUpdateLog() {
    if (!updateId.value || updateLogLoading.value) return;
    updateLogLoading.value = true;
    try {
      const res = await getUpdateLog(updateId.value, updateLogOffset.value, 500);
      if (res.data.lines.length > 0) {
        updateLogLines.value.push(...res.data.lines);
        updateLogOffset.value = res.data.offset;
      }
      // 日志读完且已终态，停止轮询
      if (res.data.finished) {
        stopUpdatePolling();
      }
    } catch (e: any) {
      console.warn('fetchUpdateLog error:', e);
    } finally {
      updateLogLoading.value = false;
    }
  }

  // ── 跳转 ──────────────────────────────────────────────────

  function gotoSubmit(m: Machine) {
    // 执行入口已统一到「测试执行 → 执行用例」，带机器预选（页面内切到远程作用域）
    router.push({ path: '/test/cases', query: { machine: m.ip } });
  }

  function gotoMonitor(taskId: string) {
    router.push(`/test/monitor/${taskId}`);
  }

  // ── 展示辅助 ──────────────────────────────────────────────

  function statusColor(status: string) {
    return (
      { online: 'success', offline: 'default', timeout: 'warning', error: 'error' }[
        status
      ] || 'default'
    );
  }

  function statusText(status: string) {
    return (
      { online: '在线', offline: '离线', timeout: '超时', error: '异常' }[status] ||
      status
    );
  }

  function progressColor(percent: number) {
    if (percent < 60) return 'var(--success-color)';
    if (percent < 80) return '#faad14';
    return 'var(--error-color)';
  }

  onMounted(() => {
    refreshMachines();
    // 编辑备注期间跳过自动刷新：刷新会整体替换 machines，把正在编辑的行连同
    // 输入内容一起换掉。添加机器弹窗开着时同理（避免表格在身后跳动）。
    // 更新服务弹窗开着时也跳过（避免干扰日志查看）。
    // 代码差异弹窗开着时也跳过。
    timer = setInterval(() => {
      if (
        editingLabelId.value ||
        addVisible.value ||
        updateVisible.value ||
        diffVisible.value
      )
        return;
      refreshMachines();
    }, 60_000);
  });

  onUnmounted(() => {
    if (timer) clearInterval(timer);
    stopUpdatePolling();
  });
</script>

<style lang="less" scoped>
  .page {
    padding: 16px;
  }

  .theme-card {
    margin-bottom: 16px;
  }

  .summary-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 24px;
  }

  .summary-item {
    text-align: center;
  }

  .summary-label {
    margin-bottom: 6px;
    font-size: var(--vben-font-size-base);
    color: var(--text-secondary);
  }

  .summary-value {
    font-size: 26px;
    font-weight: 600;
    line-height: 1.2;
  }

  .toolbar {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    align-items: center;
  }

  .hint {
    font-size: var(--vben-font-size-sm);
    color: var(--text-secondary);
  }

  .cell-flex {
    display: flex;
    gap: 6px;
    align-items: center;
  }

  .action-row {
    display: flex;
    gap: 6px;
    align-items: center;
  }

  .label-row {
    display: flex;
    flex-wrap: wrap;
    gap: 2px;
    align-items: center;
  }

  .label-input {
    width: 120px;
  }

  .label-tag,
  .label-empty {
    cursor: pointer;
  }

  .strong {
    font-weight: 500;
  }

  .status-dot,
  .service-dot {
    display: inline-block;
    width: 8px;
    height: 8px;
    border-radius: 50%;
  }

  .dot-online,
  .dot-ok {
    background: var(--success-color);
    animation: pulse 2s infinite;
  }

  .dot-offline,
  .dot-off {
    background: var(--border-color);
  }

  .dot-timeout {
    background: #faad14;
  }

  .dot-error {
    background: var(--error-color);
  }

  .resource-row {
    display: flex;
    gap: 6px;
    align-items: center;
  }

  .resource-label {
    width: 32px;
    font-size: var(--vben-font-size-sm);
    color: var(--text-secondary);
  }

  .resource-overview {
    margin-bottom: 6px;
    color: var(--text-secondary);
    font-size: var(--vben-font-size-sm);
  }

  .text-xs {
    font-size: var(--vben-font-size-sm);
  }

  .text-muted {
    color: var(--text-secondary);
  }

  .text-danger {
    color: var(--error-color);
  }

  .text-success {
    color: var(--success-color);
  }

  .text-primary {
    color: var(--info-color);
  }

  .mt-1 {
    margin-top: 4px;
  }

  .mt-3 {
    margin-top: 12px;
  }

  /* 远程仓库提示：消息注入 conn-tip 同款（蓝感叹号 + 浅蓝底 + 12px 字号） */
  .conn-tip {
    background: rgba(0, 144, 255, 0.06);
    border: 1px solid rgba(0, 144, 255, 0.25);
    border-radius: var(--vben-radius-lg);
    padding: 8px 12px;
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

  .mb-3 {
    margin-bottom: 12px;
  }

  .ml-4 {
    margin-left: 16px;
  }

  .update-log-container {
    border: 1px solid var(--border-color);
    border-radius: 4px;
    overflow: hidden;
  }

  .log-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 8px 12px;
    background: var(--component-background);
    border-bottom: 1px solid var(--border-color);
  }

  .log-content {
    max-height: 400px;
    padding: 12px;
    overflow-y: auto;
    background: var(--component-background);
    font-family: 'Consolas', 'Monaco', monospace;
    font-size: 12px;
    line-height: 1.5;

    pre {
      margin: 0;
      white-space: pre-wrap;
      word-break: break-all;
    }
  }

  .text-center {
    text-align: center;
  }

  .text-warning {
    color: #faad14;
  }

  .ml-2 {
    margin-left: 8px;
  }

  .mb-2 {
    margin-bottom: 8px;
  }

  .version-icon {
    font-size: 14px;
  }

  .clickable {
    cursor: pointer;
  }

  .commits-list {
    max-height: 420px;
    overflow-y: auto;
  }

  .commit-item {
    padding: 8px 0;
    border-bottom: 1px solid var(--border-color);

    &:last-child {
      border-bottom: none;
    }
  }

  .commit-header {
    display: flex;
    gap: 8px;
    align-items: center;
    font-size: var(--vben-font-size-sm);
    color: var(--text-secondary);
  }

  .commit-message {
    margin-top: 4px;
  }

  .untracked-files,
  .diff-content {
    max-height: 360px;
    padding: 12px;
    overflow: auto;
    background: var(--component-background);
    border: 1px solid var(--border-color);
    border-radius: 4px;
    font-family: 'Consolas', 'Monaco', monospace;
    font-size: 12px;
    line-height: 1.5;
  }

  .diff-content {
    margin: 0;
    white-space: pre;
  }

  @keyframes pulse {
    0%,
    100% {
      opacity: 1;
    }

    50% {
      opacity: 0.45;
    }
  }
</style>
