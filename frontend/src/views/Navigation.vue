<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useNavigationStore } from '@/stores/navigation'
import NavigationMap from '@/components/NavigationMap.vue'

const router = useRouter()
const store = useNavigationStore()

// 当前显示的楼层
const currentDisplayFloor = ref<number | null>(null)

// 视图模式
const viewMode = ref<'map' | 'list'>('list')

// 计算属性
const hasRoute = computed(() => store.hasRoute)
const steps = computed(() => store.steps)
const totalDistance = computed(() => store.totalDistance)
const floorsInvolved = computed(() => store.floorsInvolved)

// 起点和终点
const startNode = computed(() => store.currentLocation)
const endNode = computed(() => store.destination)

// 格式化距离
const formatDistance = (distance: number) => {
  if (distance < 1000) {
    return `${Math.round(distance)} 米`
  }
  return `${(distance / 1000).toFixed(1)} 公里`
}

// 估算时间
const estimatedTime = computed(() => {
  const seconds = totalDistance.value / 1.2
  if (seconds < 60) {
    return `约 ${Math.round(seconds)} 秒`
  }
  return `约 ${Math.round(seconds / 60)} 分钟`
})

// 获取步骤图标类型
const getStepType = (step: typeof steps.value[0]) => {
  if (step.edge_type === 'stairs') return 'stairs'
  if (step.edge_type === 'lifts') return 'lift'
  return 'walk'
}

// 初始化
onMounted(() => {
  if (!hasRoute.value) {
    router.replace('/')
    return
  }
  
  if (floorsInvolved.value.length > 0) {
    currentDisplayFloor.value = floorsInvolved.value[0]
  }
})

// 返回首页
const goBack = () => {
  store.clearRoute()
  router.push('/')
}
</script>

