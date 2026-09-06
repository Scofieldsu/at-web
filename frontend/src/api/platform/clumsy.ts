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
export function startWeaknet(params: { preset: string } | { config: ClumsyConfig }) {
  return http.post<StartResult>('/clumsy/start', params);
}

/**
 * 停止弱网
 */
export function stopWeaknet() {
  return http.post<StopResult>('/clumsy/stop', {});
}

/**
 * 查询运行状态
 */
export function getStatus() {
  return http.get<ClumsyStatus>('/clumsy/status');
}

/**
 * 获取所有预设配置
 */
export function getPresets() {
  return http.get<Record<string, PresetInfo>>('/clumsy/presets');
}

/**
 * 检查安装状态
 */
export function checkInstallation() {
  return http.get<InstallationStatus>('/clumsy/installation');
}

/**
 * 校验配置（不启动）
 */
export function validateConfig(config: ClumsyConfig) {
  return http.post<{ valid: boolean; message: string; args?: string[]; summary?: string }>(
    '/clumsy/validate',
    { config },
  );
}
