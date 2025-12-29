<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import type { MapInfo, NodeInfo } from '@/api'

interface Props {
  mapInfo: MapInfo
  nodes: NodeInfo[]
  editable?: boolean
  selectedNodeId?: string | null
}

const props = withDefaults(defineProps<Props>(), {
  editable: false,
  selectedNodeId: null,
})

const emit = defineEmits<{
  (e: 'node-drag-end', nodeId: string, x: number, y: number): void
  (e: 'node-click', nodeId: string): void
}>()

// Canvas 引用
const canvasRef = ref<HTMLCanvasElement | null>(null)
const containerRef = ref<HTMLDivElement | null>(null)

// 画布尺寸
const canvasWidth = ref(0)
const canvasHeight = ref(0)

// 缩放比例
const scale = ref(1)

// 拖拽状态
const isDragging = ref(false)
const draggingNodeId = ref<string | null>(null)
const dragOffset = ref({ x: 0, y: 0 })

// 节点半径
const NODE_RADIUS = 12

// 计算实际显示尺寸
const displaySize = computed(() => {
  if (!props.mapInfo.width || !props.mapInfo.height) {
    return { width: 0, height: 0, scale: 1 }
  }
  
  const containerWidth = containerRef.value?.clientWidth || 300
  const maxHeight = 400
  
  const widthScale = containerWidth / props.mapInfo.width
  const heightScale = maxHeight / props.mapInfo.height
  
  const s = Math.min(widthScale, heightScale, 1)
  
  return {
    width: props.mapInfo.width * s,
    height: props.mapInfo.height * s,
    scale: s,
  }
})

// 图片加载
const mapImage = ref<HTMLImageElement | null>(null)
const imageLoaded = ref(false)

const loadImage = () => {
  const img = new Image()
  img.crossOrigin = 'anonymous'
  img.onload = () => {
    mapImage.value = img
    imageLoaded.value = true
    draw()
  }
  img.onerror = () => {
    console.error('Failed to load map image:', props.mapInfo.image_url)
  }
  img.src = props.mapInfo.image_url
}

// 绘制画布
const draw = () => {
  const canvas = canvasRef.value
  if (!canvas || !mapImage.value) return
  
  const ctx = canvas.getContext('2d')
  if (!ctx) return
  
  const { width, height, scale: s } = displaySize.value
  scale.value = s
  
  // 设置画布尺寸
  canvas.width = width
  canvas.height = height
  canvasWidth.value = width
  canvasHeight.value = height
  
  // 清空画布
  ctx.clearRect(0, 0, width, height)
  
  // 绘制底图
  ctx.drawImage(mapImage.value, 0, 0, width, height)
  
  // 绘制节点
  for (const node of props.nodes) {
    if (node.x === null || node.x === undefined || 
        node.y === null || node.y === undefined) {
      continue
    }
    
    const x = node.x * s
    const y = node.y * s
    
    // 节点样式
    const isSelected = node.id === props.selectedNodeId
    const isDraggingThis = draggingNodeId.value === node.id
    
    // 绘制节点圆点
    ctx.beginPath()
    ctx.arc(x, y, NODE_RADIUS, 0, Math.PI * 2)
    
    if (isDraggingThis) {
      ctx.fillStyle = '#ff9800'
    } else if (isSelected) {
      ctx.fillStyle = '#1989fa'
    } else {
      ctx.fillStyle = '#07c160'
    }
    
    ctx.fill()
    
    // 绘制边框
    ctx.strokeStyle = '#fff'
    ctx.lineWidth = 2
    ctx.stroke()
    
    // 绘制节点名称
    ctx.font = '12px sans-serif'
    ctx.fillStyle = '#323233'
    ctx.textAlign = 'center'
    ctx.fillText(node.id, x, y + NODE_RADIUS + 14)
  }
}

// 坐标转换：屏幕坐标 -> 底图坐标
const screenToMap = (screenX: number, screenY: number) => {
  const canvas = canvasRef.value
  if (!canvas) return { x: 0, y: 0 }
  
  const rect = canvas.getBoundingClientRect()
  const x = (screenX - rect.left) / scale.value
  const y = (screenY - rect.top) / scale.value
  
  return { x, y }
}

