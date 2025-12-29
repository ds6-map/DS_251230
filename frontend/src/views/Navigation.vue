<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useNavigationStore } from '@/stores/navigation'
import NavigationMap from '@/components/NavigationMap.vue'

const router = useRouter()
const store = useNavigationStore()

// 当前显示的楼层
const currentDisplayFloor = ref<number | null>(null)

// 视图模式：map（地图）或 list（步骤列表）
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

// 估算时间（假设步行速度 1.2m/s）
const estimatedTime = computed(() => {
  const seconds = totalDistance.value / 1.2
  if (seconds < 60) {
    return `约 ${Math.round(seconds)} 秒`
  }
  return `约 ${Math.round(seconds / 60)} 分钟`
})

// 获取步骤图标类型
const getStepIconType = (index: number) => {
  if (index === 0) return 'start'
  if (index === steps.value.length - 1) return 'end'
  return 'normal'
}

// 获取步骤图标
const getStepIcon = (step: typeof steps.value[0]) => {
  if (step.edge_type === 'stairs') return '🚶'
  if (step.edge_type === 'lifts') return '🛗'
  return '➡️'
}

// 初始化
onMounted(() => {
  if (!hasRoute.value) {
    router.replace('/')
    return
  }
  
  // 默认显示第一个楼层
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
  <div class="navigation-page page-container">
    <van-nav-bar title="导航" left-arrow @click-left="goBack" />
    
    <div class="content" v-if="hasRoute">
      <!-- 路线概览 -->
      <div class="route-summary">
        <div class="summary-item">
          <span class="summary-label">总距离</span>
          <span class="summary-value">{{ formatDistance(totalDistance) }}</span>
        </div>
        <div class="summary-divider"></div>
        <div class="summary-item">
          <span class="summary-label">预计时间</span>
          <span class="summary-value">{{ estimatedTime }}</span>
        </div>
        <div class="summary-divider"></div>
        <div class="summary-item">
          <span class="summary-label">经过楼层</span>
          <span class="summary-value">{{ floorsInvolved.join(', ') }} 楼</span>
        </div>
      </div>
      
      <!-- 视图切换 -->
      <div class="view-switch">
        <van-button
          :type="viewMode === 'list' ? 'primary' : 'default'"
          size="small"
          @click="viewMode = 'list'"
        >
          步骤列表
        </van-button>
        <van-button
          :type="viewMode === 'map' ? 'primary' : 'default'"
          size="small"
          @click="viewMode = 'map'"
        >
          地图视图
        </van-button>
      </div>
      
      <!-- 地图视图 -->
      <div v-if="viewMode === 'map'" class="map-view">
        <!-- 楼层选择 -->
        <div class="floor-tabs" v-if="floorsInvolved.length > 1">
          <van-button
            v-for="floor in floorsInvolved"
            :key="floor"
            :type="currentDisplayFloor === floor ? 'primary' : 'default'"
            size="small"
            @click="currentDisplayFloor = floor"
          >
            {{ floor }}楼
          </van-button>
        </div>
        
        <NavigationMap
          v-if="currentDisplayFloor !== null"
          :floor="currentDisplayFloor"
          :path-nodes="store.pathNodes"
          :start-node-id="startNode?.id"
          :end-node-id="endNode?.id"
        />
      </div>
      
      <!-- 步骤列表 -->
      <div v-else class="steps-view">
        <!-- 起点 -->
        <div class="step-card start">
          <div class="step-icon start">
            <van-icon name="aim" />
          </div>
          <div class="step-content">
            <div class="step-title">起点</div>
            <div class="step-name">{{ startNode?.name }}</div>
            <div class="step-detail">{{ startNode?.detail }} · {{ startNode?.floor }}楼</div>
          </div>
        </div>
        
        <!-- 导航步骤 -->
        <div
          v-for="(step, index) in steps"
          :key="index"
          class="step-card"
        >
          <div class="step-connector"></div>
          <div :class="['step-icon', getStepIconType(index)]">
            {{ getStepIcon(step) }}
          </div>
          <div class="step-content">
            <div class="step-instruction">{{ step.instruction }}</div>
            <div class="step-meta">
              <span v-if="step.distance > 0">{{ formatDistance(step.distance) }}</span>
              <span v-if="step.floor_change">
                {{ step.floor_change > 0 ? `上${step.floor_change}层` : `下${Math.abs(step.floor_change)}层` }}
              </span>
            </div>
          </div>
        </div>
        
        <!-- 终点 -->
        <div class="step-card end">
          <div class="step-connector"></div>
          <div class="step-icon end">
            <van-icon name="location" />
          </div>
          <div class="step-content">
            <div class="step-title">终点</div>
            <div class="step-name">{{ endNode?.name }}</div>
            <div class="step-detail">{{ endNode?.detail }} · {{ endNode?.floor }}楼</div>
          </div>
        </div>
      </div>
    </div>
    
    <!-- 无路线 -->
    <van-empty v-else description="暂无导航路线">
      <van-button type="primary" @click="router.push('/')">返回首页</van-button>
    </van-empty>
  </div>
</template>

<style scoped>
.navigation-page {
  background: #f7f8fa;
  padding-bottom: 80px;
}

.content {
  padding: 16px;
}

.route-summary {
  display: flex;
  background: #fff;
  border-radius: 12px;
  padding: 16px;
  margin-bottom: 16px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}

.summary-item {
  flex: 1;
  text-align: center;
}

.summary-label {
  display: block;
  font-size: 12px;
  color: #969799;
  margin-bottom: 4px;
}

.summary-value {
  font-size: 14px;
  font-weight: 600;
  color: #323233;
}

.summary-divider {
  width: 1px;
  background: #ebedf0;
  margin: 0 8px;
}

.view-switch {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
}

.floor-tabs {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
  flex-wrap: wrap;
}

.map-view {
  background: #fff;
  border-radius: 12px;
  padding: 16px;
}

.steps-view {
  position: relative;
}

.step-card {
  position: relative;
  display: flex;
  align-items: flex-start;
  background: #fff;
  border-radius: 12px;
  padding: 16px;
  margin-bottom: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}

.step-connector {
  position: absolute;
  left: 27px;
  top: -12px;
  width: 2px;
  height: 12px;
  background: #dcdee0;
}

.step-card:first-child .step-connector {
  display: none;
}

.step-icon {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  margin-right: 12px;
  flex-shrink: 0;
}

.step-icon.start {
  background: linear-gradient(135deg, #07c160, #06ad56);
  color: #fff;
}

.step-icon.end {
  background: linear-gradient(135deg, #ee0a24, #c90a1f);
  color: #fff;
}

.step-icon.normal {
  background: #f2f3f5;
}

.step-content {
  flex: 1;
  min-width: 0;
}

.step-title {
  font-size: 12px;
  color: #969799;
  margin-bottom: 2px;
}

.step-name {
  font-size: 16px;
  font-weight: 600;
  color: #323233;
}

.step-detail {
  font-size: 13px;
  color: #969799;
  margin-top: 2px;
}

.step-instruction {
  font-size: 14px;
  color: #323233;
  line-height: 1.5;
}

.step-meta {
  display: flex;
  gap: 12px;
  margin-top: 4px;
  font-size: 12px;
  color: #969799;
}
</style>

