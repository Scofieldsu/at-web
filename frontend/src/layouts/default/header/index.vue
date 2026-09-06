<template>
  <Layout.Header :class="getHeaderClass">
    <!-- left start -->
    <div :class="`${prefixCls}-left`">
      <!-- logo -->
      <AppLogo
        v-if="getShowHeaderLogo || getIsMobile"
        :class="`${prefixCls}-logo`"
        :theme="getHeaderTheme"
        :style="getLogoWidth"
      />
      <LayoutTrigger
        v-if="
          (getShowContent && getShowHeaderTrigger && !getSplit && !getIsMixSidebar) || getIsMobile
        "
        :theme="getHeaderTheme"
        :sider="false"
      />
      <LayoutBreadcrumb v-if="getShowContent && getShowBread" :theme="getHeaderTheme" />
      <!-- 环境徽章 - 只在顶部菜单模式下显示 -->
      <EnvBadge v-if="getShowTopMenu && !getIsMobile" :class="`${prefixCls}-env`" />
    </div>
    <!-- left end -->

    <!-- menu start -->
    <div v-if="getShowTopMenu && !getIsMobile" :class="`${prefixCls}-menu`">
      <LayoutMenu
        :isHorizontal="true"
        :theme="getHeaderTheme"
        :splitType="getSplitType"
        :menuMode="getMenuMode"
      />
    </div>
    <!-- menu-end -->

    <!-- action  -->
    <div :class="`${prefixCls}-action`">
      <!-- 当前登录用户名（彩色标签，风格同执行用例页版本/agent chips；图标与登录页用户名字段一致） -->
      <span v-if="displayName" class="header-user-chip">
        <img v-if="userAvatar" class="header-user-chip-avatar" :src="userAvatar" alt="user" />
        <span>{{ displayName }}</span>
      </span>
      <AppSearch v-if="getShowSearch" :class="`${prefixCls}-action__item `" />

      <ErrorAction v-if="getUseErrorHandle" :class="`${prefixCls}-action__item error-action`" />

      <FullScreen v-if="getShowFullScreen" :class="`${prefixCls}-action__item fullscreen-item`" />

      <Tooltip :title="t('layout.header.tooltipLock')">
        <span :class="`${prefixCls}-action__item`" @click="handleLock">
          <LockOutlined />
        </span>
      </Tooltip>

      <Tooltip :title="t('layout.header.dropdownItemLoginOut')">
        <span :class="`${prefixCls}-action__item`" @click="handleLogout">
          <LogoutOutlined />
        </span>
      </Tooltip>

      <UserDropDown :theme="getHeaderTheme" />

      <SettingDrawer v-if="getShowSetting" :class="`${prefixCls}-action__item`" />
    </div>
  </Layout.Header>
  <LockAction @register="register" />
