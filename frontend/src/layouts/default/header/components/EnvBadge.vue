<template>
  <a-tooltip :title="`点击切换到 ${nextEnvLabel}（config/env.json）`">
    <div
      class="env-badge"
      :class="`env-badge--${currentEnv}`"
      role="button"
      :aria-label="`当前环境 ${envName}，点击切换`"
      :title="`点击切换到 ${nextEnvLabel}`"
      @click="handleSwitch"
    >
      <span class="env-badge__icon">●</span>
      <span class="env-badge__text">{{ envName }}</span>
      <CaretDownOutlined class="env-badge__caret" :class="{ 'is-switching': switching }" />
    </div>
  </a-tooltip>
</template>

<script lang="ts" setup>
  import { computed, ref } from 'vue';
  import { CaretDownOutlined } from '@ant-design/icons-vue';
  import { useEnvStore } from '@/store/modules/env';
  import { useMessage } from '@/hooks/web/useMessage';

  const envStore = useEnvStore();
  const { createMessage } = useMessage();

  const switching = ref(false);

  const currentEnv = computed(() => {
    // 使用与侧边栏一致的环境获取逻辑
    return envStore.getEnv || 'dev';
  });

  const envName = computed(() => {
    // 使用与侧边栏一致的环境标签
    return envStore.getEnvLabel;
  });

  // 下一个环境（dev/prod 两态互切；多环境时取列表中的下一个）
  const nextEnv = computed(() => {
    const envs = envStore.getEnvs;
    if (!envs.length) return 'dev';
    const idx = envs.indexOf(currentEnv.value);
    return envs[(idx + 1) % envs.length];
  });

  const nextEnvLabel = computed(() =>
    nextEnv.value === 'dev' ? '开发环境' : nextEnv.value === 'prod' ? '生产环境' : nextEnv.value,
  );

  async function handleSwitch() {
    if (switching.value) return;
    switching.value = true;
    try {
      await envStore.switchEnv(nextEnv.value);
      createMessage.success(`已切换到 ${nextEnvLabel.value}（config/env.json 已更新）`);
    } catch (e) {
      createMessage.error(`环境切换失败：${(e as Error)?.message || '未知错误'}`);
    } finally {
      switching.value = false;
    }
  }
</script>

<style lang="less" scoped>
  .env-badge {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 2px 10px;
    border-radius: 10px;
    font-size: 12px;
    font-weight: 600;
    letter-spacing: 0.3px;
    transition: all 0.3s ease;
    height: 20px;
    line-height: 1;
    cursor: pointer;
    user-select: none;

    // 可点击切换环境的 hover 反馈
    &:hover {
      filter: brightness(0.92);
      box-shadow: 0 0 0 2px rgba(255, 255, 255, 0.08);
    }

    &__icon {
      font-size: 6px;
      animation: pulse 2s ease-in-out infinite;
    }

    &__text {
      line-height: 1;
    }

    &__caret {
      font-size: 9px;
      opacity: 0.75;
      transition: transform 0.25s ease;
    }

    &--dev:hover {
      .env-badge__caret {
        color: var(--vben-primary);
      }
    }

    &--prod:hover {
      .env-badge__caret {
        color: var(--vben-warning);
      }
    }

    .env-badge__caret.is-switching {
      animation: caret-spin 0.8s linear infinite;
    }

    // 开发环境 - 蓝色（与侧边栏 primary 标签一致）
    &--dev {
      background: rgba(99, 102, 241, 0.12);
      color: var(--vben-primary);
      border: 1px solid rgba(99, 102, 241, 0.25);

      .env-badge__icon {
        color: var(--vben-primary);
      }
    }

    // 生产环境 - 橙色/警告色（与侧边栏 warn 标签一致）
    &--prod {
      background: rgba(247, 107, 21, 0.12);
      color: var(--vben-warning);
      border: 1px solid rgba(247, 107, 21, 0.25);

      .env-badge__icon {
        color: var(--vben-warning);
      }
    }

    @keyframes pulse {
      0%,
      100% {
        opacity: 1;
      }
      50% {
        opacity: 0.5;
      }
    }

    @keyframes caret-spin {
      from {
        transform: rotate(0deg);
      }
      to {
        transform: rotate(180deg);
      }
    }
  }

  // 深色主题适配
  html[data-theme='dark'] {
    .env-badge {
      &--dev {
        background: rgba(109, 112, 246, 0.15);
        border-color: rgba(109, 112, 246, 0.3);
      }

      &--prod {
        background: rgba(255, 140, 58, 0.15);
        border-color: rgba(255, 140, 58, 0.3);
      }
    }
  }
</style>
