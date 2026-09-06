<template>
  <div class="page">
    <a-card class="theme-card">
      <!-- 顶部控制栏 -->
      <div class="changelog-controls">
        <a-space size="large">
          <a-select
            v-model:value="selectedPlatform"
            style="width: 180px"
            @change="handlePlatformChange"
            :loading="platformsLoading"
          >
            <a-select-option
              v-for="p in platforms"
              :key="p.key"
              :value="p.key"
            >
              <span :style="{ color: platformColor(p.key) }">{{ p.label }}</span>
            </a-select-option>
          </a-select>

          <a-input-search
            v-model:value="keyword"
            placeholder="搜索版本号或内容关键词"
            style="width: 320px"
            allow-clear
          />
        </a-space>

        <div v-if="currentLabel" class="platform-title">
          <span :style="{ color: platformColor(selectedPlatform) }">{{ currentLabel }}</span>
          版本更新说明
        </div>
      </div>

      <!-- 加载状态 -->
      <div v-if="loading" class="loading-container">
        <a-spin size="large" />
      </div>

      <!-- 错误提示 -->
      <a-alert
        v-else-if="error"
        type="error"
        :message="error"
        show-icon
        style="margin-top: 20px"
      />

      <!-- 时间线 -->
      <a-timeline v-else-if="filteredEntries.length > 0" class="changelog-timeline">
        <a-timeline-item
          v-for="entry in filteredEntries"
          :key="entry.version"
        >
          <template #dot>
            <ClockCircleOutlined
              :style="{ fontSize: '16px', color: platformColor(selectedPlatform) }"
            />
          </template>

          <div class="changelog-item">
            <div class="version-header">
              <!-- 所有版本统一系统色（靛蓝 tint-indigo），时间统一青色；均不与平台色相同 -->
              <a-tag class="version-tag tint-indigo">
                {{ entry.version }}
              </a-tag>
              <span class="date-text">{{ entry.date }}</span>
            </div>

            <div class="content-wrapper">
              <div
                v-if="!entry.expanded"
                class="content-preview"
                @click="entry.expanded = true"
              >
                {{ getPreview(entry.content) }}
                <a class="expand-link">展开详情 ▼</a>
              </div>

              <div v-else class="content-full">
                <div v-html="formatContent(entry.content)"></div>
                <a class="collapse-link" @click="entry.expanded = false">
                  收起 ▲
                </a>
              </div>
            </div>
          </div>
        </a-timeline-item>
      </a-timeline>

      <!-- 空状态 -->
      <a-empty
        v-else
        description="暂无版本更新记录"
        style="margin-top: 60px"
      />
    </a-card>
  </div>
</template>

<script lang="ts" setup>
import { ref, computed, onMounted } from 'vue';
import { ClockCircleOutlined } from '@ant-design/icons-vue';
import { message } from 'ant-design-vue';
import { getPlatforms, getChangelog, type Platform, type ChangelogEntry } from '@/api/platform/changelog';
import Showdown from 'showdown';

// Markdown 转换器
const converter = new Showdown.Converter({
  tables: true,
  strikethrough: true,
  tasklists: true,
  simpleLineBreaks: true, // \n 转 <br>
});

// 平台配色与测试参数页/总览徽标一致（A #e5484d / B #0090ff / C #f76b15 / D #30a46c）
const PLATFORM_COLORS: Record<string, string> = {
  platform_a: '#e5484d',
  platform_b: '#0090ff',
  platform_c: '#f76b15',
  platform_d: '#30a46c',
};

function platformColor(key: string): string {
  return PLATFORM_COLORS[key] || 'var(--vben-primary)';
}

// 响应式数据
const platforms = ref<Platform[]>([]);
const platformsLoading = ref(false);
const selectedPlatform = ref('platform_a'); // 默认平台A
const currentLabel = ref('');
const keyword = ref('');
const entries = ref<Array<ChangelogEntry & { expanded?: boolean }>>([]);
const loading = ref(false);
const error = ref('');

