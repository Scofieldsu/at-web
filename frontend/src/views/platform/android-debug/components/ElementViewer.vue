<template>
  <div class="element-viewer">
    <!-- 设备选择器 -->
    <div class="device-switcher">
      <span class="switcher-label">当前操作设备：</span>
      <a-radio-group
        :value="activeDevice"
        button-style="solid"
        @change="(e) => $emit('update:activeDevice', e.target.value)"
      >
        <a-radio-button :value="1" :disabled="!online1">
          设备 1 {{ online1 ? '✓' : '✗' }}
        </a-radio-button>
        <a-radio-button :value="2" :disabled="!online2">
          设备 2 {{ online2 ? '✓' : '✗' }}
        </a-radio-button>
      </a-radio-group>
    </div>

    <a-row :gutter="16">
      <!-- 左侧：XML 树 -->
      <a-col :span="10">
        <a-card title="📋 UI 层级树" size="small" :bordered="false" class="tree-card">
          <template #extra>
            <a-button type="primary" size="small" :loading="dumping" :disabled="!currentOnline" @click="dump">
              <template #icon><ReloadOutlined /></template>
              Dump
            </a-button>
          </template>

          <a-input-search
            v-model:value="search"
            size="small"
            placeholder="搜索 text/id/class"
            style="margin-bottom: 12px"
          />

          <div class="tree-wrapper">
            <a-tree
              v-if="treeData.length"
              :tree-data="filteredTree"
              :selected-keys="selectedKeys"
              :expanded-keys="expandedKeys"
              show-line
              @select="onSelect"
              @expand="onExpand"
            >
              <template #title="{ title }">
                <span v-html="highlightMatch(title)" />
              </template>
            </a-tree>
            <a-empty v-else description="点击 Dump 获取 UI 树" :image="Empty.PRESENTED_IMAGE_SIMPLE" />
          </div>

          <a-divider style="margin: 12px 0" />
          <a-row :gutter="16">
            <a-col :span="12">
              <a-statistic
                title="节点总数"
                :value="summary.total"
                :value-style="{ fontSize: '16px', color: '#1890ff' }"
              />
            </a-col>
            <a-col :span="12">
              <a-statistic
                title="可点击"
                :value="summary.clickable"
                :value-style="{ fontSize: '16px', color: '#52c41a' }"
              />
            </a-col>
          </a-row>
        </a-card>
      </a-col>

      <!-- 右侧：属性面板 -->
      <a-col :span="14">
        <a-card title="📝 节点属性" size="small" :bordered="false" class="attr-card">
          <template #extra>
            <a-button v-if="node" size="small" type="primary" @click="copySelector">
              <template #icon><CopyOutlined /></template>
              复制 Selector
            </a-button>
          </template>

          <div v-if="node" class="attr-content">
            <a-descriptions size="small" :column="1" bordered>
              <a-descriptions-item label="resource-id">
                <a-typography-text copyable code>
                  {{ node.attrs['resource-id'] || '-' }}
                </a-typography-text>
              </a-descriptions-item>
              <a-descriptions-item label="class">
                {{ node.attrs.class || '-' }}
              </a-descriptions-item>
              <a-descriptions-item label="text">
                {{ node.attrs.text || '-' }}
              </a-descriptions-item>
              <a-descriptions-item label="content-desc">
                {{ node.attrs['content-desc'] || '-' }}
              </a-descriptions-item>
              <a-descriptions-item label="bounds">
                {{ fmtBounds(node.bounds) }}
              </a-descriptions-item>
              <a-descriptions-item label="clickable">
                <a-tag :color="node.attrs.clickable === 'true' ? 'green' : 'default'" size="small">
                  {{ node.attrs.clickable }}
                </a-tag>
              </a-descriptions-item>
              <a-descriptions-item label="enabled">
                <a-tag :color="node.attrs.enabled === 'true' ? 'green' : 'default'" size="small">
                  {{ node.attrs.enabled }}
                </a-tag>
              </a-descriptions-item>
              <a-descriptions-item label="checkable">
                <a-tag :color="node.attrs.checkable === 'true' ? 'blue' : 'default'" size="small">
                  {{ node.attrs.checkable || 'false' }}
                </a-tag>
              </a-descriptions-item>
            </a-descriptions>

            <a-divider>🎯 Selector 生成器</a-divider>
            <a-alert
              message="以下是根据节点属性自动生成的 uiautomator2 定位代码"
              type="info"
              show-icon
              style="margin-bottom: 12px"
            >
              <template #icon>
                <InfoCircleOutlined style="color: #1890ff" />
              </template>
            </a-alert>
            <a-textarea
              :value="selector"
              :rows="10"
              readonly
              class="selector-code"
            />
          </div>
          <a-empty v-else description="选择一个节点查看属性" :image="Empty.PRESENTED_IMAGE_SIMPLE" />
        </a-card>
      </a-col>
    </a-row>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue';
import { message, Empty } from 'ant-design-vue';
import { ReloadOutlined, CopyOutlined, InfoCircleOutlined } from '@ant-design/icons-vue';
import { useAndroidDemo } from '../demo/store';

const props = defineProps<{
  device1: string;
  device2: string;
  online1?: boolean;
  online2?: boolean;
  activeDevice: 1 | 2;
}>();

const emit = defineEmits<{
  'update:activeDevice': [value: 1 | 2];
  select: [bounds: number[]];
}>();

const demo = useAndroidDemo();

