<template>
  <div class="cpf">
    <a-form-item label="过滤规则（WinDivert 语法）">
      <a-input v-model:value="cfg.filter_rule" placeholder="tcp.DstPort == 8765 or tcp.SrcPort == 8765" allow-clear />
      <div class="cpf-hint">仅影响匹配规则的流量，其他流量不受影响</div>
    </a-form-item>

    <a-row :gutter="[16, 16]">
      <a-col :xs="24" :sm="12" :lg="6" v-for="m in MODULES" :key="m.key">
        <a-card size="small" class="cpf-mod" :class="{ on: cfg[m.enabled] }">
          <template #title>
            <a-checkbox :checked="!!cfg[m.enabled]" @update:checked="(v) => onEnable(m, v)">
              {{ m.title }}
            </a-checkbox>
          </template>

          <div class="cpf-fields" :class="{ disabled: !cfg[m.enabled] }">
            <!-- 延迟 -->
            <a-input-number
              v-if="m.key === 'lag'"
              v-model:value="cfg.lag_time"
              :min="0" :max="10000"
              :disabled="!cfg.lag_enabled"
              addon-after="ms"
              style="width: 100%"
            />
            <!-- 丢包 -->
            <a-input-number
              v-else-if="m.key === 'drop'"
              v-model:value="dropPct"
              :min="0" :max="100"
              :disabled="!cfg.drop_enabled"
              addon-after="%"
              style="width: 100%"
            />
            <!-- 节流 -->
            <template v-else-if="m.key === 'throttle'">
              <a-input-number
                v-model:value="cfg.throttle_timeframe"
                :min="0" :max="5000"
                :disabled="!cfg.throttle_enabled"
                addon-after="ms 窗口"
                style="width: 100%; margin-bottom: 8px"
              />
              <a-input-number
                v-model:value="throttlePct"
                :min="0" :max="100"
                :disabled="!cfg.throttle_enabled"
                addon-after="% 概率"
                style="width: 100%"
              />
            </template>
            <!-- 限速 -->
            <a-input-number
              v-else-if="m.key === 'bandwidth'"
              v-model:value="cfg.bandwidth_limit"
              :min="0" :max="99999"
              :disabled="!cfg.bandwidth_enabled"
              addon-after="KB/s"
              style="width: 100%"
            />
            <!-- 重复 -->
            <template v-else-if="m.key === 'dup'">
              <a-input-number
                v-model:value="dupPct"
                :min="0" :max="100"
                :disabled="!cfg.dup_enabled"
                addon-after="% 概率"
                style="width: 100%; margin-bottom: 8px"
              />
              <a-input-number
                v-model:value="cfg.dup_count"
                :min="2" :max="50"
                :disabled="!cfg.dup_enabled"
                addon-after="份"
                style="width: 100%"
              />
            </template>
            <!-- 乱序 -->
            <a-input-number
              v-else-if="m.key === 'ooo'"
              v-model:value="oooPct"
              :min="0" :max="100"
              :disabled="!cfg.out_of_order_enabled"
              addon-after="%"
              style="width: 100%"
            />
            <!-- 篡改 -->
            <template v-else-if="m.key === 'tamper'">
              <a-input-number
                v-model:value="tamperPct"
                :min="0" :max="100"
                :disabled="!cfg.tamper_enabled"
                addon-after="%"
                style="width: 100%; margin-bottom: 8px"
              />
              <a-checkbox
                :checked="cfg.tamper_checksum"
                :disabled="!cfg.tamper_enabled"
                @update:checked="(v) => { cfg.tamper_checksum = v; emitUpdate(); }"
              >
                重算校验和
              </a-checkbox>
            </template>
            <!-- TCP RST -->
            <a-input-number
              v-else-if="m.key === 'reset'"
              v-model:value="resetPct"
              :min="0" :max="100"
              :disabled="!cfg.reset_enabled"
              addon-after="%"
              style="width: 100%"
            />
          </div>

          <div class="cpf-dir">
            <span class="cpf-dir-label">方向</span>
            <a-radio-group
              size="small"
              :value="dirOf(m.key)"
              :disabled="!cfg[m.enabled]"
              @update:value="(v) => onDir(m.key, v)"
            >
              <a-radio-button value="both">双向</a-radio-button>
              <a-radio-button value="in">下行</a-radio-button>
              <a-radio-button value="out">上行</a-radio-button>
            </a-radio-group>
          </div>
        </a-card>
      </a-col>
    </a-row>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import type { ClumsyConfig } from '@/api/fault/clumsy';

const props = defineProps<{ modelValue: ClumsyConfig }>();
const emit = defineEmits<{ (e: 'update:modelValue', v: ClumsyConfig): void }>();

const cfg = computed(() => props.modelValue);

const MODULES = [
  { key: 'lag', enabled: 'lag_enabled' as const, title: '延迟 Lag' },
  { key: 'drop', enabled: 'drop_enabled' as const, title: '丢包 Drop' },
  { key: 'throttle', enabled: 'throttle_enabled' as const, title: '节流 Throttle' },
  { key: 'bandwidth', enabled: 'bandwidth_enabled' as const, title: '限速 Bandwidth' },
  { key: 'dup', enabled: 'dup_enabled' as const, title: '重复 Dup' },
  { key: 'ooo', enabled: 'out_of_order_enabled' as const, title: '乱序 OOO' },
  { key: 'tamper', enabled: 'tamper_enabled' as const, title: '篡改 Tamper' },
  { key: 'reset', enabled: 'reset_enabled' as const, title: 'TCP RST' },
];

function emitUpdate() {
  emit('update:modelValue', { ...props.modelValue });
}

function onEnable(m: (typeof MODULES)[number], v: boolean) {
  (cfg.value as any)[m.enabled] = v;
  emitUpdate();
}

// ── 概率字段用百分比输入 ──
function pct(prop: 'drop_chance' | 'throttle_chance' | 'dup_chance' | 'out_of_order_chance' | 'tamper_chance' | 'reset_chance') {
  return computed({
    get: () => Math.round(((cfg.value[prop] as number) || 0) * 10000) / 100,
    set: (v: number | null) => {
      (cfg.value as any)[prop] = (v || 0) / 100;
      emitUpdate();
    },
  });
}
const dropPct = pct('drop_chance');
const throttlePct = pct('throttle_chance');
const dupPct = pct('dup_chance');
const oooPct = pct('out_of_order_chance');
const tamperPct = pct('tamper_chance');
const resetPct = pct('reset_chance');

// ── 方向：双向/下行/上行 映射到 inbound/outbound ──
function dirOf(key: string): 'both' | 'in' | 'out' {
  const i = (cfg.value as any)[`${key}_inbound`] ?? true;
  const o = (cfg.value as any)[`${key}_outbound`] ?? true;
  return i && o ? 'both' : i ? 'in' : 'out';
}

function onDir(key: string, v: 'both' | 'in' | 'out') {
  (cfg.value as any)[`${key}_inbound`] = v !== 'out';
  (cfg.value as any)[`${key}_outbound`] = v !== 'in';
  emitUpdate();
}
</script>

<style scoped lang="less">
.cpf {
  width: 100%;
}

.cpf-hint {
  font-size: 12px;
  color: #666;
  margin-top: 4px;
}

.cpf-mod {
  height: 100%;

  &.on {
    border-color: #1890ff;
  }
}

.cpf-fields {
  min-height: 52px;

  &.disabled {
    opacity: 0.55;
  }
}

.cpf-dir {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 8px;
}

.cpf-dir-label {
  font-size: 12px;
  color: #999;
}
</style>