// 查找点击的节点
const findNodeAtPosition = (screenX: number, screenY: number): NodeInfo | null => {
  const { x, y } = screenToMap(screenX, screenY)
  const hitRadius = NODE_RADIUS / scale.value + 5
  
  for (const node of props.nodes) {
    if (node.x === null || node.x === undefined || 
        node.y === null || node.y === undefined) {
      continue
    }
    
    const dx = node.x - x
    const dy = node.y - y
    const distance = Math.sqrt(dx * dx + dy * dy)
    
    if (distance <= hitRadius) {
      return node
    }
  }
  
  return null
}

// 鼠标/触摸事件处理
const handlePointerDown = (e: MouseEvent | TouchEvent) => {
  if (!props.editable) return
  
  const clientX = 'touches' in e ? e.touches[0].clientX : e.clientX
  const clientY = 'touches' in e ? e.touches[0].clientY : e.clientY
  
  const node = findNodeAtPosition(clientX, clientY)
  
  if (node) {
    isDragging.value = true
    draggingNodeId.value = node.id
    
    const { x, y } = screenToMap(clientX, clientY)
    dragOffset.value = {
      x: (node.x || 0) - x,
      y: (node.y || 0) - y,
    }
    
    e.preventDefault()
  }
}

const handlePointerMove = (e: MouseEvent | TouchEvent) => {
  if (!isDragging.value || !draggingNodeId.value) return
  
  const clientX = 'touches' in e ? e.touches[0].clientX : e.clientX
  const clientY = 'touches' in e ? e.touches[0].clientY : e.clientY
  
  const { x, y } = screenToMap(clientX, clientY)
  
  // 更新节点位置
  const node = props.nodes.find(n => n.id === draggingNodeId.value)
  if (node) {
    node.x = Math.max(0, Math.min(props.mapInfo.width || 0, x + dragOffset.value.x))
    node.y = Math.max(0, Math.min(props.mapInfo.height || 0, y + dragOffset.value.y))
    draw()
  }
  
  e.preventDefault()
}

const handlePointerUp = (e: MouseEvent | TouchEvent) => {
  if (isDragging.value && draggingNodeId.value) {
    const node = props.nodes.find(n => n.id === draggingNodeId.value)
    if (node && node.x !== undefined && node.y !== undefined) {
      emit('node-drag-end', draggingNodeId.value, node.x, node.y)
    }
  }
  
  isDragging.value = false
  draggingNodeId.value = null
}

const handleClick = (e: MouseEvent) => {
  if (isDragging.value) return
  
  const node = findNodeAtPosition(e.clientX, e.clientY)
  if (node) {
    emit('node-click', node.id)
  }
}

// 监听数据变化
watch(() => props.mapInfo.image_url, () => {
  imageLoaded.value = false
  loadImage()
})

watch(() => props.nodes, () => {
  if (imageLoaded.value) {
    draw()
  }
}, { deep: true })

watch(() => props.selectedNodeId, () => {
  if (imageLoaded.value) {
    draw()
  }
})

// 窗口大小变化
const handleResize = () => {
  nextTick(() => {
    if (imageLoaded.value) {
      draw()
    }
  })
}

onMounted(() => {
  loadImage()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
})
</script>

<template>
  <div ref="containerRef" class="map-canvas-container">
    <canvas
      ref="canvasRef"
      :width="canvasWidth"
      :height="canvasHeight"
      @mousedown="handlePointerDown"
      @mousemove="handlePointerMove"
      @mouseup="handlePointerUp"
      @mouseleave="handlePointerUp"
      @touchstart="handlePointerDown"
      @touchmove="handlePointerMove"
      @touchend="handlePointerUp"
      @click="handleClick"
    />
    
    <div v-if="!imageLoaded" class="loading-overlay">
      <van-loading type="spinner" size="24px" />
      <span>加载中...</span>
    </div>
  </div>
</template>

<style scoped>
.map-canvas-container {
  position: relative;
  width: 100%;
  overflow: hidden;
}

canvas {
  display: block;
  max-width: 100%;
  cursor: default;
}

.map-canvas-container[data-editable="true"] canvas {
  cursor: grab;
}

.map-canvas-container[data-editable="true"] canvas:active {
  cursor: grabbing;
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
  background: rgba(255, 255, 255, 0.8);
  color: #969799;
  font-size: 14px;
}
</style>

