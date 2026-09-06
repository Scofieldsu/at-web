import type { Menu as MenuType } from '@/router/types';
import type { MenuState } from './types';
import { computed, Ref, toRaw, unref, watch } from 'vue';
import { uniq } from 'lodash-es';
import { getAllParentPath } from '@/router/helper/menuHelper';
import { useTimeoutFn } from '@vben/hooks';
import { useDebounceFn } from '@vueuse/core';

export function useOpenKeys(
  menuState: MenuState,
  menus: Ref<MenuType[]>,
  accordion: Ref<boolean>,
  mixSider: Ref<boolean>,
  collapse: Ref<boolean>,
) {
  // 初始化时展开所有父级菜单
  const initOpenKeys = () => {
    if (unref(collapse)) {
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
    // 强制初始化全部展开
    menuState.openNames = allParentKeys;
    menuState.activeSubMenuNames = allParentKeys;
  };

  // 菜单是异步加载的，用 watch 等到有数据再展开
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

  const debounceSetOpenKeys = useDebounceFn(setOpenKeys, 50);
  async function setOpenKeys(path: string) {
    const native = !mixSider.value;
    const menuList = toRaw(menus.value);

    const handle = () => {
      if (menuList?.length === 0) {
        menuState.activeSubMenuNames = [];
        menuState.openNames = [];
        return;
      }
      const keys = getAllParentPath(menuList, path);

      if (!unref(accordion)) {
        menuState.openNames = uniq([...menuState.openNames, ...keys]);
      } else {
        menuState.openNames = keys;
      }
      menuState.activeSubMenuNames = menuState.openNames;
    };
    if (native) {
      handle();
    } else {
      useTimeoutFn(handle, 30);
    }
  }

  const getOpenKeys = computed(() => {
    return unref(collapse) ? [] : menuState.openNames;
  });

  return { setOpenKeys: debounceSetOpenKeys, getOpenKeys };
}
