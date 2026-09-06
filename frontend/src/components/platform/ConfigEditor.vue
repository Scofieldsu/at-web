<template>
  <div class="cfg">
    <!-- 左：文件列表 -->
    <a-card class="theme-card file-list">
      <template #title>
        <div class="hdr">
          <span class="sec-title tint-blue"><FolderOpenOutlined />config/ 配置文件</span>
          <div class="tools">
            <a-button :loading="restarting" size="small" danger @click="restartService">
              <ReloadOutlined /><span style="margin-left:4px">重启服务</span>
            </a-button>
            <a-button :loading="loadingList" size="small" @click="loadFiles">刷新</a-button>
          </div>
        </div>
      </template>
      <!-- 按真实子文件夹层级展示；文件夹带主题色 logo -->
      <a-tree
        v-if="dirTree.length"
        class="cfg-tree"
        :tree-data="dirTree"
        :field-names="{ title: 'name', key: 'key', children: 'children' }"
        default-expand-all
        :selected-keys="selectedKeys"
        @select="onTreeSelect"
      >
        <template #title="node">
          <span v-if="node.type === 'dir'" class="tn-row tn-dir">
            <FolderFilled class="dir-icon" :style="{ color: node.color }" />
            <span class="dir-name">{{ node.name }}</span>
          </span>
          <span v-else class="tn-row tn-file">
            <FileOutlined class="fi-icon" />
            <span class="fi-path">{{ node.name }}</span>
            <a-tag v-if="!node.editable" size="small" color="default">只读</a-tag>
          </span>
        </template>
      </a-tree>
      <div v-if="!dirTree.length && !loadingList" class="muted pad">config/ 下暂无文件</div>
    </a-card>

    <!-- 右：编辑区 -->
    <a-card class="theme-card editor-area">
      <template #title>
        <div class="hdr">
          <span v-if="current" class="cur-path sec-title tint-blue"><EditOutlined />{{ current }}</span>
          <span v-else class="muted">未选择文件</span>
          <a-tag v-if="editorLabel" color="blue" size="small" class="mode-tag">{{ editorLabel }}</a-tag>
          <div class="tools">
            <a-upload :show-upload-list="false" :before-upload="onBeforeUpload" :disabled="!current">
              <a-button size="small" :disabled="!current" title="上传同名文件覆盖（旧文件自动备份为 .old）">
                <UploadOutlined /><span style="margin-left:4px">上传覆盖</span>
              </a-button>
            </a-upload>
            <a-button size="small" :loading="loadingFile" :disabled="!current || !editable" @click="reloadFile">
              重新加载
            </a-button>
            <a-button type="primary" size="small" :loading="saving"
                       :disabled="!current || !editable || !dirty" @click="save">
              保存
            </a-button>
          </div>
        </div>
      </template>

      <template v-if="current">
        <a-alert v-if="!editable" type="info" :closable="false" show-icon
                  message="该文件类型不支持在线编辑，仅可通过「上传覆盖」替换。" style="margin-bottom:10px" />
        <a-alert v-else-if="dirty" type="warning" :closable="false" show-icon class="warn-tip"
                  message="有未保存的修改。部分配置（端口、代理）需重启服务后生效。" style="margin-bottom:10px" />
        <CodeEditor v-if="editable" :value="raw" :mode="editorMode" bordered
                   class="code-editor" @change="onRawChange" />
      </template>
      <div v-else class="muted pad">从左侧选择一个配置文件进行查看 / 编辑</div>
    </a-card>
  </div>
</template>

<script lang="ts" setup>
import { ref, computed, onMounted } from 'vue'
import { message, Modal } from 'ant-design-vue'
import { FileOutlined, UploadOutlined, FolderOpenOutlined, EditOutlined, ReloadOutlined, FolderFilled } from '@ant-design/icons-vue'
import { CodeEditor, MODE } from '@/components/CodeEditor'
import http from '@/api/platform/http'

const files = ref<any[]>([])
const loadingList = ref(false)

