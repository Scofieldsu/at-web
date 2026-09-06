<template>
  <a-card class="theme-card">
    <template #title>
      <div class="hdr">
        <span class="sec-title tint-green"><GlobalOutlined />代理状态</span>
        <a-button :loading="loading" size="small" @click="loadStatus">刷新</a-button>
      </div>
    </template>

    <a-descriptions :column="2" bordered>
      <a-descriptions-item label="运行状态">
        <a-tag :color="status.running ? 'success' : 'default'">
          {{ status.running ? '运行中' : '已停止' }}
        </a-tag>
      </a-descriptions-item>
      <a-descriptions-item label="是否本服务管理">
        <a-tag :color="status.managed ? 'success' : 'warning'">
          {{ status.managed ? '是' : '外部启动 / 否' }}
        </a-tag>
      </a-descriptions-item>
      <a-descriptions-item label="规则数">{{ status.rules_count ?? '-' }}</a-descriptions-item>
      <a-descriptions-item label="PID">{{ status.pid ?? '-' }}</a-descriptions-item>
      <a-descriptions-item label="API 地址" :span="2">{{ status.url || '-' }}</a-descriptions-item>
    </a-descriptions>

    <div class="actions">
      <a-button type="primary" :loading="acting" :disabled="status.running" @click="act('start')">启动</a-button>
      <a-button type="warning" :loading="acting" @click="act('restart')">重启</a-button>
      <a-button type="danger" :loading="acting" :disabled="!status.running" @click="act('stop')">停止</a-button>
      <a-checkbox v-model:checked="setSystemProxy" style="margin-left:12px">同时设置系统代理</a-checkbox>
    </div>
  </a-card>

  <a-card class="theme-card" style="margin-top:16px">
    <template #title>
      <div class="hdr">
        <span class="sec-title tint-blue"><ApiOutlined />活跃 WebSocket 连接</span>
        <a-button :loading="loadingFlows" size="small" @click="loadFlows">刷新</a-button>
      </div>
    </template>
    <a-table
      :data-source="flows"
      :columns="flowColumns"
      row-key="flow_id"
      :pagination="false"
      :scroll="{ y: 320 }"
      class="theme-table"
      :locale="{ emptyText: '暂无活跃连接' }"
    />
  </a-card>
</template>

<script lang="ts" setup>
  defineOptions({ name: 'Proxy' });
import { ref, onMounted } from 'vue'
import { message } from 'ant-design-vue'
import { ApiOutlined, GlobalOutlined } from '@ant-design/icons-vue'
import http from '@/api/platform/http'

const status = ref<any>({})
const flows = ref<any[]>([])
const loading = ref(false)
const loadingFlows = ref(false)
const acting = ref(false)
const setSystemProxy = ref(true)

const flowColumns = [
  { title: 'Flow ID', dataIndex: 'flow_id', key: 'flow_id', minWidth: 220 },
  { title: 'URL', dataIndex: 'url', key: 'url', minWidth: 360 },
]

async function loadStatus() {
  loading.value = true
  try {
    const { data } = await http.get('/proxy/status')
    status.value = data
  } catch (e: any) {
    message.error(e.response?.data?.error || '获取代理状态失败')
  } finally {
    loading.value = false
  }
}

async function loadFlows() {
  loadingFlows.value = true
  try {
    const { data } = await http.get('/proxy/flows')
    flows.value = Array.isArray(data) ? data : []
  } catch (e: any) {
    message.error('获取连接列表失败')
  } finally {
    loadingFlows.value = false
  }
}

async function act(kind: string) {
  acting.value = true
  try {
    const body = kind === 'stop'
      ? { restore_system_proxy: setSystemProxy.value }
      : { set_system_proxy: setSystemProxy.value }
    const { data } = await http.post(`/proxy/${kind}`, body)
    if (data.success === false) {
      message.error(data.error || `${kind} 失败`)
    } else {
      message.success(`${kind} 成功`)
    }
    await loadStatus()
  } catch (e: any) {
    message.error(e.response?.data?.error || `${kind} 失败`)
  } finally {
    acting.value = false
  }
}

onMounted(() => {
  loadStatus()
  loadFlows()
})
</script>

<style scoped>
.hdr {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.actions {
  margin-top: 16px;
  display: flex;
  align-items: center;
}
.empty {
  color: var(--text-muted);
  padding: 12px;
}
</style>
