/**
 * 分布式测试执行 API
 * 对应后端：server/modules/health、machines、tasks/remote_tasks
 */
import http from './http';

// ============ 类型定义 ============

/** Git 版本信息 */
export interface GitInfo {
  commit_hash: string;
  commit_date: string;
  branch: string;
  version: string;
  has_uncommitted_changes: boolean;
}

/** 资源占用 */
export interface Resources {
  cpu_percent: number;
  memory_percent: number;
  disk_percent: number;
  // 机器真实参数（旧版 agent 可能缺失，前端有兜底）
  cpu_cores?: number;
  cpu_model?: string;
  memory_total_gb?: number;
  disk_total_gb?: number;
}

/** 服务状态 */
export interface Services {
  mitmproxy: boolean;
  python_processes: number;
  minio: boolean;
}

/** 当前任务 */
export interface CurrentTask {
  task_id: string;
  name: string;
  started_at: number;
}

/** 健康检查响应 */
export interface HealthCheck {
  status: string;
  timestamp: string;
  hostname: string;
  ip: string;
  version: string;
  git: GitInfo;
  resources: Resources;
  services: Services;
  current_task: CurrentTask | null;
}

/** 机器信息 */
export interface Machine {
  id: string;
  ip: string;
  port: number;
  hostname: string;
  label: string;
  /** 是否为运行本控制台的机器（IP 由后端每次加载时自动校正） */
  is_local: boolean;
  available: boolean;
  status: 'online' | 'offline' | 'timeout' | 'error';
  error?: string;
  version: string;
  git_info: GitInfo;
  cpu_percent: number;
  memory_percent: number;
  disk_percent: number;
  // 机器真实参数（旧版 agent 可能缺失，前端有兜底）
  cpu_cores?: number;
  cpu_model?: string;
  memory_total_gb?: number;
  disk_total_gb?: number;
  services: Services;
  current_task: CurrentTask | null;
  idle: boolean;
  last_check: string;
}

/** 远程仓库 main 分支版本 */
export interface RemoteVersion {
  commit_hash: string;
  commit_date: string;
  branch?: string;
  error?: string;
}

/** 机器列表响应 */
export interface MachinesListResponse {
  data: Machine[];
  summary: {
    total: number;
    online: number;
    idle: number;
    versions: string[];
    version_consistent: boolean;
    remote_version: RemoteVersion;
  };
}

/** 代码差异（本机 HEAD vs origin/main） */
export interface CodeDiffResponse {
  local_hash: string;
  remote_hash: string;
  behind: number;
  ahead: number;
  commits: Array<{
    hash: string;
    date: string;
    author: string;
    message: string;
  }>;
  uncommitted_diff: string;
  untracked_files: string[];
  has_uncommitted: boolean;
  truncated: boolean;
}

/** 任务状态 */
export interface TaskStatus {
  task_id: string;
  name: string;
  status: 'pending' | 'running' | 'success' | 'failed' | 'stopped';
  platform: string;
  cases: string[];
  started_at: number | null;
  finished_at: number | null;
  progress: number;
  exit_code: number | null;
  error: string | null;
}

/** 任务日志响应 */
export interface TaskLogResponse {
  lines: string[];
  offset: number;
  total: number;
  finished: boolean;
}

/** 测试计划参数 */
export interface TestPlan {
  version?: string;
  shop?: string;
  agent?: string;
  install_type?: string;
}

/** 提交任务请求 */
export interface SubmitTaskRequest {
  target_machine: string;
  platform: string;
  cases: string[];
  plan?: TestPlan;
  skip_install?: boolean;
  keep_alive?: boolean;
  name?: string;
}

/** 提交任务响应 */
export interface SubmitTaskResponse {
  success: boolean;
  task_id?: string;
  target_machine?: string;
  error?: string;
}

// ============ API 函数 ============

/** 健康检查（单机） */
export function healthCheck() {
  return http.get<HealthCheck>('/health/check');
}

/** 获取机器列表（带实时健康检查） */
export function getMachinesList() {
  return http.get<MachinesListResponse>('/machines/list');
}

/** 添加机器 */
export function addMachine(data: {
  ip: string;
  hostname?: string;
  port?: number;
  label?: string;
}) {
  return http.post('/machines/add', data);
}

/** 移除机器 */
export function removeMachine(data: { ip: string; port?: number }) {
  return http.post('/machines/remove', data);
}

/** 修改机器备注标签（label 传空字符串即清除；本机条目同样可改） */
export function setMachineLabel(data: { ip: string; port?: number; label: string }) {
  return http.post<{ success: boolean; updated: number; label: string }>(
    '/machines/label',
    data,
  );
}

/** 探测单台机器 */
export function checkMachine(ip: string, port = 5000) {
  return http.get<HealthCheck>('/machines/check', { params: { ip, port } });
}

/** 获取指定机器与远程 main 分支的代码差异 */
export function getMachineDiff(params: { ip: string; port?: number }) {
  return http.get<CodeDiffResponse>('/machines/diff', { params });
}

/** 提交任务 */
export function submitTask(data: SubmitTaskRequest) {
  return http.post<SubmitTaskResponse>('/tasks/submit', data);
}

/** 获取任务状态 */
export function getTaskStatus(taskId: string) {
  return http.get<TaskStatus>(`/tasks/${taskId}/status`);
}

/** 获取任务日志（增量） */
export function getTaskLog(taskId: string, offset = 0, limit = 200) {
  return http.get<TaskLogResponse>(`/tasks/${taskId}/log`, {
    params: { offset, limit },
  });
}

/** 获取任务结果 */
export function getTaskResult(taskId: string) {
  return http.get(`/tasks/${taskId}/result`);
}

/** 下载录屏 */
export function downloadVideo(taskId: string) {
  return http.get(`/tasks/${taskId}/video`, {
    responseType: 'blob',
  });
}

/** 服务更新相关 */

/** 触发服务更新 */
export function triggerUpdate(data: { target: string; port?: number }) {
  return http.post<{
    success: boolean;
    update_id?: string;
    log_url?: string;
    target?: string;
    error?: string;
    code?: number;
  }>('/machines/update', data);
}

/** 查询更新状态 */
export interface UpdateStatus {
  update_id: string;
  status: 'running' | 'success' | 'failed';
  exit_code: number | null;
  error: string;
  log_file: string;
  started_at: number;
  finished_at: number | null;
}

export function getUpdateStatus(updateId: string) {
  return http.get<UpdateStatus>(`/machines/update-status/${updateId}`);
}

/** 获取更新日志（增量） */
export interface UpdateLogResponse {
  lines: string[];
  offset: number;
  total: number;
  finished: boolean;
}

export function getUpdateLog(updateId: string, offset = 0, limit = 200) {
  return http.get<UpdateLogResponse>(`/machines/update-log/${updateId}`, {
    params: { offset, limit },
  });
}
