<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useNavigationStore } from '@/stores/navigation'
import type { PathNode, MapInfo } from '@/api'

interface Props {
  floor: number
  pathNodes: PathNode[]
  startNodeId?: string
  endNodeId?: string
}

const props = defineProps<Props>()

const store = useNavigationStore()

// Canvas 引用
const canvasRef = ref<HTMLCanvasElement | null>(null)
const containerRef = ref<HTMLDivElement | null>(null)

// 地图信息
const mapInfo = ref<MapInfo | null>(null)
const mapImage = ref<HTMLImageElement | null>(null)
const imageLoaded = ref(false)

// 节点半径
const NODE_RADIUS = 10
const PATH_LINE_WIDTH = 4

// 缩放比例
const scale = ref(1)

// 加载地图信息
const loadMapInfo = async () => {
  mapInfo.value = await store.getMapInfo(props.floor)
  if (mapInfo.value) {
    loadImage()
  }
}

// 加载图片
const loadImage = () => {
  if (!mapInfo.value) return
  
  const img = new Image()
  img.crossOrigin = 'anonymous'
  img.onload = () => {
    mapImage.value = img
    imageLoaded.value = true
    draw()
  }
  img.onerror = () => {
    console.error('Failed to load map image')
  }
  img.src = mapInfo.value.image_url
}

// 计算显示尺寸
const displaySize = computed(() => {
  if (!mapInfo.value?.width || !mapInfo.value?.height) {
    return { width: 300, height: 200, scale: 1 }
  }
  
  const containerWidth = containerRef.value?.clientWidth || 300
  const maxHeight = 350
  
  const widthScale = containerWidth / mapInfo.value.width
  const heightScale = maxHeight / mapInfo.value.height
  
  const s = Math.min(widthScale, heightScale, 1)
  
  return {
    width: mapInfo.value.width * s,
    height: mapInfo.value.height * s,
    scale: s,
  }
})

// 获取当前楼层的路径节点
const currentFloorNodes = computed(() => {
  return props.pathNodes.filter(node => node.floor === props.floor)
})

// 绘制
const draw = () => {
  const canvas = canvasRef.value
  if (!canvas || !mapImage.value || !mapInfo.value) return
  
  const ctx = canvas.getContext('2d')
  if (!ctx) return
  
  const { width, height, scale: s } = displaySize.value
  scale.value = s
  
  // 设置画布尺寸
  canvas.width = width
  canvas.height = height
  
  // 清空画布
  ctx.clearRect(0, 0, width, height)
  
  // 绘制底图
  ctx.drawImage(mapImage.value, 0, 0, width, height)
  
  // 过滤有坐标的节点
  const nodesWithCoords = currentFloorNodes.value.filter(
    n => n.x !== null && n.x !== undefined && n.y !== null && n.y !== undefined
  )
  
  // 绘制路径线
  if (nodesWithCoords.length >= 2) {
    ctx.beginPath()
    ctx.strokeStyle = '#ee0a24'
    ctx.lineWidth = PATH_LINE_WIDTH
    ctx.lineCap = 'round'
    ctx.lineJoin = 'round'
    
    const firstNode = nodesWithCoords[0]
    ctx.moveTo(firstNode.x! * s, firstNode.y! * s)
    
    for (let i = 1; i < nodesWithCoords.length; i++) {
      const node = nodesWithCoords[i]
      ctx.lineTo(node.x! * s, node.y! * s)
    }
    
    ctx.stroke()
  }
  
  // 绘制节点
  for (const node of nodesWithCoords) {
    const x = node.x! * s
    const y = node.y! * s
    
    const isStart = node.id === props.startNodeId
    const isEnd = node.id === props.endNodeId
    
    // 节点样式
    ctx.beginPath()
    ctx.arc(x, y, NODE_RADIUS, 0, Math.PI * 2)
    
    if (isStart) {
      ctx.fillStyle = '#07c160'  // 绿色起点
    } else if (isEnd) {
      ctx.fillStyle = '#ee0a24'  // 红色终点
    } else {
      ctx.fillStyle = 'rgba(25, 137, 250, 0.6)'  // 蓝色中间点
    }
    
    ctx.fill()
    
    // 边框
    ctx.strokeStyle = '#fff'
    ctx.lineWidth = 2
    ctx.stroke()
    
    // 起点/终点标签
    if (isStart || isEnd) {
      ctx.font = 'bold 10px sans-serif'
      ctx.fillStyle = '#fff'
      ctx.textAlign = 'center'
      ctx.textBaseline = 'middle'
      ctx.fillText(isStart ? '起' : '终', x, y)
    }
  }
  
  // 绘制图例
  drawLegend(ctx, width, height)
}

// 绘制图例
const drawLegend = (ctx: CanvasRenderingContext2D, width: number, height: number) => {
  const legendX = 10
  const legendY = height - 50
  
  ctx.fillStyle = 'rgba(255, 255, 255, 0.9)'
  ctx.fillRect(legendX, legendY, 100, 40)
  
  ctx.font = '11px sans-serif'
  ctx.textAlign = 'left'
  ctx.textBaseline = 'middle'
  
  // 起点
  ctx.beginPath()
  ctx.arc(legendX + 10, legendY + 12, 6, 0, Math.PI * 2)
  ctx.fillStyle = '#07c160'
  ctx.fill()
  ctx.fillStyle = '#323233'
  ctx.fillText('起点', legendX + 22, legendY + 12)
  
  // 终点
  ctx.beginPath()
  ctx.arc(legendX + 60, legendY + 12, 6, 0, Math.PI * 2)
  ctx.fillStyle = '#ee0a24'
  ctx.fill()
  ctx.fillStyle = '#323233'
  ctx.fillText('终点', legendX + 72, legendY + 12)
  
  // 路径
  ctx.strokeStyle = '#ee0a24'
  ctx.lineWidth = 3
  ctx.beginPath()
  ctx.moveTo(legendX + 10, legendY + 30)
  ctx.lineTo(legendX + 40, legendY + 30)
  ctx.stroke()
  ctx.fillStyle = '#323233'
  ctx.fillText('路径', legendX + 48, legendY + 30)
}

// 监听变化
watch(() => props.floor, () => {
  imageLoaded.value = false
  loadMapInfo()
})

watch(() => props.pathNodes, () => {
  if (imageLoaded.value) {
    draw()
  }
}, { deep: true })

onMounted(() => {
  loadMapInfo()
})
</script>

<template>
  <div ref="containerRef" class="navigation-map-container">
    <canvas ref="canvasRef" />
    
    <div v-if="!imageLoaded" class="loading-overlay">
      <van-loading type="spinner" size="24px" />
      <span>加载地图中...</span>
    </div>
    
    <div v-if="imageLoaded && currentFloorNodes.length === 0" class="no-path-hint">
      该楼层无路径经过
    </div>
  </div>
</template>

<style scoped>
.navigation-map-container {
  position: relative;
  width: 100%;
  min-height: 200px;
}

canvas {
  display: block;
  max-width: 100%;
  border-radius: 8px;
}

.loading-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  background: rgba(247, 248, 250, 0.9);
  color: #969799;
  font-size: 14px;
}

.no-path-hint {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  padding: 12px 24px;
  background: rgba(0, 0, 0, 0.6);
  color: #fff;
  border-radius: 8px;
  font-size: 14px;
}
</style>

