import http from './http';

/** Mock 中控服务状态 */
export interface MockStatus {
  running: boolean;
  uptime?: number;
  rpa_connections?: Array<{ cid: string; channel?: string; [k: string]: any }>;
  log_seq?: number;
  error?: string;
}

/** Mock 收发日志条目 */
export interface MockLogItem {
  seq: number;
  ts: string;
  direction: 'send' | 'recv';
  kind: string;
  summary: string;
  /** 报文 type（帧日志有值；连接/断开事件无） */
  msg_type?: string;
  /** 报文原文 JSON 文本（后端按长度截断），可格式化展示 */
  raw?: string;
  /** 平台（channel：platform_a/platform_b/platform_c/platform_d 等，来自连接 query） */
  channel?: string;
  detail?: {
    user_name?: string;
    conversation_id?: string;
    nick_name?: string;
    product_id?: string;
    product_name?: string;
    url?: string;
  };
}

/** 消息模板参数定义 */
export interface TemplateParam {
  key: string;
  label: string;
  default: string;
}

/** 消息模板元信息 */
export interface MessageTemplate {
  key: string;
  name: string;
  description: string;
  params: TemplateParam[];
}

export function getMockStatus() {
  return http.get('/mock_ws/status');
}

export function startMock() {
  return http.post('/mock_ws/start');
}

export function stopMock() {
  return http.post('/mock_ws/stop');
}

export function getMockTemplates() {
  return http.get('/mock_ws/templates');
}

/** 获取图片 URL 列表（来自 shopping_replies.json 的 img_reply） */
export function getImageUrls() {
  return http.get('/mock_ws/image_urls');
}

/**
 * 向 RPA 推送消息
 * payload 支持两种：{"template": key, "params": {...}} 或 {"message": {完整报文}}
 */
export function sendMockMessage(payload: Record<string, any>) {
  return http.post('/mock_ws/send', payload);
}

/**
 * 预览模板构造的 JSON 报文（不下发）
 * payload: {"template": key, "params": {...}}
 */
export function previewMockMessage(payload: Record<string, any>) {
  return http.post('/mock_ws/preview', payload);
}

/** 增量拉取收发日志 */
export function getMockLogs(after = 0) {
  return http.get('/mock_ws/logs', { params: { after } });
}

/** 获取服务器信息（包含自动探测的本机 IP） */
export function getServerInfo() {
  return http.get('/mock_ws/server_info');
}
