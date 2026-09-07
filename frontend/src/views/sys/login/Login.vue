<template>
  <div :class="prefixCls" class="relative w-full h-full px-4">
    <!-- 迁移自旧前端：Matrix 字符雨背景（最底层） -->
    <canvas ref="matrixCanvas" class="matrix-canvas"></canvas>
    <!-- 背景细节叠加层：渐变压暗 + 氛围光晕 + 科技网格（位于字符雨之上、内容之下） -->
    <div class="login-bg-overlay"></div>
    <div class="flex items-center absolute right-4 top-4">
      <AppLocalePicker
        class="text-white enter-x xl:text-gray-600"
        :show-text="false"
        v-if="!sessionTimeout && showLocale"
      />
    </div>

    <div class="container relative h-full mx-auto sm:px-10">
      <div class="flex items-center justify-center h-full">
        <div class="hidden h-full xl:flex xl:items-center xl:w-5/12 pl-4">
          <div class="flex flex-col items-center mt-5 w-full">
            <div class="login-hero-main animate-fade-in">AT Web</div>
            <div class="login-hero-sub animate-fade-in" style="animation-delay: 0.2s">
              <span class="hero-zdh">自动化</span><span class="hero-ceshi">测试</span><span class="hero-gzt">工作台</span>
            </div>
            <div class="login-hero-tagline animate-fade-in" style="animation-delay: 0.3s">All Your Tests, Automated &amp; Intelligent</div>
          </div>
        </div>
        <div class="flex w-full xl:w-7/12">
          <div
            :class="`${prefixCls}-form`"
            class="relative w-full px-6 my-auto pt-24 rounded-xl shadow-2xl xl:bg-transparent xl:shadow-none sm:w-3/4 lg:w-2/4 xl:w-1/2 animate-fade-in xl:ml-24"
            style="animation-delay: 0.4s"
          >
            <LoginForm />
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
<script lang="ts" setup>
  import { AppLocalePicker } from '@/components/Application';
  import { useDesign } from '@/hooks/web/useDesign';
  import { useLocaleStore } from '@/store/modules/locale';
  import { ref, onMounted, onUnmounted } from 'vue';
  import LoginForm from './LoginForm.vue';

  defineProps({
    sessionTimeout: {
      type: Boolean,
    },
  });

  const { prefixCls } = useDesign('login');
  const localeStore = useLocaleStore();
  const showLocale = localeStore.getShowPicker;

  // ---- Matrix 字符雨（迁移自旧前端 Login.vue）----
  const matrixCanvas = ref<HTMLCanvasElement | null>(null);
  let animId: number | null = null;
  const CAT =
    'お   は  よ  う  ご  ざ  い   ま   す ご   元   気   で   す   か   ユ   ・   ウ   ォ   ン   ✔';
  const FALL_SPEED = 0.35;  // 下落速度（像素/帧），越大越快

  onMounted(() => {
    const canvas = matrixCanvas.value;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    // 固化非空引用，供闭包使用（避免 TS strict 下的 null 判定）
    const cv = canvas;
    const c = ctx;

    function resize() {
      cv.width = window.innerWidth;
      cv.height = window.innerHeight;
    }
    resize();
    window.addEventListener('resize', resize);

    const fontSize = 14;
    const cols = Math.floor(cv.width / fontSize);
    const drops = Array(cols).fill(1);

    function draw() {
      c.fillStyle = 'rgba(0, 0, 0, 0.05)';
      c.fillRect(0, 0, cv.width, cv.height);
      c.font = fontSize + 'px monospace';
      for (let i = 0; i < drops.length; i++) {
        const char = CAT[Math.floor(Math.random() * CAT.length)];
        if (char === '✘') {
          c.fillStyle = '#ff3344';
        } else if (char === '✔') {
          c.fillStyle = '#33ff77';
        } else {
          c.fillStyle = drops[i] < 6 ? '#ccffcc' : '#00cc44';
        }
        c.fillText(char, i * fontSize, drops[i] * fontSize);
        if (drops[i] * fontSize > cv.height && Math.random() > 0.975) {
          drops[i] = 0;
        }
        drops[i] += FALL_SPEED;
      }
    }

    function loop() {
      draw();
      animId = requestAnimationFrame(loop);
    }
    loop();

    onUnmounted(() => {
      window.removeEventListener('resize', resize);
      if (animId) cancelAnimationFrame(animId);
    });
  });