<template>
  <div class="navigation-page">
    <!-- 顶部导航栏 -->
    <header class="nav-header">
      <button class="back-btn" @click="goBack">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M19 12H5M12 19l-7-7 7-7"/>
        </svg>
      </button>
      <h1 class="header-title">导航详情</h1>
      <div class="header-spacer"></div>
    </header>
    
    <div class="content" v-if="hasRoute">
      <!-- 路线概览卡片 -->
      <div class="overview-card glass-card slide-up">
        <div class="route-endpoints">
          <div class="endpoint start">
            <div class="endpoint-dot start"></div>
            <div class="endpoint-info">
              <span class="endpoint-label">起点</span>
              <span class="endpoint-name">{{ startNode?.name }}</span>
            </div>
          </div>
          <div class="route-line">
            <div class="line-track"></div>
          </div>
          <div class="endpoint end">
            <div class="endpoint-dot end"></div>
            <div class="endpoint-info">
              <span class="endpoint-label">终点</span>
              <span class="endpoint-name">{{ endNode?.name }}</span>
            </div>
          </div>
        </div>
        
        <div class="route-stats">
          <div class="stat-item">
            <div class="stat-icon">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="12" cy="12" r="10"/>
                <polyline points="12 6 12 12 16 14"/>
              </svg>
            </div>
            <div class="stat-content">
              <span class="stat-value">{{ estimatedTime }}</span>
              <span class="stat-label">预计时间</span>
            </div>
          </div>
          <div class="stat-divider"></div>
          <div class="stat-item">
            <div class="stat-icon">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M17 3l4 4-4 4"/>
                <path d="M3 11V9a4 4 0 014-4h14"/>
                <path d="M7 21l-4-4 4-4"/>
                <path d="M21 13v2a4 4 0 01-4 4H3"/>
              </svg>
            </div>
            <div class="stat-content">
              <span class="stat-value">{{ formatDistance(totalDistance) }}</span>
              <span class="stat-label">总距离</span>
            </div>
          </div>
          <div class="stat-divider"></div>
          <div class="stat-item">
            <div class="stat-icon">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <rect x="3" y="3" width="7" height="7"/>
                <rect x="14" y="3" width="7" height="7"/>
                <rect x="14" y="14" width="7" height="7"/>
                <rect x="3" y="14" width="7" height="7"/>
              </svg>
            </div>
            <div class="stat-content">
              <span class="stat-value">{{ floorsInvolved.join(', ') }}F</span>
              <span class="stat-label">经过楼层</span>
            </div>
          </div>
        </div>
      </div>
      
      <!-- 视图切换 -->
      <div class="view-switch">
        <button
          :class="['switch-btn', { active: viewMode === 'list' }]"
          @click="viewMode = 'list'"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="8" y1="6" x2="21" y2="6"/>
            <line x1="8" y1="12" x2="21" y2="12"/>
            <line x1="8" y1="18" x2="21" y2="18"/>
            <line x1="3" y1="6" x2="3.01" y2="6"/>
            <line x1="3" y1="12" x2="3.01" y2="12"/>
            <line x1="3" y1="18" x2="3.01" y2="18"/>
          </svg>
          步骤列表
        </button>
        <button
          :class="['switch-btn', { active: viewMode === 'map' }]"
          @click="viewMode = 'map'"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polygon points="1 6 1 22 8 18 16 22 23 18 23 2 16 6 8 2 1 6"/>
            <line x1="8" y1="2" x2="8" y2="18"/>
            <line x1="16" y1="6" x2="16" y2="22"/>
          </svg>
          地图视图
        </button>
      </div>
      
      <!-- 地图视图 -->
      <div v-if="viewMode === 'map'" class="map-section slide-up">
        <div v-if="floorsInvolved.length > 1" class="floor-tabs">
          <button
            v-for="floor in floorsInvolved"
            :key="floor"
            :class="['floor-tab', { active: currentDisplayFloor === floor }]"
            @click="currentDisplayFloor = floor"
          >
            {{ floor }}F
          </button>
        </div>
        
        <div class="map-card glass-card">
          <NavigationMap
            v-if="currentDisplayFloor !== null"
            :floor="currentDisplayFloor"
            :path-nodes="store.pathNodes"
            :start-node-id="startNode?.id"
            :end-node-id="endNode?.id"
          />
        </div>
      </div>
      
      <!-- 步骤列表 -->
      <div v-else class="steps-section">
        <!-- 起点卡片 -->
        <div class="step-card start-card slide-up">
          <div class="step-marker start">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="10"/>
              <circle cx="12" cy="12" r="3"/>
            </svg>
          </div>
          <div class="step-body">
            <div class="step-title">出发点</div>
            <div class="step-name">{{ startNode?.name }}</div>
            <div class="step-meta">
              <span class="meta-tag">{{ startNode?.floor }}F</span>
              <span class="meta-text">{{ startNode?.detail }}</span>
            </div>
          </div>
        </div>
        
        <!-- 导航步骤 -->
        <div
          v-for="(step, index) in steps"
          :key="index"
          class="step-card slide-up"
          :style="{ animationDelay: `${(index + 1) * 0.05}s` }"
        >
          <div class="step-connector"></div>
          <div class="step-marker" :class="getStepType(step)">
            <!-- 楼梯图标 -->
            <svg v-if="getStepType(step) === 'stairs'" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M4 20h4v-4h4v-4h4v-4h4"/>
            </svg>
            <!-- 电梯图标 -->
            <svg v-else-if="getStepType(step) === 'lift'" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="3" y="3" width="18" height="18" rx="2"/>
              <line x1="12" y1="8" x2="12" y2="16"/>
              <polyline points="8 12 12 8 16 12"/>
            </svg>
            <!-- 步行图标 -->
            <svg v-else width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M5 12h14M12 5l7 7-7 7"/>
            </svg>
          </div>
          <div class="step-body">
            <div class="step-instruction">{{ step.instruction }}</div>
            <div class="step-meta">
              <span v-if="step.distance > 0" class="meta-badge">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M5 12h14M12 5l7 7-7 7"/>
                </svg>
                {{ formatDistance(step.distance) }}
              </span>
              <span v-if="step.floor_change" class="meta-badge alt">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M12 19V5M5 12l7-7 7 7"/>
                </svg>
                {{ step.floor_change > 0 ? `上${step.floor_change}层` : `下${Math.abs(step.floor_change)}层` }}
              </span>
            </div>
          </div>
        </div>
        
        <!-- 终点卡片 -->
        <div class="step-card end-card slide-up">
          <div class="step-connector"></div>
          <div class="step-marker end">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0118 0z"/>
              <circle cx="12" cy="10" r="3"/>
            </svg>
          </div>
          <div class="step-body">
            <div class="step-title">到达目的地</div>
            <div class="step-name">{{ endNode?.name }}</div>
            <div class="step-meta">
              <span class="meta-tag">{{ endNode?.floor }}F</span>
              <span class="meta-text">{{ endNode?.detail }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
    
    <!-- 无路线 -->
    <div v-else class="empty-state">
      <div class="empty-icon">
        <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" opacity="0.3">
          <polygon points="1 6 1 22 8 18 16 22 23 18 23 2 16 6 8 2 1 6"/>
          <line x1="8" y1="2" x2="8" y2="18"/>
          <line x1="16" y1="6" x2="16" y2="22"/>
        </svg>
      </div>
      <h3 class="empty-title">暂无导航路线</h3>
      <p class="empty-desc">请先选择起点和终点</p>
      <button class="btn btn-primary" @click="router.push('/')">返回首页</button>
    </div>
  </div>
</template>

<style scoped>
.navigation-page {
  min-height: 100vh;
  background: var(--bg);
  padding-bottom: 90px;
  position: relative;
}

/* 背景光效 */
.navigation-page::before {
  content: '';
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  height: 350px;
  background: radial-gradient(ellipse at 50% -10%, rgba(0, 229, 255, 0.08) 0%, transparent 60%);
  pointer-events: none;
  z-index: 0;
}

/* ========== 顶部导航 - iOS 26 玻璃态 ========== */
.nav-header {
  display: flex;
  align-items: center;
  padding: 18px 20px;
  padding-top: max(18px, env(safe-area-inset-top));
  background: linear-gradient(180deg,
    rgba(15, 25, 50, 0.9) 0%,
    rgba(10, 20, 40, 0.8) 100%
  );
  backdrop-filter: blur(40px) saturate(180%);
  -webkit-backdrop-filter: blur(40px) saturate(180%);
  border-bottom: 1px solid rgba(0, 229, 255, 0.1);
  position: sticky;
  top: 0;
  z-index: 100;
}

.nav-header::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(0, 229, 255, 0.2), transparent);
}

