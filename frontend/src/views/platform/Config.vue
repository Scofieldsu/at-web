<template>
  <div class="config-page">
    <ConfigEditor />
  </div>
</template>

<script lang="ts" setup>
  defineOptions({ name: 'Config' });
  import ConfigEditor from '@/components/platform/ConfigEditor.vue';
</script>

<style scoped>
  .config-page {
    height: calc(100vh - 92px);
    padding: 16px;
  }
</style>