</script>
<style lang="less">
  @prefix-cls: ~'@{namespace}-login';
  @logo-prefix-cls: ~'@{namespace}-app-logo';
  @countdown-prefix-cls: ~'@{namespace}-countdown-input';
  @dark-bg: #293146;

  html[data-theme='dark'] {
    .@{prefix-cls} {
      background-color: @dark-bg;

      &::before {
        background-image: url('@/assets/svg/login-bg-dark.svg');
      }

      .ant-input,
      .ant-input-password {
        background-color: #232a3b;
      }

      .ant-btn:not(.ant-btn-link, .ant-btn-primary) {
        border: 1px solid #4a5569;
      }

      &-form {
        background: transparent !important;
      }

      .app-iconify {
        color: #fff;
      }

      .ant-divider-inner-text {
        color: @text-color-secondary;
      }
    }
  }

  // 迁移自旧前端：Matrix 字符雨背景铺满、置于最底层
  .matrix-canvas {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    z-index: 0;
    background: #000;
  }

  // 背景细节叠加层：顶部/底部渐变压暗 + 中央绿色氛围光 + 极淡科技网格
  .login-bg-overlay {
    position: absolute;
    z-index: 0;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background:
      linear-gradient(0deg, rgb(0 0 0 / 55%), transparent 60%),
      linear-gradient(180deg, rgb(0 0 0 / 60%), transparent 30%),
      radial-gradient(ellipse at 70% 45%, rgb(0 255 136 / 8%), transparent 55%),
      repeating-linear-gradient(0deg, rgb(0 255 136 / 4%) 0 1px, transparent 1px 40px),
      repeating-linear-gradient(90deg, rgb(0 255 136 / 4%) 0 1px, transparent 1px 40px);
    pointer-events: none;
  }

  .@{prefix-cls} {
    min-height: 100%;
    overflow: hidden;
    // 字符雨背景下，让内容层浮于其上
    background-color: #000 !important;

    .container,
    .flex.items-center.absolute {
      position: relative;
      z-index: 1;
    }

    // 隐藏 Vben 自带的 SVG 背景装饰，避免盖住字符雨
    &::before {
      display: none !important;
    }

    /* stylelint-disable-next-line media-query-no-invalid */
    @media (max-width: @screen-xl) {
      background-color: #293146;

      .@{prefix-cls}-form {
        background: rgb(10 14 16 / 92%) !important;
      }
    }

    &::before {
      content: '';
      position: absolute;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      margin-left: -48%;
      background-image: url('@/assets/svg/login-bg.svg');
      background-repeat: no-repeat;
      background-position: 100%;
      background-size: auto 100%;
      /* stylelint-disable-next-line media-query-no-invalid */
      @media (max-width: @screen-xl) {
        display: none;
      }
    }

    .@{logo-prefix-cls} {
      position: absolute;
      top: 12px;
      height: 30px;

      &__title {
        color: #fff;
        font-size: 16px;
      }

      img {
        width: 32px;
      }
    }

    .container {
      .@{logo-prefix-cls} {
        display: flex;
        width: 60%;
        height: 80px;

        &__title {
          color: #fff;
          font-size: 24px;
        }

        img {
          width: 48px;
        }
      }
    }

    &-sign-in-way {
      .anticon {
        color: #888;
        font-size: 22px;
        cursor: pointer;

        &:hover {
          color: @primary-color;
        }
      }
    }

    .@{countdown-prefix-cls} input {
      min-width: unset;
    }
  }

  // 删除旧 logo、sign-in-way 样式
  .@{logo-prefix-cls},
  .@{prefix-cls}-sign-in-way {
    display: none !important;
  }

  // 登录按钮 Indigo 渐变（与系统主色 primary #6366f1 统一）
  .@{prefix-cls} .login-btn-glow {
    background: linear-gradient(135deg, #818cf8, #6366f1) !important;
    border-color: #6366f1 !important;
    box-shadow: 0 0 20px rgba(99, 102, 241, 0.35) !important;
    transition: all 0.3s ease;
    height: 48px !important;
    font-size: 16px !important;
    font-weight: 600 !important;
    letter-spacing: 2px;
    border-radius: 10px !important;
  }
  .@{prefix-cls} .login-btn-glow:hover {
    box-shadow: 0 0 35px rgba(99, 102, 241, 0.55) !important;
    transform: translateY(-1px);
    background: linear-gradient(135deg, #6366f1, #4f46e5) !important;
    border-color: #4f46e5 !important;
  }
  .@{prefix-cls} .login-btn-glow:active {
    transform: translateY(0);
  }

  // 入场淡入动画
  .animate-fade-in {
    opacity: 0;
    animation: atFadeIn 0.6s ease-out forwards;
  }
  @keyframes atFadeIn {
    from { opacity: 0; transform: translateY(20px); }
    to   { opacity: 1; transform: translateY(0); }
  }

  // 左侧两行大字：AT Web / 自动化测试工作台（与系统 Indigo/Info 色彩设计统一）
  .login-hero-main {
    font-family: 'Orbitron', 'Arial Black', sans-serif;
    font-size: 76px;
    font-weight: 700;
    line-height: 1.1;
    letter-spacing: 6px;
    background: linear-gradient(135deg, #818cf8 0%, #6366f1 55%, #0090ff 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    filter: drop-shadow(0 0 18px rgba(99, 102, 241, 0.45));
  }
  // 副标题「自动化测试工作台」：60px；自动化/测试=系统 info 蓝 #0090ff；工作台=四平台色渐变（三字同一条渐变）
  .login-hero-sub {
    margin-top: 36px;
    font-size: 60px;
    font-weight: 600;
    letter-spacing: 2px;
    text-align: center;
    filter: drop-shadow(0 0 16px rgba(99, 102, 241, 0.3));
  }
  .hero-zdh { color: #0090ff; }     /* 自动化 — 系统 info 蓝 */
  .hero-ceshi { color: #0090ff; }   /* 测试 — 与自动化同色 */
  .hero-gzt {                       /* 工作台 — 四平台色渐变：红→橙→蓝→绿 */
    background: linear-gradient(90deg, #e5484d 0%, #f76b15 33%, #0090ff 66%, #30a46c 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
  }
  // 标语行：四平台色横向渐变（红→橙→蓝→绿），含义「所有测试均可在本工作台自动且智能完成」
  // 与副标题同在 items-center 列容器内居中，且 letter-spacing 一致（2px）→ 两行视觉中心对齐
  .login-hero-tagline {
    margin-top: 24px;
    font-family: 'Orbitron', 'Arial Black', sans-serif;
    font-size: 20px;
    font-weight: 600;
    letter-spacing: 2px;
    text-align: center;
    background: linear-gradient(90deg, #e5484d 0%, #f76b15 33%, #0090ff 66%, #30a46c 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    filter: drop-shadow(0 0 10px rgba(0, 144, 255, 0.35));
  }

  // 表单整体：去掉多余内边距，由内部 item 控制间距
  .login-form {
    padding: 0;
  }
  // 登录表单玻璃面板 — 更通透 + 强模糊 + 顶部高光 + 背后 Indigo 晕（与系统主色统一）
  .@{prefix-cls}-form {
    position: relative;
    width: 420px;
    padding: 70px 60px 44px;
    border: 1px solid rgb(99 102 241 / 25%);
    border-radius: 16px;
    background: rgb(15 17 23 / 55%) !important;
    box-shadow: 0 0 40px rgb(99 102 241 / 10%);
    backdrop-filter: blur(16px) saturate(1.4);

    &::before {
      content: '';
      position: absolute;
      top: 0;
      right: 0;
      left: 0;
      height: 1px;
      border-radius: 16px 16px 0 0;
      background: rgb(129 140 248 / 18%);
      pointer-events: none;
    }

    &::after {
      content: '';
      position: absolute;
      z-index: -1;
      top: 20%;
      left: 50%;
      width: 70%;
      height: 60%;
      transform: translateX(-50%);
      background: radial-gradient(
        ellipse,
        rgb(99 102 241 / 12%),
        transparent 70%
      );
      filter: blur(24px);
      pointer-events: none;
    }
  }

  // 输入框组间距
  .@{prefix-cls} .form-item-space {
    margin-bottom: 24px !important;
  }
  .form-item-space:last-child {
    margin-bottom: 0;
  }
  // 输入框与登录按钮之间间隔加大
  .@{prefix-cls} .form-item-space:last-of-type {
    margin-bottom: 12px !important;
  }

  // 登录按钮高度与输入框一致
  .@{prefix-cls} .login-btn-glow {
    height: 48px !important;
  }

  // 输入框玻璃拟态 — 半透明玻璃底 + 绿光聚焦 + 图标随焦点变色
  .@{prefix-cls} {
    .ant-input-affix-wrapper,
    .ant-input,
    .ant-input-password {
      height: 48px !important;
      transition:
        border-color 0.3s ease,
        box-shadow 0.3s ease,
        background-color 0.3s ease;
      border: 1px solid rgb(129 140 248 / 30%) !important;
      border-radius: 10px !important;
      background: rgb(255 255 255 / 6%) !important;
      color: #eef0ff;
      font-size: 16px !important;
      backdrop-filter: blur(8px);
    }

    // 输入文本整体右移（前缀图标后留更大空隙），确保字符完全落在玻璃面板阴影区内
    .ant-input-affix-wrapper {
      padding-left: 24px !important;
      padding-right: 16px !important;
    }
    .ant-input-affix-wrapper .ant-input {
      padding-left: 10px !important;
      padding-right: 4px !important;
    }

    .ant-input-affix-wrapper:hover,
    .ant-input-password:hover {
      border-color: rgb(129 140 248 / 55%) !important;
    }

    .ant-input-affix-wrapper:focus,
    .ant-input-affix-wrapper-focused,
    .ant-input-password:focus,
    .ant-input-password-focused {
      border-color: #6366f1 !important;
      box-shadow: 0 0 0 3px rgb(99 102 241 / 18%) !important;
    }

    // 内层 input 透明露出玻璃底，不重复描边
    .ant-input-affix-wrapper .ant-input {
      height: 100% !important;
      border: none !important;
      background: transparent !important;
      box-shadow: none !important;
    }

    .ant-input::placeholder {
      color: rgb(199 210 254 / 40%) !important;
      font-size: 15px !important;
    }

    .ant-input-password-icon {
      transition: color 0.3s ease;
      color: rgb(165 180 252 / 60%) !important;
    }

    .ant-input-affix-wrapper-focused .ant-input-password-icon {
      color: #818cf8 !important;
    }
  }

  // 输入框前缀图标：默认淡靛，聚焦变亮靛
  .login-input-icon {
    transition: color 0.3s ease;
    color: rgb(165 180 252 / 60%);
  }

  .ant-input-affix-wrapper-focused .login-input-icon {
    color: #818cf8 !important;
  }

  // 密码点阵掩码：更大更黑的圆点（真实文本 ●，可着色），带呼吸动效
  .pass-dots {
    color: #000 !important;
    font-size: 22px !important;
    letter-spacing: 4px !important;
    caret-color: #6366f1 !important;
    animation: login-pass-dot-breathe 1.2s ease-in-out infinite;
  }
  @keyframes login-pass-dot-breathe {
    0%,
    100% {
      text-shadow: 0 0 0 rgba(0, 0, 0, 0);
    }
    50% {
      text-shadow: 0 0 6px rgba(0, 0, 0, 0.45);
    }
  }

  // 输入框响应式宽度
  input:not([type='checkbox']) {
    min-width: 240px;
    @media (max-width: @screen-xl) { min-width: 220px; }
    @media (max-width: @screen-lg) { min-width: 200px; }
    @media (max-width: @screen-sm) { min-width: 100%; }
  }
</style>
