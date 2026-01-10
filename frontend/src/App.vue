<script setup lang="ts">
import { ref } from 'vue'

const showNav = ref(true)
</script>

<template>
  <div class="app-container">
    <router-view v-slot="{ Component }">
      <transition name="fade" mode="out-in">
        <component :is="Component" />
      </transition>
    </router-view>
    
    <!-- 底部导航 -->
    <van-tabbar v-if="showNav" route class="app-tabbar">
      <van-tabbar-item to="/" icon="home-o">首页</van-tabbar-item>
      <van-tabbar-item to="/editor" icon="edit">编辑器</van-tabbar-item>
    </van-tabbar>
  </div>
</template>

<style scoped>
/* ═══════════════════════════════════════════════════════════
   App Container - iOS 26 Glassmorphism Foundation
   ═══════════════════════════════════════════════════════════ */
.app-container {
  min-height: 100vh;
  min-height: 100dvh;
  background: linear-gradient(180deg, #000a0a 0%, #001414 50%, #000a0f 100%);
  position: relative;
  overflow-x: hidden;
}

/* 背景氛围光效 */
.app-container::before {
  content: '';
  position: fixed;
  top: -50%;
  left: -50%;
  width: 200%;
  height: 200%;
  background:
    radial-gradient(ellipse 600px 400px at 20% 20%, rgba(0, 229, 255, 0.08) 0%, transparent 50%),
    radial-gradient(ellipse 500px 500px at 80% 80%, rgba(0, 255, 200, 0.06) 0%, transparent 50%),
    radial-gradient(ellipse 400px 300px at 50% 50%, rgba(0, 200, 255, 0.04) 0%, transparent 50%);
  pointer-events: none;
  z-index: 0;
  animation: ambientPulse 20s ease-in-out infinite alternate;
}

@keyframes ambientPulse {
  0% { opacity: 0.6; transform: scale(1) rotate(0deg); }
  50% { opacity: 0.8; transform: scale(1.05) rotate(1deg); }
  100% { opacity: 0.6; transform: scale(1) rotate(-1deg); }
}

/* ═══════════════════════════════════════════════════════════
   底部导航栏 - Premium Glass Tabbar
   ═══════════════════════════════════════════════════════════ */
.app-tabbar {
  position: fixed !important;
  bottom: 0 !important;
  left: 0 !important;
  right: 0 !important;
  background: linear-gradient(
    180deg,
    rgba(0, 30, 35, 0.85) 0%,
    rgba(0, 20, 25, 0.95) 100%
  ) !important;
  backdrop-filter: blur(40px) saturate(180%) brightness(1.1) !important;
  -webkit-backdrop-filter: blur(40px) saturate(180%) brightness(1.1) !important;
  border: none !important;
  box-shadow:
    0 -1px 0 0 rgba(0, 229, 255, 0.15),
    0 -4px 20px rgba(0, 0, 0, 0.4),
    0 -8px 40px rgba(0, 229, 255, 0.08),
    inset 0 1px 0 0 rgba(255, 255, 255, 0.05) !important;
  padding-bottom: env(safe-area-inset-bottom, 0) !important;
  z-index: 1000 !important;
}

/* 顶部高光边缘 */
.app-tabbar::before {
  content: '';
  position: absolute;
  top: 0;
  left: 20%;
  right: 20%;
  height: 1px;
  background: linear-gradient(
    90deg,
    transparent 0%,
    rgba(0, 229, 255, 0.4) 20%,
    rgba(0, 255, 200, 0.6) 50%,
    rgba(0, 229, 255, 0.4) 80%,
    transparent 100%
  );
  border-radius: 1px;
}

/* 导航项基础样式 */
:deep(.van-tabbar-item) {
  color: rgba(139, 149, 168, 0.8) !important;
  background: transparent !important;
  transition: all 0.35s cubic-bezier(0.34, 1.56, 0.64, 1) !important;
  position: relative;
  z-index: 1;
}

/* 导航项悬停效果 */
:deep(.van-tabbar-item:active) {
  transform: scale(0.92);
}

/* 活跃状态 */
:deep(.van-tabbar-item--active) {
  color: #00e5ff !important;
  text-shadow: 0 0 20px rgba(0, 229, 255, 0.6);
}

/* 活跃状态背景光晕 */
:deep(.van-tabbar-item--active::before) {
  content: '';
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 56px;
  height: 56px;
  background: radial-gradient(
    circle,
    rgba(0, 229, 255, 0.2) 0%,
    rgba(0, 229, 255, 0.08) 40%,
    transparent 70%
  );
  border-radius: 50%;
  z-index: -1;
  animation: activeGlow 2s ease-in-out infinite;
}

@keyframes activeGlow {
  0%, 100% { opacity: 0.8; transform: translate(-50%, -50%) scale(1); }
  50% { opacity: 1; transform: translate(-50%, -50%) scale(1.1); }
}

/* 图标样式 */
:deep(.van-tabbar-item__icon) {
  font-size: 24px !important;
  margin-bottom: 4px !important;
  transition: all 0.35s cubic-bezier(0.34, 1.56, 0.64, 1) !important;
}

:deep(.van-tabbar-item--active .van-tabbar-item__icon) {
  transform: translateY(-2px) scale(1.1);
  filter: drop-shadow(0 4px 8px rgba(0, 229, 255, 0.4));
}

/* 文字标签 */
:deep(.van-tabbar-item__text) {
  font-size: 11px !important;
  font-weight: 500 !important;
  letter-spacing: 0.3px !important;
  transition: all 0.3s ease !important;
}

:deep(.van-tabbar-item--active .van-tabbar-item__text) {
  font-weight: 600 !important;
  letter-spacing: 0.5px !important;
}

/* ═══════════════════════════════════════════════════════════
   页面切换动画 - Spring Physics
   ═══════════════════════════════════════════════════════════ */
.fade-enter-active {
  transition:
    opacity 0.4s cubic-bezier(0.34, 1.56, 0.64, 1),
    transform 0.4s cubic-bezier(0.34, 1.56, 0.64, 1),
    filter 0.4s ease;
}

.fade-leave-active {
  transition:
    opacity 0.25s cubic-bezier(0.4, 0, 0.2, 1),
    transform 0.25s cubic-bezier(0.4, 0, 0.2, 1),
    filter 0.25s ease;
}

.fade-enter-from {
  opacity: 0;
  transform: translateY(16px) scale(0.98);
  filter: blur(4px);
}

.fade-leave-to {
  opacity: 0;
  transform: translateY(-8px) scale(0.99);
  filter: blur(2px);
}

/* ═══════════════════════════════════════════════════════════
   Reduced Motion Support
   ═══════════════════════════════════════════════════════════ */
@media (prefers-reduced-motion: reduce) {
  .app-container::before {
    animation: none;
  }

  :deep(.van-tabbar-item--active::before) {
    animation: none;
  }

  .fade-enter-active,
  .fade-leave-active {
    transition-duration: 0.15s;
  }

  .fade-enter-from,
  .fade-leave-to {
    transform: none;
    filter: none;
  }
}
</style>
