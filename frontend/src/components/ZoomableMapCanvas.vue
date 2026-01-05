<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import type { MapInfo, NodeInfo } from '@/api'

interface Props {
  mapInfo: MapInfo
  nodes: NodeInfo[]
  editable?: boolean
  selectedNodeId?: string | null
  pathNodes?: { id: string; x?: number; y?: number }[]
  startNodeId?: string
  endNodeId?: string
  showPath?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  editable: false,
  selectedNodeId: null,
  pathNodes: () => [],
  showPath: false,
})

const emit = defineEmits<{
  (e: 'node-drag-end', nodeId: string, x: number, y: number): void
  (e: 'node-click', nodeId: string): void
}>()

// Canvas 引用
const canvasRef = ref<HTMLCanvasElement | null>(null)
const containerRef = ref<HTMLDivElement | null>(null)

// 视图状态
const viewState = ref({
  zoom: 1,
  minZoom: 0.5,
  maxZoom: 8,  // 增加最大缩放范围，从 4 提升到 8（800%）
  offsetX: 0,
  offsetY: 0,
})

// 画布尺寸
const canvasWidth = ref(0)
const canvasHeight = ref(0)

// 拖拽状态
const isDraggingNode = ref(false)
const draggingNodeId = ref<string | null>(null)
const dragOffset = ref({ x: 0, y: 0 })

// 平移拖拽状态
const isPanning = ref(false)
const panStart = ref({ x: 0, y: 0 })
const lastPanOffset = ref({ x: 0, y: 0 })

// 触摸缩放状态
const lastTouchDistance = ref(0)
const lastTouchCenter = ref({ x: 0, y: 0 })

// 节点半径
const NODE_RADIUS = 14
const PATH_LINE_WIDTH = 5

// 图片加载
const mapImage = ref<HTMLImageElement | null>(null)
const imageLoaded = ref(false)

// 容器尺寸
const containerSize = ref({ width: 0, height: 0 })

const updateContainerSize = () => {
  if (containerRef.value) {
    containerSize.value = {
      width: containerRef.value.clientWidth,
      height: containerRef.value.clientHeight,
    }
  }
}

// 计算画布基础尺寸（填满容器）
const baseSize = computed(() => {
  if (!props.mapInfo.width || !props.mapInfo.height) {
    return { width: containerSize.value.width || 400, height: containerSize.value.height || 400, scale: 1 }
  }
  
  const containerWidth = containerSize.value.width || 400
  const containerHeight = containerSize.value.height || 400
  
  const widthScale = containerWidth / props.mapInfo.width
  const heightScale = containerHeight / props.mapInfo.height
  
  const s = Math.min(widthScale, heightScale)
  
  return {
    width: props.mapInfo.width * s,
    height: props.mapInfo.height * s,
    scale: s,
  }
})

const loadImage = () => {
  const img = new Image()
  img.crossOrigin = 'anonymous'
  
  // 禁用图片解码时的压缩
  // 使用 decode() 方法确保图片完全加载后再显示
  img.onload = () => {
    // 确保图片完全解码
    if (img.decode) {
      img.decode().then(() => {
        mapImage.value = img
        imageLoaded.value = true
        // 初始化视图，让地图居中
        resetView()
        draw()
      }).catch((err) => {
        console.error('Image decode error:', err)
        // 即使解码失败也继续显示
        mapImage.value = img
        imageLoaded.value = true
        resetView()
        draw()
      })
    } else {
      // 不支持 decode() 的浏览器直接使用
      mapImage.value = img
      imageLoaded.value = true
      resetView()
      draw()
    }
  }
  img.onerror = () => {
    console.error('Failed to load map image:', props.mapInfo.image_url)
  }
  
  // 直接使用原始 URL，不添加任何压缩参数
  img.src = props.mapInfo.image_url
}

// 重置视图
const resetView = () => {
  viewState.value.zoom = 1
  viewState.value.offsetX = 0
  viewState.value.offsetY = 0
}

