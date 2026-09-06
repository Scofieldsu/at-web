<template>
  <a-card class="theme-card">
    <template #title>
      <div class="hdr">
        <span class="sec-title tint-indigo"><ControlOutlined />规则管理</span>
        <div>
          <a-button :loading="loading" size="small" @click="load">刷新</a-button>
          <a-button type="primary" size="small" @click="openAdd">新增规则</a-button>
          <a-button danger size="small" :disabled="!rules.length" @click="clearAll">清空</a-button>
        </div>
      </div>
    </template>

    <a-table
      :data-source="rules"
      :columns="columns"
      :pagination="false"
      row-key="id"
      bordered
      size="small"
      class="theme-table"
      :scroll="{ y: 360 }"
      :locale="{ emptyText: '暂无规则。代理需先启动，规则才会生效。' }"
    >
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'direction'">
          {{ dirLabel(record.direction) }}
        </template>
        <template v-else-if="column.key === 'match'">
          <span v-if="record.match_field">
            {{ record.match_field }} = {{ record.match_value ?? record.match_regex ?? '*' }}
          </span>
          <span v-else class="muted">全部</span>
        </template>
        <template v-else-if="column.key === 'enabled'">
          <a-tag :color="record.enabled === false ? 'default' : 'success'">
            {{ record.enabled === false ? '否' : '是' }}
          </a-tag>
        </template>
        <template v-else-if="column.key === 'action_buttons'">
          <a-button size="small" @click="openEdit(record)">修改</a-button>
          <a-button size="small" danger @click="remove(record)">删除</a-button>
        </template>
      </template>
    </a-table>
  </a-card>

  <!-- 新增 / 修改弹窗 -->
  <a-modal v-model:open="dialogVisible" :title="editing ? '修改规则' : '新增规则'" width="560px">
    <a-form :model="form" :label-col="{ style: { width: '110px' } }" label-align="left">
      <a-form-item label="名称">
        <a-input v-model:value="form.name" placeholder="规则名称" />
      </a-form-item>
      <a-form-item label="方向">
        <a-select v-model:value="form.direction" placeholder="选择方向" style="width:100%">
          <a-select-option value="client_to_server">客户端 → 服务端</a-select-option>
          <a-select-option value="server_to_client">服务端 → 客户端</a-select-option>
        </a-select>
      </a-form-item>
      <a-form-item label="匹配字段">
        <a-input v-model:value="form.match_field" placeholder="JSON 路径，如 data.type" />
      </a-form-item>
      <a-form-item label="匹配值">
        <a-input v-model:value="form.match_value" placeholder="精确匹配值（与正则二选一）" />
      </a-form-item>
      <a-form-item label="匹配正则">
        <a-input v-model:value="form.match_regex" placeholder="正则匹配（可选）" />
      </a-form-item>
      <a-form-item label="动作">
        <a-select v-model:value="form.action" style="width:100%">
          <a-select-option value="modify">modify（修改字段）</a-select-option>
          <a-select-option value="replace">replace（替换整体）</a-select-option>
          <a-select-option value="drop">drop（丢弃）</a-select-option>
          <a-select-option value="delay">delay（延迟）</a-select-option>
        </a-select>
      </a-form-item>
      <template v-if="form.action === 'modify'">
        <a-form-item label="修改字段">
          <a-input v-model:value="form.modify_field" placeholder="如 data.msg_list" />
        </a-form-item>
        <a-form-item label="修改值(JSON)">
          <a-textarea v-model:value="form.modify_value_raw" :rows="3"
                    placeholder='字符串或 JSON，如 "hello" 或 [{"content":"x"}]' />
        </a-form-item>
      </template>
      <template v-if="form.action === 'replace'">
        <a-form-item label="替换体(JSON)">
          <a-textarea v-model:value="form.replace_body_raw" :rows="3"
                    placeholder='整体替换的 JSON，如 {"type":"fake"}' />
        </a-form-item>
      </template>
      <a-form-item v-if="form.action === 'delay'" label="延迟(ms)">
        <a-input v-model:value.number="form.delay_ms" type="number" placeholder="毫秒" />
      </a-form-item>
      <a-form-item label="启用">
        <a-switch v-model:checked="form.enabled" />
      </a-form-item>
    </a-form>
    <template #footer>
      <a-button @click="dialogVisible = false">取消</a-button>
      <a-button type="primary" :loading="saving" @click="save">保存</a-button>
    </template>
  </a-modal>
</template>

<script lang="ts" setup>
import { ref, onMounted } from 'vue'
import { message, Modal } from 'ant-design-vue'
import { ControlOutlined } from '@ant-design/icons-vue'
import http from '@/api/platform/http'

