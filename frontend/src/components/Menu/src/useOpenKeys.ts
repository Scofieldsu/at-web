import { MenuModeEnum } from '@/enums/menuEnum';
import type { Menu as MenuType } from '@/router/types';
import type { MenuState, Key } from './types';
import { computed, Ref, toRaw, unref, watch } from 'vue';
import { useTimeoutFn } from '@vben/hooks';
import { uniq } from 'lodash-es';
import { useMenuSetting } from '@/hooks/setting/useMenuSetting';
import { getAllParentPath } from '@/router/helper/menuHelper';

export function useOpenKeys(
  menuState: MenuState,
  menus: Ref<MenuType[]>,
  mode: Ref<MenuModeEnum>,
  accordion: Ref<boolean>,
) {
  const { getCollapsed, getIsMixSidebar } = useMenuSetting();

  // 初始化时展开所有父级菜单
  const initOpenKeys = () => {
    if (mode.value === MenuModeEnum.HORIZONTAL || unref(getCollapsed)) {
      return;
    }
    const menuList = toRaw(menus.value);
    if (!menuList || menuList.length === 0) {
      return;
    }
    // 收集所有有子菜单的路径
    const allParentKeys: string[] = [];
    const collectParentKeys = (items: MenuType[]) => {
      items.forEach((item) => {
        if (item.children && item.children.length > 0) {
          allParentKeys.push(item.path);
          collectParentKeys(item.children);
        }
      });
    };
    collectParentKeys(menuList);
    // 强制初始化全部展开（移除 length === 0 判断，确保每次加载都展开）
    menuState.openKeys = allParentKeys;
  };

  // 菜单是异步加载的（路由构建完才有值），用 watch 等到有数据再展开。
  // immediate: true 兼容已经有值的情况；展开一次即可，之后交给用户手动折叠。
  let hasInitialized = false;
  watch(
    menus,
    (list) => {
      if (list && list.length > 0 && !hasInitialized) {
        initOpenKeys();
        hasInitialized = true;
      }
    },
    { immediate: true },
  );

  async function setOpenKeys(path: string) {
    if (mode.value === MenuModeEnum.HORIZONTAL) {
      return;
    }
    const native = unref(getIsMixSidebar);
    const handle = () => {
      const menuList = toRaw(menus.value);
      if (menuList?.length === 0) {
        menuState.openKeys = [];
        return;
      }
      if (!unref(accordion)) {
        menuState.openKeys = uniq([...menuState.openKeys, ...getAllParentPath(menuList, path)]);
      } else {
        menuState.openKeys = getAllParentPath(menuList, path);
      }
    };
    if (native) {
      handle();
    } else {
      useTimeoutFn(handle, 16);
    }
  }

  const getOpenKeys = computed(() => {
    const collapse = unref(getIsMixSidebar) ? false : unref(getCollapsed);

    return collapse ? menuState.collapsedOpenKeys : menuState.openKeys;
  });

  /**
   * @description:  重置值
   */
  function resetKeys() {
    menuState.selectedKeys = [];
    menuState.openKeys = [];
  }

  function handleOpenChange(openKeys: Key[]) {
    if (unref(mode) === MenuModeEnum.HORIZONTAL || !unref(accordion) || unref(getIsMixSidebar)) {
      menuState.openKeys = openKeys;
    } else {
      // const menuList = toRaw(menus.value);
      // getAllParentPath(menuList, path);
      const rootSubMenuKeys: Key[] = [];
      for (const { children, path } of unref(menus)) {
        if (children && children.length > 0) {
          rootSubMenuKeys.push(path);
        }
      }
      if (!unref(getCollapsed)) {
        const latestOpenKey = openKeys.find((key) => menuState.openKeys.indexOf(key) === -1);
        if (rootSubMenuKeys.indexOf(latestOpenKey as string) === -1) {
          menuState.openKeys = openKeys;
        } else {
          menuState.openKeys = latestOpenKey ? [latestOpenKey] : [];
        }
      } else {
        menuState.collapsedOpenKeys = openKeys;
      }
    }
  }
  return { setOpenKeys, resetKeys, getOpenKeys, handleOpenChange };
}
