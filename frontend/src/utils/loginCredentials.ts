/**
 * 登录凭据记忆：登录成功后写入 localStorage，刷新登录页预填上次用户名+密码；
 * 主动退出到登录页时只保留用户名（clearSavedPassword 清空密码），下次需重新输入密码。
 */
const LAST_CREDENTIALS_KEY = 'RPA_LAST_LOGIN_CREDENTIALS';

export function loadLastCredentials(): { account: string; password: string } {
  try {
    const raw = localStorage.getItem(LAST_CREDENTIALS_KEY);
    if (raw) {
      const data = JSON.parse(raw);
      if (data && data.account && data.password) {
        return { account: data.account, password: data.password };
      }
    }
  } catch {
    // 记录损坏则回退默认值
  }
  return { account: 'admin', password: 'demo123' };
}

export function saveLastCredentials(account: string, password: string) {
  try {
    localStorage.setItem(
      LAST_CREDENTIALS_KEY,
      JSON.stringify({ account, password }),
    );
  } catch {
    // 存储不可用（隐私模式等）时忽略
  }
}

/** 退出登录时调用：保留记住的用户名，清空已存密码 */
export function clearSavedPassword() {
  try {
    const raw = localStorage.getItem(LAST_CREDENTIALS_KEY);
    if (!raw) return;
    const data = JSON.parse(raw);
    if (data && data.account) {
      localStorage.setItem(
        LAST_CREDENTIALS_KEY,
        JSON.stringify({ account: data.account, password: '' }),
      );
    }
  } catch {
    // 记录异常时保持原样，不影响退出流程
  }
}
