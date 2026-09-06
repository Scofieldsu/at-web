import { createAvatar } from '@dicebear/core';
import { notionists } from '@dicebear/collection';

/**
 * 生成用户头像（Data URL）—— DiceBear notionists（现代都市插画人像），
 * 按用户名 seed 本地确定性渲染，自托管无外链。
 * 头部用户标签、锁屏弹窗、解锁页统一使用，保证同一用户全站头像一致。
 */
export function createAvatarUrl(seed: string, size = 64): string {
  const key = seed || 'user';
  try {
    const svg = createAvatar(notionists, { seed: key, size }).toString();
    return `data:image/svg+xml;utf8,${encodeURIComponent(svg)}`;
  } catch {
    return '';
  }
}