// 获取节点的显示坐标
const getNodeDisplayCoords = (node: NodeInfo | { id: string; x?: number; y?: number }) => {
  const hasCoords = node.x !== null && node.x !== undefined && 
                    node.y !== null && node.y !== undefined
  
  if (hasCoords) {
    return { x: node.x!, y: node.y!, hasCoords: true }
  }
  
  const centerX = (props.mapInfo.width || 300) / 2
  const centerY = (props.mapInfo.height || 300) / 2
  return { x: centerX, y: centerY, hasCoords: false }
}

// 世界坐标转屏幕坐标（返回逻辑坐标，绘制时会自动应用 dpr）
const worldToScreen = (worldX: number, worldY: number) => {
  const { scale } = baseSize.value
  const { zoom, offsetX, offsetY } = viewState.value
  
  return {
    x: worldX * scale * zoom + offsetX,
    y: worldY * scale * zoom + offsetY,
  }
}

// 屏幕坐标转世界坐标（传入屏幕坐标 clientX, clientY）
const screenToWorld = (screenX: number, screenY: number) => {
  const canvas = canvasRef.value
  if (!canvas) return { x: 0, y: 0 }
  
  const rect = canvas.getBoundingClientRect()
  // 转换为画布本地坐标
  const canvasLocalX = screenX - rect.left
  const canvasLocalY = screenY - rect.top
  
  const { scale } = baseSize.value
  const { zoom, offsetX, offsetY } = viewState.value
  
  return {
    x: (canvasLocalX - offsetX) / (scale * zoom),
    y: (canvasLocalY - offsetY) / (scale * zoom),
  }
}