const dumping = ref(false);
const treeData = ref<any[]>([]);
const nodeMap = ref<Map<string, any>>(new Map());
const selectedKeys = ref<string[]>([]);
const expandedKeys = ref<string[]>([]);
const search = ref('');
const summary = ref({ total: 0, clickable: 0 });

const currentDevice = computed(() => (props.activeDevice === 1 ? props.device1 : props.device2));
const currentOnline = computed(() => (props.activeDevice === 1 ? props.online1 : props.online2));

const node = computed(() => {
  const k = selectedKeys.value[0];
  return k ? nodeMap.value.get(k) : null;
});

const selector = computed(() => {
  if (!node.value) return '';
  const n = node.value;
  const lines: string[] = [];
  const rid = n.attrs['resource-id'];
  if (rid) lines.push(`# 按 resource-id\nd(resourceId="${rid.split(':id/').pop()}")`);
  const text = n.attrs.text;
  if (text) lines.push(`# 按 text\nd(text="${text}")`);
  const desc = n.attrs['content-desc'];
  if (desc) lines.push(`# 按 content-desc\nd(description="${desc}")`);
  const cls = n.attrs.class;
  if (cls && text) lines.push(`# 按 class + text\nd(className="${cls}", text="${text}")`);
  return lines.join('\n\n') || '# 无明显特征，建议用坐标或结构化定位';
});

const filteredTree = computed(() => {
  if (!search.value) return treeData.value;
  const kw = search.value.toLowerCase();
  return filterTree(treeData.value, kw);
});

function dump() {
  if (!currentOnline.value) {
    message.warning('请先连接设备');
    return;
  }
  dumping.value = true;
  // 模拟一次 dump_hierarchy 的耗时
  window.setTimeout(() => {
    const res = demo.dump(currentDevice.value);
    summary.value = { total: res.summary.total, clickable: res.summary.clickable };
    if (res.tree) {
      const { tree, map } = buildTree(res.tree);
      treeData.value = [tree];
      nodeMap.value = map;
      selectedKeys.value = [];
      expandedKeys.value = [tree.key];
      message.success('UI 树已刷新（演示）');
      dumping.value = false;
    } else {
      dumping.value = false;
      message.error('Dump 失败');
    }
  }, 350);
}

function buildTree(root: any) {
  const map = new Map<string, any>();
  let seq = 0;

  function walk(n: any, prefix: string): any {
    const key = `${prefix}-${seq++}`;
    const cls = (n.attrs.class || '').split('.').pop() || 'node';
    const text = n.attrs.text || '';
    const rid = (n.attrs['resource-id'] || '').split(':id/').pop() || '';
    const title = `${cls}${text ? ` "${text}"` : ''}${rid ? ` #${rid}` : ''}`;
    const children = (n.children || []).map((c: any) => walk(c, key));
    map.set(key, n);
    return { key, title, children };
  }

  const tree = walk(root, '0');
  return { tree, map };
}

function filterTree(nodes: any[], kw: string): any[] {
  return nodes
    .map((n) => {
      const match = n.title.toLowerCase().includes(kw);
      const children = filterTree(n.children || [], kw);
      if (match || children.length) return { ...n, children };
      return null;
    })
    .filter(Boolean);
}

function highlightMatch(title: string): string {
  if (!search.value) return title;
  const re = new RegExp(`(${escapeRegex(search.value)})`, 'gi');
  return title.replace(re, '<mark>$1</mark>');
}

function escapeRegex(s: string): string {
  return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

function onSelect(keys: string[]) {
  selectedKeys.value = keys;
  if (keys.length && node.value?.bounds) {
    emit('select', node.value.bounds);
  } else {
    emit('select', []);
  }
}

function onExpand(keys: string[]) {
  expandedKeys.value = keys;
}

function copySelector() {
  if (!selector.value) return;
  navigator.clipboard.writeText(selector.value).then(
    () => message.success('已复制到剪贴板'),
    () => message.error('复制失败'),
  );
}

function fmtBounds(b: number[]): string {
  if (!b || b.length !== 4) return '-';
  return `[${b[0]},${b[1]}][${b[2]},${b[3]}]`;
}
</script>

<style scoped lang="less">
.element-viewer {
  padding: 20px;
}

.device-switcher {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 20px;
  padding: 12px 16px;
  background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%);
  border-radius: 8px;
  border-left: 4px solid #2196f3;

  .switcher-label {
    font-weight: 500;
    color: #1976d2;
  }
}

.tree-card,
.attr-card {
  border: 1px solid #e8e8e8;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);

  :deep(.ant-card-head) {
    background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
    border-bottom: 2px solid #1890ff;
    min-height: 42px;
    padding: 0 16px;

    .ant-card-head-title {
      font-weight: 600;
      font-size: 14px;
      padding: 10px 0;
    }
  }

  :deep(.ant-card-body) {
    padding: 16px;
  }
}

.tree-wrapper {
  max-height: 480px;
  overflow: auto;
  border: 1px solid #f0f0f0;
  border-radius: 6px;
  padding: 12px;
  background: #fafafa;

  :deep(mark) {
    background: #ffe58f;
    padding: 1px 3px;
    border-radius: 2px;
  }
}

.attr-content {
  max-height: 600px;
  overflow: auto;
}

.selector-code {
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
  font-size: 13px;
  line-height: 1.6;
  background: #f5f5f5;
  border: 1px solid #d9d9d9;
}
</style>
