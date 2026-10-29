import http from '@/api/platform/http';

// ── 运行时补丁（演示版：纯模拟，目标为演示客户端 client-a）──

export type RpaPatchRisk = 'low' | 'medium' | 'high';

export interface RpaPatchScenario {
  no: number;
  key: string;
  group: string;
  title: string;
  risk: RpaPatchRisk;
  risk_label: string;
  desc: string;
  params: Record<string, number | string>;
  keywords: string[];
  available: boolean;
}

export interface PatchProcess {
  pid: number;
  ppid: number;
  memory_mb: number;
  role: string;
}

export interface ActivePatch {
  key: string;
  no: number;
  title: string;
  mode: string;
  params: Record<string, number | string>;
  pid: number;
  injected_at: string;
  message: string;
  pid_alive: boolean;
  stale: boolean;
}

export interface RpaPatchStatus {
  is_admin: boolean;
  tool_ready: boolean;
  target_name: string;
  selected_pid: number;
  processes: PatchProcess[];
  active: ActivePatch | null;
  log_file: string;
  status_lines: string[];
}

export interface RpaPatchEvent {
  time: string;
  keyword: string;
  line: string;
}

export interface RpaPatchEvents {
  keywords: string[];
  log_file: string;
  exists: boolean;
  events: RpaPatchEvent[];
}

export interface ApplyResult {
  success: boolean;
  message: string;
}

export async function getRpaPatchScenarios() {
  const res = await http.get<RpaPatchScenario[]>('/fault/patch/scenarios');
  return res.data;
}

export async function getRpaPatchStatus() {
  const res = await http.get<RpaPatchStatus>('/fault/patch/status');
  return res.data;
}

export async function applyRpaPatch(params: {
  key: string;
  params: Record<string, number | string>;
  pid: number | null;
}) {
  const res = await http.post<ApplyResult>('/fault/patch/apply', params);
  return res.data;
}

export async function removeRpaPatch(pid: number | null) {
  const res = await http.post<ApplyResult>('/fault/patch/remove', { pid });
  return res.data;
}

export async function getRpaPatchEvents(key: string | null, limit = 200) {
  const res = await http.get<RpaPatchEvents>('/fault/patch/events', {
    params: { key: key || undefined, limit },
  });
  return res.data;
}
