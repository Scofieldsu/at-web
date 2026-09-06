import http from './http';

export interface Platform {
  key: string;
  label: string;
  count: number;
}

export interface ChangelogEntry {
  version: string;
  date: string;
  content: string;
}

export interface ChangelogResponse {
  platform: string;
  label: string;
  entries: ChangelogEntry[];
  error?: string;
}

/**
 * 获取有 changelog 的平台列表
 */
export async function getPlatforms() {
  const res = await http.get<{ platforms: Platform[] }>('/changelog/platforms');
  return res.data;
}

/**
 * 获取某平台的版本更新说明（按日期从新到旧）
 */
export async function getChangelog(platform: string) {
  const res = await http.get<ChangelogResponse>(`/changelog/${platform}`);
  return res.data;
}