.back-btn {
  width: 42px;
  height: 42px;
  border: 1px solid rgba(0, 229, 255, 0.12);
  border-radius: 12px;
  background: linear-gradient(135deg, rgba(15, 30, 55, 0.6) 0%, rgba(10, 25, 45, 0.5) 100%);
  backdrop-filter: blur(10px);
  color: var(--text);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 280ms cubic-bezier(0.25, 0.46, 0.45, 0.94);
}

.back-btn:hover {
  background: linear-gradient(135deg, rgba(20, 40, 70, 0.7) 0%, rgba(15, 35, 60, 0.6) 100%);
  border-color: rgba(0, 229, 255, 0.25);
  transform: translateX(-3px);
  box-shadow: 0 0 15px rgba(0, 229, 255, 0.15);
}

.header-title {
  flex: 1;
  text-align: center;
  font-size: 18px;
  font-weight: 700;
  background: linear-gradient(135deg, #ffffff 0%, #00e5ff 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  margin: 0;
  letter-spacing: -0.02em;
}

.header-spacer {
  width: 42px;
}

.content {
  padding: 20px;
  position: relative;
  z-index: 1;
}

/* ========== 概览卡片 - 高级玻璃态 ========== */
.overview-card {
  padding: 26px;
  margin-bottom: 24px;
}

.glass-card {
  background: linear-gradient(135deg, rgba(15, 30, 60, 0.6) 0%, rgba(10, 25, 50, 0.5) 100%);
  border: 1px solid rgba(0, 229, 255, 0.1);
  border-radius: 24px;
  backdrop-filter: blur(40px) saturate(180%);
  -webkit-backdrop-filter: blur(40px) saturate(180%);
  position: relative;
  overflow: hidden;
}

.glass-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 1px;
  background: linear-gradient(90deg,
    transparent 0%,
    rgba(255, 255, 255, 0.06) 20%,
    rgba(0, 229, 255, 0.2) 50%,
    rgba(255, 255, 255, 0.06) 80%,
    transparent 100%
  );
}