// 绘制画布
const draw = () => {
  const canvas = canvasRef.value
  if (!canvas || !mapImage.value) return
  
  const ctx = canvas.getContext('2d', {
    alpha: false,  // 禁用透明度以提高性能
    desynchronized: true,  // 启用异步渲染
    willReadFrequently: false,  // 不频繁读取像素数据
  })
  if (!ctx) return
  
  const { width: containerWidth, height: containerHeight } = containerSize.value
  if (!containerWidth || !containerHeight) return
  
  // 设置画布尺寸（使用设备像素比以获得更高分辨率）
  // 在高缩放级别时，使用更高的 DPR 倍数以保持清晰度
  const baseDpr = window.devicePixelRatio || 1
  const zoomLevel = viewState.value.zoom
  // 当缩放超过 2 倍时，增加 DPR 倍数以保持清晰度
  const dprMultiplier = zoomLevel > 2 ? Math.min(2, 1 + (zoomLevel - 2) * 0.3) : 1
  const dpr = baseDpr * dprMultiplier
  canvas.width = containerWidth * dpr
  canvas.height = containerHeight * dpr
  canvas.style.width = `${containerWidth}px`
  canvas.style.height = `${containerHeight}px`
  canvasWidth.value = containerWidth
  canvasHeight.value = containerHeight
  
  // 缩放上下文以匹配设备像素比
  ctx.scale(dpr, dpr)
  
  // 启用高质量图像平滑
  ctx.imageSmoothingEnabled = true
  ctx.imageSmoothingQuality = 'high'  // 'low' | 'medium' | 'high'
  
  // 清空画布（深色背景）
  ctx.fillStyle = '#0a0a0a'
  ctx.fillRect(0, 0, containerWidth, containerHeight)
  
  // 保存状态
  ctx.save()
  
  // 应用变换
  const { scale } = baseSize.value
  const { zoom, offsetX, offsetY } = viewState.value
  const totalScale = scale * zoom
  
  ctx.translate(offsetX, offsetY)
  ctx.scale(totalScale, totalScale)
  
  // 绘制底图（使用原始尺寸，不压缩）
  ctx.drawImage(
    mapImage.value,
    0,
    0,
    props.mapInfo.width || mapImage.value.naturalWidth,
    props.mapInfo.height || mapImage.value.naturalHeight
  )
  
  // 绘制路径
  if (props.showPath && props.pathNodes.length >= 2) {
    const nodesWithCoords = props.pathNodes.filter(
      n => n.x !== null && n.x !== undefined && n.y !== null && n.y !== undefined
    )
    
    if (nodesWithCoords.length >= 2) {
      // 路径光晕效果 - 低饱和灰色
      ctx.save()
      ctx.strokeStyle = 'rgba(161, 161, 166, 0.3)'
      ctx.lineWidth = PATH_LINE_WIDTH * 3 / totalScale
      ctx.lineCap = 'round'
      ctx.lineJoin = 'round'
      
      ctx.beginPath()
      ctx.moveTo(nodesWithCoords[0].x!, nodesWithCoords[0].y!)
      for (let i = 1; i < nodesWithCoords.length; i++) {
        ctx.lineTo(nodesWithCoords[i].x!, nodesWithCoords[i].y!)
      }
      ctx.stroke()
      ctx.restore()
      
      // 主路径 - 低饱和灰色
      ctx.strokeStyle = '#a1a1a6'
      ctx.lineWidth = PATH_LINE_WIDTH / totalScale
      ctx.lineCap = 'round'
      ctx.lineJoin = 'round'
      
      ctx.beginPath()
      ctx.moveTo(nodesWithCoords[0].x!, nodesWithCoords[0].y!)
      for (let i = 1; i < nodesWithCoords.length; i++) {
        ctx.lineTo(nodesWithCoords[i].x!, nodesWithCoords[i].y!)
      }
      ctx.stroke()
    }
  }
  
  // 恢复状态（不缩放节点，保持固定大小）
  ctx.restore()
  
  // 绘制节点（使用屏幕坐标，保持固定大小）
  const nodesToDraw = props.showPath ? props.pathNodes : props.nodes
  
  for (const node of nodesToDraw) {
    const { x: nodeX, y: nodeY, hasCoords } = getNodeDisplayCoords(node)
    const { x: screenX, y: screenY } = worldToScreen(nodeX, nodeY)
    
    const isSelected = node.id === props.selectedNodeId
    const isDraggingThis = draggingNodeId.value === node.id
    const isStart = node.id === props.startNodeId
    const isEnd = node.id === props.endNodeId
    
    // 节点阴影
    ctx.save()
    ctx.shadowColor = 'rgba(0, 0, 0, 0.4)'
    ctx.shadowBlur = 8
    ctx.shadowOffsetY = 2
    
    // 绘制节点圆点
    ctx.beginPath()
    ctx.arc(screenX, screenY, NODE_RADIUS, 0, Math.PI * 2)
    
    if (isStart) {
      // 起点 - 灰色
      ctx.fillStyle = '#8e8e93'
    } else if (isEnd) {
      // 终点 - 亮灰/白
      ctx.fillStyle = '#f5f5f7'
    } else if (isDraggingThis) {
      ctx.fillStyle = '#a1a1a6'  // 拖拽中 - 中灰
    } else if (isSelected) {
      // 选中 - 亮灰
      ctx.fillStyle = '#d1d1d6'
    } else if (!hasCoords && props.editable) {
      ctx.fillStyle = '#636366'  // 未定位 - 暗灰
    } else {
      // 普通节点 - 中灰
      ctx.fillStyle = '#8e8e93'
    }
    
    ctx.fill()
    ctx.restore()
    
    // 绘制边框
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.6)'
    ctx.lineWidth = 2
    ctx.stroke()
    
    // 未定位的节点绘制脉冲动画边框
    if (!hasCoords && !isDraggingThis && props.editable) {
      ctx.beginPath()
      ctx.arc(screenX, screenY, NODE_RADIUS + 6, 0, Math.PI * 2)
      ctx.strokeStyle = 'rgba(142, 142, 147, 0.5)'
      ctx.lineWidth = 2
      ctx.setLineDash([4, 4])
      ctx.stroke()
      ctx.setLineDash([])
    }
    
    // 起点/终点标签
    if (isStart || isEnd) {
      ctx.font = 'bold 11px -apple-system, BlinkMacSystemFont, sans-serif'
      ctx.fillStyle = isEnd ? '#000' : '#fff'
      ctx.textAlign = 'center'
      ctx.textBaseline = 'middle'
      ctx.fillText(isStart ? '起' : '终', screenX, screenY)
    }
    
    // 绘制节点名称（仅在编辑模式或选中时显示）
    if (props.editable || isSelected || isStart || isEnd) {
      ctx.font = 'bold 11px -apple-system, BlinkMacSystemFont, sans-serif'
      ctx.fillStyle = '#d1d1d6'
      ctx.textAlign = 'center'
      ctx.shadowColor = 'rgba(0, 0, 0, 0.8)'
      ctx.shadowBlur = 4
      ctx.fillText(node.id, screenX, screenY + NODE_RADIUS + 14)
      ctx.shadowBlur = 0
    }
  }
  
  // 绘制缩放指示器
  drawZoomIndicator(ctx, containerWidth, containerHeight)
}