</template>
<script lang="ts" setup>
  import { Layout, Tooltip } from 'ant-design-vue';
  import { LockOutlined, LogoutOutlined } from '@ant-design/icons-vue';
  import { computed, unref } from 'vue';

  import { AppLogo, AppSearch } from '@/components/Application';
  import { SettingButtonPositionEnum } from '@/enums/appEnum';
  import { MenuModeEnum, MenuSplitTyeEnum } from '@/enums/menuEnum';
  import { useHeaderSetting } from '@/hooks/setting/useHeaderSetting';
  import { useMenuSetting } from '@/hooks/setting/useMenuSetting';
  import { useRootSetting } from '@/hooks/setting/useRootSetting';
  import { useAppInject } from '@/hooks/web/useAppInject';
  import { useDesign } from '@/hooks/web/useDesign';
  import { useLocale } from '@/locales/useLocale';
  import { useI18n } from '@/hooks/web/useI18n';
  import { createAsyncComponent } from '@/utils/factory/createAsyncComponent';
  import { propTypes } from '@/utils/propTypes';
  import { useUserStore } from '@/store/modules/user';
  import { useModal } from '@/components/Modal';
  import { createAvatarUrl } from '@/utils/avatar';

  import LayoutMenu from '../menu/index.vue';
  import LayoutTrigger from '../trigger/index.vue';
  import { ErrorAction, FullScreen, LayoutBreadcrumb, UserDropDown, EnvBadge } from './components';

  const SettingDrawer = createAsyncComponent(() => import('@/layouts/default/setting/index.vue'), {
    loading: true,
  });
  const LockAction = createAsyncComponent(() => import('./components/lock/LockModal.vue'));
  defineOptions({ name: 'LayoutHeader' });

  const props = defineProps({
    fixed: propTypes.bool,
  });
  const { prefixCls } = useDesign('layout-header');
  const {
    getShowTopMenu,
    getShowHeaderTrigger,
    getSplit,
    getIsMixMode,
    getMenuWidth,
    getIsMixSidebar,
  } = useMenuSetting();
  const { getUseErrorHandle, getShowSettingButton, getSettingButtonPosition } = useRootSetting();

  const {
    getHeaderTheme,
    getShowFullScreen,
    getShowContent,
    getShowBread,
    getShowHeaderLogo,
    getShowHeader,
    getShowSearch,
  } = useHeaderSetting();

  const { getIsMobile } = useAppInject();
  const { t } = useI18n();
  const userStore = useUserStore();
  const [register, { openModal }] = useModal();

  function handleLock() {
    openModal(true);
  }

  function handleLogout() {
    userStore.confirmLoginOut();
  }

  const getHeaderClass = computed(() => {
    const theme = unref(getHeaderTheme);
    return [
      prefixCls,
      {
        [`${prefixCls}--fixed`]: props.fixed,
        [`${prefixCls}--mobile`]: unref(getIsMobile),
        [`${prefixCls}--${theme}`]: theme,
      },
    ];
  });

  // 当前登录用户名（锁屏等场景显示同步用：realName 缺省回退 username）
  const displayName = computed(
    () => userStore.getUserInfo?.realName || userStore.getUserInfo?.username || '',
  );

  // DiceBear 头像（utils/avatar 统一生成：与锁屏弹窗、解锁页同一用户头像一致）
  const userAvatar = computed(() => createAvatarUrl(displayName.value));

  const getShowSetting = computed(() => {
    if (!unref(getShowSettingButton)) {
      return false;
    }
    const settingButtonPosition = unref(getSettingButtonPosition);

    if (settingButtonPosition === SettingButtonPositionEnum.AUTO) {
      return unref(getShowHeader);
    }
    return settingButtonPosition === SettingButtonPositionEnum.HEADER;
  });

  const getLogoWidth = computed(() => {
    if (!unref(getIsMixMode) || unref(getIsMobile)) {
      return {};
    }
    const width = unref(getMenuWidth) < 180 ? 180 : unref(getMenuWidth);
    return { width: `${width}px` };
  });

  const getSplitType = computed(() => {
    return unref(getSplit) ? MenuSplitTyeEnum.TOP : MenuSplitTyeEnum.NONE;
  });

  const getMenuMode = computed(() => {
    return unref(getSplit) ? MenuModeEnum.HORIZONTAL : null;
  });
</script>
<style lang="less" scoped>
  /* 当前登录用户名彩色标签：与执行用例页「版本/Agent」chip 风格一致 */
  .header-user-chip {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    margin-right: 8px;
    padding: 4px 12px;
    border-radius: 6px;
    font-size: var(--vben-font-size-base);
    line-height: 28px;
    color: var(--accent);
    background: rgba(99, 102, 241, 0.12);
    white-space: nowrap;
  }
  /* 极客风头像：DiceBear bottts，本地生成（按用户名 seed），方形小圆角，不超出标签 */
  .header-user-chip-avatar {
    display: inline-block;
    width: 28px;
    height: 28px;
    border-radius: 6px;
    object-fit: cover;
    flex-shrink: 0;
    vertical-align: middle;
    border: 1px solid rgba(255, 255, 255, 0.45);
  }
</style>
<style lang="less">
  @import url('./index.less');
</style>
