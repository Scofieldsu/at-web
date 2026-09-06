import http from './http';

export interface ScheduleSpec {
  type: 'daily' | 'weekly' | 'monthly' | 'interval';
  time?: string;            // HH:MM（24 小时制）
  weekdays?: number[];      // isoweekday 1-7（周一=1）
  day_of_month?: number;    // 1-31
  interval_hours?: number;  // ≥1
}

export interface ScheduleLastRun {
  task_id: string;
  status: string;           // success | failed | running
  at: string;
  error: string | null;
}

export interface Schedule {
  id: string;
  name: string;
  enabled: boolean;
  spec: ScheduleSpec;
  target_machine: string;
  platform: string;
  cases: string[];
  plan: Record<string, any>;
  created_at: string;
  next_run_at: string;
  last_triggered_at: string;
  last_run: ScheduleLastRun | null;
}

export function getSchedules() {
  return http.get<{ schedules: Schedule[] }>('/schedules');
}

export function createSchedule(data: Partial<Schedule>) {
  return http.post<Schedule>('/schedules', data);
}

export function updateSchedule(id: string, data: Partial<Schedule>) {
  return http.put<Schedule>(`/schedules/${id}`, data);
}

export function deleteSchedule(id: string) {
  return http.delete(`/schedules/${id}`);
}

export function runSchedule(id: string) {
  return http.post<{ success: boolean; task_id?: string; error?: string }>(
    `/schedules/${id}/run`,
  );
}
