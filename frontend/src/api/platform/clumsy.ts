import http from './http';

export interface ClumsyConfig {
  filter_rule: string;
  lag_enabled: boolean;
  lag_time: number;
  drop_enabled: boolean;
  drop_chance: number;
  throttle_enabled: boolean;
  throttle_timeframe: number;
  throttle_chance: number;
  dup_enabled?: boolean;
  dup_chance?: number;
  dup_count?: number;
  out_of_order_enabled?: boolean;
  out_of_order_chance?: number;
  tamper_enabled?: boolean;
  tamper_chance?: number;
  preset_name?: string;
}

export interface ClumsyStatus {
  running: boolean;
  installed: boolean;
  exe_path: string;
  pid?: number;
  config?: ClumsyConfig;
  start_time?: number;
  elapsed_seconds: number;
  summary: string;
}

export interface PresetInfo {
  name: string;
  description: string;
  summary: string;
  config: ClumsyConfig;
}

export interface StartResult {
  success: boolean;
  message: string;
  pid?: number;
  config?: ClumsyConfig;
}

export interface StopResult {
  success: boolean;
  message: string;
}

export interface InstallationStatus {
  installed: boolean;
  path: string;
  version?: string;
  message: string;
}

/**
 * 启动弱网（预设或自定义配置）
 */
export async function startWeaknet(params: { preset: string } | { config: ClumsyConfig }) {
  const res = await http.post<StartResult>('/clumsy/start', params);
  return res.data;
}

/**
 * 停止弱网
 */
export async function stopWeaknet() {
  const res = await http.post<StopResult>('/clumsy/stop', {});
  return res.data;
}

/**
 * 查询运行状态
 */
export async function getStatus() {
  const res = await http.get<ClumsyStatus>('/clumsy/status');
  return res.data;
}

/**
 * 获取所有预设配置
 */
export async function getPresets() {
  const res = await http.get<Record<string, PresetInfo>>('/clumsy/presets');
  return res.data;
}

/**
 * 检查安装状态
 */
export async function checkInstallation() {
  const res = await http.get<InstallationStatus>('/clumsy/installation');
  return res.data;
}

/**
 * 校验配置（不启动）
 */
export async function validateConfig(config: ClumsyConfig) {
  const res = await http.post<{ valid: boolean; message: string; args?: string[]; summary?: string }>(
    '/clumsy/validate',
    { config },
  );
  return res.data;
}