.route-endpoints {
  display: flex;
  flex-direction: column;
  align-items: center;
  margin-bottom: 24px;
}

.endpoint {
  display: flex;
  align-items: center;
  gap: 16px;
  width: 100%;
  padding: 16px 20px;
  background: linear-gradient(135deg, rgba(15, 30, 55, 0.4) 0%, rgba(10, 25, 45, 0.3) 100%);
  border: 1px solid rgba(255, 255, 255, 0.04);
  border-radius: 16px;
  transition: all 280ms ease;
}

.endpoint:hover {
  background: linear-gradient(135deg, rgba(20, 40, 65, 0.5) 0%, rgba(15, 35, 55, 0.4) 100%);
}

.endpoint-dot {
  width: 14px;
  height: 14px;
  border-radius: 50%;
  flex-shrink: 0;
  position: relative;
}

.endpoint-dot::after {
  content: '';
  position: absolute;
  inset: -4px;
  border-radius: 50%;
  opacity: 0.3;
  animation: pulse-ring 2s ease-in-out infinite;
}

@keyframes pulse-ring {
  0%, 100% { transform: scale(1); opacity: 0.3; }
  50% { transform: scale(1.4); opacity: 0; }
}

.endpoint-dot.start {
  background: linear-gradient(135deg, #7a8ba8 0%, #5a6b88 100%);
  box-shadow: 0 0 12px rgba(122, 139, 168, 0.4);
}

.endpoint-dot.start::after {
  background: #7a8ba8;
}

.endpoint-dot.end {
  background: linear-gradient(135deg, #00e5ff 0%, #00ffc8 100%);
  box-shadow: 0 0 15px rgba(0, 229, 255, 0.5);
}

.endpoint-dot.end::after {
  background: #00e5ff;
}

.endpoint-info {
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.endpoint-label {
  font-size: 11px;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.8px;
  font-weight: 600;
}

.endpoint-name {
  font-size: 17px;
  font-weight: 700;
  color: var(--text);
}

.route-line {
  width: 2px;
  height: 24px;
  margin: 6px 0;
  position: relative;
  border-radius: 1px;
  overflow: hidden;
}

.line-track {
  position: absolute;
  inset: 0;
  background: linear-gradient(180deg, #7a8ba8 0%, #00e5ff 100%);
  animation: line-flow 1.5s ease-in-out infinite;
}

@keyframes line-flow {
  0% { opacity: 0.4; }
  50% { opacity: 1; }
  100% { opacity: 0.4; }
}

.route-stats {
  display: flex;
  align-items: stretch;
  background: linear-gradient(135deg, rgba(10, 20, 40, 0.4) 0%, rgba(5, 15, 30, 0.3) 100%);
  border: 1px solid rgba(255, 255, 255, 0.03);
  border-radius: 18px;
  padding: 20px;
}

.stat-item {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 14px;
}

.stat-icon {
  width: 42px;
  height: 42px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, rgba(0, 229, 255, 0.1) 0%, rgba(0, 255, 200, 0.06) 100%);
  border: 1px solid rgba(0, 229, 255, 0.12);
  border-radius: 12px;
  color: var(--primary);
  flex-shrink: 0;
  transition: all 280ms ease;
}

.stat-item:hover .stat-icon {
  box-shadow: 0 0 15px rgba(0, 229, 255, 0.2);
}

.stat-content {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.stat-value {
  font-size: 16px;
  font-weight: 700;
  color: var(--text);
}

.stat-label {
  font-size: 11px;
  color: var(--text-muted);
  font-weight: 500;
}

.stat-divider {
  width: 1px;
  background: linear-gradient(180deg, transparent, rgba(0, 229, 255, 0.15), transparent);
  margin: 0 18px;
}

/* ========== 视图切换 - 玻璃态选项卡 ========== */
.view-switch {
  display: flex;
  gap: 6px;
  margin-bottom: 24px;
  background: linear-gradient(135deg, rgba(10, 20, 40, 0.6) 0%, rgba(5, 15, 30, 0.5) 100%);
  backdrop-filter: blur(16px);
  padding: 6px;
  border-radius: 16px;
  border: 1px solid rgba(255, 255, 255, 0.04);
}

.switch-btn {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 14px 18px;
  font-size: 14px;
  font-weight: 600;
  border: none;
  border-radius: 12px;
  background: transparent;
  color: var(--text-muted);
  cursor: pointer;
  transition: all 280ms ease;
}

.switch-btn:hover {
  color: var(--text);
}

.switch-btn.active {
  background: linear-gradient(135deg, rgba(0, 229, 255, 0.15) 0%, rgba(0, 255, 200, 0.1) 100%);
  color: var(--primary);
  box-shadow: 0 0 15px rgba(0, 229, 255, 0.15);
}

/* ========== 楼层选择 ========== */
.floor-tabs {
  display: flex;
  gap: 12px;
  margin-bottom: 18px;
  flex-wrap: wrap;
}

.floor-tab {
  padding: 13px 22px;
  font-size: 14px;
  font-weight: 700;
  border: 1px solid rgba(0, 229, 255, 0.1);
  border-radius: 12px;
  background: linear-gradient(135deg, rgba(15, 30, 55, 0.5) 0%, rgba(10, 25, 45, 0.4) 100%);
  backdrop-filter: blur(10px);
  color: var(--text-muted);
  cursor: pointer;
  transition: all 280ms ease;
}

.floor-tab:hover {
  background: linear-gradient(135deg, rgba(20, 40, 70, 0.6) 0%, rgba(15, 35, 60, 0.5) 100%);
  color: var(--text);
  border-color: rgba(0, 229, 255, 0.2);
}

.floor-tab.active {
  background: linear-gradient(135deg, #00e5ff 0%, #00ffc8 100%);
  border-color: transparent;
  color: #050810;
  box-shadow: 0 4px 20px rgba(0, 229, 255, 0.35);
}

/* ========== 地图卡片 ========== */
.map-card {
  height: 440px;
  padding: 0;
  overflow: hidden;
}

/* ========== 步骤列表 ========== */
.steps-section {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.step-card {
  position: relative;
  display: flex;
  align-items: flex-start;
  gap: 18px;
  padding: 22px;
  background: linear-gradient(135deg, rgba(15, 30, 60, 0.5) 0%, rgba(10, 25, 50, 0.4) 100%);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid rgba(0, 229, 255, 0.06);
  border-radius: 20px;
  transition: all 300ms cubic-bezier(0.25, 0.46, 0.45, 0.94);
}

.step-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.04), transparent);
}

.step-card:hover {
  background: linear-gradient(135deg, rgba(20, 40, 70, 0.6) 0%, rgba(15, 35, 60, 0.5) 100%);
  border-color: rgba(0, 229, 255, 0.15);
  transform: translateX(6px);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.35);
}

.step-connector {
  position: absolute;
  left: 40px;
  top: -14px;
  width: 2px;
  height: 14px;
  background: linear-gradient(180deg, transparent, rgba(0, 229, 255, 0.3));
  border-radius: 1px;
}

.step-card:first-child .step-connector {
  display: none;
}

.step-marker {
  width: 44px;
  height: 44px;
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, rgba(255, 255, 255, 0.06) 0%, rgba(255, 255, 255, 0.03) 100%);
  border: 1px solid rgba(255, 255, 255, 0.06);
  color: var(--text-muted);
  flex-shrink: 0;
  transition: all 280ms ease;
}

.step-marker.start {
  background: linear-gradient(135deg, rgba(122, 139, 168, 0.2) 0%, rgba(90, 107, 136, 0.15) 100%);
  border-color: rgba(122, 139, 168, 0.25);
  color: #7a8ba8;
}

.step-marker.end {
  background: linear-gradient(135deg, rgba(0, 229, 255, 0.2) 0%, rgba(0, 255, 200, 0.15) 100%);
  border-color: rgba(0, 229, 255, 0.25);
  color: var(--primary);
  box-shadow: 0 0 15px rgba(0, 229, 255, 0.2);
}

.step-marker.stairs,
.step-marker.lift {
  background: linear-gradient(135deg, rgba(0, 229, 255, 0.15) 0%, rgba(0, 255, 200, 0.1) 100%);
  border-color: rgba(0, 229, 255, 0.2);
  color: var(--primary);
}

.step-card:hover .step-marker {
  box-shadow: 0 0 12px rgba(0, 229, 255, 0.15);
}

.step-body {
  flex: 1;
  min-width: 0;
}

.step-title {
  font-size: 11px;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.8px;
  margin-bottom: 5px;
  font-weight: 600;
}

.step-name {
  font-size: 18px;
  font-weight: 700;
  color: var(--text);
}

.step-instruction {
  font-size: 15px;
  font-weight: 500;
  color: var(--text);
  line-height: 1.6;
}

.step-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 12px;
}