// 绘制缩放指示器
const drawZoomIndicator = (ctx: CanvasRenderingContext2D, width: number, height: number) => {
  const zoom = Math.round(viewState.value.zoom * 100)
  
  ctx.save()
  
  // 背景
  const padding = 12
  const text = `${zoom}%`
  ctx.font = 'bold 12px -apple-system, BlinkMacSystemFont, sans-serif'
  const textWidth = ctx.measureText(text).width
  
  const boxX = width - textWidth - padding * 2 - 12
  const boxY = 12
  const boxWidth = textWidth + padding * 2
  const boxHeight = 30
  
  // 圆角矩形（深色玻璃态背景）
  ctx.fillStyle = 'rgba(28, 28, 30, 0.9)'
  ctx.strokeStyle = 'rgba(255, 255, 255, 0.08)'
  ctx.lineWidth = 1
  ctx.beginPath()
  ctx.roundRect(boxX, boxY, boxWidth, boxHeight, 8)
  ctx.fill()
  ctx.stroke()
  
  // 文字（灰色主题）
  ctx.fillStyle = '#a1a1a6'
  ctx.textAlign = 'center'
  ctx.textBaseline = 'middle'
  ctx.fillText(text, boxX + boxWidth / 2, boxY + boxHeight / 2)
  
  ctx.restore()
}

// 查找点击的节点（传入的是相对于画布的坐标，已经减去了 rect.left/top）
const findNodeAtPosition = (canvasLocalX: number, canvasLocalY: number): NodeInfo | null => {
  const nodesToCheck = props.showPath ? [] : props.nodes
  
  const hitRadius = NODE_RADIUS + 8  // 增大点击范围
  
  for (const node of nodesToCheck) {
    const { x: nodeX, y: nodeY } = getNodeDisplayCoords(node)
    const { scale } = baseSize.value
    const { zoom, offsetX, offsetY } = viewState.value
    // 节点在画布上的位置
    const nodeCanvasX = nodeX * scale * zoom + offsetX
    const nodeCanvasY = nodeY * scale * zoom + offsetY
    
    const dx = nodeCanvasX - canvasLocalX
    const dy = nodeCanvasY - canvasLocalY
    const distance = Math.sqrt(dx * dx + dy * dy)
    
    if (distance <= hitRadius) {
      return node as NodeInfo
    }
  }
  
  return null
}

// 获取触摸点之间的距离
const getTouchDistance = (touches: TouchList) => {
  if (touches.length < 2) return 0
  const dx = touches[0].clientX - touches[1].clientX
  const dy = touches[0].clientY - touches[1].clientY
  return Math.sqrt(dx * dx + dy * dy)
}

