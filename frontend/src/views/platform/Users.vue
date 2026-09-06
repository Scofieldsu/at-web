<template>
  <a-row :gutter="16">
    <!-- 创建用户 -->
    <a-col :span="12">
      <a-card class="theme-card">
        <template #title>
          <div class="hdr">
            <span class="sec-title tint-blue"><UserAddOutlined />创建浏览器用户</span>
          </div>
        </template>
        <a-alert
          type="info"
          :closable="false"
          show-icon
          style="margin-bottom: 14px"
          message="启动 Chrome 浏览器实例并自动登录（凭证模式读 accounts.yaml 的端口+密码自动填入；扫码模式弹二维码人工扫码）。"
        />

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
    </a-col>

    <!-- 已创建用户列表 -->
    <a-col :span="12">
      <a-card class="theme-card">
        <template #title>
          <div class="hdr">
            <span class="sec-title tint-green"><UsergroupAddOutlined />已创建的用户</span>
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
              <a-tag :color="record.logged_in ? 'success' : 'error'">
                {{ record.logged_in ? '在线' : '离线' }}
              </a-tag>
            </template>
            <template v-else-if="column.key === 'platform'">
              {{ platformLabel(record.platform_type) }}
            </template>
          </template>
        </a-table>
      </a-card>
    </a-col>
  </a-row>
</template>

<script lang="ts" setup>
  defineOptions({ name: 'CreateUsers' });
  import { ref, reactive, onMounted } from 'vue';
  import { UserAddOutlined, UsergroupAddOutlined } from '@ant-design/icons-vue';
  import { message } from 'ant-design-vue';
  import http from '@/api/platform/http';

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
    { title: '端口', dataIndex: 'port', key: 'port', width: 100 },
    { title: '用户名', dataIndex: 'username', key: 'username', ellipsis: true },
    { title: '平台', key: 'platform', width: 100 },
    { title: '在线状态', key: 'logged_in', width: 100 },
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
      // 先扫描已存在的浏览器（页面刷新恢复）
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

  onMounted(loadUsers);
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
  max-height: 360px;
  overflow: auto;
  font-size: var(--vben-font-size-sm);
  white-space: pre-wrap;
  margin: 12px 0 0 0;
  line-height: 1.6;
}
.muted {
  color: var(--text-muted);
}
</style>