.meta-tag {
  display: inline-flex;
  align-items: center;
  padding: 6px 14px;
  font-size: 12px;
  font-weight: 700;
  background: linear-gradient(135deg, rgba(0, 229, 255, 0.12) 0%, rgba(0, 255, 200, 0.08) 100%);
  border: 1px solid rgba(0, 229, 255, 0.15);
  color: var(--primary);
  border-radius: 10px;
}

.meta-text {
  font-size: 13px;
  color: var(--text-muted);
  line-height: 1.8;
}

.meta-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  font-size: 12px;
  font-weight: 600;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.06);
  color: var(--text-muted);
  border-radius: 10px;
}

.meta-badge.alt {
  background: linear-gradient(135deg, rgba(0, 229, 255, 0.1) 0%, rgba(0, 255, 200, 0.06) 100%);
  border-color: rgba(0, 229, 255, 0.15);
  color: var(--primary);
}

.start-card {
  border-left: 4px solid #7a8ba8;
}

.end-card {
  border-left: 4px solid transparent;
  border-image: linear-gradient(180deg, #00e5ff 0%, #00ffc8 100%) 1;
}

/* ========== 空状态 ========== */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 60vh;
  padding: 50px 20px;
  text-align: center;
}

.empty-icon {
  width: 100px;
  height: 100px;
  margin-bottom: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, rgba(15, 30, 55, 0.5) 0%, rgba(10, 25, 45, 0.4) 100%);
  border: 1px solid rgba(255, 255, 255, 0.05);
  border-radius: 28px;
  color: var(--text-light);
}

