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
  background: #000000;
  padding-bottom: 80px;
}

/* ========== 顶部导航 ========== */
.nav-header {
  display: flex;
  align-items: center;
  padding: 18px 20px;
  background: rgba(28, 28, 30, 0.9);
  backdrop-filter: blur(40px) saturate(150%);
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
  position: sticky;
  top: 0;
  z-index: 100;
}

.back-btn {
  width: 40px;
  height: 40px;
  border: none;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.06);
  color: #f5f5f7;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.25s;
}

.back-btn:hover {
  background: rgba(255, 255, 255, 0.1);
  transform: translateX(-2px);
}

.header-title {
  flex: 1;
  text-align: center;
  font-size: 18px;
  font-weight: 600;
  color: #f5f5f7;
  margin: 0;
  letter-spacing: -0.02em;
}

.header-spacer {
  width: 40px;
}

.content {
  padding: 20px;
}

/* ========== 概览卡片 ========== */
.overview-card {
  padding: 24px;
  margin-bottom: 20px;
}

.glass-card {
  background: rgba(28, 28, 30, 0.85);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 18px;
  backdrop-filter: blur(40px) saturate(150%);
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
  gap: 14px;
  width: 100%;
  padding: 14px 18px;
  background: rgba(255, 255, 255, 0.04);
  border-radius: 14px;
}

.endpoint-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  flex-shrink: 0;
}

.endpoint-dot.start {
  background: #a1a1a6;
  box-shadow: 0 0 8px rgba(161, 161, 166, 0.4);
}

.endpoint-dot.end {
  background: #f5f5f7;
  box-shadow: 0 0 8px rgba(245, 245, 247, 0.4);
}

.endpoint-info {
  display: flex;
  flex-direction: column;
}

.endpoint-label {
  font-size: 11px;
  color: #636366;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.endpoint-name {
  font-size: 16px;
  font-weight: 600;
  color: #f5f5f7;
  margin-top: 2px;
}

.route-line {
  width: 1px;
  height: 20px;
  margin: 4px 0;
  position: relative;
}

.line-track {
  position: absolute;
  inset: 0;
  background: linear-gradient(180deg, #636366, #3a3a3c);
}

.route-stats {
  display: flex;
  align-items: stretch;
  background: rgba(255, 255, 255, 0.03);
  border-radius: 14px;
  padding: 18px;
}

.stat-item {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 12px;
}

.stat-icon {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.06);
  border-radius: 10px;
  color: #a1a1a6;
  flex-shrink: 0;
}

.stat-content {
  display: flex;
  flex-direction: column;
}

.stat-value {
  font-size: 15px;
  font-weight: 600;
  color: #f5f5f7;
}

.stat-label {
  font-size: 11px;
  color: #636366;
  margin-top: 2px;
}

.stat-divider {
  width: 1px;
  background: rgba(255, 255, 255, 0.06);
  margin: 0 16px;
}

/* ========== 视图切换 ========== */
.view-switch {
  display: flex;
  gap: 8px;
  margin-bottom: 20px;
  background: rgba(28, 28, 30, 0.6);
  padding: 6px;
  border-radius: 14px;
}

.switch-btn {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 14px 18px;
  font-size: 14px;
  font-weight: 500;
  border: none;
  border-radius: 10px;
  background: transparent;
  color: #636366;
  cursor: pointer;
  transition: all 0.25s;
}

.switch-btn:hover {
  color: #a1a1a6;
}

.switch-btn.active {
  background: rgba(255, 255, 255, 0.08);
  color: #f5f5f7;
}

/* ========== 楼层选择 ========== */
.floor-tabs {
  display: flex;
  gap: 10px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}

.floor-tab {
  padding: 12px 20px;
  font-size: 14px;
  font-weight: 600;
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 10px;
  background: rgba(28, 28, 30, 0.6);
  color: #636366;
  cursor: pointer;
  transition: all 0.25s;
}

.floor-tab:hover {
  background: rgba(255, 255, 255, 0.06);
  color: #a1a1a6;
}