// ── 目录树：按真实子文件夹层级展开，文件夹带主题色 logo ──
// 顶层文件夹固定配色（系统语义色系），深层继承顶层色；未知目录按顺序回退调色板
const TOP_DIR_COLORS: Record<string, string> = {
  accounts: '#06b6d4',
  main: '#6366f1',
  rpa: '#0090ff',
  phrases: '#30a46c',
  proxy: '#f76b15',
}
const DIR_FALLBACK_COLORS = ['#6366f1', '#0090ff', '#30a46c', '#f76b15', '#06b6d4', '#7c3aed']
const selectedKeys = ref<string[]>([])

const dirTree = computed(() => {
  const root: any[] = []
  const map = new Map<string, any>() // 目录 key → 节点
  for (const f of files.value) {
    const segs = f.path.split('/')
    let list = root
    let acc = ''
    segs.forEach((seg, i) => {
      acc = acc ? `${acc}/${seg}` : seg
      if (i < segs.length - 1) {
        let node = map.get(acc)
        if (!node) {
          node = { type: 'dir', name: seg, key: acc, children: [] }
          map.set(acc, node)
          list.push(node)
        }
        list = node.children
      } else {
        list.push({
          type: 'file',
          name: seg,
          path: f.path,
          key: `file:${f.path}`,
          editable: f.editable,
          entry: f,
        })
      }
    })
  }
  // 顶层目录取固定主题色（无匹配则按出现顺序回退）；深层目录继承所在顶层目录色
  const paint = (nodes: any[], parentColor?: string) => {
    nodes.forEach((n) => {
      if (n.type !== 'dir') return
      n.color =
        parentColor ||
        TOP_DIR_COLORS[n.name] ||
        DIR_FALLBACK_COLORS[root.indexOf(n) % DIR_FALLBACK_COLORS.length]
      paint(n.children, n.color)
    })
  }
  paint(root)
  return root
})

function onTreeSelect(_keys: any[], info: any) {
  const node = info?.node
  if (!node || node.type !== 'file') return
  selectedKeys.value = [node.key]
  selectFile(node.entry)
}

const current = ref('')        // 当前选中的相对路径
const editable = ref(false)
const raw = ref('')
const original = ref('')
const dirty = ref(false)
const loadingFile = ref(false)
const saving = ref(false)
const restarting = ref(false)

// 根据文件后缀选择编辑器模式
const editorMode = computed(() => {
  const name = current.value.toLowerCase()
  if (name.endsWith('.json')) return MODE.JSON
  if (name.endsWith('.yaml') || name.endsWith('.yml')) return MODE.YAML
  return MODE.JSON  // 默认
})

const editorLabel = computed(() => {
  const name = current.value.toLowerCase()
  if (name.endsWith('.json')) return 'JSON'
  if (name.endsWith('.yaml') || name.endsWith('.yml')) return 'YAML'
  return ''
})

function onRawChange(val: string) {
  raw.value = val
  dirty.value = true
}

async function loadFiles() {
  loadingList.value = true
  try {
    const { data } = await http.get('/config/files')
    files.value = data.files || []
  } catch {
    message.error('读取配置文件列表失败')
  } finally {
    loadingList.value = false
  }
}

async function selectFile(f: any) {
  if (dirty.value) {
    const ok = await new Promise<boolean>((resolve) => {
      Modal.confirm({
        title: '提示',
        content: '当前文件有未保存的修改，切换将丢失，确定继续？',
        onOk: () => resolve(true),
        onCancel: () => resolve(false),
      })
    })
    if (!ok) return
  }
  current.value = f.path
  editable.value = f.editable
  raw.value = ''
  original.value = ''
  dirty.value = false
  if (f.editable) await reloadFile()
}

async function reloadFile() {
  if (!current.value) return
  loadingFile.value = true
  try {
    const { data } = await http.get('/config/file', { params: { path: current.value } })
    raw.value = data.raw || ''
    original.value = data.raw || ''
    editable.value = data.editable !== false
    dirty.value = false
  } catch (e: any) {
    message.error(e.response?.data?.error || '读取文件失败')
  } finally {
    loadingFile.value = false
  }
}

