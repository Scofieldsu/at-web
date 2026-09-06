/**
 * Application configuration
 */
import type { ProjectConfig } from '#/config';

import { PROJ_CFG_KEY, APP_DARK_MODE_KEY } from '@/enums/cacheEnum';
import projectSetting from '@/settings/projectSetting';

import { updateDarkTheme } from '@/logics/theme/dark';
import { updateHeaderBgColor, updateSidebarBgColor } from '@/logics/theme/updateBackground';
import { updateColorWeak } from '@/logics/theme/updateColorWeak';
import { updateGrayMode } from '@/logics/theme/updateGrayMode';

import { useAppStore } from '@/store/modules/app';
import { useLocaleStore } from '@/store/modules/locale';

import { getCommonStoragePrefix, getStorageShortName } from '@/utils/env';

import { ThemeEnum } from '@/enums/appEnum';
import { deepMerge } from '@/utils';
import { Persistent } from '@/utils/cache/persistent';

// Initial project configuration
export function initAppConfigStore() {
  const localeStore = useLocaleStore();
  const appStore = useAppStore();
  let projCfg = Persistent.getLocal<ProjectConfig>(PROJ_CFG_KEY);
  projCfg = deepMerge(projectSetting, projCfg || {});
  // 菜单展开状态与标签页开关始终以源码配置为准：deepMerge 会让 localStorage
  // 里的历史值（用户上次手动折叠后写入的 collapsed: true）盖掉默认值，
  // 导致改了 projectSetting 也不生效。这几项不做持久化继承。
  projCfg.menuSetting.collapsed = projectSetting.menuSetting.collapsed;
  projCfg.menuSetting.accordion = projectSetting.menuSetting.accordion;
  projCfg.multiTabsSetting.show = projectSetting.multiTabsSetting.show;
  // 主题与侧边栏底色同样不继承本地历史值，否则改了配色也看不到效果
  projCfg.menuSetting.theme = projectSetting.menuSetting.theme;
  projCfg.menuSetting.bgColor = projectSetting.menuSetting.bgColor;
  projCfg.menuSetting.menuWidth = projectSetting.menuSetting.menuWidth;
  // 全局默认浅色：清除历史遗留的暗色偏好。
  // 旧版本把菜单深色主题作为默认暗色模式，写入过 __APP__DARK__MODE__，
  // 不清理会导致新版本仍整体渲染为深色。用户之后手动切换仍可生效（本会话内）。
  localStorage.removeItem(APP_DARK_MODE_KEY);
  const darkMode = appStore.getDarkMode;
  const {
    colorWeak,
    grayMode,

    headerSetting: { bgColor: headerBgColor } = {},
    menuSetting: { bgColor } = {},
  } = projCfg;
  try {
    grayMode && updateGrayMode(grayMode);
    colorWeak && updateColorWeak(colorWeak);
  } catch (error) {
    console.log(error);
  }
  appStore.setProjectConfig(projCfg);

  // init dark mode
  updateDarkTheme(darkMode);
  if (darkMode === ThemeEnum.DARK) {
    updateHeaderBgColor();
    updateSidebarBgColor();
  } else {
    headerBgColor && updateHeaderBgColor(headerBgColor);
    bgColor && updateSidebarBgColor(bgColor);
  }
  // init store
  localeStore.initLocale();

  setTimeout(() => {
    clearObsoleteStorage();
  }, 16);
}

/**
 * As the version continues to iterate, there will be more and more cache keys stored in localStorage.
 * This method is used to delete useless keys
 */
export function clearObsoleteStorage() {
  const commonPrefix = getCommonStoragePrefix();
  const shortPrefix = getStorageShortName();

  [localStorage, sessionStorage].forEach((item: Storage) => {
    Object.keys(item).forEach((key) => {
      if (key && key.startsWith(commonPrefix) && !key.startsWith(shortPrefix)) {
        item.removeItem(key);
      }
    });
  });
}
