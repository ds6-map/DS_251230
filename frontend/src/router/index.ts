import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    name: 'Home',
    component: () => import('@/views/Home.vue'),
    meta: { title: '首页' }
  },
  {
    path: '/recognition',
    name: 'Recognition',
    component: () => import('@/views/Recognition.vue'),
    meta: { title: '位置识别' }
  },
  {
    path: '/navigation',
    name: 'Navigation',
    component: () => import('@/views/Navigation.vue'),
    meta: { title: '导航' }
  },
  {
    path: '/editor',
    name: 'MapEditor',
    component: () => import('@/views/MapEditor.vue'),
    meta: { title: '地图编辑器' }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 路由标题
router.beforeEach((to, _from, next) => {
  const title = to.meta.title as string
  if (title) {
    document.title = `${title} - 校园导航`
  }
  next()
})

export default router