.empty-title {
  font-size: 24px;
  font-weight: 700;
  background: linear-gradient(135deg, #ffffff 0%, #00e5ff 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  margin: 0 0 12px;
}

.empty-desc {
  font-size: 15px;
  color: var(--text-muted);
  margin: 0 0 32px;
}

/* ========== 按钮 ========== */
.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 16px 32px;
  font-size: 15px;
  font-weight: 700;
  border: none;
  border-radius: 16px;
  cursor: pointer;
  transition: all 280ms cubic-bezier(0.25, 0.46, 0.45, 0.94);
  position: relative;
  overflow: hidden;
}

.btn-primary {
  background: linear-gradient(135deg, #00e5ff 0%, #00ffc8 100%);
  color: #050810;
  box-shadow: 0 4px 20px rgba(0, 229, 255, 0.35),
              inset 0 1px 0 rgba(255, 255, 255, 0.2);
}

.btn-primary::before {
  content: '';
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.3), transparent);
  transition: left 400ms ease;
}

.btn-primary:hover {
  box-shadow: 0 6px 28px rgba(0, 229, 255, 0.45),
              inset 0 1px 0 rgba(255, 255, 255, 0.25);
  transform: translateY(-2px);
}

.btn-primary:hover::before {
  left: 100%;
}

/* ========== 动画 ========== */
.slide-up {
  animation: slideUp 0.5s cubic-bezier(0.22, 1, 0.36, 1);
  animation-fill-mode: both;
}

@keyframes slideUp {
  from {
    opacity: 0;
    transform: translateY(24px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* ========== 移动端适配 ========== */
@media (max-width: 768px) {
  .content {
    padding: 16px;
  }

  .overview-card {
    padding: 22px;
  }

  .route-stats {
    flex-direction: column;
    gap: 16px;
  }

  .stat-divider {
    width: 100%;
    height: 1px;
    margin: 0;
  }

  .map-card {
    height: 360px;
  }

  .step-card {
    padding: 18px;
  }
}
</style>