async function save() {
  saving.value = true
  try {
    const { data } = await http.put('/config/file', { path: current.value, raw: raw.value })
    if (data.success) {
      original.value = raw.value
      dirty.value = false
      message.success(data.note || '已保存')
    } else {
      message.error(data.error || '保存失败')
    }
  } catch (e: any) {
    message.error(e.response?.data?.error || '保存失败（请检查语法）')
  } finally {
    saving.value = false
  }
}

// 上传覆盖：不自动上传，拿到文件后手动 POST，便于带上目标 path
async function onBeforeUpload(file: File) {
  if (!current.value) return false
  const form = new FormData()
  form.append('file', file)
  form.append('path', current.value)
  try {
    const { data } = await http.post('/config/upload', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    if (data.success) {
      message.success(data.note || '已覆盖')
      await loadFiles()
      if (editable.value) await reloadFile()
    } else {
      message.error(data.error || '上传失败')
    }
  } catch (e: any) {
    message.error(e.response?.data?.error || '上传失败')
  }
  return false
}

onMounted(loadFiles)

/** 重启本机服务让配置文件改动生效（纯重启：不拉代码/不构建，停 run_all 再拉起） */
function restartService() {
  const unsaved = dirty.value
    ? '当前文件还有未保存的修改，重启不会触发保存，未保存的修改将丢失。\n'
    : ''
  Modal.confirm({
    title: '重启服务？',
    content: `${unsaved}将停止并重新拉起本机服务（run_all.py），使已保存的配置生效。\n服务重启约需数秒，期间页面会短暂断连，恢复后请刷新页面。`,
    okText: '重启',
    okButtonProps: { danger: true },
    cancelText: '取消',
    onOk: async () => {
      restarting.value = true
      try {
        const { data } = await http.post('/machines/restart')
        if (data.success) {
          Modal.success({
            title: '重启已触发',
            content: '服务将在数秒内自动恢复，恢复后请刷新页面确认新配置已生效。',
          })
        } else {
          message.error(data.error || '重启失败')
        }
      } catch (e: any) {
        message.error(e?.response?.data?.error || '重启失败（请确认服务以管理员权限运行）')
      } finally {
        restarting.value = false
      }
    },
  })
}
</script>

<style scoped>
.cfg {
  display: grid;
  grid-template-columns: 360px minmax(0, 1fr);
  grid-template-rows: 1fr;
  gap: 16px;
  height: 100%;
  min-height: 0;
}
.file-list,
.editor-area {
  min-width: 0;
  min-height: 0;
}
/* 左侧配置文件结构：不设卡内强制滚动，紧凑行高让全部文件可见、无竖向滚动条 */
.file-list {
  overflow: hidden;
}
.hdr {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.tools {
  display: flex;
  align-items: center;
  gap: 8px;
}
.cur-path {
  font-family: monospace;
  font-weight: 600;
  color: var(--text-primary);
}
/* 未保存提示：系统 warning 语义色（浅橙底 + 橙色边框 + 同色感叹号） */
.warn-tip.ant-alert-warning {
  background: rgba(247, 107, 21, 0.06) !important;
  border: 1px solid rgba(247, 107, 21, 0.25) !important;
}
.warn-tip :deep(.ant-alert-icon) {
  color: var(--warning-color, #f76b15) !important;
}
/* 左栏目录树（按真实子文件夹层级 + 文件夹彩色 logo） */
.cfg-tree {
  background: transparent;
}
.cfg-tree :deep(.ant-tree-node-content-wrapper) {
  display: inline-flex;
  align-items: center;
  min-width: 0;
  min-height: 22px;
  line-height: 22px;
  padding: 0 4px;
  font-size: 13px;
}
/* 紧凑行距：压缩树节点默认上下内边距，容纳更多文件而不出现竖向滚动条 */
.cfg-tree :deep(.ant-tree-treenode) {
  padding: 0 !important;
}
.cfg-tree :deep(.ant-tree-node-content-wrapper.ant-tree-node-selected) {
  background: rgba(99, 102, 241, 0.12);
}
.cfg-tree :deep(.ant-tree-treenode-selected .tn-file .fi-path) {
  color: var(--accent);
  font-weight: 500;
}
.tn-row {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  width: 100%;
  overflow: hidden;
}
.dir-icon {
  font-size: 15px;
  flex-shrink: 0;
}
.dir-name {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-weight: 600;
  color: var(--text-primary);
}
.fi-icon {
  color: var(--text-muted);
  flex-shrink: 0;
}
.fi-path {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--text-secondary);
}
.muted {
  color: var(--text-muted);
}
.pad {
  padding: 12px;
}
.yaml-editor :deep(.ant-input) {
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 13px;
  line-height: 1.6;
}
.mode-tag {
  flex-shrink: 0;
  font-weight: 600;
  margin-left: 8px;
}
/* CodeEditor 自带 h-full 类，这里用 !important 压过 Tailwind 的 height:100%，
   由 card body 的 flex 分配剩余空间，避免和外层各算一套 vh 导致底部溢出。 */
.code-editor {
  flex: 1 1 auto !important;
  height: auto !important;
  min-height: 0;
  border: 1px solid var(--border-color);
  border-radius: 6px;
  overflow: hidden;
}
/* CodeEditor.vue 内层包装（div.h-full）需撑满，否则 CodeMirror 拿不到高度 */
.code-editor > :deep(*) {
  height: 100%;
}
/* CodeMirror 默认 height:300px，需覆盖为 100% 才能随容器铺满。
   注意：本文件是纯 CSS scoped，:deep() 不能写在嵌套块里，
   否则编译出的选择器会把 data-v 属性插到中间层而失效。 */
.code-editor :deep(.CodeMirror) {
  height: 100% !important;
}
/* CodeMirror 容器在 bordered 模式下带 ant-input class（模拟边框），
   全局 .ant-input 的 height:32px !important 会把它压成单行，这里还原为撑满父级 */
.code-editor :deep(.ant-input) {
  height: 100% !important;
}
/* JSON/YAML 语法高亮 token 配色：与系统语义色一致（键靛蓝/串绿/数橙/布尔紫/注释灰） */
.code-editor :deep(.cm-property),
.code-editor :deep(.cm-variable),
.code-editor :deep(.cm-variable-2),
.code-editor :deep(.cm-def) {
  color: #6366f1;
}
.code-editor :deep(.cm-string),
.code-editor :deep(.cm-string-2) {
  color: #2f9e6b;
}
.code-editor :deep(.cm-number) {
  color: #f76b15;
}
.code-editor :deep(.cm-atom) {
  color: #7c3aed;
}
.code-editor :deep(.cm-comment) {
  color: var(--text-muted, #9ca3af);
}
.code-editor :deep(.cm-keyword) {
  color: #0090ff;
}
.code-editor :deep(.cm-tag) {
  color: #e5484d;
}
.code-editor :deep(.cm-error) {
  color: #e5484d;
  text-decoration: underline dotted;
}
/* JSON 键名通常同时带 cm-string + cm-property 双类：显式压成键色（靛蓝），
   与字符串值（绿）区分开 —— 否则键和值同色会让整份 JSON 看起来没有高亮 */
.code-editor :deep(.cm-string.cm-property),
.code-editor :deep(.cm-property.cm-string) {
  color: #6366f1;
}
.editor-area {
  display: flex;
  flex-direction: column;
  height: 100%;
}
.editor-area :deep(.ant-card-body) {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
  padding-bottom: 12px;
}
.file-list {
  height: 100%;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  min-height: 0;
}
/* 左栏与右编辑区同高（.cfg 已撑满 100%），卡片体内滚动直达底部；
   不再用 vh 估高，避免不同分辨率/文件多时左栏高度与右栏不齐 */
.file-list :deep(.ant-card-body) {
  flex: 1;
  min-height: 0;
  overflow: auto;
  padding-bottom: 12px;
}
</style>
