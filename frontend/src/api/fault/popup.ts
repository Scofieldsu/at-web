import http from '@/api/platform/http';

// ── 弹窗模拟（演示版：纯模拟，不真正弹框）──

export type PopupSimMode = 'zh' | 'std';

export interface PopupSimStatus {
  exe_exists: boolean;
  exe_name: string;
  exe_path: string;
  modes: Record<PopupSimMode, string>;
  running: number[];
  history: {
    at: string;
    mode: PopupSimMode;
    args: string[];
    pid: number;
    alive: boolean;
  }[];
  log_file: string;
}

export interface PopupSimEvent {
  time: string;
  keyword: string;
  line: string;
}

export interface PopupSimEvents {
  keywords: string[];
  log_file: string;
  exists: boolean;
  events: PopupSimEvent[];
}

export interface TriggerResult {
  success: boolean;
  message: string;
}

export async function getPopupSimStatus() {
  const res = await http.get<PopupSimStatus>('/fault/popup/status');
  return res.data;
}

export async function triggerPopupSim(params: { mode: PopupSimMode; code?: string }) {
  const res = await http.post<TriggerResult>('/fault/popup/trigger', params);
  return res.data;
}

export async function getPopupSimEvents(limit = 200) {
  const res = await http.get<PopupSimEvents>('/fault/popup/events', { params: { limit } });
  return res.data;
}
