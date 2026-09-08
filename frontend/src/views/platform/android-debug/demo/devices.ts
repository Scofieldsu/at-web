/**
 * 演示设备定义 — at-web 无真实 Android 设备，虚拟两台机器模拟「双设备并行调试」。
 *
 * 与真实项目 rpa-test-automation 的设备契约保持一致：
 *  - 设备 1：1080×2400 常规旗舰（与 case 坐标基准一致）
 *  - 设备 2：1200×2670 超长屏（刘海屏），用于验证坐标按比例兜底
 * 前端镜像按 width*scale / height*scale 等比缩放渲染，DOM 内元素用百分比布局，
 * 因此不同分辨率下版式一致。
 */

export interface DemoDevice {
  udid: string;
  name: string;
  wired_udid: string;
  notes: string;
  source: 'config' | 'adb';
  model: string;
  brand: string;
  sdk: number;
  android_version: string;
  width: number;
  height: number;
  /** 刘海屏（高度 >= 2300 且比例 < 0.48） */
  hasNotch: boolean;
}

function notch(width: number, height: number): boolean {
  return height >= 2300 && width / height < 0.48;
}

export const DEMO_DEVICES: DemoDevice[] = [
  {
    udid: '192.168.8.144:5555',
    name: '设备 1 · 测试旗舰',
    wired_udid: 'ZS22224B5Z',
    notes: '有线 udid: ZS22224B5Z · 抖音极速版主力调试机（演示虚拟设备）',
    source: 'config',
    model: 'Redmi K70 Pro',
    brand: 'Xiaomi',
    sdk: 34,
    android_version: 'Android 14 (SDK 34)',
    width: 1080,
    height: 2400,
    hasNotch: notch(1080, 2400),
  },
  {
    udid: '192.168.8.150:5555',
    name: '设备 2 · 长屏平板',
    wired_udid: 'YB3A7Q1M8K',
    notes: '有线 udid: YB3A7Q1M8K · 超长屏验证坐标缩放兜底（演示虚拟设备）',
    source: 'config',
    model: 'vivo X100 Ultra',
    brand: 'vivo',
    sdk: 34,
    android_version: 'Android 14 (SDK 34)',
    width: 1200,
    height: 2670,
    hasNotch: notch(1200, 2670),
  },
];

export function deviceByUdid(udid: string): DemoDevice | undefined {
  return DEMO_DEVICES.find((d) => d.udid === udid);
}
