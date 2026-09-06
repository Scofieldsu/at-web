<template>
  <span :class="getTagClass" v-if="getShowTag">{{ getContent }}</span>
</template>
<script lang="ts" setup>
  import type { Menu } from '@/router/types';
  import { computed } from 'vue';
  import { useDesign } from '@/hooks/web/useDesign';
  import { propTypes } from '@/utils/propTypes';

  defineOptions({ name: 'SimpleMenuTag' });

  const props = defineProps({
    item: {
      type: Object as PropType<Menu>,
      default: () => ({}),
    },
    dot: propTypes.bool,
    collapseParent: propTypes.bool,
  });

  const { prefixCls } = useDesign('simple-menu');

  const getShowTag = computed(() => {
    const { item } = props;

    if (!item) return false;

    const { tag } = item;
    if (!tag) return false;

    const { dot, content } = tag;
    if (!dot && !content) return false;
    return true;
  });

  const getContent = computed(() => {
    if (!getShowTag.value) return '';
    const { item, collapseParent } = props;
    const { tag } = item;
    const { dot, content } = tag!;
    return dot || collapseParent ? '' : content;
  });

  const getTagClass = computed(() => {
    const { item, collapseParent } = props;
    const { tag = {} } = item || {};
    const { dot, type = 'error', class: extraClass } = tag as any;
    const tagCls = `${prefixCls}-tag`;
    return [
      tagCls,

      [`${tagCls}--${type}`],
      {
        [`${tagCls}--collapse`]: collapseParent,
        [`${tagCls}--dot`]: dot || props.dot,
        // 额外修饰符（如 env：浅底深字，与页面内 a-tag 风格统一）
        [`${tagCls}--${extraClass}`]: !!extraClass,
      },
    ];
  });
</script>
