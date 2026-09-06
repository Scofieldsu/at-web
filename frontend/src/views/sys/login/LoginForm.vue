<template>
  <Form
    class="login-form"
    :model="formData"
    :rules="getFormRules"
    ref="formRef"
    v-show="getShow"
    @keypress.enter="handleLogin"
  >
    <FormItem name="account" class="form-item-space">
      <Input
        size="large"
        v-model:value="formData.account"
        :placeholder="t('sys.login.userName')"
        class="fix-auto-fill login-input"
      >
        <template #prefix><UserOutlined class="login-input-icon" /></template>
      </Input>
    </FormItem>
    <FormItem name="password" class="form-item-space">
      <!-- 自定义掩码输入：显示为大号黑色圆点（可着色/动效），真实值仍写入 formData.password -->
      <Input
        size="large"
        :value="passwordDots"
        :placeholder="t('sys.login.password')"
        class="login-input pass-dots"
        @beforeinput="onPassBefore"
        @input="onPassInput"
      >
        <template #prefix><LockOutlined class="login-input-icon" /></template>
      </Input>
    </FormItem>

    <FormItem class="form-item-space">
      <Button type="primary" size="large" block class="login-btn-glow" @click="handleLogin" :loading="loading">
        {{ t('sys.login.loginButton') }}
      </Button>
    </FormItem>
  </Form>
</template>
<script lang="ts" setup>
  import { reactive, ref, unref, computed } from 'vue';

  import { Form, Input, Button } from 'ant-design-vue';
  import { UserOutlined, LockOutlined } from '@ant-design/icons-vue';
  import { useI18n } from '@/hooks/web/useI18n';
  import { useMessage } from '@/hooks/web/useMessage';

  import { useUserStore } from '@/store/modules/user';
  import { LoginStateEnum, useLoginState, useFormRules, useFormValid } from './useLogin';
  import { useDesign } from '@/hooks/web/useDesign';

  const FormItem = Form.Item;
  const { t } = useI18n();
  const { notification, createErrorModal } = useMessage();
  const { prefixCls } = useDesign('login');
  const userStore = useUserStore();

  const { getLoginState } = useLoginState();
  const { getFormRules } = useFormRules();

  const formRef = ref();
  const loading = ref(false);

  const formData = reactive({
    account: 'admin',
    password: 'demo123',
  });

  // 密码掩码点阵：按真实长度渲染大号黑色圆点
  const passwordDots = computed(() => '●'.repeat(formData.password.length));
  const pendingPaste = ref('');
  function onPassBefore(e: any) {
    if (e?.inputType === 'insertFromPaste') {
      pendingPaste.value = String(e.dataTransfer?.getData?.('text') ?? e.data ?? '').replace(/●/g, '');
    }
  }
  function onPassInput(e: any) {
    const raw: string = e?.target?.value ?? '';
    const cur = formData.password.length;
    const len = raw.length;
    if (len < cur) {
      // 退格 / 多字符删除：真实密码同步截断
      formData.password = formData.password.slice(0, len);
    } else if (len > cur) {
      // 新增字符：优先取 beforeinput/InputEvent.data，兜底取末尾新增段
      let added = pendingPaste.value || e?.data || '';
      if (!added) added = raw.slice(cur, len);
      added = String(added).replace(/●/g, '');
      if (added) formData.password = formData.password + added;
    }
    pendingPaste.value = '';
  }

  const { validForm } = useFormValid(formRef);

  //onKeyStroke('Enter', handleLogin);

  const getShow = computed(() => unref(getLoginState) === LoginStateEnum.LOGIN);

  async function handleLogin() {
    const data = await validForm();
    if (!data) return;
    try {
      loading.value = true;
      const userInfo = await userStore.login({
        password: data.password,
        username: data.account,
        mode: 'none', //不要默认的错误提示
      });
      if (userInfo) {
        notification.success({
          message: t('sys.login.loginSuccessTitle'),
          description: `${t('sys.login.loginSuccessDesc')}: ${userInfo.realName}`,
          duration: 1,
        });
      }
    } catch (error) {
      createErrorModal({
        title: t('sys.api.errorTip'),
        content: (error as unknown as Error).message || t('sys.api.networkExceptionMsg'),
        getContainer: () => document.body.querySelector(`.${prefixCls}`) || document.body,
      });
    } finally {
      loading.value = false;
    }
  }
</script>