const columns = [
  { title: '名称', dataIndex: 'name', key: 'name', minWidth: 120 },
  { title: '方向', key: 'direction', width: 150 },
  { title: '匹配', key: 'match', minWidth: 180 },
  { title: '动作', dataIndex: 'action', key: 'action_type', width: 100 },
  { title: '启用', key: 'enabled', width: 80 },
  { title: '操作', key: 'action_buttons', width: 140, fixed: 'right' },
]

const rules = ref<any[]>([])
const loading = ref(false)
const saving = ref(false)
const dialogVisible = ref(false)
const editing = ref(false)
const editingId = ref('')

const emptyForm = () => ({
  name: '', direction: 'server_to_client', match_field: '', match_value: '',
  match_regex: '', action: 'modify', modify_field: '', modify_value_raw: '',
  replace_body_raw: '', delay_ms: 0, enabled: true,
})
const form = ref<any>(emptyForm())

function dirLabel(d: any) {
  return { client_to_server: '客户端→服务端', server_to_client: '服务端→客户端' }[d] || '全部'
}

async function load() {
  loading.value = true
  try {
    const { data } = await http.get('/proxy/rules')
    rules.value = Array.isArray(data) ? data : []
  } catch (e) {
    message.error('获取规则失败，代理可能未启动')
  } finally {
    loading.value = false
  }
}

function openAdd() {
  editing.value = false
  editingId.value = ''
  form.value = emptyForm()
  dialogVisible.value = true
}

function openEdit(row: any) {
  editing.value = true
  editingId.value = row.id
  form.value = {
    name: row.name || '',
    direction: row.direction || 'server_to_client',
    match_field: row.match_field || '',
    match_value: row.match_value ?? '',
    match_regex: row.match_regex ?? '',
    action: row.action || 'modify',
    modify_field: row.modify_field || '',
    modify_value_raw: row.modify_value !== undefined ? toRaw(row.modify_value) : '',
    replace_body_raw: row.replace_body !== undefined ? toRaw(row.replace_body) : '',
    delay_ms: row.delay_ms || 0,
    enabled: row.enabled !== false,
  }
  dialogVisible.value = true
}

function toRaw(v: any) {
  if (v == null) return ''
  return typeof v === 'string' ? v : JSON.stringify(v)
}

// 尝试 JSON 解析，失败则当作纯字符串
function parseValue(raw: any) {
  if (raw === '' || raw == null) return undefined
  try {
    return JSON.parse(raw)
  } catch {
    return raw
  }
}

function buildPayload() {
  const f = form.value
  const payload: any = {
    name: f.name,
    direction: f.direction,
    action: f.action,
    enabled: f.enabled,
  }
  if (f.match_field) payload.match_field = f.match_field
  if (f.match_value !== '') payload.match_value = f.match_value
  if (f.match_regex !== '') payload.match_regex = f.match_regex
  if (f.action === 'modify') {
    payload.modify_field = f.modify_field
    payload.modify_value = parseValue(f.modify_value_raw)
  } else if (f.action === 'replace') {
    payload.replace_body = parseValue(f.replace_body_raw)
  } else if (f.action === 'delay') {
    payload.delay_ms = Number(f.delay_ms) || 0
  }
  return payload
}

async function save() {
  if (!form.value.name) {
    message.warning('请填写规则名称')
    return
  }
  saving.value = true
  try {
    const payload = buildPayload()
    if (editing.value) {
      await http.put(`/proxy/rules/${editingId.value}`, payload)
      message.success('规则已修改')
    } else {
      await http.post('/proxy/rules', payload)
      message.success('规则已新增')
    }
    dialogVisible.value = false
    await load()
  } catch (e: any) {
    message.error(e.response?.data?.error || '保存失败')
  } finally {
    saving.value = false
  }
}

async function remove(row: any) {
  Modal.confirm({
    title: '提示',
    content: `确认删除规则「${row.name || row.id}」？`,
    onOk: async () => {
      try {
        await http.delete(`/proxy/rules/${row.id}`)
        message.success('已删除')
        await load()
      } catch (e: any) {
        message.error(e.response?.data?.error || '删除失败')
      }
    },
  })
}

async function clearAll() {
  Modal.confirm({
    title: '提示',
    content: '确认清空所有规则？',
    onOk: async () => {
      try {
        await http.post('/proxy/rules/clear')
        message.success('已清空')
        await load()
      } catch (e: any) {
        message.error(e.response?.data?.error || '清空失败')
      }
    },
  })
}

onMounted(load)
defineExpose({ load })
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
</style>
