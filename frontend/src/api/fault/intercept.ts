import http from '@/api/platform/http';

// ── 代理拦截（演示版：纯模拟，目标为演示客户端 client-a）──

export type InterceptMode = 'off' | '404' | 'once' | 'empty' | 'delay';

export interface InterceptControl {
  mode: InterceptMode;
  count: number;
  delay: number;
  path: string;
  restart_client: boolean;
}

export interface InterceptTarget {
  install_path: string;
  version: string;
  uses_system_proxy: boolean | null;
  error?: string;
}

export interface InterceptStatus {
  running: boolean;
  control: InterceptControl | null;
  pid?: number;
  target: InterceptTarget;
  system_proxy: { enabled: boolean; server: string; bypass_active: boolean } | null;
  external_capture: { active: boolean; port?: number } | null;
  is_admin: boolean;
}

export interface InterceptHit {
  time: string;
  action: string;
  url: string;
}

export interface StartParams {
  mode: InterceptMode;
  count: number;
  delay: number;
  path: string;
  restart_client: boolean;
}

export interface StartResult {
  success: boolean;
  message: string;
}

export async function getInterceptStatus() {
  const res = await http.get<InterceptStatus>('/fault/intercept/status');
  return res.data;
}

export async function startIntercept(params: StartParams) {
  const res = await http.post<StartResult>('/fault/intercept/start', params);
  return res.data;
}

export async function stopIntercept() {
  const res = await http.post<StartResult>('/fault/intercept/stop', {});
  return res.data;
}

export async function getInterceptHits(limit = 200) {
  const res = await http.get<InterceptHit[]>('/fault/intercept/hits', { params: { limit } });
  return res.data;
}