// 获取触摸点中心
const getTouchCenter = (touches: TouchList) => {
  if (touches.length < 2) return { x: touches[0].clientX, y: touches[0].clientY }
  return {
    x: (touches[0].clientX + touches[1].clientX) / 2,
    y: (touches[0].clientY + touches[1].clientY) / 2,
  }
}

// 鼠标滚轮缩放
const handleWheel = (e: WheelEvent) => {
  e.preventDefault()
  
  const canvas = canvasRef.value
  if (!canvas) return
  
  const rect = canvas.getBoundingClientRect()
  const mouseX = e.clientX - rect.left
  const mouseY = e.clientY - rect.top
  
  // 计算缩放因子
  const zoomFactor = e.deltaY > 0 ? 0.9 : 1.1
  const newZoom = Math.max(
    viewState.value.minZoom,
    Math.min(viewState.value.maxZoom, viewState.value.zoom * zoomFactor)
  )
  
  // 以鼠标位置为中心缩放
  const zoomChange = newZoom / viewState.value.zoom
  viewState.value.offsetX = mouseX - (mouseX - viewState.value.offsetX) * zoomChange
  viewState.value.offsetY = mouseY - (mouseY - viewState.value.offsetY) * zoomChange
  viewState.value.zoom = newZoom
  
  draw()
}

// 鼠标/触摸事件处理
const handlePointerDown = (e: MouseEvent | TouchEvent) => {
  const clientX = 'touches' in e ? e.touches[0].clientX : e.clientX
  const clientY = 'touches' in e ? e.touches[0].clientY : e.clientY
  
  const canvas = canvasRef.value
  if (!canvas) return
  
  const rect = canvas.getBoundingClientRect()
  const canvasX = clientX - rect.left
  const canvasY = clientY - rect.top
  
  // 检查是否点击了节点（仅在编辑模式）
  if (props.editable) {
    const node = findNodeAtPosition(canvasX, canvasY)
    
    if (node) {
      isDraggingNode.value = true
      draggingNodeId.value = node.id
      
      const { x: nodeX, y: nodeY } = getNodeDisplayCoords(node)
      const worldPos = screenToWorld(clientX, clientY)
      dragOffset.value = {
        x: nodeX - worldPos.x,
        y: nodeY - worldPos.y,
      }
      
      e.preventDefault()
      return
    }
  }
  
  // 双指触摸缩放
  if ('touches' in e && e.touches.length === 2) {
    lastTouchDistance.value = getTouchDistance(e.touches)
    lastTouchCenter.value = getTouchCenter(e.touches)
    e.preventDefault()
    return
  }
  
  // 开始平移
  isPanning.value = true
  panStart.value = { x: clientX, y: clientY }
  lastPanOffset.value = { x: viewState.value.offsetX, y: viewState.value.offsetY }
}

const handlePointerMove = (e: MouseEvent | TouchEvent) => {
  const clientX = 'touches' in e ? e.touches[0].clientX : e.clientX
  const clientY = 'touches' in e ? e.touches[0].clientY : e.clientY
  
  // 节点拖拽
  if (isDraggingNode.value && draggingNodeId.value) {
    const worldPos = screenToWorld(clientX, clientY)
    const node = props.nodes.find(n => n.id === draggingNodeId.value)
    
    if (node) {
      node.x = Math.max(0, Math.min(props.mapInfo.width || 0, worldPos.x + dragOffset.value.x))
      node.y = Math.max(0, Math.min(props.mapInfo.height || 0, worldPos.y + dragOffset.value.y))
      draw()
    }
    
    e.preventDefault()
    return
  }
  
  // 双指触摸缩放
  if ('touches' in e && e.touches.length === 2) {
    const currentDistance = getTouchDistance(e.touches)
    const currentCenter = getTouchCenter(e.touches)
    
    if (lastTouchDistance.value > 0) {
      const scale = currentDistance / lastTouchDistance.value
      const newZoom = Math.max(
        viewState.value.minZoom,
        Math.min(viewState.value.maxZoom, viewState.value.zoom * scale)
      )
      
      const canvas = canvasRef.value
      if (canvas) {
        const rect = canvas.getBoundingClientRect()
        const centerX = currentCenter.x - rect.left
        const centerY = currentCenter.y - rect.top
        
        const zoomChange = newZoom / viewState.value.zoom
        viewState.value.offsetX = centerX - (centerX - viewState.value.offsetX) * zoomChange
        viewState.value.offsetY = centerY - (centerY - viewState.value.offsetY) * zoomChange
        viewState.value.zoom = newZoom
      }
    }
    
    lastTouchDistance.value = currentDistance
    lastTouchCenter.value = currentCenter
    e.preventDefault()
    draw()
    return
  }
  
  // 平移
  if (isPanning.value) {
    viewState.value.offsetX = lastPanOffset.value.x + (clientX - panStart.value.x)
    viewState.value.offsetY = lastPanOffset.value.y + (clientY - panStart.value.y)
    draw()
    e.preventDefault()
  }
}

