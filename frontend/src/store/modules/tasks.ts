import { defineStore } from 'pinia';
import { ref } from 'vue';
import { notification } from 'ant-design-vue';
import http from '@/api/platform/http';

// 迁移自旧前端 web/src/store/tasks.js：全局任务轮询 store。
//   - 每 POLL_MS 拉一次 /api/tasks/，供顶栏角标与 Dashboard 复用；
//   - 对比上一轮快照，发现任务从 running/pending → success/failed 时弹完成通知；
//   - 单例轮询（引用计数），多组件 start() 只起一个定时器。
// 改造：ElNotification → ant-design-vue 的 notification。
const POLL_MS = 4000;
const ACTIVE = new Set(['pending', 'running']);
const DONE = new Set(['success', 'failed']);

export const useTasksStore = defineStore('tasks', () => {
  const tasks = ref<any[]>([]);
  const runningCount = ref(0);
  const loaded = ref(false);

  const _prevStatus = new Map<string, string>();
  let _timer: ReturnType<typeof setInterval> | null = null;
  let _refs = 0;

  function _fmtName(t: any) {
    const n = (t.name || '').trim();
    if (n) return n.length > 40 ? n.slice(0, 40) + '…' : n;
    return t.id ? t.id.slice(0, 8) + '…' : '任务';
  }

  function _notifyDone(t: any) {
    const ok = t.status === 'success';
    notification[ok ? 'success' : 'error']({
      message: ok ? '任务完成' : '任务失败',
      description: `${_fmtName(t)} ${ok ? '执行成功' : '执行失败'}`,
      duration: ok ? 4 : 0, // 失败常驻，成功 4s 自动关
      onClick: () => {
        window.location.hash = `#/tasks?focus=${t.id}`;
      },
    });
  }

  async function refresh() {
    try {
      const { data } = await http.get('/tasks/', { params: { limit: 50 } });
      const list = Array.isArray(data) ? data : [];
      tasks.value = list;
      runningCount.value = list.filter((t: any) => ACTIVE.has(t.status)).length;

      // 完成跳变检测（首拉不报，仅建立基线）
      if (loaded.value) {
        for (const t of list) {
          const prev = _prevStatus.get(t.id);
          if (prev && ACTIVE.has(prev) && DONE.has(t.status)) {
            _notifyDone(t);
          }
        }
      }
      for (const t of list) _prevStatus.set(t.id, t.status);
      loaded.value = true;
    } catch {
      /* 忽略单次轮询失败，下一轮重试 */
    }
  }

  function start() {
    _refs += 1;
    if (_timer) return;
    refresh();
    _timer = setInterval(refresh, POLL_MS);
  }

  function stop() {
    _refs = Math.max(0, _refs - 1);
    if (_refs === 0 && _timer) {
      clearInterval(_timer);
      _timer = null;
    }
  }

  return { tasks, runningCount, loaded, refresh, start, stop };
});
