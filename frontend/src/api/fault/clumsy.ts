import http from '@/api/platform/http';

// ── 类型定义（与后端 clumsy 模块契约一致；演示版参数含上下行方向/限速/RST）──

export interface ClumsyConfig {
  filter_rule: string;
  lag_enabled: boolean;
  lag_time: number;
  lag_inbound: boolean;
  lag_outbound: boolean;
  drop_enabled: boolean;
  drop_chance: number;
  drop_inbound: boolean;
  drop_outbound: boolean;
  throttle_enabled: boolean;
  throttle_timeframe: number;
  throttle_chance: number;
  throttle_inbound: boolean;
  throttle_outbound: boolean;
  bandwidth_enabled: boolean;
  bandwidth_limit: number;
  bandwidth_inbound: boolean;
  bandwidth_outbound: boolean;
  dup_enabled: boolean;
  dup_chance: number;
  dup_count: number;
  dup_inbound: boolean;
  dup_outbound: boolean;
  out_of_order_enabled: boolean;
  out_of_order_chance: number;
  out_of_order_inbound: boolean;
  out_of_order_outbound: boolean;
  tamper_enabled: boolean;
  tamper_chance: number;
  tamper_checksum: boolean;
  tamper_inbound: boolean;
  tamper_outbound: boolean;
  reset_enabled: boolean;
  reset_chance: number;
  reset_inbound: boolean;
  reset_outbound: boolean;
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
  config_version?: string;
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

export interface CollectPlatform {
  key: string;
  label: string;
  preset: string;
  hint: string;
}

export interface CollectNetwork {
  cidr: string;
  ips: string[];
  hits: number;
  covered: boolean;
}

export interface CollectResult {
  platform: string;
  label: string;
  seconds: number;
  prefix_len: number;
  filter_rule: string;
  networks: CollectNetwork[];
  ip_count: number;
  excluded: string[];
  processes: Record<string, number>;
  warnings: string[];
}

export interface CollectResponse {
  success: boolean;
  message?: string;
  data?: CollectResult;
}

/** 前端默认配置（补齐所有字段，供表单绑定）。 */
export function defaultClumsyConfig(): ClumsyConfig {
  return {
    filter_rule: 'tcp.DstPort == 8765 or tcp.SrcPort == 8765',
    lag_enabled: false,
    lag_time: 0,
    lag_inbound: true,
    lag_outbound: true,
    drop_enabled: false,
    drop_chance: 0,
    drop_inbound: true,
    drop_outbound: true,
    throttle_enabled: false,
    throttle_timeframe: 0,
    throttle_chance: 0,
    throttle_inbound: true,
    throttle_outbound: true,
    bandwidth_enabled: false,
    bandwidth_limit: 0,
    bandwidth_inbound: true,
    bandwidth_outbound: true,
    dup_enabled: false,
    dup_chance: 0,
    dup_count: 2,
    dup_inbound: true,
    dup_outbound: true,
    out_of_order_enabled: false,
    out_of_order_chance: 0,
    out_of_order_inbound: true,
    out_of_order_outbound: true,
    tamper_enabled: false,
    tamper_chance: 0,
    tamper_checksum: true,
    tamper_inbound: true,
    tamper_outbound: true,
    reset_enabled: false,
    reset_chance: 0,
    reset_inbound: true,
    reset_outbound: true,
    preset_name: undefined,
  };
}

/** 启动弱网（预设或自定义配置） */
export async function startWeaknet(params: { preset: string } | { config: ClumsyConfig }) {
  const res = await http.post<StartResult>('/clumsy/start', params);
  return res.data;
}

/** 停止弱网 */
export async function stopWeaknet() {
  const res = await http.post<StopResult>('/clumsy/stop', {});
  return res.data;
}

/** 查询运行状态 */
export async function getStatus() {
  const res = await http.get<ClumsyStatus>('/clumsy/status');
  return res.data;
}

/** 获取所有预设配置 */
export async function getPresets() {
  const res = await http.get<Record<string, PresetInfo>>('/clumsy/presets');
  return res.data;
}

/** 检查安装状态 */
export async function checkInstallation() {
  const res = await http.get<InstallationStatus>('/clumsy/installation');
  return res.data;
}

/** 校验配置（不启动） */
export async function validateConfig(config: ClumsyConfig) {
  const res = await http.post<{ valid: boolean; message: string; args?: string[]; summary?: string }>(
    '/clumsy/validate',
    { config },
  );
  return res.data;
}

/** 可采集网段的平台列表 */
export async function getCollectPlatforms() {
  const res = await http.get<CollectPlatform[]>('/clumsy/collect/platforms');
  return res.data;
}

/** 按平台采集外网 IP 段并生成过滤规则（演示：模拟采样，阻塞数秒） */
export async function collectIps(params: { platform: string; seconds: number; prefix_len: number }) {
  const res = await http.post<CollectResponse>('/clumsy/collect', params);
  return res.data;
}