const handlePointerUp = (e: MouseEvent | TouchEvent) => {
  if (isDraggingNode.value && draggingNodeId.value) {
    const node = props.nodes.find(n => n.id === draggingNodeId.value)
    if (node && node.x !== undefined && node.y !== undefined) {
      emit('node-drag-end', draggingNodeId.value, node.x, node.y)
    }
  }
  
  isDraggingNode.value = false
  draggingNodeId.value = null
  isPanning.value = false
  lastTouchDistance.value = 0
}

const handleClick = (e: MouseEvent) => {
  if (isPanning.value || isDraggingNode.value) return
  
  const canvas = canvasRef.value
  if (!canvas) return
  
  const rect = canvas.getBoundingClientRect()
  const canvasX = e.clientX - rect.left
  const canvasY = e.clientY - rect.top
  
  const node = findNodeAtPosition(canvasX, canvasY)
  if (node) {
    emit('node-click', node.id)
  }
}

// 缩放控制
const zoomIn = () => {
  const centerX = canvasWidth.value / 2
  const centerY = canvasHeight.value / 2
  
  const newZoom = Math.min(viewState.value.maxZoom, viewState.value.zoom * 1.3)
  const zoomChange = newZoom / viewState.value.zoom
  
  viewState.value.offsetX = centerX - (centerX - viewState.value.offsetX) * zoomChange
  viewState.value.offsetY = centerY - (centerY - viewState.value.offsetY) * zoomChange
  viewState.value.zoom = newZoom
  
  draw()
}

const zoomOut = () => {
  const centerX = canvasWidth.value / 2
  const centerY = canvasHeight.value / 2
  
  const newZoom = Math.max(viewState.value.minZoom, viewState.value.zoom / 1.3)
  const zoomChange = newZoom / viewState.value.zoom
  
  viewState.value.offsetX = centerX - (centerX - viewState.value.offsetX) * zoomChange
  viewState.value.offsetY = centerY - (centerY - viewState.value.offsetY) * zoomChange
  viewState.value.zoom = newZoom
  
  draw()
}

// 监听数据变化
watch(() => props.mapInfo.image_url, () => {
  imageLoaded.value = false
  loadImage()
})

watch(() => [props.nodes, props.pathNodes, props.selectedNodeId], () => {
  if (imageLoaded.value) {
    draw()
  }
}, { deep: true })

// 窗口大小变化
const handleResize = () => {
  nextTick(() => {
    updateContainerSize()
    if (imageLoaded.value) {
      draw()
    }
  })
}

onMounted(() => {
  updateContainerSize()
  loadImage()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
})

// 暴露方法给父组件
defineExpose({
  resetView,
  zoomIn,
  zoomOut,
})
</script>

