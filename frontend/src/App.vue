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
.app-container {
  min-height: 100vh;
  background-color: #000000;
}

/* 底部导航栏 - 青绿色主题 */
.app-tabbar {
  background: rgba(11, 40, 40, 0.95) !important;
  backdrop-filter: blur(40px) saturate(150%) !important;
  -webkit-backdrop-filter: blur(40px) saturate(150%) !important;
  border-top: 1px solid rgba(30, 123, 120, 0.3) !important;
}

:deep(.van-tabbar-item) {
  color: #1E7B78 !important;
  background: transparent !important;
}

:deep(.van-tabbar-item--active) {
  color: #27A5A2 !important;
}

:deep(.van-tabbar-item__icon) {
  font-size: 22px !important;
}

/* 页面切换动画 */
.fade-enter-active {
  transition: opacity 0.3s cubic-bezier(0.4, 0, 0.2, 1), 
              transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.fade-leave-active {
  transition: opacity 0.2s cubic-bezier(0.4, 0, 0.2, 1), 
              transform 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}

.fade-enter-from {
  opacity: 0;
  transform: translateY(10px);
}

.fade-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}
</style>