.floor-tab.active {
  background: #f5f5f7;
  border-color: transparent;
  color: #000;
}

/* ========== 地图卡片 ========== */
.map-card {
  height: 420px;
  padding: 0;
  overflow: hidden;
}

/* ========== 步骤列表 ========== */
.steps-section {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.step-card {
  position: relative;
  display: flex;
  align-items: flex-start;
  gap: 16px;
  padding: 20px;
  background: rgba(28, 28, 30, 0.7);
  backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.04);
  border-radius: 16px;
  transition: all 0.25s;
}

.step-card:hover {
  background: rgba(28, 28, 30, 0.9);
  border-color: rgba(255, 255, 255, 0.08);
  transform: translateX(4px);
}

.step-connector {
  position: absolute;
  left: 37px;
  top: -12px;
  width: 1px;
  height: 12px;
  background: linear-gradient(180deg, transparent, #3a3a3c);
}

.step-card:first-child .step-connector {
  display: none;
}

.step-marker {
  width: 40px;
  height: 40px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.04);
  color: #a1a1a6;
  flex-shrink: 0;
}

.step-marker.start {
  background: rgba(161, 161, 166, 0.15);
  color: #a1a1a6;
}

.step-marker.end {
  background: rgba(245, 245, 247, 0.15);
  color: #f5f5f7;
}

.step-marker.stairs,
.step-marker.lift {
  background: rgba(100, 210, 255, 0.1);
  color: #64d2ff;
}

.step-body {
  flex: 1;
  min-width: 0;
}

.step-title {
  font-size: 11px;
  color: #636366;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 4px;
}

.step-name {
  font-size: 17px;
  font-weight: 600;
  color: #f5f5f7;
}

.step-instruction {
  font-size: 15px;
  font-weight: 500;
  color: #f5f5f7;
  line-height: 1.5;
}

.step-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 10px;
}

.meta-tag {
  display: inline-flex;
  align-items: center;
  padding: 5px 12px;
  font-size: 12px;
  font-weight: 600;
  background: rgba(255, 255, 255, 0.06);
  color: #a1a1a6;
  border-radius: 8px;
}

.meta-text {
  font-size: 13px;
  color: #636366;
}

.meta-badge {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 5px 12px;
  font-size: 12px;
  font-weight: 500;
  background: rgba(255, 255, 255, 0.04);
  color: #a1a1a6;
  border-radius: 8px;
}

.meta-badge.alt {
  background: rgba(100, 210, 255, 0.08);
  color: #64d2ff;
}

.start-card {
  border-left: 3px solid #a1a1a6;
}

.end-card {
  border-left: 3px solid #f5f5f7;
}

/* ========== 空状态 ========== */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 60vh;
  padding: 40px 20px;
  text-align: center;
}

.empty-icon {
  margin-bottom: 24px;
  color: #3a3a3c;
}

.empty-title {
  font-size: 22px;
  font-weight: 600;
  color: #f5f5f7;
  margin: 0 0 10px;
}

.empty-desc {
  font-size: 15px;
  color: #636366;
  margin: 0 0 28px;
}

/* ========== 按钮 ========== */
.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 14px 28px;
  font-size: 15px;
  font-weight: 600;
  border: none;
  border-radius: 14px;
  cursor: pointer;
  transition: all 0.25s;
}

.btn-primary {
  background: #f5f5f7;
  color: #000;
}

.btn-primary:hover {
  background: #e5e5e7;
  transform: translateY(-2px);
}

/* ========== 动画 ========== */
.slide-up {
  animation: slideUp 0.4s cubic-bezier(0.4, 0, 0.2, 1);
}

@keyframes slideUp {
  from {
    opacity: 0;
    transform: translateY(20px);
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
    padding: 20px;
  }
  
  .route-stats {
    flex-direction: column;
    gap: 14px;
  }
  
  .stat-divider {
    width: 100%;
    height: 1px;
    margin: 0;
  }
  
  .map-card {
    height: 340px;
  }
}
</style>