<template>
  <div ref="containerRef" class="zoomable-map-container" :data-editable="editable">
    <canvas
      ref="canvasRef"
      :width="canvasWidth"
      :height="canvasHeight"
      @wheel="handleWheel"
      @mousedown="handlePointerDown"
      @mousemove="handlePointerMove"
      @mouseup="handlePointerUp"
      @mouseleave="handlePointerUp"
      @touchstart="handlePointerDown"
      @touchmove="handlePointerMove"
      @touchend="handlePointerUp"
      @click="handleClick"
    />
    
    <!-- 缩放控制按钮 -->
    <div class="zoom-controls">
      <button class="zoom-btn" @click="zoomIn" title="放大">
        <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="11" cy="11" r="8"/>
          <line x1="21" y1="21" x2="16.65" y2="16.65"/>
          <line x1="11" y1="8" x2="11" y2="14"/>
          <line x1="8" y1="11" x2="14" y2="11"/>
        </svg>
      </button>
      <button class="zoom-btn" @click="zoomOut" title="缩小">
        <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="11" cy="11" r="8"/>
          <line x1="21" y1="21" x2="16.65" y2="16.65"/>
          <line x1="8" y1="11" x2="14" y2="11"/>
        </svg>
      </button>
      <button class="zoom-btn" @click="resetView" title="重置">
        <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/>
          <path d="M3 3v5h5"/>
        </svg>
      </button>
    </div>
    
    <!-- 加载状态 -->
    <div v-if="!imageLoaded" class="loading-overlay">
      <div class="loading-spinner"></div>
      <span>加载地图中...</span>
    </div>
    
    <!-- 操作提示 -->
    <div class="help-hint" v-if="imageLoaded">
      <span>滚轮缩放 · 拖拽平移</span>
    </div>
  </div>
</template>

<style scoped>
/* ========== 夜间极简灰主题 ========== */
.zoomable-map-container {
  position: relative;
  width: 100%;
  height: 100%;
  min-height: 300px;
  overflow: hidden;
  background: #0a0a0a;
  border-radius: 14px;
  border: 1px solid rgba(255, 255, 255, 0.06);
}

canvas {
  display: block;
  width: 100%;
  height: 100%;
  cursor: grab;
  touch-action: none;
}

canvas:active {
  cursor: grabbing;
}

.zoomable-map-container[data-editable="true"] canvas {
  cursor: crosshair;
}

/* ========== 缩放控制 ========== */
.zoom-controls {
  position: absolute;
  right: 14px;
  bottom: 55px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  z-index: 10;
}

.zoom-btn {
  width: 38px;
  height: 38px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 10px;
  background: rgba(28, 28, 30, 0.9);
  color: #636366;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  backdrop-filter: blur(16px);
}

.zoom-btn:hover {
  border-color: rgba(255, 255, 255, 0.15);
  color: #f5f5f7;
  background: rgba(38, 38, 40, 0.95);
}

.zoom-btn:active {
  transform: scale(0.95);
}

/* ========== 加载状态 ========== */
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
  gap: 16px;
  background: rgba(0, 0, 0, 0.95);
  color: #636366;
  font-size: 14px;
  backdrop-filter: blur(12px);
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

/* ========== 操作提示 ========== */
.help-hint {
  position: absolute;
  left: 14px;
  bottom: 14px;
  padding: 8px 14px;
  background: rgba(28, 28, 30, 0.9);
  backdrop-filter: blur(16px);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 8px;
  font-size: 11px;
  color: #636366;
  pointer-events: none;
}

/* ========== 移动端适配 ========== */
@media (max-width: 768px) {
  .zoomable-map-container {
    min-height: 250px;
  }
  
  .zoom-controls {
    right: 10px;
    bottom: 45px;
    gap: 4px;
  }
  
  .zoom-btn {
    width: 34px;
    height: 34px;
  }
  
  .help-hint {
    left: 10px;
    bottom: 10px;
    font-size: 10px;
    padding: 6px 10px;
  }
}
</style>
