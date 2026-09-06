import type { App } from 'vue';
import Antd from 'ant-design-vue';
import { Button } from './Button';
import { Input, Layout } from 'ant-design-vue';
import VXETable from 'vxe-table';
import VXEUI from 'vxe-pc-ui';

export function registerGlobComp(app: App) {
  // 迁移改造：全局注册整个 Ant Design Vue，使搬迁页面的 <a-table>/<a-card>/<a-form> 等标签可用。
  // Vben 默认仅注册 Input/Button/Layout（按需局部引入），而我们的业务页用的是全局标签写法。
  app.use(Antd).use(Input).use(Button).use(Layout).use(VXETable).use(VXEUI);
}
