<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useNavigationStore } from '@/stores/navigation'
import type { PathNode, MapInfo } from '@/api'
import ZoomableMapCanvas from './ZoomableMapCanvas.vue'

interface Props {
  floor: number
  pathNodes: PathNode[]
  startNodeId?: string
  endNodeId?: string
}

const props = defineProps<Props>()

const store = useNavigationStore()

// 地图信息
const mapInfo = ref<MapInfo | null>(null)
const loading = ref(true)

// 地图画布引用
const mapCanvasRef = ref<InstanceType<typeof ZoomableMapCanvas> | null>(null)

// 获取当前楼层的路径节点
const currentFloorNodes = computed(() => {
  return props.pathNodes.filter(node => node.floor === props.floor)
})

// 加载地图信息
const loadMapInfo = async () => {
  loading.value = true
  mapInfo.value = await store.getMapInfo(props.floor)
  loading.value = false
}

// 监听变化
watch(() => props.floor, () => {
  loadMapInfo()
})

onMounted(() => {
  loadMapInfo()
})
</script>

<template>
  <div class="navigation-map-wrapper">
    <ZoomableMapCanvas
      v-if="mapInfo && !loading"
      ref="mapCanvasRef"
      :map-info="mapInfo"
      :nodes="[]"
      :path-nodes="currentFloorNodes"
      :start-node-id="startNodeId"
      :end-node-id="endNodeId"
      :show-path="true"
      :editable="false"
    />
    
    <div v-else-if="loading" class="loading-state">
      <div class="loading-spinner"></div>
      <span>加载地图中...</span>
    </div>
    
    <van-empty v-else description="该楼层暂无地图" />
    
    <div v-if="mapInfo && currentFloorNodes.length === 0 && !loading" class="no-path-overlay">
      <span>该楼层无路径经过</span>
    </div>
    
    <!-- 图例 -->
    <div v-if="mapInfo && !loading" class="map-legend">
      <div class="legend-item">
        <span class="legend-dot start"></span>
        <span>起点</span>
      </div>
      <div class="legend-item">
        <span class="legend-dot end"></span>
        <span>终点</span>
      </div>
      <div class="legend-item">
        <span class="legend-line"></span>
        <span>路径</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.navigation-map-wrapper {
  position: relative;
  width: 100%;
  height: 100%;
  min-height: 300px;
  border-radius: 14px;
  overflow: hidden;
  background: #0a0a0a;
}

/* 加载状态 */
.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  min-height: 250px;
  background: #0a0a0a;
  color: #636366;
  font-size: 14px;
  gap: 14px;
}

.loading-spinner {
  width: 36px;
  height: 36px;
  border: 3px solid rgba(255, 255, 255, 0.06);
  border-top-color: #a1a1a6;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* 无路径提示 */
.no-path-overlay {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  padding: 14px 28px;
  background: rgba(28, 28, 30, 0.9);
  backdrop-filter: blur(12px);
  color: #f5f5f7;
  border-radius: 12px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  font-size: 14px;
  pointer-events: none;
}

/* 图例 */
.map-legend {
  position: absolute;
  left: 14px;
  bottom: 14px;
  display: flex;
  gap: 14px;
  padding: 10px 16px;
  background: rgba(28, 28, 30, 0.9);
  backdrop-filter: blur(16px);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 10px;
  font-size: 12px;
  color: #a1a1a6;
  pointer-events: none;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.legend-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
}

.legend-dot.start {
  background: #8e8e93;
  box-shadow: 0 0 6px rgba(142, 142, 147, 0.4);
}

.legend-dot.end {
  background: #f5f5f7;
  box-shadow: 0 0 6px rgba(245, 245, 247, 0.4);
}

.legend-line {
  width: 20px;
  height: 3px;
  background: #a1a1a6;
  border-radius: 2px;
}

/* 移动端适配 */
@media (max-width: 768px) {
  .navigation-map-wrapper {
    min-height: 250px;
  }
  
  .map-legend {
    left: 10px;
    bottom: 10px;
    gap: 12px;
    padding: 8px 12px;
    font-size: 11px;
  }
}
</style>