// 过滤后的条目（按关键词搜索）
const filteredEntries = computed(() => {
  if (!keyword.value.trim()) {
    return entries.value;
  }
  const kw = keyword.value.toLowerCase();
  return entries.value.filter(
    (e) =>
      e.version.toLowerCase().includes(kw) ||
      e.content.toLowerCase().includes(kw) ||
      e.date.includes(kw),
  );
});

// 获取平台列表
async function loadPlatforms() {
  platformsLoading.value = true;
  try {
    const data = await getPlatforms();
    platforms.value = data.platforms || [];
    // 如果默认平台不存在，切换到第一个
    if (platforms.value.length > 0) {
      const hasDefault = platforms.value.some((p) => p.key === selectedPlatform.value);
      if (!hasDefault) {
        selectedPlatform.value = platforms.value[0].key;
      }
    }
  } catch (err: any) {
    message.error('加载平台列表失败: ' + (err.message || err));
  } finally {
    platformsLoading.value = false;
  }
}

// 加载某平台的 changelog
async function loadChangelog(platform: string) {
  loading.value = true;
  error.value = '';
  entries.value = [];

  try {
    const data = await getChangelog(platform);

    if (data.error) {
      error.value = data.error;
      currentLabel.value = data.label || platform;
      return;
    }

    currentLabel.value = data.label || platform;
    // 默认全部展开
    entries.value = (data.entries || []).map((e) => ({ ...e, expanded: true }));
  } catch (err: any) {
    error.value = '加载失败: ' + (err.message || err);
  } finally {
    loading.value = false;
  }
}

// 平台切换
function handlePlatformChange(platform: string) {
  loadChangelog(platform);
}

// 获取预览文本（取前 80 字符）
function getPreview(content: string): string {
  const plain = content.replace(/\n+/g, ' ').trim();
  return plain.length > 80 ? plain.slice(0, 80) + '...' : plain;
}

// 用 showdown 把 content 的 Markdown 渲染成 HTML。
// changelog 里含 **加粗**、> 引用、![图片](url)、## 小标题等语法，
// 手写正则覆盖不全，交给解析库。
// 数据来自仓库内的配置文件（非用户输入），所以直接 v-html 渲染。
function formatContent(text: string): string {
  if (!text) return '';
  return converter.makeHtml(text);
}

// 初始化
onMounted(async () => {
  await loadPlatforms();
  await loadChangelog(selectedPlatform.value);
});
</script>

<style scoped lang="less">
.changelog-controls {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
  /* 吸顶：页面滚动时下拉框/搜索框/右侧标题保持常显（滚动容器为布局内容区，top:0 即贴内容区上沿） */
  position: sticky;
  top: 0;
  z-index: 10;
  background: var(--bg-card);
  padding: 8px 0;
  margin-bottom: 16px;
}

.platform-title {
  font-size: 18px;
  font-weight: 600;
  color: #262626;
}

.loading-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 300px;
}

.changelog-timeline {
  margin-top: 24px;
  padding-left: 12px;
}

.changelog-item {
  padding-left: 16px;
}

.version-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}

.version-tag {
  font-size: 14px;
  font-weight: 600;
  padding: 4px 12px;
}

.date-text {
  /* 时间统一青色（系统 tint-cyan 色值），与版本色（靛蓝）区分，且不占用平台色 */
  font-size: 13px;
  font-weight: 600;
  color: #06b6d4;
}

.content-wrapper {
  line-height: 1.7;
  color: #595959;
}

.content-preview {
  cursor: pointer;

  &:hover {
    color: #262626;
  }
}

.expand-link,
.collapse-link {
  display: inline-block;
  margin-left: 8px;
  color: #1890ff;
  font-size: 13px;
  cursor: pointer;
  user-select: none;

  &:hover {
    color: #40a9ff;
  }
}

.content-full {
  :deep(p) {
    margin: 8px 0;
  }

  :deep(ul) {
    margin: 12px 0;
    padding-left: 24px;
  }

  :deep(li) {
    margin: 6px 0;
    line-height: 1.6;
  }
}
</style>
