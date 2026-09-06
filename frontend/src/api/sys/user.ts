import { LoginParams, LoginResultModel, GetUserInfoModel } from './model/userModel';
import { ErrorMessageMode } from '#/axios';
import http from '@/api/platform/http';

// 改造：鉴权改走 Flask cookie-session（裸 JSON），不再用 Vben 的 defHttp 信封。
// 凭证靠 cookie，不存真实 token；返回一个占位 token 让 store 的 getToken 闸门通过。
const FAKE_TOKEN = 'cookie-session';

/**
 * @description: 登录 —— POST /api/auth/login，成功后 cookie 已由后端 set。
 * 返回结构对齐 LoginResultModel（token 为占位符）。
 */
export async function loginApi(
  params: LoginParams,
  _mode: ErrorMessageMode = 'modal',
): Promise<LoginResultModel> {
  try {
    const { data } = await http.post('/auth/login', {
      username: params.username,
      password: params.password,
    });
    return {
      userId: data?.user ?? params.username,
      token: FAKE_TOKEN,
      roles: [{ roleName: 'super', value: 'super' }],
    };
  } catch (e: any) {
    // 抛出 Flask 返回的中文错误文案（如「用户名或密码错误」），供登录页弹窗展示
    throw new Error(e?.response?.data?.error || '登录失败');
  }
}

/**
 * @description: 取用户信息 —— GET /api/auth/me。
 * 后端返回形如 { user: 'admin' }，映射成 Vben 的 GetUserInfoModel。
 */
export async function getUserInfo(): Promise<GetUserInfoModel> {
  const { data } = await http.get('/auth/me');
  const name = data?.user ?? 'user';
  return {
    userId: name,
    username: name,
    realName: name,
    avatar: '',
    desc: '',
    roles: [{ roleName: 'super', value: 'super' }],
    // homePath 可选，交给 PageEnum.BASE_HOME 默认跳转
  } as GetUserInfoModel;
}

/**
 * @description: 权限码 —— ROUTE_MAPPING 模式下不会被调用，留空实现兜底。
 */
export function getPermCode(): Promise<string[]> {
  return Promise.resolve([]);
}

/**
 * @description: 登出 —— POST /api/auth/logout，清 cookie。
 */
export async function doLogout() {
  try {
    await http.post('/auth/logout');
  } catch {
    /* 忽略 */
  }
}
