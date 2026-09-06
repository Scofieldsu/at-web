<template>
  <span :class="`${prefixCls}- flex items-center `">
    <img v-if="getImg" :src="getImg" class="w-18px h-18px align-top mr-2" />
    <Icon
      v-if="getIcon"
      :icon="getIcon"
      :size="18"
      :color="getIconColor"
      :class="`${prefixCls}-wrapper__icon mr-2`"
    />
    <span :style="getTextStyle">{{ getI18nName }}</span>
  </span>
</template>
<script lang="ts" setup>
  import { computed } from 'vue';
  import Icon from '@/components/Icon/Icon.vue';
  import { useI18n } from '@/hooks/web/useI18n';
  import { useDesign } from '@/hooks/web/useDesign';
  import { contentProps } from '../props';

  defineOptions({ name: 'MenuItemContent' });

  const props = defineProps(contentProps);

  const { t } = useI18n();
  const { prefixCls } = useDesign('basic-menu-item-content');

  const getI18nName = computed(() => t(props.item?.meta?.title || props.item?.name));
  const getIcon = computed(() => (props.item?.img ? undefined : props.item?.icon));
  const getImg = computed(() => props.item?.img);
  // 一级菜单配色：meta.color 未定义时走主题色（向后兼容）
  const getItemColor = computed(() => (props.item?.meta?.color as string | undefined) || undefined);
  // 仅一级分组（含 children）着色文字，二级菜单保持主题色
  const getIconColor = computed(() => (hasChildren() ? getItemColor.value : undefined));
  const getTextStyle = computed(() =>
    hasChildren() && getItemColor.value ? { color: getItemColor.value } : undefined,
  );
  function hasChildren(): boolean {
    return !!props.item?.children && props.item.children.length > 0;
  }
</script>
