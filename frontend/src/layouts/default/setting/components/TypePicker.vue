<template>
  <div :class="prefixCls">
    <template v-for="item in menuTypeList || []" :key="item.title">
      <Tooltip :title="item.title" placement="bottom">
        <div
          @click="handler(item)"
          :class="[
            `${prefixCls}__item`,
            `${prefixCls}__item--${item.type}`,
            {
              [`${prefixCls}__item--active`]: def === item.type,
            },
          ]"
        >
          <div class="mix-sidebar"></div>
        </div>
      </Tooltip>
    </template>
  </div>
</template>
<script lang="ts" setup>
  import type { PropType } from 'vue';

  import { Tooltip } from 'ant-design-vue';
  import { useDesign } from '@/hooks/web/useDesign';

  import { menuTypeListEnum } from '../enum';

  defineOptions({ name: 'MenuTypePicker' });

  defineProps({
    menuTypeList: {
      type: Array as PropType<typeof menuTypeListEnum>,
      default: () => [],
    },
    handler: {
      type: Function,
      default: () => ({}),
    },
    def: {
      type: String,
      default: '',
    },
  });

  const { prefixCls } = useDesign('setting-menu-type-picker');
</script>
<style lang="less" scoped>
  @prefix-cls: ~'@{namespace}-setting-menu-type-picker';

  .@{prefix-cls} {
    display: flex;
    gap: 16px;
    justify-content: center;
    padding: 16px 0;

    &__item {
      position: relative;
      width: 80px;
      height: 64px;
      overflow: hidden;
      border-radius: 8px;
      background-color: var(--vben-bg-elevated);
      border: 2px solid var(--vben-border);
      cursor: pointer;
      transition: all 0.3s ease;

      &::before,
      &::after {
        content: '';
        position: absolute;
        transition: all 0.3s ease;
      }

      &--sidebar,
      &--light {
        &::before {
          z-index: 1;
          top: 0;
          left: 0;
          width: 30%;
          height: 100%;
          border-radius: 6px 0 0 6px;
          background: linear-gradient(135deg, var(--vben-primary) 0%, var(--vben-primary-active) 100%);
        }

        &::after {
          top: 0;
          left: 0;
          width: 100%;
          height: 22%;
          background-color: var(--vben-bg-base);
          border-bottom: 1px solid var(--vben-border-light);
        }
      }

      &--top-menu {
        &::after {
          top: 0;
          left: 0;
          width: 100%;
          height: 22%;
          background: linear-gradient(135deg, var(--vben-primary) 0%, var(--vben-primary-active) 100%);
          border-radius: 6px 6px 0 0;
        }
      }

      &:hover {
        transform: translateY(-2px);
        border-color: var(--vben-primary);
        box-shadow: 0 4px 12px rgba(99, 102, 241, 0.15);
      }

      &--active {
        border-color: var(--vben-primary);
        box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.1);

        &::before,
        &::after {
          opacity: 1;
        }
      }
    }

    img {
      width: 100%;
      height: 100%;
      cursor: pointer;
    }
  }
</style>
