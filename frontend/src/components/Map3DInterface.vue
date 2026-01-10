<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, nextTick, watch } from 'vue'
import { showToast, showLoadingToast, closeToast } from 'vant'
import { useNavigationStore } from '@/stores/navigation'
import { recognizeLocation, calculateRoute } from '@/api'
import type { PathNode, LocationCandidate } from '@/api'
import api from '@/api'
import NavigationMap from './NavigationMap.vue'

// 导入楼层地图图片
import MapL1 from '@/assets/maps/Map_NS_L1.png'
import MapL2 from '@/assets/maps/Map_NS_L2.png'
import MapL3 from '@/assets/maps/Map_NS_L3.png'
import MapL4 from '@/assets/maps/Map_NS_L4.png'
import MapL5 from '@/assets/maps/Map_NS_L5.png'

const store = useNavigationStore()

// 楼层数据
interface Floor {
  id: number
  name: string
  image: string
}

const floors: Floor[] = [
  { id: 1, name: 'L1', image: MapL1 },
  { id: 2, name: 'L2', image: MapL2 },
  { id: 3, name: 'L3', image: MapL3 },
  { id: 4, name: 'L4', image: MapL4 },
  { id: 5, name: 'L5', image: MapL5 },
]

// 状态管理
const currentView = ref<'overview' | 'navigation'>('overview')
const selectedFloor = ref<Floor | null>(null)
const isPhotoSearchOpen = ref(false)

// 导航输入相关
const startInput = ref('')
const endInput = ref('')
const startFocused = ref(false)
const endFocused = ref(false)
const isNavigating = ref(false)
const isSearchingStart = ref(false)
const isSearchingEnd = ref(false)

// 起点终点节点
const startNode = ref<PathNode | null>(null)
const endNode = ref<PathNode | null>(null)

// 搜索结果
const startSearchResults = ref<PathNode[]>([])
const endSearchResults = ref<PathNode[]>([])

// 图片识别相关
const fileInput = ref<HTMLInputElement | null>(null)
const uploadedImage = ref<string | null>(null)
const recognitionCandidates = ref<LocationCandidate[]>([])
const selectedCandidate = ref<LocationCandidate | null>(null)
const isRecognizing = ref(false)

// 导航路线结果
interface NavigationStep {
  direction: string
  instruction: string
  distance: string
  icon: string
  floorChange?: number
}

const navigationSteps = ref<NavigationStep[]>([])
const totalDistance = ref(0)
const floorsInvolved = ref<number[]>([])

// 路径节点数据（用于绘制路线）
const routePathNodes = ref<PathNode[]>([])

// 获取某楼层的路径节点
const getFloorPathNodes = (floorId: number) => {
  return routePathNodes.value.filter(node => node.floor === floorId)
}

// 可缩放地图相关
const isMapExpanded = ref(false)
const expandedFloor = ref<Floor | null>(null)
const mapContainerRef = ref<HTMLDivElement | null>(null)

// 缩放拖拽状态
const mapZoom = ref(1)
const mapOffset = ref({ x: 0, y: 0 })
const isDragging = ref(false)
const dragStart = ref({ x: 0, y: 0 })
const lastOffset = ref({ x: 0, y: 0 })

// 3D视图控制
const scene3dRotateX = ref(55)
const scene3dRotateZ = ref(-25)
const scene3dScale = ref(1)
const is3dDragging = ref(false)
const drag3dStart = ref({ x: 0, y: 0 })
const last3dRotation = ref({ x: 55, z: -25 })

// 惯性动画
const velocity = ref({ x: 0, z: 0 })
const lastMoveTime = ref(0)
const lastDelta = ref({ x: 0, y: 0 })
let inertiaAnimationId: number | null = null

// 图层间距控制
const floorSpacing = ref(50)
const minSpacing = 20
const maxSpacing = 120

// 悬停楼层
const hoveredFloor = ref<Floor | null>(null)

// 自动旋转
const isAutoRotating = ref(false)
let autoRotateId: number | null = null

// 右侧快捷导航展开状态
const isQuickNavExpanded = ref(true)
const toggleQuickNav = () => {
  isQuickNavExpanded.value = !isQuickNavExpanded.value
}

// 聊天消息列表
interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
}
const chatMessages = ref<ChatMessage[]>([])
const isLoadingChat = ref(false)
const chatListRef = ref<HTMLDivElement | null>(null)

// 搜索起点 - 使用防抖
let startSearchTimeout: number | null = null
const searchStart = async () => {
  if (!startInput.value.trim()) {
    startSearchResults.value = []
    return
  }
  
  if (startSearchTimeout) clearTimeout(startSearchTimeout)
  startSearchTimeout = window.setTimeout(async () => {
    isSearchingStart.value = true
    try {
      await store.search(startInput.value)
      startSearchResults.value = store.searchResults
    } catch (e) {
      console.error('搜索起点失败:', e)
    } finally {
      isSearchingStart.value = false
    }
  }, 300)
}

// 搜索终点 - 使用防抖
let endSearchTimeout: number | null = null
const searchEnd = async () => {
  if (!endInput.value.trim()) {
    endSearchResults.value = []
    return
  }
  
  if (endSearchTimeout) clearTimeout(endSearchTimeout)
  endSearchTimeout = window.setTimeout(async () => {
    isSearchingEnd.value = true
    try {
      await store.search(endInput.value)
      endSearchResults.value = store.searchResults
    } catch (e) {
      console.error('搜索终点失败:', e)
    } finally {
      isSearchingEnd.value = false
    }
  }, 300)
}

// 选择起点
const selectStart = (node: PathNode) => {
  startInput.value = node.name
  startNode.value = node
  startFocused.value = false
  startSearchResults.value = []
}

// 选择终点
const selectEnd = (node: PathNode) => {
  endInput.value = node.name
  endNode.value = node
  endFocused.value = false
  endSearchResults.value = []
}

// 重置输入
const resetInputs = () => {
  startInput.value = ''
  endInput.value = ''
  startNode.value = null
  endNode.value = null
  isNavigating.value = false
  navigationSteps.value = []
  routePathNodes.value = []  // 清空路径节点
  currentView.value = 'overview'
  store.clearRoute()
  // 关闭右侧详情栏
  isMapExpanded.value = false
  expandedFloor.value = null
}

// 开始导航
const startNavigation = async () => {
  if (!startNode.value || !endNode.value) {
    showToast('请先选择起点和终点')
    return
  }
  
  showLoadingToast({ message: '规划路线中...', forbidClick: true })
  
  try {
    const response = await calculateRoute(startNode.value.id, undefined, endNode.value.id)
    closeToast()
    
    if (response.success) {
      isNavigating.value = true
      currentView.value = 'navigation'
      totalDistance.value = response.total_distance
      floorsInvolved.value = response.floors_involved
      
      // 保存路径节点数据（用于绘制路线）
      routePathNodes.value = response.path_nodes || []
      
      // 转换步骤格式
      navigationSteps.value = response.steps.map(step => ({
        direction: step.edge_type,
        instruction: step.instruction,
        distance: `${Math.round(step.distance)} M`,
        icon: getStepIcon(step.edge_type),
        floorChange: step.floor_change
      }))
      
      // 选择起点所在楼层
      const floor = floors.find(f => f.id === startNode.value?.floor)
      if (floor) selectedFloor.value = floor
    } else {
      showToast(response.message || '路径规划失败')
    }
  } catch (e: any) {
    closeToast()
    showToast(e.message || '路径规划失败')
  }
}

// 获取步骤图标
const getStepIcon = (edgeType: string): string => {
  switch (edgeType) {
    case 'stairs': return '🪜'
    case 'lifts': return '🛗'
    case 'escalator': return '↗️'
    default: return '→'
  }
}

// 格式化距离
const formatDistance = (distance: number): string => {
  if (distance < 1000) {
    return `${Math.round(distance)} 米`
  }
  return `${(distance / 1000).toFixed(1)} 公里`
}

// 计算每层的Z轴偏移
const getFloorTransform = (index: number) => {
  const zOffset = index * floorSpacing.value
  return `translateZ(${zOffset}px)`
}

// 增加间距
const increaseSpacing = () => {
  floorSpacing.value = Math.min(maxSpacing, floorSpacing.value + 10)
}

// 减少间距
const decreaseSpacing = () => {
  floorSpacing.value = Math.max(minSpacing, floorSpacing.value - 10)
}

// 重置间距
const resetSpacing = () => {
  floorSpacing.value = 50
}

// 点击楼层 - 打开右侧详情栏
const handleFloorClick = (floor: Floor) => {
  selectedFloor.value = floor
  expandedFloor.value = floor
  isMapExpanded.value = true
  // 自动收起左侧导航栏
  isSidebarCollapsed.value = true
  // 初始化缩放状态：20%缩放，居中定位
  mapZoom.value = 0.2
  mapOffset.value = { x: 0, y: 0 }
}

// 关闭放大视图
const closeExpandedMap = () => {
  isMapExpanded.value = false
  expandedFloor.value = null
}

// 切换详情栏显示的楼层
const switchDetailFloor = (floorId: number) => {
  const floor = floors.find(f => f.id === floorId)
  if (floor) {
    expandedFloor.value = floor
    selectedFloor.value = floor
  }
}

// ============================================
// 图片识别相关
// ============================================
const openPhotoSearch = () => {
  // 触发文件选择
  fileInput.value?.click()
}

const handleFileChange = async (event: Event) => {
  const target = event.target as HTMLInputElement
  const file = target.files?.[0]
  
  if (!file) return
  
  // 预览图片
  const reader = new FileReader()
  reader.onload = (e) => {
    uploadedImage.value = e.target?.result as string
  }
  reader.readAsDataURL(file)
  
  // 打开弹窗
  isPhotoSearchOpen.value = true
  isRecognizing.value = true
  recognitionCandidates.value = []
  selectedCandidate.value = null
  
  try {
    console.log('📤 [识别请求] 开始上传图片识别', {
      fileName: file.name,
      fileSize: file.size,
      fileType: file.type
    })
    
    const response = await recognizeLocation(file)
    
    console.log('✅ [识别响应] 收到识别结果', {
      success: response.success,
      method: response.method,
      candidates_count: response.candidates.length,
      message: response.message,
      candidates: response.candidates.map((c, i) => 
        `[${i+1}] ${c.node_name} (楼层: ${c.floor}, 置信度: ${c.confidence})`
      )
    })
    
    if (response.success && response.candidates.length > 0) {
      recognitionCandidates.value = response.candidates.slice(0, 3)
    } else {
      showToast(response.message || '未能识别位置，请重试')
    }
  } catch (e: any) {
    console.error('❌ [识别错误]', e)
    showToast(e.message || '识别失败')
  } finally {
    isRecognizing.value = false
    target.value = ''
  }
}

const selectRecognitionCandidate = (candidate: LocationCandidate) => {
  selectedCandidate.value = candidate
}

const confirmRecognizedLocation = () => {
  if (!selectedCandidate.value) {
    showToast('请先选择一个位置')
    return
  }
  
  // 设置为起点
  startNode.value = {
    id: selectedCandidate.value.node_id,
    name: selectedCandidate.value.node_name,
    detail: selectedCandidate.value.detail,
    floor: selectedCandidate.value.floor,
  }
  startInput.value = selectedCandidate.value.node_name
  
  closePhotoSearch()
  showToast({
    message: '起点已设置',
    icon: 'success',
  })
}

const closePhotoSearch = () => {
  isPhotoSearchOpen.value = false
  uploadedImage.value = null
  recognitionCandidates.value = []
  selectedCandidate.value = null
}

const retakePhoto = () => {
  uploadedImage.value = null
  recognitionCandidates.value = []
  selectedCandidate.value = null
  fileInput.value?.click()
}

// 格式化置信度
const formatConfidence = (confidence: number) => {
  return `${Math.round(confidence * 100)}%`
}

// ============================================
// 可缩放地图相关
// ============================================
const handleMapWheel = (e: WheelEvent) => {
  e.preventDefault()
  
  const container = mapContainerRef.value
  if (!container) return
  
  const rect = container.getBoundingClientRect()
  const mouseX = e.clientX - rect.left
  const mouseY = e.clientY - rect.top
  
  const zoomFactor = e.deltaY > 0 ? 0.9 : 1.1
  const newZoom = Math.max(0.2, Math.min(8, mapZoom.value * zoomFactor))
  
  // 以鼠标位置为中心缩放
  const zoomChange = newZoom / mapZoom.value
  mapOffset.value = {
    x: mouseX - (mouseX - mapOffset.value.x) * zoomChange,
    y: mouseY - (mouseY - mapOffset.value.y) * zoomChange,
  }
  mapZoom.value = newZoom
}

const handleMapMouseDown = (e: MouseEvent) => {
  isDragging.value = true
  dragStart.value = { x: e.clientX, y: e.clientY }
  lastOffset.value = { ...mapOffset.value }
}

const handleMapMouseMove = (e: MouseEvent) => {
  if (!isDragging.value) return
  
  mapOffset.value = {
    x: lastOffset.value.x + (e.clientX - dragStart.value.x),
    y: lastOffset.value.y + (e.clientY - dragStart.value.y),
  }
}

const handleMapMouseUp = () => {
  isDragging.value = false
}

const zoomIn = () => {
  mapZoom.value = Math.min(8, mapZoom.value * 1.3)
}

const zoomOut = () => {
  mapZoom.value = Math.max(0.1, mapZoom.value / 1.3)
}

const resetMapView = () => {
  // 重置到初始状态：20%缩放，居中
  mapZoom.value = 0.2
  mapOffset.value = { x: 0, y: 0 }
}

// ============================================
// 3D视图控制
// ============================================
const handle3dWheel = (e: WheelEvent) => {
  e.preventDefault()
  const zoomFactor = e.deltaY > 0 ? 0.95 : 1.05
  scene3dScale.value = Math.max(0.5, Math.min(2, scene3dScale.value * zoomFactor))
}

const handle3dMouseDown = (e: MouseEvent) => {
  // 如果点击的是楼层，不开始旋转
  if ((e.target as HTMLElement).closest('.floor-layer')) return

  // 停止惯性动画
  if (inertiaAnimationId) {
    cancelAnimationFrame(inertiaAnimationId)
    inertiaAnimationId = null
  }
  // 停止自动旋转
  if (isAutoRotating.value) {
    isAutoRotating.value = false
    stopAutoRotate()
  }

  is3dDragging.value = true
  drag3dStart.value = { x: e.clientX, y: e.clientY }
  last3dRotation.value = { x: scene3dRotateX.value, z: scene3dRotateZ.value }
  lastMoveTime.value = performance.now()
  lastDelta.value = { x: 0, y: 0 }
  velocity.value = { x: 0, z: 0 }
}

const handle3dMouseMove = (e: MouseEvent) => {
  if (!is3dDragging.value) return

  const now = performance.now()
  const deltaX = e.clientX - drag3dStart.value.x
  const deltaY = e.clientY - drag3dStart.value.y

  // 计算速度用于惯性
  const timeDelta = now - lastMoveTime.value
  if (timeDelta > 0) {
    velocity.value = {
      x: (deltaX - lastDelta.value.x) / timeDelta * 16,
      z: (deltaY - lastDelta.value.y) / timeDelta * 16
    }
  }
  lastMoveTime.value = now
  lastDelta.value = { x: deltaX, y: deltaY }

  // 360度自由旋转
  scene3dRotateZ.value = last3dRotation.value.z + deltaX * 0.4
  scene3dRotateX.value = Math.max(10, Math.min(85, last3dRotation.value.x - deltaY * 0.4))
}

// 惯性动画
const startInertia = () => {
  if (inertiaAnimationId) cancelAnimationFrame(inertiaAnimationId)

  const friction = 0.95
  const minVelocity = 0.01

  const animate = () => {
    if (Math.abs(velocity.value.x) < minVelocity && Math.abs(velocity.value.z) < minVelocity) {
      inertiaAnimationId = null
      return
    }

    scene3dRotateZ.value += velocity.value.x * 0.5
    scene3dRotateX.value = Math.max(10, Math.min(85, scene3dRotateX.value - velocity.value.z * 0.5))

    velocity.value.x *= friction
    velocity.value.z *= friction

    inertiaAnimationId = requestAnimationFrame(animate)
  }

  animate()
}

// 楼层悬停
const handleFloorHover = (floor: Floor) => {
  hoveredFloor.value = floor
}

const handleFloorLeave = () => {
  hoveredFloor.value = null
}

const handle3dMouseUp = () => {
  is3dDragging.value = false
  // 启动惯性动画
  if (Math.abs(velocity.value.x) > 0.5 || Math.abs(velocity.value.z) > 0.5) {
    startInertia()
  }
}

// 自动旋转
const toggleAutoRotate = () => {
  isAutoRotating.value = !isAutoRotating.value
  if (isAutoRotating.value) {
    startAutoRotate()
  } else {
    stopAutoRotate()
  }
}

const startAutoRotate = () => {
  if (autoRotateId) return
  const rotate = () => {
    if (!isAutoRotating.value) return
    scene3dRotateZ.value += 0.15
    autoRotateId = requestAnimationFrame(rotate)
  }
  rotate()
}

const stopAutoRotate = () => {
  if (autoRotateId) {
    cancelAnimationFrame(autoRotateId)
    autoRotateId = null
  }
}

const reset3dView = () => {
  scene3dRotateX.value = 55
  scene3dRotateZ.value = -25
  scene3dScale.value = 1
}

const zoom3dIn = () => {
  scene3dScale.value = Math.min(2, scene3dScale.value * 1.2)
}

const zoom3dOut = () => {
  scene3dScale.value = Math.max(0.5, scene3dScale.value / 1.2)
}

// 3D场景变换样式
const scene3dStyle = computed(() => ({
  transform: `rotateX(${scene3dRotateX.value}deg) rotateZ(${scene3dRotateZ.value}deg) scale(${scene3dScale.value})`
}))

// 收起/展开侧边栏
const isSidebarCollapsed = ref(false)
const toggleSidebar = () => {
  isSidebarCollapsed.value = !isSidebarCollapsed.value
}

// 聊天相关
const isChatExpanded = ref(false)
const chatMessage = ref('')
const chatInputRef = ref<HTMLInputElement | null>(null)

// 切换聊天展开/收起
const toggleChat = () => {
  isChatExpanded.value = !isChatExpanded.value
  if (isChatExpanded.value) {
    // 展开时聚焦输入框
    nextTick(() => {
      chatInputRef.value?.focus()
    })
  } else {
    // 收起时清空输入
    chatMessage.value = ''
  }
}

// 处理聊天按钮点击
const handleChatButtonClick = () => {
  if (!isChatExpanded.value) {
    // 未展开：展开输入框
    toggleChat()
  } else {
    // 已展开
    if (chatMessage.value.trim()) {
      // 有输入：发送消息
      sendMessage()
    } else {
      // 无输入：收起输入框
      toggleChat()
    }
  }
}

// 发送消息
const sendMessage = async () => {
  if (!chatMessage.value.trim() || isLoadingChat.value) return
  
  const userMessage = chatMessage.value.trim()
  chatMessage.value = ''
  
  // 添加用户消息
  chatMessages.value.push({
    id: Date.now().toString(),
    role: 'user',
    content: userMessage,
    timestamp: new Date()
  })
  
  // 滚动到底部
  scrollChatToBottom()
  
  // 发送到后端
  isLoadingChat.value = true
  try {
    const response = await api.post('/chat', {
      message: userMessage,
      session_id: 'map3d-session'
    })
    
    // 添加助手回复
    chatMessages.value.push({
      id: (Date.now() + 1).toString(),
      role: 'assistant',
      content: response.reply || '收到',
      timestamp: new Date()
    })
    
    scrollChatToBottom()
  } catch (e: any) {
    // 简单回复
    chatMessages.value.push({
      id: (Date.now() + 1).toString(),
      role: 'assistant',
      content: '抱歉，暂时无法连接到助手服务。',
      timestamp: new Date()
    })
    scrollChatToBottom()
  } finally {
    isLoadingChat.value = false
  }
}

// 滚动聊天到底部（最新消息在底部）
const scrollChatToBottom = () => {
  nextTick(() => {
    if (chatListRef.value) {
      chatListRef.value.scrollTop = chatListRef.value.scrollHeight
    }
  })
}

// 点击容器空白处收起聊天
const handleContainerClick = (e: MouseEvent) => {
  if (isChatExpanded.value) {
    const target = e.target as HTMLElement
    // 如果点击的不是聊天栏区域，则收起
    if (!target.closest('.bottom-chat-bar')) {
      isChatExpanded.value = false
      chatMessage.value = ''
    }
  }
}

// 清理
onMounted(() => {
  window.addEventListener('mouseup', handleMapMouseUp)
  window.addEventListener('mousemove', handleMapMouseMove)
  window.addEventListener('mouseup', handle3dMouseUp)
  window.addEventListener('mousemove', handle3dMouseMove)
})

onUnmounted(() => {
  window.removeEventListener('mouseup', handleMapMouseUp)
  window.removeEventListener('mousemove', handleMapMouseMove)
  window.removeEventListener('mouseup', handle3dMouseUp)
  window.removeEventListener('mousemove', handle3dMouseMove)
  if (startSearchTimeout) clearTimeout(startSearchTimeout)
  if (endSearchTimeout) clearTimeout(endSearchTimeout)
  if (inertiaAnimationId) cancelAnimationFrame(inertiaAnimationId)
  if (autoRotateId) cancelAnimationFrame(autoRotateId)
})
</script>

<template>
  <div class="map3d-container" :class="{ 'photo-search-active': isPhotoSearchOpen }" @click="handleContainerClick">

    <!-- 顶部导航栏 -->
    <header class="top-header">
      <div class="header-left">
        <div class="ntu-logo">
          <svg width="40" height="40" viewBox="0 0 100 100" fill="none">
            <circle cx="50" cy="50" r="45" fill="#e01932"/>
            <text x="50" y="58" text-anchor="middle" fill="white" font-size="24" font-weight="bold" font-family="Arial">NTU</text>
          </svg>
        </div>
        <div class="header-titles">
          <h1 class="main-title">NTU Campus Navigator</h1>
          <p class="sub-title">3D Indoor Navigation System</p>
        </div>
      </div>
      <div class="header-center">
        <div class="building-badge">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M3 21h18M5 21V7l8-4 8 4v14M9 21v-6h6v6"/>
          </svg>
          <span>North Spine</span>
        </div>
        <div class="floor-count-badge">
          <span class="count">5</span>
          <span class="label">层</span>
        </div>
      </div>
      <div class="header-right">
        <div class="status-indicator online">
          <span class="dot"></span>
          <span>系统在线</span>
        </div>
        <div class="time-display">{{ new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' }) }}</div>
      </div>
    </header>

    <!-- 隐藏的文件输入 -->
    <input
      ref="fileInput"
      type="file"
      accept="image/*"
      style="display: none"
      @change="handleFileChange"
    />

    <!-- 左侧导航面板 -->
    <div class="nav-sidebar" :class="{ 'collapsed': isSidebarCollapsed }">
      <!-- 收起按钮 -->
      <button class="collapse-btn" @click="toggleSidebar">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path v-if="isSidebarCollapsed" d="M9 18l6-6-6-6"/>
          <path v-else d="M15 18l-6-6 6-6"/>
        </svg>
      </button>

      <div v-show="!isSidebarCollapsed" class="sidebar-content">
        <!-- 起点输入 -->
        <div class="input-group">
          <div class="input-icon start-icon"></div>
          <div class="input-wrapper">
            <input
              v-model="startInput"
              type="text"
              placeholder="输入起点..."
              class="nav-input"
              @focus="startFocused = true"
              @blur="setTimeout(() => startFocused = false, 200)"
              @input="searchStart"
            />
            <button class="camera-btn" @click="openPhotoSearch" title="拍照识别起点">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"/>
                <circle cx="12" cy="13" r="4"/>
              </svg>
            </button>
          </div>
          <!-- 起点联想列表 -->
          <div v-if="startFocused && (startSearchResults.length > 0 || isSearchingStart)" class="suggestions-dropdown">
            <div v-if="isSearchingStart" class="suggestion-loading">
              <span>搜索中...</span>
            </div>
            <div 
              v-else
              v-for="node in startSearchResults" 
              :key="node.id"
              class="suggestion-item"
              @mousedown="selectStart(node)"
            >
              <span class="suggestion-name">{{ node.name }}</span>
              <span class="suggestion-floor">{{ node.floor }}F</span>
            </div>
            <div v-if="!isSearchingStart && startSearchResults.length === 0 && startInput" class="suggestion-empty">
              未找到匹配结果
            </div>
          </div>
        </div>

        <!-- 连接线 -->
        <div class="connector-line">
          <div class="dot"></div>
          <div class="dot"></div>
          <div class="dot"></div>
        </div>

        <!-- 终点输入 -->
        <div class="input-group">
          <div class="input-icon end-icon">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/>
              <circle cx="12" cy="10" r="3"/>
            </svg>
          </div>
          <div class="input-wrapper">
            <input
              v-model="endInput"
              type="text"
              placeholder="输入终点..."
              class="nav-input"
              @focus="endFocused = true"
              @blur="setTimeout(() => endFocused = false, 200)"
              @input="searchEnd"
            />
          </div>
          <!-- 终点联想列表 -->
          <div v-if="endFocused && (endSearchResults.length > 0 || isSearchingEnd)" class="suggestions-dropdown">
            <div v-if="isSearchingEnd" class="suggestion-loading">
              <span>搜索中...</span>
            </div>
            <div 
              v-else
              v-for="node in endSearchResults" 
              :key="node.id"
              class="suggestion-item"
              @mousedown="selectEnd(node)"
            >
              <span class="suggestion-name">{{ node.name }}</span>
              <span class="suggestion-floor">{{ node.floor }}F</span>
            </div>
            <div v-if="!isSearchingEnd && endSearchResults.length === 0 && endInput" class="suggestion-empty">
              未找到匹配结果
            </div>
          </div>
        </div>

        <!-- 按钮组 -->
        <div class="action-row">
          <div class="time-icon">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="10"/>
              <polyline points="12 6 12 12 16 14"/>
            </svg>
          </div>
          <button class="btn-secondary" @click="resetInputs">重新输入</button>
          <button 
            class="btn-primary" 
            :disabled="!startNode || !endNode"
            @click="startNavigation"
          >
            开始导航
          </button>
        </div>

        <!-- 导航结果 -->
        <div v-if="isNavigating" class="navigation-results">
          <!-- 路线概览 -->
          <div class="route-overview">
            <div class="route-stat">
              <span class="stat-value">{{ formatDistance(totalDistance) }}</span>
              <span class="stat-label">总距离</span>
            </div>
            <div class="route-stat">
              <span class="stat-value">{{ floorsInvolved.join(', ') }}F</span>
              <span class="stat-label">经过楼层</span>
            </div>
          </div>
          
          <!-- 起点信息 -->
          <div class="location-info start">
            <div class="location-dot green"></div>
            <div class="location-details">
              <div class="location-name">{{ startNode?.name }}</div>
              <div class="location-address">{{ startNode?.detail || `${startNode?.floor}楼` }}</div>
            </div>
          </div>

          <!-- 导航步骤 -->
          <div class="nav-steps-list">
            <div v-for="(step, index) in navigationSteps" :key="index" class="nav-step-item">
              <div class="step-icon">{{ step.icon }}</div>
              <div class="step-content">
                <div class="step-instruction">{{ step.instruction }}</div>
                <div class="step-distance">{{ step.distance }}</div>
              </div>
            </div>
          </div>

          <!-- 终点信息 -->
          <div class="location-info end">
            <div class="location-dot red">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor">
                <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/>
              </svg>
            </div>
            <div class="location-details">
              <div class="location-name">{{ endNode?.name }}</div>
              <div class="location-address">{{ endNode?.detail || `${endNode?.floor}楼` }}</div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 3D地图视图 -->
    <div 
      class="map3d-viewport" 
      :class="{ 
        'with-nav': isNavigating,
        'sidebar-collapsed': isSidebarCollapsed,
        'detail-open': isMapExpanded
      }"
      @wheel="handle3dWheel"
      @mousedown="handle3dMouseDown"
    >
      <!-- 3D控制面板 - 左侧 -->
      <div class="viewport-controls left">
        <div class="control-group">
          <span class="control-label">视角</span>
          <button class="viewport-ctrl-btn" @click="zoom3dIn" title="放大">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>
            </svg>
          </button>
          <button class="viewport-ctrl-btn" @click="zoom3dOut" title="缩小">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="5" y1="12" x2="19" y2="12"/>
            </svg>
          </button>
          <button class="viewport-ctrl-btn" @click="reset3dView" title="重置视角">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/>
              <path d="M3 3v5h5"/>
            </svg>
          </button>
          <button
            :class="['viewport-ctrl-btn', { 'active': isAutoRotating }]"
            @click="toggleAutoRotate"
            title="自动旋转"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M21 12a9 9 0 1 1-9-9c2.52 0 4.93 1 6.74 2.74L21 8"/>
              <path d="M21 3v5h-5"/>
            </svg>
          </button>
        </div>
        <div class="control-group">
          <span class="control-label">间距</span>
          <button class="viewport-ctrl-btn" @click="decreaseSpacing" title="减少间距">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M17 8l-5 5-5-5"/>
            </svg>
          </button>
          <span class="spacing-value">{{ floorSpacing }}px</span>
          <button class="viewport-ctrl-btn" @click="increaseSpacing" title="增加间距">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M7 16l5-5 5 5"/>
            </svg>
          </button>
          <button class="viewport-ctrl-btn" @click="resetSpacing" title="重置间距">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M21 3H3v18h18V3z"/>
              <line x1="9" y1="3" x2="9" y2="21"/>
              <line x1="15" y1="3" x2="15" y2="21"/>
            </svg>
          </button>
        </div>
      </div>
      
      <div class="scene-wrapper" :style="scene3dStyle">
        <div class="scene">
          <div
            v-for="(floor, index) in floors"
            :key="floor.id"
            :class="['floor-layer', {
              'selected': selectedFloor?.id === floor.id,
              'hovered': hoveredFloor?.id === floor.id,
              'dimmed': (selectedFloor || hoveredFloor) && selectedFloor?.id !== floor.id && hoveredFloor?.id !== floor.id,
              'has-route': getFloorPathNodes(floor.id).length > 0
            }]"
            :style="{
              transform: getFloorTransform(index),
              '--floor-index': index,
              '--spacing': floorSpacing + 'px'
            }"
            @click="handleFloorClick(floor)"
            @mouseenter="handleFloorHover(floor)"
            @mouseleave="handleFloorLeave"
          >
            <img 
              :src="floor.image" 
              :alt="floor.name"
              class="floor-image"
            />
            <!-- 路线叠加层 -->
            <svg 
              v-if="isNavigating && getFloorPathNodes(floor.id).length >= 2"
              class="route-overlay"
              viewBox="0 0 1000 750"
              preserveAspectRatio="xMidYMid meet"
            >
              <!-- 路径光晕 -->
              <polyline 
                :points="getFloorPathNodes(floor.id).map(n => `${n.x || 0},${n.y || 0}`).join(' ')"
                fill="none"
                stroke="rgba(255, 100, 100, 0.4)"
                stroke-width="12"
                stroke-linecap="round"
                stroke-linejoin="round"
              />
              <!-- 主路径 -->
              <polyline 
                :points="getFloorPathNodes(floor.id).map(n => `${n.x || 0},${n.y || 0}`).join(' ')"
                fill="none"
                stroke="#ff4444"
                stroke-width="5"
                stroke-linecap="round"
                stroke-linejoin="round"
              />
              <!-- 起点标记 -->
              <circle 
                v-if="startNode && startNode.floor === floor.id"
                :cx="startNode.x || 0"
                :cy="startNode.y || 0"
                r="10"
                fill="#22c55e"
                stroke="#fff"
                stroke-width="3"
              />
              <!-- 终点标记 -->
              <circle 
                v-if="endNode && endNode.floor === floor.id"
                :cx="endNode.x || 0"
                :cy="endNode.y || 0"
                r="10"
                fill="#ef4444"
                stroke="#fff"
                stroke-width="3"
              />
            </svg>
            <div class="floor-label-tag">{{ floor.name }}</div>
            <!-- 楼层路线指示 -->
            <div v-if="isNavigating && floorsInvolved.includes(floor.id)" class="floor-route-indicator">
              <span v-if="startNode?.floor === floor.id">起</span>
              <span v-else-if="endNode?.floor === floor.id">终</span>
              <span v-else>经</span>
            </div>
          </div>
        </div>
      </div>
      
      <div class="viewport-hint">拖拽旋转 · 滚轮缩放 · 点击楼层查看详情</div>

      <!-- 右侧楼层快捷导航 -->
      <transition name="quick-nav-slide">
        <div v-if="isQuickNavExpanded && !isMapExpanded" class="floor-quick-nav">
          <button class="quick-nav-close" @click="toggleQuickNav" title="收起">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M18 6L6 18M6 6l12 12"/>
            </svg>
          </button>
          <div class="quick-nav-title">楼层</div>
          <div class="quick-nav-list">
            <button
              v-for="floor in floors.slice().reverse()"
              :key="floor.id"
              :class="['quick-nav-btn', {
                'active': selectedFloor?.id === floor.id,
                'has-route': floorsInvolved.includes(floor.id)
              }]"
              @click="handleFloorClick(floor)"
            >
              <span class="floor-num">{{ floor.name }}</span>
              <span v-if="startNode?.floor === floor.id" class="floor-badge start">起</span>
              <span v-else-if="endNode?.floor === floor.id" class="floor-badge end">终</span>
            </button>
          </div>
        </div>
      </transition>

      <!-- 快捷导航展开按钮 -->
      <button
        v-if="!isQuickNavExpanded && !isMapExpanded"
        class="quick-nav-expand-btn"
        @click="toggleQuickNav"
        title="展开楼层导航"
      >
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <rect x="3" y="3" width="7" height="7"/>
          <rect x="14" y="3" width="7" height="7"/>
          <rect x="14" y="14" width="7" height="7"/>
          <rect x="3" y="14" width="7" height="7"/>
        </svg>
      </button>

      <!-- 底部信息栏 -->
      <div class="bottom-info-bar">
        <div class="info-section">
          <div class="info-item">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="10"/>
              <path d="M12 6v6l4 2"/>
            </svg>
            <span>实时导航</span>
          </div>
          <div class="info-divider"></div>
          <div class="info-item">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/>
              <circle cx="12" cy="10" r="3"/>
            </svg>
            <span>{{ isNavigating ? `${formatDistance(totalDistance)}` : '选择起点终点' }}</span>
          </div>
        </div>
        <div class="legend-section">
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
            <span>路线</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 右侧楼层详情栏 -->
    <transition name="slide-right">
      <div v-if="isMapExpanded && expandedFloor" class="detail-sidebar">
        <!-- 头部 -->
        <div class="detail-header">
          <h3>{{ expandedFloor.name }} - {{ isNavigating ? '导航路线' : '详细地图' }}</h3>
          <button class="close-btn" @click="closeExpandedMap" title="关闭">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M18 6L6 18M6 6l12 12"/>
            </svg>
          </button>
        </div>
        
        <!-- 导航状态：使用 NavigationMap 组件显示路线 -->
        <template v-if="isNavigating">
          <div class="detail-map-wrapper">
            <NavigationMap
              :floor="expandedFloor.id"
              :path-nodes="routePathNodes"
              :start-node-id="startNode?.id"
              :end-node-id="endNode?.id"
            />
          </div>
          <!-- 楼层切换器 -->
          <div class="floor-switcher" v-if="floorsInvolved.length > 1">
            <span class="switcher-label">切换楼层：</span>
            <div class="floor-tabs">
              <button 
                v-for="floorId in floorsInvolved" 
                :key="floorId"
                :class="['floor-tab', { active: expandedFloor.id === floorId }]"
                @click="switchDetailFloor(floorId)"
              >
                L{{ floorId }}
                <span v-if="startNode?.floor === floorId" class="tab-badge start">起</span>
                <span v-else-if="endNode?.floor === floorId" class="tab-badge end">终</span>
              </button>
            </div>
          </div>
        </template>
        
        <!-- 非导航状态：使用原来的图片视图 -->
        <template v-else>
          <!-- 控制栏 -->
          <div class="detail-controls">
            <button class="ctrl-btn" @click="zoomIn" title="放大">
              <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="11" cy="11" r="8"/>
                <line x1="21" y1="21" x2="16.65" y2="16.65"/>
                <line x1="11" y1="8" x2="11" y2="14"/>
                <line x1="8" y1="11" x2="14" y2="11"/>
              </svg>
            </button>
            <button class="ctrl-btn" @click="zoomOut" title="缩小">
              <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="11" cy="11" r="8"/>
                <line x1="21" y1="21" x2="16.65" y2="16.65"/>
                <line x1="8" y1="11" x2="14" y2="11"/>
              </svg>
            </button>
            <button class="ctrl-btn" @click="resetMapView" title="重置">
              <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/>
                <path d="M3 3v5h5"/>
              </svg>
            </button>
            <span class="zoom-indicator">{{ Math.round(mapZoom * 100) }}%</span>
          </div>
          
          <!-- 地图区域 -->
          <div 
            ref="mapContainerRef"
            class="detail-map-view"
            @wheel="handleMapWheel"
            @mousedown="handleMapMouseDown"
            :class="{ 'dragging': isDragging }"
          >
            <img 
              :src="expandedFloor.image" 
              :alt="expandedFloor.name"
              class="detail-map-image"
              :style="{
                transform: `translate(-50%, -50%) translate(${mapOffset.x}px, ${mapOffset.y}px) scale(${mapZoom})`,
              }"
              draggable="false"
            />
          </div>
          
          <!-- 操作提示 -->
          <div class="detail-hint">
            <span>滚轮缩放 · 拖拽平移</span>
          </div>
        </template>
      </div>
    </transition>

    <!-- 底部聊天组件 -->
    <div class="chat-container" :class="{ 'expanded': isChatExpanded }" @click.stop>
      <!-- 对话气泡区域 -->
      <transition name="chat-panel">
        <div v-if="isChatExpanded" class="chat-panel">
          <div class="chat-header">
            <span class="chat-title">智能助手</span>
            <button class="chat-close-btn" @click="toggleChat">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M18 6L6 18M6 6l12 12"/>
              </svg>
            </button>
          </div>
          
          <div ref="chatListRef" class="chat-messages">
            <div v-if="chatMessages.length === 0" class="chat-empty">
              <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" opacity="0.3">
                <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
              </svg>
              <span>有什么可以帮您的？</span>
            </div>
            <!-- 正常顺序：最新消息在底部 -->
            <transition-group name="bubble-up" tag="div" class="chat-messages-list">
              <div 
                v-for="msg in chatMessages" 
                :key="msg.id"
                :class="['chat-bubble', msg.role]"
              >
                <div class="bubble-content">{{ msg.content }}</div>
              </div>
              <div 
                v-if="isLoadingChat" 
                key="loading"
                class="chat-bubble assistant loading"
              >
                <div class="typing-indicator">
                  <span></span><span></span><span></span>
                </div>
              </div>
            </transition-group>
          </div>
          
          <div class="chat-input-area">
            <input 
              ref="chatInputRef"
              v-model="chatMessage"
              type="text" 
              placeholder="输入消息..." 
              class="chat-input"
              @keyup.enter="sendMessage"
              :disabled="isLoadingChat"
            />
            <button 
              class="chat-send-btn" 
              :class="{ 'active': chatMessage.trim() }"
              :disabled="!chatMessage.trim() || isLoadingChat"
              @click="sendMessage"
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z"/>
              </svg>
            </button>
          </div>
        </div>
      </transition>
      
      <!-- 聊天触发按钮 - 始终显示，图标平滑切换 -->
      <button 
        class="chat-trigger-btn"
        @click="toggleChat"
      >
        <transition name="icon-fade" mode="out-in">
          <!-- 对话图标 -->
          <svg 
            v-if="!isChatExpanded"
            key="chat"
            width="22" 
            height="22" 
            viewBox="0 0 24 24" 
            fill="none" 
            stroke="currentColor" 
            stroke-width="2"
            class="chat-icon-svg"
          >
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
          </svg>
          <!-- 关闭图标 -->
          <svg 
            v-else
            key="close"
            width="22" 
            height="22" 
            viewBox="0 0 24 24" 
            fill="none" 
            stroke="currentColor" 
            stroke-width="2"
            class="chat-icon-svg"
          >
            <path d="M18 6L6 18M6 6l12 12"/>
          </svg>
        </transition>
      </button>
    </div>

    <!-- 图片识别弹窗 -->
    <transition name="modal">
      <div v-if="isPhotoSearchOpen" class="photo-search-modal" @click.self="closePhotoSearch">
        <div class="photo-search-content">
          <button class="close-modal" @click="closePhotoSearch">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M18 6L6 18M6 6l12 12"/>
            </svg>
          </button>
          
          <h2 class="modal-title">图片识别定位</h2>
          
          <div class="photo-grid">
            <!-- 用户上传的图片 -->
            <div class="photo-card your-photo" :class="{ 'selected': selectedCandidate === null }">
              <div class="photo-placeholder cyan-border" v-if="!uploadedImage">
                <div v-if="isRecognizing" class="loading-spinner"></div>
                <svg v-else width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1">
                  <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"/>
                  <circle cx="12" cy="13" r="4"/>
                </svg>
              </div>
              <div v-else class="photo-preview">
                <img :src="uploadedImage" alt="您的照片" />
              </div>
              <div class="photo-label">您的照片</div>
            </div>
            
            <!-- 识别结果 -->
            <template v-if="recognitionCandidates.length > 0">
              <div 
                v-for="(candidate, index) in recognitionCandidates" 
                :key="candidate.node_id"
                class="photo-card result-card"
                :class="{ 'selected': selectedCandidate?.node_id === candidate.node_id }"
                @click="selectRecognitionCandidate(candidate)"
              >
                <div class="photo-placeholder result-placeholder">
                  <div class="result-rank">{{ index + 1 }}</div>
                  <div class="result-info">
                    <div class="result-name">{{ candidate.node_name }}</div>
                    <div class="result-floor">{{ candidate.floor }}楼</div>
                  </div>
                </div>
                <div class="photo-label">
                  <span class="confidence-badge">{{ formatConfidence(candidate.confidence) }}</span>
                  {{ candidate.node_name }}
                </div>
                <div class="check-icon" :class="{ 'active': selectedCandidate?.node_id === candidate.node_id }">
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M20 6L9 17l-5-5"/>
                  </svg>
                </div>
              </div>
            </template>
            
            <!-- 识别中 -->
            <template v-else-if="isRecognizing">
              <div class="photo-card loading-card" v-for="i in 3" :key="i">
                <div class="photo-placeholder">
                  <div class="loading-pulse"></div>
                </div>
                <div class="photo-label skeleton"></div>
              </div>
            </template>
            
            <!-- 无结果 -->
            <div v-else-if="!isRecognizing && uploadedImage" class="no-results">
              <p>未能识别到匹配的位置</p>
              <p class="hint">请尝试拍摄更清晰的照片</p>
            </div>
          </div>
          
          <div class="photo-actions">
            <button class="btn-secondary" @click="retakePhoto">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"/>
                <circle cx="12" cy="13" r="4"/>
              </svg>
              重新上传
            </button>
            <button 
              class="btn-primary" 
              :disabled="!selectedCandidate"
              @click="confirmRecognizedLocation"
            >
              确认位置
            </button>
          </div>
        </div>
      </div>
    </transition>
  </div>
</template>

<style scoped>
/* ═══════════════════════════════════════════════════════════
   NTU Campus Navigator - 3D Map Interface
   Brand Colors: #e01932 (NTU Red), #0e0e0e (Dark), #95ccff (Light Blue)
   ═══════════════════════════════════════════════════════════ */

/* ============================================
   主容器 - NTU深色主题背景
   ============================================ */
.map3d-container {
  position: relative;
  width: 100%;
  height: 100vh;
  height: 100dvh;
  min-height: 600px;
  background: linear-gradient(145deg, #0a0a0f 0%, #0e0e14 30%, #12121a 60%, #0a0a10 100%);
  overflow: hidden;
  display: flex;
  font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'PingFang SC', sans-serif;
}

/* 背景氛围光效 - NTU红色和蓝色 */
.map3d-container::before {
  content: '';
  position: absolute;
  top: -30%;
  left: -30%;
  width: 160%;
  height: 160%;
  background:
    radial-gradient(ellipse 900px 600px at 10% 20%, rgba(224, 25, 50, 0.15) 0%, transparent 50%),
    radial-gradient(ellipse 700px 500px at 90% 80%, rgba(149, 204, 255, 0.12) 0%, transparent 50%),
    radial-gradient(ellipse 600px 400px at 50% 50%, rgba(224, 25, 50, 0.08) 0%, transparent 50%),
    radial-gradient(ellipse 500px 300px at 70% 30%, rgba(149, 204, 255, 0.06) 0%, transparent 50%);
  pointer-events: none;
  z-index: 0;
  animation: ntuPulse 20s ease-in-out infinite alternate;
}

@keyframes ntuPulse {
  0% { opacity: 0.8; transform: scale(1) rotate(0deg); }
  50% { opacity: 1; transform: scale(1.05) rotate(1deg); }
  100% { opacity: 0.8; transform: scale(1) rotate(-1deg); }
}

/* 网格背景装饰 */
.map3d-container::after {
  content: '';
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(224, 25, 50, 0.03) 1px, transparent 1px),
    linear-gradient(90deg, rgba(224, 25, 50, 0.03) 1px, transparent 1px);
  background-size: 60px 60px;
  pointer-events: none;
  z-index: 0;
}

.map3d-container.photo-search-active .map3d-viewport::before {
  content: '';
  position: absolute;
  inset: 0;
  background: rgba(10, 10, 15, 0.9);
  backdrop-filter: blur(8px);
  z-index: 100;
}

/* ============================================
   顶部导航栏 - iOS 26 Ultra Glass Header
   ============================================ */
.top-header {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  height: 64px;
  background: linear-gradient(
    180deg,
    rgba(255, 255, 255, 0.08) 0%,
    rgba(255, 255, 255, 0.03) 50%,
    rgba(0, 0, 0, 0.1) 100%
  );
  backdrop-filter: blur(60px) saturate(200%) brightness(1.05);
  -webkit-backdrop-filter: blur(60px) saturate(200%) brightness(1.05);
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 28px;
  z-index: 200;
  box-shadow:
    0 4px 32px rgba(0, 0, 0, 0.35),
    inset 0 -1px 0 rgba(0, 0, 0, 0.15),
    inset 0 1px 0 rgba(255, 255, 255, 0.1);
  animation: headerSlideIn 0.7s cubic-bezier(0.22, 1, 0.36, 1);
}

/* 顶部高光线 */
.top-header::before {
  content: '';
  position: absolute;
  top: 0;
  left: 60px;
  right: 60px;
  height: 1px;
  background: linear-gradient(
    90deg,
    transparent 0%,
    rgba(255, 255, 255, 0.3) 20%,
    rgba(255, 255, 255, 0.5) 50%,
    rgba(255, 255, 255, 0.3) 80%,
    transparent 100%
  );
}

@keyframes headerSlideIn {
  0% {
    opacity: 0;
    transform: translateY(-30px);
    filter: blur(10px);
  }
  100% {
    opacity: 1;
    transform: translateY(0);
    filter: blur(0);
  }
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.ntu-logo {
  display: flex;
  align-items: center;
  justify-content: center;
  filter: drop-shadow(0 2px 8px rgba(224, 25, 50, 0.4));
}

.header-titles {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.main-title {
  font-size: 18px;
  font-weight: 700;
  color: #fff;
  margin: 0;
  letter-spacing: 0.5px;
}

.sub-title {
  font-size: 11px;
  color: rgba(149, 204, 255, 0.8);
  margin: 0;
  letter-spacing: 0.3px;
  text-transform: uppercase;
}

.header-center {
  display: flex;
  align-items: center;
  gap: 16px;
}

.building-badge {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 18px;
  background: linear-gradient(
    135deg,
    rgba(224, 25, 50, 0.18) 0%,
    rgba(224, 25, 50, 0.08) 100%
  );
  border: 1px solid rgba(224, 25, 50, 0.25);
  border-radius: 14px;
  color: #e01932;
  font-size: 13px;
  font-weight: 600;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.06);
  transition: all 0.3s ease;
}

.building-badge:hover {
  background: linear-gradient(
    135deg,
    rgba(224, 25, 50, 0.25) 0%,
    rgba(224, 25, 50, 0.12) 100%
  );
  border-color: rgba(224, 25, 50, 0.35);
}

.floor-count-badge {
  display: flex;
  align-items: baseline;
  gap: 4px;
  padding: 8px 16px;
  background: linear-gradient(
    135deg,
    rgba(149, 204, 255, 0.15) 0%,
    rgba(149, 204, 255, 0.06) 100%
  );
  border: 1px solid rgba(149, 204, 255, 0.2);
  border-radius: 12px;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.06);
}

.floor-count-badge .count {
  font-size: 20px;
  font-weight: 700;
  color: #95ccff;
  text-shadow: 0 2px 8px rgba(149, 204, 255, 0.3);
}

.floor-count-badge .label {
  font-size: 12px;
  color: rgba(149, 204, 255, 0.7);
}

.header-right {
  display: flex;
  align-items: center;
  gap: 20px;
}

.status-indicator {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.7);
  padding: 8px 14px;
  background: linear-gradient(
    135deg,
    rgba(34, 197, 94, 0.12) 0%,
    rgba(34, 197, 94, 0.04) 100%
  );
  border: 1px solid rgba(34, 197, 94, 0.2);
  border-radius: 12px;
}

.status-indicator .dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: linear-gradient(135deg, #22c55e 0%, #16a34a 100%);
  box-shadow:
    0 0 12px rgba(34, 197, 94, 0.6),
    inset 0 1px 0 rgba(255, 255, 255, 0.3);
  animation: statusPulse 2.5s ease-in-out infinite;
}

@keyframes statusPulse {
  0%, 100% { opacity: 1; box-shadow: 0 0 12px rgba(34, 197, 94, 0.6); }
  50% { opacity: 0.7; box-shadow: 0 0 20px rgba(34, 197, 94, 0.8); }
}

.time-display {
  font-size: 14px;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.9);
  font-variant-numeric: tabular-nums;
  padding: 8px 16px;
  background: linear-gradient(
    135deg,
    rgba(255, 255, 255, 0.1) 0%,
    rgba(255, 255, 255, 0.04) 100%
  );
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 12px;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.08);
}

/* ============================================
   左侧导航面板 - iOS 26 Ultra Glassmorphism Sidebar
   ============================================ */
.nav-sidebar {
  position: relative;
  width: 380px;
  min-width: 380px;
  height: calc(100% - 84px);
  margin-top: 74px;
  margin-left: 10px;
  margin-bottom: 10px;
  background: linear-gradient(
    165deg,
    rgba(255, 255, 255, 0.08) 0%,
    rgba(255, 255, 255, 0.03) 40%,
    rgba(224, 25, 50, 0.04) 100%
  );
  backdrop-filter: blur(60px) saturate(200%) brightness(1.05);
  -webkit-backdrop-filter: blur(60px) saturate(200%) brightness(1.05);
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 28px;
  display: flex;
  flex-direction: column;
  z-index: 50;
  transition: all 0.5s cubic-bezier(0.22, 1, 0.36, 1);
  box-shadow:
    0 8px 40px rgba(0, 0, 0, 0.45),
    0 0 0 1px rgba(255, 255, 255, 0.05) inset,
    0 2px 0 rgba(255, 255, 255, 0.08) inset,
    0 -1px 0 rgba(0, 0, 0, 0.3) inset;
  animation: sidebarSlideIn 0.8s cubic-bezier(0.22, 1, 0.36, 1) 0.15s backwards;
  overflow: hidden;
}

@keyframes sidebarSlideIn {
  0% {
    opacity: 0;
    transform: translateX(-40px) scale(0.95);
    filter: blur(10px);
  }
  100% {
    opacity: 1;
    transform: translateX(0) scale(1);
    filter: blur(0);
  }
}

/* iOS 26 顶部高光效果 */
.nav-sidebar::before {
  content: '';
  position: absolute;
  top: 0;
  left: 20px;
  right: 20px;
  height: 1px;
  background: linear-gradient(
    90deg,
    transparent 0%,
    rgba(255, 255, 255, 0.3) 20%,
    rgba(255, 255, 255, 0.5) 50%,
    rgba(255, 255, 255, 0.3) 80%,
    transparent 100%
  );
  border-radius: 28px 28px 0 0;
  z-index: 1;
}

/* iOS 26 内部光晕 */
.nav-sidebar::after {
  content: '';
  position: absolute;
  top: -50%;
  left: -50%;
  width: 200%;
  height: 200%;
  background: radial-gradient(
    ellipse 40% 30% at 30% 0%,
    rgba(255, 255, 255, 0.06) 0%,
    transparent 50%
  );
  pointer-events: none;
  z-index: 0;
}

.nav-sidebar.collapsed {
  width: 0;
  min-width: 0;
  padding: 0;
  margin-left: 0;
  border: none;
  background: transparent;
  backdrop-filter: none;
  box-shadow: none;
}

.nav-sidebar.collapsed .sidebar-content {
  opacity: 0;
  pointer-events: none;
  transform: translateX(-20px);
}

.collapse-btn {
  position: absolute;
  right: -18px;
  top: 50%;
  transform: translateY(-50%);
  width: 36px;
  height: 72px;
  background: linear-gradient(
    135deg,
    rgba(255, 255, 255, 0.12) 0%,
    rgba(255, 255, 255, 0.05) 100%
  );
  backdrop-filter: blur(30px) saturate(180%);
  -webkit-backdrop-filter: blur(30px) saturate(180%);
  border: 1px solid rgba(255, 255, 255, 0.15);
  border-left: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 0 14px 14px 0;
  color: rgba(224, 25, 50, 0.9);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 60;
  transition: all 0.4s cubic-bezier(0.22, 1, 0.36, 1);
  box-shadow:
    4px 0 20px rgba(0, 0, 0, 0.3),
    inset 0 1px 0 rgba(255, 255, 255, 0.1);
}

.collapse-btn:hover {
  background: linear-gradient(
    135deg,
    rgba(224, 25, 50, 0.2) 0%,
    rgba(224, 25, 50, 0.08) 100%
  );
  color: #e01932;
  border-color: rgba(224, 25, 50, 0.3);
  transform: translateY(-50%) scale(1.05);
  box-shadow:
    6px 0 24px rgba(224, 25, 50, 0.2),
    0 0 30px rgba(224, 25, 50, 0.1),
    inset 0 1px 0 rgba(255, 255, 255, 0.15);
}

.collapse-btn:active {
  transform: translateY(-50%) scale(0.95);
  transition: transform 0.1s ease;
}

.sidebar-content {
  position: relative;
  padding: 28px 24px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  transition: all 0.4s cubic-bezier(0.22, 1, 0.36, 1);
  overflow-y: auto;
  flex: 1;
  z-index: 1;
}

/* ============================================
   输入框组 - Glass Input Fields
   ============================================ */
.input-group {
  position: relative;
  display: flex;
  align-items: center;
  gap: 14px;
}

.input-icon {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: all 0.3s ease;
}

.start-icon {
  background: linear-gradient(135deg, #95ccff 0%, #6bb3ff 100%);
  box-shadow: 0 2px 8px rgba(149, 204, 255, 0.4);
}

.end-icon {
  color: #e01932;
  filter: drop-shadow(0 2px 4px rgba(224, 25, 50, 0.4));
}

.input-wrapper {
  flex: 1;
  position: relative;
  display: flex;
  align-items: center;
}

.nav-input {
  width: 100%;
  padding: 16px 54px 16px 18px;
  background: linear-gradient(
    135deg,
    rgba(255, 255, 255, 0.08) 0%,
    rgba(255, 255, 255, 0.04) 100%
  );
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 16px;
  font-size: 15px;
  color: #fff;
  outline: none;
  transition: all 0.4s cubic-bezier(0.22, 1, 0.36, 1);
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.08),
    inset 0 -1px 0 rgba(0, 0, 0, 0.1),
    0 2px 8px rgba(0, 0, 0, 0.15);
}

.nav-input::placeholder {
  color: rgba(255, 255, 255, 0.4);
  transition: color 0.3s ease;
}

.nav-input:hover {
  background: linear-gradient(
    135deg,
    rgba(255, 255, 255, 0.1) 0%,
    rgba(255, 255, 255, 0.05) 100%
  );
  border-color: rgba(255, 255, 255, 0.18);
}

.nav-input:focus {
  border-color: rgba(224, 25, 50, 0.5);
  background: linear-gradient(
    135deg,
    rgba(224, 25, 50, 0.08) 0%,
    rgba(255, 255, 255, 0.06) 100%
  );
  box-shadow:
    0 0 0 4px rgba(224, 25, 50, 0.1),
    inset 0 1px 0 rgba(255, 255, 255, 0.1),
    0 8px 32px rgba(0, 0, 0, 0.25);
}

.nav-input:focus::placeholder {
  color: rgba(255, 255, 255, 0.25);
}

.camera-btn {
  position: absolute;
  right: 10px;
  width: 40px;
  height: 40px;
  background: linear-gradient(
    135deg,
    rgba(224, 25, 50, 0.15) 0%,
    rgba(224, 25, 50, 0.05) 100%
  );
  border: 1px solid rgba(224, 25, 50, 0.25);
  border-radius: 12px;
  color: rgba(224, 25, 50, 0.9);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.35s cubic-bezier(0.22, 1, 0.36, 1);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.06);
}

.camera-btn:hover {
  background: linear-gradient(
    135deg,
    rgba(224, 25, 50, 0.25) 0%,
    rgba(224, 25, 50, 0.1) 100%
  );
  border-color: rgba(224, 25, 50, 0.45);
  color: #e01932;
  transform: scale(1.08);
  box-shadow:
    0 6px 20px rgba(224, 25, 50, 0.25),
    inset 0 1px 0 rgba(255, 255, 255, 0.1);
}

.camera-btn:active {
  transform: scale(0.94);
  transition: transform 0.1s ease;
}

/* 连接线 */
.connector-line {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 5px;
  padding: 6px 0;
  margin-left: 13px;
}

.connector-line .dot {
  width: 5px;
  height: 5px;
  background: linear-gradient(135deg, #e01932 0%, #c4162b 100%);
  border-radius: 50%;
  opacity: 0.6;
  animation: dotPulse 1.5s ease-in-out infinite;
}

.connector-line .dot:nth-child(2) {
  animation-delay: 0.2s;
}

.connector-line .dot:nth-child(3) {
  animation-delay: 0.4s;
}

@keyframes dotPulse {
  0%, 100% { opacity: 0.4; transform: scale(0.8); }
  50% { opacity: 1; transform: scale(1.1); }
}

/* 联想下拉 - iOS 26 Glass Dropdown */
.suggestions-dropdown {
  position: absolute;
  top: 100%;
  left: 42px;
  right: 0;
  margin-top: 10px;
  background: linear-gradient(
    165deg,
    rgba(30, 30, 40, 0.95) 0%,
    rgba(20, 20, 28, 0.98) 100%
  );
  backdrop-filter: blur(50px) saturate(180%);
  -webkit-backdrop-filter: blur(50px) saturate(180%);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 18px;
  overflow: hidden;
  z-index: 100;
  box-shadow:
    0 16px 48px rgba(0, 0, 0, 0.5),
    inset 0 1px 0 rgba(255, 255, 255, 0.08),
    0 0 0 1px rgba(255, 255, 255, 0.03) inset;
  max-height: 300px;
  overflow-y: auto;
  animation: dropdownFadeIn 0.3s cubic-bezier(0.22, 1, 0.36, 1);
}

@keyframes dropdownFadeIn {
  0% {
    opacity: 0;
    transform: translateY(-10px) scale(0.96);
  }
  100% {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

.suggestion-item {
  padding: 14px 18px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  cursor: pointer;
  transition: all 0.25s cubic-bezier(0.22, 1, 0.36, 1);
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}

.suggestion-item:last-child {
  border-bottom: none;
}

.suggestion-item:hover {
  background: linear-gradient(
    90deg,
    rgba(224, 25, 50, 0.12) 0%,
    rgba(224, 25, 50, 0.05) 100%
  );
  padding-left: 22px;
}

.suggestion-name {
  color: #fff;
  font-size: 14px;
  font-weight: 500;
  transition: color 0.25s ease;
}

.suggestion-item:hover .suggestion-name {
  color: #fff;
}

.suggestion-floor {
  color: #95ccff;
  font-size: 11px;
  background: linear-gradient(
    135deg,
    rgba(149, 204, 255, 0.2) 0%,
    rgba(149, 204, 255, 0.1) 100%
  );
  padding: 5px 12px;
  border-radius: 8px;
  font-weight: 600;
  border: 1px solid rgba(149, 204, 255, 0.2);
  transition: all 0.25s ease;
}

.suggestion-item:hover .suggestion-floor {
  background: linear-gradient(
    135deg,
    rgba(224, 25, 50, 0.25) 0%,
    rgba(224, 25, 50, 0.1) 100%
  );
  color: #e01932;
  border-color: rgba(224, 25, 50, 0.3);
}

.suggestion-loading,
.suggestion-empty {
  padding: 24px 20px;
  text-align: center;
  color: rgba(255, 255, 255, 0.45);
  font-size: 14px;
}

/* ============================================
   按钮组 - Glass Buttons
   ============================================ */
.action-row {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-top: 12px;
}

.time-icon {
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #95ccff;
  opacity: 0.7;
}

.btn-secondary {
  flex: 1;
  padding: 14px 18px;
  background: linear-gradient(
    135deg,
    rgba(255, 255, 255, 0.1) 0%,
    rgba(255, 255, 255, 0.04) 100%
  );
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  border: 1px solid rgba(255, 255, 255, 0.15);
  border-radius: 14px;
  color: #fff;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.4s cubic-bezier(0.22, 1, 0.36, 1);
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.1),
    0 2px 8px rgba(0, 0, 0, 0.15);
}

.btn-secondary:hover {
  background: linear-gradient(
    135deg,
    rgba(255, 255, 255, 0.15) 0%,
    rgba(255, 255, 255, 0.06) 100%
  );
  border-color: rgba(255, 255, 255, 0.25);
  transform: translateY(-2px);
  box-shadow:
    0 6px 20px rgba(0, 0, 0, 0.25),
    inset 0 1px 0 rgba(255, 255, 255, 0.15);
}

.btn-secondary:active {
  transform: scale(0.96);
  transition: transform 0.1s ease;
}

.btn-primary {
  flex: 1;
  padding: 14px 18px;
  background: linear-gradient(135deg, #e01932 0%, #c4162b 100%);
  border: 1px solid rgba(255, 255, 255, 0.15);
  border-radius: 14px;
  color: #fff;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.4s cubic-bezier(0.22, 1, 0.36, 1);
  box-shadow:
    0 4px 20px rgba(224, 25, 50, 0.4),
    inset 0 1px 0 rgba(255, 255, 255, 0.25),
    inset 0 -1px 0 rgba(0, 0, 0, 0.15);
}

.btn-primary:hover {
  background: linear-gradient(135deg, #ff3d4d 0%, #e01932 100%);
  transform: translateY(-3px);
  box-shadow:
    0 8px 32px rgba(224, 25, 50, 0.5),
    0 0 40px rgba(224, 25, 50, 0.2),
    inset 0 1px 0 rgba(255, 255, 255, 0.35);
}

.btn-primary:active {
  transform: translateY(-1px) scale(0.98);
  transition: transform 0.1s ease;
}

.btn-primary:disabled {
  opacity: 0.35;
  cursor: not-allowed;
  transform: none;
  box-shadow: none;
  filter: grayscale(0.3);
}

/* ============================================
   导航结果
   ============================================ */
.navigation-results {
  margin-top: 16px;
  display: flex;
  flex-direction: column;
  gap: 0;
  flex: 1;
  overflow-y: auto;
}

.route-overview {
  display: flex;
  gap: 16px;
  padding: 16px;
  background: #3a3d45;
  border-radius: 12px;
  margin-bottom: 16px;
}

.route-stat {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}

.stat-value {
  color: #fff;
  font-size: 18px;
  font-weight: 600;
}

.stat-label {
  color: #9ca3af;
  font-size: 12px;
}

.location-info {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 16px 0;
}

.location-info.start {
  border-bottom: 1px solid #3a3d45;
}

.location-info.end {
  border-top: 1px solid #3a3d45;
  margin-top: auto;
}

.location-dot {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.location-dot.green {
  background: #61C554;
}

.location-dot.red {
  background: transparent;
  color: #ef4444;
}

.location-details {
  flex: 1;
  min-width: 0;
}

.location-name {
  color: #fff;
  font-size: 15px;
  font-weight: 600;
  margin-bottom: 4px;
}

.location-address {
  color: #9ca3af;
  font-size: 12px;
  line-height: 1.4;
}

/* 导航步骤列表 */
.nav-steps-list {
  display: flex;
  flex-direction: column;
  padding: 8px 0;
  max-height: 300px;
  overflow-y: auto;
}

.nav-step-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 0;
  border-left: 2px solid #3a3d45;
  margin-left: 11px;
  padding-left: 20px;
}

.nav-step-item .step-icon {
  width: 32px;
  height: 32px;
  background: #3a3d45;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 16px;
  flex-shrink: 0;
}

.step-content {
  flex: 1;
}

.step-instruction {
  color: #fff;
  font-size: 14px;
  font-weight: 500;
}

.step-distance {
  color: #9ca3af;
  font-size: 12px;
  margin-top: 2px;
}

/* ============================================
   3D地图视图 - Immersive 3D Viewport
   ============================================ */
.map3d-viewport {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  perspective: 1400px;
  perspective-origin: 50% 45%;
  transition: all 0.5s cubic-bezier(0.34, 1.56, 0.64, 1);
  position: relative;
  overflow: hidden;
  margin-top: 64px;
  height: calc(100% - 64px);
}

.map3d-viewport.with-nav {
  justify-content: flex-end;
  padding-right: 5%;
}

.map3d-viewport.sidebar-collapsed {
  justify-content: center;
  padding-left: 50px;
}

.map3d-viewport.sidebar-collapsed.with-nav {
  justify-content: center;
}

/* 当右侧详情栏展开时，3D视图向左移动 */
.map3d-viewport.detail-open {
  padding-right: 45%;
  justify-content: center;
}

.map3d-viewport.sidebar-collapsed.detail-open {
  padding-left: 50px;
  padding-right: 45%;
}

/* 3D视图控制面板 - 左侧 */
.viewport-controls {
  position: absolute;
  top: 24px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  z-index: 10;
}

.viewport-controls.left {
  left: 24px;
}

.control-group {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  background: linear-gradient(
    135deg,
    rgba(255, 255, 255, 0.1) 0%,
    rgba(255, 255, 255, 0.04) 100%
  );
  backdrop-filter: blur(50px) saturate(180%);
  -webkit-backdrop-filter: blur(50px) saturate(180%);
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 16px;
  box-shadow:
    0 8px 32px rgba(0, 0, 0, 0.35),
    inset 0 1px 0 rgba(255, 255, 255, 0.1),
    inset 0 -1px 0 rgba(0, 0, 0, 0.1);
  animation: controlGroupFadeIn 0.6s cubic-bezier(0.22, 1, 0.36, 1) backwards;
}

.control-group:nth-child(1) {
  animation-delay: 0.25s;
}

.control-group:nth-child(2) {
  animation-delay: 0.35s;
}

@keyframes controlGroupFadeIn {
  0% {
    opacity: 0;
    transform: translateX(-30px) scale(0.92);
    filter: blur(8px);
  }
  100% {
    opacity: 1;
    transform: translateX(0) scale(1);
    filter: blur(0);
  }
}

.control-label {
  color: rgba(255, 255, 255, 0.5);
  font-size: 11px;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-right: 4px;
}

.spacing-value {
  color: #95ccff;
  font-size: 12px;
  font-weight: 600;
  min-width: 42px;
  text-align: center;
  font-variant-numeric: tabular-nums;
}

.viewport-ctrl-btn {
  width: 38px;
  height: 38px;
  background: linear-gradient(
    135deg,
    rgba(255, 255, 255, 0.08) 0%,
    rgba(255, 255, 255, 0.02) 100%
  );
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 12px;
  color: rgba(149, 204, 255, 0.85);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.35s cubic-bezier(0.22, 1, 0.36, 1);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.06);
}

.viewport-ctrl-btn:hover {
  background: linear-gradient(
    135deg,
    rgba(224, 25, 50, 0.15) 0%,
    rgba(224, 25, 50, 0.05) 100%
  );
  border-color: rgba(224, 25, 50, 0.35);
  color: #e01932;
  transform: scale(1.1);
  box-shadow:
    0 6px 20px rgba(224, 25, 50, 0.2),
    inset 0 1px 0 rgba(255, 255, 255, 0.1);
}

.viewport-ctrl-btn:active {
  transform: scale(0.92);
  transition: transform 0.1s ease;
}

.viewport-ctrl-btn.active {
  background: linear-gradient(135deg, #e01932 0%, #c4162b 100%);
  border-color: rgba(255, 255, 255, 0.2);
  color: #fff;
  box-shadow:
    0 6px 24px rgba(224, 25, 50, 0.45),
    inset 0 1px 0 rgba(255, 255, 255, 0.25);
  animation: rotateGlow 2.5s ease-in-out infinite;
}

@keyframes rotateGlow {
  0%, 100% {
    box-shadow: 0 6px 24px rgba(224, 25, 50, 0.45), inset 0 1px 0 rgba(255, 255, 255, 0.25);
  }
  50% {
    box-shadow: 0 8px 32px rgba(224, 25, 50, 0.6), inset 0 1px 0 rgba(255, 255, 255, 0.35);
  }
}

.viewport-hint {
  position: absolute;
  bottom: 100px;
  left: 50%;
  transform: translateX(-50%);
  padding: 14px 28px;
  background: linear-gradient(
    135deg,
    rgba(255, 255, 255, 0.08) 0%,
    rgba(255, 255, 255, 0.03) 100%
  );
  backdrop-filter: blur(40px) saturate(180%);
  -webkit-backdrop-filter: blur(40px) saturate(180%);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 14px;
  font-size: 13px;
  color: rgba(255, 255, 255, 0.55);
  pointer-events: none;
  box-shadow:
    0 8px 32px rgba(0, 0, 0, 0.3),
    inset 0 1px 0 rgba(255, 255, 255, 0.08);
  animation: hintFadeIn 0.8s cubic-bezier(0.22, 1, 0.36, 1) 0.5s backwards;
}

@keyframes hintFadeIn {
  0% {
    opacity: 0;
    transform: translateX(-50%) translateY(20px);
  }
  100% {
    opacity: 1;
    transform: translateX(-50%) translateY(0);
  }
}

.scene-wrapper {
  transform-style: preserve-3d;
  transition: transform 0.05s cubic-bezier(0.25, 0.1, 0.25, 1);
  cursor: grab;
  will-change: transform;
  backface-visibility: hidden;
  -webkit-font-smoothing: antialiased;
}

.scene-wrapper:active {
  cursor: grabbing;
  transition: none;
}

/* GPU 加速优化 */
.scene-wrapper,
.floor-layer,
.detail-map-image {
  transform: translateZ(0);
  perspective: 1000px;
}

.scene {
  position: relative;
  width: 700px;
  height: 500px;
  transform-style: preserve-3d;
  animation: sceneFloat 8s ease-in-out infinite;
}

@keyframes sceneFloat {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-8px); }
}

/* ============================================
   楼层 - Interactive 3D Floor Layers
   ============================================ */
.floor-layer {
  position: absolute;
  width: 100%;
  height: 100%;
  cursor: pointer;
  transform-style: preserve-3d;
  transition:
    transform 0.4s cubic-bezier(0.34, 1.56, 0.64, 1),
    opacity 0.3s ease,
    filter 0.3s ease,
    box-shadow 0.3s ease;
  background: transparent;
  border-radius: 12px;
  overflow: hidden;
  will-change: transform, opacity, filter;
  animation: floorEntrance 0.8s cubic-bezier(0.34, 1.56, 0.64, 1) backwards;
  animation-delay: calc(var(--floor-index) * 0.1s);
}

@keyframes floorEntrance {
  0% {
    opacity: 0;
    transform: translateZ(calc(var(--floor-index) * var(--spacing, 50px) - 100px)) scale(0.8);
  }
  100% {
    opacity: 1;
    transform: translateZ(calc(var(--floor-index) * var(--spacing, 50px))) scale(1);
  }
}

/* 楼层底部光效 */
.floor-layer::before {
  content: '';
  position: absolute;
  bottom: -10px;
  left: 10%;
  right: 10%;
  height: 20px;
  background: radial-gradient(ellipse at center, rgba(224, 25, 50, 0.15) 0%, transparent 70%);
  filter: blur(8px);
  opacity: 0;
  transition: opacity 0.4s ease;
  pointer-events: none;
}

/* 楼层边框光效 */
.floor-layer::after {
  content: '';
  position: absolute;
  inset: 0;
  border: 2px solid transparent;
  border-radius: 12px;
  pointer-events: none;
  transition: all 0.4s ease;
}

/* 默认状态：完全显示 */
.floor-layer .floor-image {
  opacity: 1;
  transition: all 0.4s ease;
}

/* 有选中或悬停时，其他楼层变暗 (dimmed) */
.floor-layer.dimmed {
  opacity: 0.35;
  filter: saturate(0.4) brightness(0.6);
}

.floor-layer.dimmed .floor-image {
  opacity: 0.5;
}

/* 悬停状态：轻微上浮 + 边框发光 */
.floor-layer:hover {
  transform: translateZ(calc(var(--floor-index) * var(--spacing, 50px))) translateY(-12px) scale(1.02);
}

.floor-layer:hover::before {
  opacity: 1;
}

.floor-layer:hover::after {
  border-color: rgba(149, 204, 255, 0.5);
  box-shadow:
    0 0 20px rgba(149, 204, 255, 0.3),
    inset 0 0 20px rgba(149, 204, 255, 0.1);
}

/* 悬停状态 */
.floor-layer.hovered {
  opacity: 1;
  filter: saturate(1.2) brightness(1.1);
  z-index: 20;
}

.floor-layer.hovered::after {
  border-color: rgba(149, 204, 255, 0.6);
  box-shadow:
    0 0 30px rgba(149, 204, 255, 0.4),
    inset 0 0 30px rgba(149, 204, 255, 0.15);
}

/* 选中状态：高亮 + 强发光 */
.floor-layer.selected {
  opacity: 1;
  filter: saturate(1.3) brightness(1.15);
  z-index: 30;
}

.floor-layer.selected::before {
  opacity: 1;
  background: radial-gradient(ellipse at center, rgba(224, 25, 50, 0.25) 0%, transparent 70%);
}

.floor-layer.selected::after {
  border-color: rgba(224, 25, 50, 0.8);
  box-shadow:
    0 0 40px rgba(224, 25, 50, 0.5),
    0 0 80px rgba(149, 204, 255, 0.2),
    inset 0 0 40px rgba(224, 25, 50, 0.15);
  animation: selectedPulse 2s ease-in-out infinite;
}

@keyframes selectedPulse {
  0%, 100% { box-shadow: 0 0 40px rgba(224, 25, 50, 0.5), 0 0 80px rgba(149, 204, 255, 0.2), inset 0 0 40px rgba(224, 25, 50, 0.15); }
  50% { box-shadow: 0 0 50px rgba(224, 25, 50, 0.7), 0 0 100px rgba(149, 204, 255, 0.3), inset 0 0 50px rgba(224, 25, 50, 0.25); }
}

.floor-image {
  width: 100%;
  height: 100%;
  object-fit: contain;
  display: block;
  border-radius: 12px;
}

.floor-label-tag {
  position: absolute;
  top: 14px;
  left: 14px;
  padding: 6px 14px;
  background: rgba(14, 14, 20, 0.92);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border: 1px solid rgba(149, 204, 255, 0.25);
  border-radius: 8px;
  color: #95ccff;
  font-size: 13px;
  font-weight: 600;
  pointer-events: none;
  z-index: 5;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.5);
  letter-spacing: 0.5px;
}

.floor-layer.selected .floor-label-tag {
  background: linear-gradient(135deg, #e01932 0%, #c4162b 100%);
  color: #fff;
  border-color: transparent;
  box-shadow: 0 4px 16px rgba(224, 25, 50, 0.5);
}

/* 路线叠加层 */
.route-overlay {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  z-index: 2;
}

/* 有路线经过的楼层高亮 */
.floor-layer.has-route {
  box-shadow: 0 0 30px rgba(255, 100, 100, 0.4);
}

.floor-layer.has-route::after {
  border-color: rgba(255, 100, 100, 0.5);
}

/* 楼层路线指示器 */
.floor-route-indicator {
  position: absolute;
  top: 14px;
  right: 14px;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: linear-gradient(135deg, #ff6b6b 0%, #ee5a5a 100%);
  color: #fff;
  font-size: 12px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow:
    0 4px 12px rgba(255, 107, 107, 0.5),
    inset 0 1px 0 rgba(255, 255, 255, 0.3);
  z-index: 5;
  pointer-events: none;
  animation: indicatorPulse 1.5s ease-in-out infinite;
}

@keyframes indicatorPulse {
  0%, 100% { transform: scale(1); box-shadow: 0 4px 12px rgba(255, 107, 107, 0.5); }
  50% { transform: scale(1.1); box-shadow: 0 6px 20px rgba(255, 107, 107, 0.7); }
}

.floor-route-indicator span {
  line-height: 1;
}

/* ============================================
   右侧楼层详情栏 - iOS 26 NTU Glassmorphism Panel
   ============================================ */
.detail-sidebar {
  position: fixed;
  top: 10px;
  right: 10px;
  bottom: 10px;
  width: calc(45% - 20px);
  min-width: 400px;
  max-width: 680px;
  background: linear-gradient(
    165deg,
    rgba(255, 255, 255, 0.1) 0%,
    rgba(255, 255, 255, 0.04) 40%,
    rgba(224, 25, 50, 0.05) 100%
  );
  backdrop-filter: blur(60px) saturate(200%) brightness(1.02);
  -webkit-backdrop-filter: blur(60px) saturate(200%) brightness(1.02);
  border: 1px solid rgba(255, 255, 255, 0.15);
  border-radius: 24px;
  display: flex;
  flex-direction: column;
  z-index: 50;
  overflow: hidden;
  box-shadow:
    0 12px 48px rgba(0, 0, 0, 0.45),
    0 0 0 1px rgba(255, 255, 255, 0.06) inset,
    0 2px 0 rgba(255, 255, 255, 0.1) inset;
}

/* 详情栏顶部高光 */
.detail-sidebar::before {
  content: '';
  position: absolute;
  top: 0;
  left: 24px;
  right: 24px;
  height: 1px;
  background: linear-gradient(
    90deg,
    transparent 0%,
    rgba(255, 255, 255, 0.35) 20%,
    rgba(255, 255, 255, 0.5) 50%,
    rgba(255, 255, 255, 0.35) 80%,
    transparent 100%
  );
  z-index: 1;
}

/* 详情栏内部光晕 */
.detail-sidebar::after {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 150px;
  background: radial-gradient(
    ellipse 70% 100% at 50% -20%,
    rgba(255, 255, 255, 0.08) 0%,
    transparent 70%
  );
  pointer-events: none;
  z-index: 0;
}

.detail-header {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 24px;
  background: linear-gradient(
    180deg,
    rgba(255, 255, 255, 0.06) 0%,
    rgba(255, 255, 255, 0.02) 100%
  );
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  z-index: 1;
}

.detail-header h3 {
  color: #fff;
  font-size: 17px;
  font-weight: 600;
  margin: 0;
  text-shadow: 0 2px 8px rgba(0, 0, 0, 0.4);
}

.detail-header .close-btn {
  width: 38px;
  height: 38px;
  background: linear-gradient(
    135deg,
    rgba(255, 255, 255, 0.1) 0%,
    rgba(255, 255, 255, 0.04) 100%
  );
  border: 1px solid rgba(255, 255, 255, 0.15);
  border-radius: 12px;
  color: rgba(224, 25, 50, 0.9);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.4s cubic-bezier(0.22, 1, 0.36, 1);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.1);
}

.detail-header .close-btn:hover {
  background: linear-gradient(
    135deg,
    rgba(224, 25, 50, 0.2) 0%,
    rgba(224, 25, 50, 0.08) 100%
  );
  border-color: rgba(224, 25, 50, 0.4);
  color: #e01932;
  transform: scale(1.1) rotate(90deg);
  box-shadow: 0 4px 20px rgba(224, 25, 50, 0.25);
}

.detail-header .close-btn:active {
  transform: scale(0.95) rotate(90deg);
}

.detail-controls {
  position: relative;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px 24px;
  background: rgba(255, 255, 255, 0.03);
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
  z-index: 1;
}

.detail-controls .ctrl-btn {
  width: 38px;
  height: 38px;
  background: linear-gradient(
    135deg,
    rgba(255, 255, 255, 0.1) 0%,
    rgba(255, 255, 255, 0.04) 100%
  );
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 12px;
  color: rgba(149, 204, 255, 0.9);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.35s cubic-bezier(0.22, 1, 0.36, 1);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.08);
}

.detail-controls .ctrl-btn:hover {
  background: linear-gradient(
    135deg,
    rgba(149, 204, 255, 0.15) 0%,
    rgba(149, 204, 255, 0.05) 100%
  );
  border-color: rgba(149, 204, 255, 0.35);
  color: #95ccff;
  transform: scale(1.08);
  box-shadow: 0 4px 20px rgba(149, 204, 255, 0.2);
}

.detail-controls .ctrl-btn:active {
  transform: scale(0.95);
}

.detail-controls .zoom-indicator {
  color: #95ccff;
  font-size: 13px;
  font-weight: 600;
  min-width: 50px;
  text-align: center;
  margin-left: auto;
  font-variant-numeric: tabular-nums;
}

.detail-map-view {
  flex: 1;
  overflow: hidden;
  cursor: grab;
  position: relative;
  background: linear-gradient(
    145deg,
    rgba(10, 10, 18, 0.95) 0%,
    rgba(14, 14, 22, 0.98) 100%
  );
  z-index: 1;
}

.detail-map-view.dragging {
  cursor: grabbing;
}

.detail-map-image {
  position: absolute;
  top: 50%;
  left: 50%;
  max-width: none;
  transform-origin: center center;
  user-select: none;
  transition: transform 0.06s linear;
  border-radius: 8px;
  will-change: transform;
}

.detail-hint {
  position: relative;
  padding: 14px 24px;
  background: linear-gradient(
    180deg,
    rgba(255, 255, 255, 0.03) 0%,
    rgba(255, 255, 255, 0.06) 100%
  );
  border-top: 1px solid rgba(255, 255, 255, 0.08);
  text-align: center;
  color: rgba(255, 255, 255, 0.5);
  font-size: 12px;
  z-index: 1;
}

/* 导航状态下的地图包装器 */
.detail-map-wrapper {
  flex: 1;
  min-height: 0;
  position: relative;
  background: linear-gradient(
    145deg,
    rgba(10, 10, 18, 0.95) 0%,
    rgba(14, 14, 22, 0.98) 100%
  );
  z-index: 1;
}

/* 楼层切换器 - iOS 26 Glass Floor Tabs */
.floor-switcher {
  position: relative;
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 14px 24px;
  background: linear-gradient(
    180deg,
    rgba(255, 255, 255, 0.03) 0%,
    rgba(255, 255, 255, 0.06) 100%
  );
  border-top: 1px solid rgba(255, 255, 255, 0.08);
  z-index: 1;
}

.switcher-label {
  color: rgba(255, 255, 255, 0.55);
  font-size: 12px;
  white-space: nowrap;
}

.floor-tabs {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.floor-tab {
  position: relative;
  padding: 10px 18px;
  background: linear-gradient(
    135deg,
    rgba(255, 255, 255, 0.08) 0%,
    rgba(255, 255, 255, 0.03) 100%
  );
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 12px;
  color: rgba(255, 255, 255, 0.75);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.35s cubic-bezier(0.22, 1, 0.36, 1);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.08);
}

.floor-tab:hover {
  background: linear-gradient(
    135deg,
    rgba(149, 204, 255, 0.12) 0%,
    rgba(149, 204, 255, 0.04) 100%
  );
  border-color: rgba(149, 204, 255, 0.3);
  color: #fff;
  transform: translateY(-3px);
  box-shadow:
    0 6px 20px rgba(149, 204, 255, 0.15),
    inset 0 1px 0 rgba(255, 255, 255, 0.12);
}

.floor-tab.active {
  background: linear-gradient(135deg, #e01932 0%, #c4162b 100%);
  border-color: rgba(255, 255, 255, 0.2);
  color: #fff;
  font-weight: 600;
  box-shadow:
    0 6px 24px rgba(224, 25, 50, 0.4),
    inset 0 1px 0 rgba(255, 255, 255, 0.25);
}

.tab-badge {
  position: absolute;
  top: -8px;
  right: -8px;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  font-size: 10px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 3px 10px rgba(0, 0, 0, 0.35);
  border: 1px solid rgba(255, 255, 255, 0.2);
}

.tab-badge.start {
  background: linear-gradient(135deg, #95ccff 0%, #6bb3ff 100%);
  color: #0a0a10;
}

.tab-badge.end {
  background: linear-gradient(135deg, #e01932 0%, #c4162b 100%);
  color: #fff;
}

/* 右侧栏滑入动画 - 丝滑增强 */
.slide-right-enter-active {
  transition: all 0.5s cubic-bezier(0.22, 1, 0.36, 1);
}

.slide-right-leave-active {
  transition: all 0.35s cubic-bezier(0.4, 0, 1, 1);
}

.slide-right-enter-from {
  opacity: 0;
  transform: translateX(40px) scale(0.96);
  filter: blur(8px);
}

.slide-right-leave-to {
  opacity: 0;
  transform: translateX(30px) scale(0.98);
  filter: blur(4px);
}

/* ============================================
   聊天组件 - Premium Glass Chat
   ============================================ */
.chat-container {
  position: fixed;
  bottom: 28px;
  right: 28px;
  z-index: 100;
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 16px;
}

.chat-container.expanded {
  gap: 16px;
}

.chat-trigger-btn {
  width: 60px;
  height: 60px;
  background: linear-gradient(135deg, #00e5ff 0%, #00c4cc 100%);
  border: none;
  border-radius: 50%;
  color: #001a1a;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.4s cubic-bezier(0.34, 1.56, 0.64, 1);
  box-shadow:
    0 8px 32px rgba(0, 229, 255, 0.4),
    inset 0 1px 0 rgba(255, 255, 255, 0.3);
  position: relative;
  overflow: hidden;
}

/* 聊天按钮光晕 */
.chat-trigger-btn::before {
  content: '';
  position: absolute;
  inset: -4px;
  border-radius: 50%;
  background: linear-gradient(135deg, rgba(0, 229, 255, 0.4) 0%, rgba(0, 255, 200, 0.4) 100%);
  z-index: -1;
  opacity: 0;
  transition: opacity 0.4s ease;
  animation: btnGlow 3s ease-in-out infinite;
}

@keyframes btnGlow {
  0%, 100% { transform: scale(1); opacity: 0.5; }
  50% { transform: scale(1.1); opacity: 0.8; }
}

.chat-trigger-btn:hover {
  transform: scale(1.12);
  box-shadow:
    0 12px 40px rgba(0, 229, 255, 0.5),
    inset 0 1px 0 rgba(255, 255, 255, 0.4);
}

.chat-trigger-btn:hover::before {
  opacity: 1;
}

.chat-icon-svg {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 22px;
  height: 22px;
}

/* 图标切换动画 */
.icon-fade-enter-active,
.icon-fade-leave-active {
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}

.icon-fade-enter-from {
  opacity: 0;
  transform: translate(-50%, -50%) rotate(-90deg) scale(0.8);
}

.icon-fade-leave-to {
  opacity: 0;
  transform: translate(-50%, -50%) rotate(90deg) scale(0.8);
}

.chat-panel {
  width: 380px;
  height: 500px;
  background: linear-gradient(
    180deg,
    rgba(0, 25, 35, 0.9) 0%,
    rgba(0, 18, 25, 0.95) 100%
  );
  backdrop-filter: blur(40px) saturate(180%);
  -webkit-backdrop-filter: blur(40px) saturate(180%);
  border: 1px solid rgba(0, 229, 255, 0.2);
  border-radius: 24px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  margin-bottom: 16px;
  box-shadow:
    0 16px 64px rgba(0, 0, 0, 0.5),
    inset 0 1px 0 rgba(255, 255, 255, 0.05);
}

.chat-header {
  display: none;
}

.chat-messages {
  flex: 1;
  padding: 20px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-height: 0;
}

.chat-messages-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  justify-content: flex-end;
  min-height: 100%;
}

.chat-empty {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  color: rgba(255, 255, 255, 0.6);
  font-size: 14px;
  pointer-events: none;
}

.chat-bubble {
  max-width: 85%;
  padding: 12px 16px;
  border-radius: 16px;
  font-size: 14px;
  line-height: 1.5;
  word-wrap: break-word;
  animation: bubbleUp 0.4s cubic-bezier(0.4, 0, 0.2, 1);
}

/* 向上堆叠的动画 */
.bubble-up-enter-active {
  animation: bubbleUp 0.4s cubic-bezier(0.4, 0, 0.2, 1);
}

.bubble-up-leave-active {
  animation: bubbleUpLeave 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.bubble-up-enter-from {
  opacity: 0;
  transform: translateY(30px) scale(0.9);
}

.bubble-up-leave-to {
  opacity: 0;
  transform: translateY(-10px) scale(0.95);
}

@keyframes bubbleUp {
  from {
    opacity: 0;
    transform: translateY(30px) scale(0.9);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

@keyframes bubbleUpLeave {
  from {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
  to {
    opacity: 0;
    transform: translateY(-10px) scale(0.95);
  }
}

.chat-bubble.user {
  align-self: flex-end;
  background: linear-gradient(135deg, rgba(0, 229, 255, 0.9) 0%, rgba(0, 200, 200, 0.9) 100%);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  color: #001a1a;
  border-bottom-right-radius: 4px;
  box-shadow:
    0 4px 16px rgba(0, 229, 255, 0.3),
    inset 0 1px 0 rgba(255, 255, 255, 0.3);
}

.chat-bubble.assistant {
  align-self: flex-start;
  background: rgba(0, 50, 60, 0.85);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  border: 1px solid rgba(0, 229, 255, 0.15);
  color: #fff;
  border-bottom-left-radius: 4px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.3);
}

.chat-bubble.loading {
  padding: 16px 20px;
}

.typing-indicator {
  display: flex;
  gap: 4px;
}

.typing-indicator span {
  width: 8px;
  height: 8px;
  background: #9ca3af;
  border-radius: 50%;
  animation: typing 1.4s infinite ease-in-out;
}

.typing-indicator span:nth-child(2) {
  animation-delay: 0.2s;
}

.typing-indicator span:nth-child(3) {
  animation-delay: 0.4s;
}

@keyframes typing {
  0%, 60%, 100% { transform: translateY(0); }
  30% { transform: translateY(-6px); }
}

.chat-input-area {
  display: flex;
  gap: 12px;
  padding: 16px 20px 20px;
  background: transparent;
}

.chat-input-area .chat-input {
  flex: 1;
  padding: 14px 18px;
  background: rgba(0, 40, 50, 0.7);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border: 1px solid rgba(0, 229, 255, 0.2);
  border-radius: 24px;
  font-size: 14px;
  color: #fff;
  outline: none;
  transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
}

.chat-input-area .chat-input::placeholder {
  color: rgba(255, 255, 255, 0.4);
}

.chat-input-area .chat-input:focus {
  background: rgba(0, 50, 60, 0.8);
  border-color: rgba(0, 229, 255, 0.5);
  box-shadow: 0 0 0 3px rgba(0, 229, 255, 0.15);
}

.chat-input-area .chat-input:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.chat-send-btn {
  width: 46px;
  height: 46px;
  background: rgba(0, 60, 70, 0.7);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  border: 1px solid rgba(0, 229, 255, 0.2);
  border-radius: 50%;
  color: #00e5ff;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
  flex-shrink: 0;
}

.chat-send-btn.active {
  background: linear-gradient(135deg, #00e5ff 0%, #00c4cc 100%);
  border-color: transparent;
  color: #001a1a;
  box-shadow:
    0 4px 20px rgba(0, 229, 255, 0.5),
    inset 0 1px 0 rgba(255, 255, 255, 0.3);
}

.chat-send-btn:hover:not(:disabled) {
  transform: scale(1.1);
  box-shadow: 0 6px 24px rgba(0, 229, 255, 0.5);
}

.chat-send-btn:disabled {
  cursor: not-allowed;
  opacity: 0.4;
}

/* 聊天面板动画 */
.chat-panel-enter-active,
.chat-panel-leave-active {
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
}

.chat-panel-enter-from {
  opacity: 0;
  transform: translateY(40px) scale(0.96);
}

.chat-panel-leave-to {
  opacity: 0;
  transform: translateY(20px) scale(0.98);
}


/* ============================================
   图片识别弹窗 - Glass Modal
   ============================================ */
.photo-search-modal {
  position: fixed;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 200;
  padding: 40px;
}

.photo-search-content {
  position: relative;
  width: 100%;
  max-width: 900px;
  background: linear-gradient(
    180deg,
    rgba(0, 25, 35, 0.95) 0%,
    rgba(0, 18, 25, 0.98) 100%
  );
  backdrop-filter: blur(40px) saturate(180%);
  -webkit-backdrop-filter: blur(40px) saturate(180%);
  border-radius: 24px;
  padding: 36px;
  border: 1px solid rgba(0, 229, 255, 0.2);
  box-shadow:
    0 24px 80px rgba(0, 0, 0, 0.6),
    inset 0 1px 0 rgba(255, 255, 255, 0.05);
}

.close-modal {
  position: absolute;
  top: 20px;
  right: 20px;
  width: 44px;
  height: 44px;
  background: rgba(0, 60, 70, 0.6);
  border: 1px solid rgba(0, 229, 255, 0.25);
  color: #00e5ff;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 12px;
  transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
}

.close-modal:hover {
  background: rgba(255, 100, 100, 0.2);
  border-color: rgba(255, 100, 100, 0.5);
  color: #ff6b6b;
  transform: scale(1.1) rotate(90deg);
}

.modal-title {
  color: #fff;
  font-size: 22px;
  font-weight: 600;
  margin: 0 0 28px;
  text-align: center;
  text-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
}

.photo-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 20px;
  margin: 20px 0;
}

.photo-card {
  position: relative;
  cursor: pointer;
  transition: all 0.2s;
}

.photo-card.selected .photo-placeholder,
.photo-card.selected .photo-preview,
.photo-card.selected .result-placeholder {
  border-color: #B952FF;
  box-shadow: 0 0 0 3px rgba(185, 82, 255, 0.3);
}

.photo-placeholder {
  aspect-ratio: 4/3;
  background: rgba(0, 40, 50, 0.6);
  border-radius: 18px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: rgba(255, 255, 255, 0.5);
  font-size: 14px;
  border: 2px solid rgba(0, 229, 255, 0.15);
  transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
}

.photo-placeholder.cyan-border {
  border-color: rgba(0, 229, 255, 0.5);
  box-shadow: 0 0 20px rgba(0, 229, 255, 0.2);
}

.photo-preview {
  aspect-ratio: 4/3;
  border-radius: 18px;
  overflow: hidden;
  border: 2px solid rgba(0, 229, 255, 0.5);
  box-shadow: 0 0 20px rgba(0, 229, 255, 0.2);
}

.photo-preview img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.result-placeholder {
  background: rgba(0, 40, 50, 0.6);
  padding: 24px;
  display: flex;
  align-items: center;
  gap: 18px;
  border: 2px solid rgba(0, 229, 255, 0.15);
  border-radius: 18px;
}

.result-rank {
  width: 52px;
  height: 52px;
  background: linear-gradient(135deg, rgba(0, 229, 255, 0.3) 0%, rgba(0, 200, 200, 0.3) 100%);
  border: 1px solid rgba(0, 229, 255, 0.3);
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #00e5ff;
  font-size: 22px;
  font-weight: 700;
  flex-shrink: 0;
}

.result-info {
  flex: 1;
}

.result-name {
  color: #fff;
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 4px;
}

.result-floor {
  color: #9ca3af;
  font-size: 14px;
}

.photo-label {
  color: #fff;
  font-size: 14px;
  margin-top: 12px;
  text-align: center;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.confidence-badge {
  background: linear-gradient(135deg, #00e5ff 0%, #00c4cc 100%);
  color: #001a1a;
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 600;
  box-shadow: 0 2px 8px rgba(0, 229, 255, 0.3);
}

.check-icon {
  position: absolute;
  top: 14px;
  right: 14px;
  width: 32px;
  height: 32px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: transparent;
  background: transparent;
  transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
}

.check-icon.active {
  border-color: #00ffc8;
  background: linear-gradient(135deg, #00ffc8 0%, #00e5b0 100%);
  color: #001a1a;
  box-shadow: 0 4px 12px rgba(0, 255, 200, 0.4);
  transform: scale(1.1);
}

.loading-card .photo-placeholder {
  background: #3a3d45;
}

.loading-pulse {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: #4a4d55;
  animation: pulse 1.5s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 0.5; transform: scale(0.95); }
  50% { opacity: 1; transform: scale(1); }
}

.photo-label.skeleton {
  height: 20px;
  background: #3a3d45;
  border-radius: 4px;
  animation: pulse 1.5s infinite;
}

.no-results {
  grid-column: span 2;
  text-align: center;
  padding: 40px;
  color: #9ca3af;
}

.no-results .hint {
  font-size: 14px;
  margin-top: 8px;
  color: #6b7280;
}

.loading-spinner {
  width: 40px;
  height: 40px;
  border: 3px solid #4a4d55;
  border-top-color: #B952FF;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.photo-actions {
  display: flex;
  justify-content: center;
  gap: 16px;
  margin-top: 24px;
}

.photo-actions .btn-secondary,
.photo-actions .btn-primary {
  min-width: 160px;
}

/* ============================================
   动画
   ============================================ */
.modal-enter-active,
.modal-leave-active {
  transition: all 0.3s ease;
}

.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}

.modal-enter-from .photo-search-content,
.modal-leave-to .photo-search-content {
  transform: scale(0.95);
}

.expand-enter-active,
.expand-leave-active {
  transition: all 0.3s ease;
}

.expand-enter-from,
.expand-leave-to {
  opacity: 0;
}

.expand-enter-from .expanded-map-container,
.expand-leave-to .expanded-map-container {
  transform: scale(0.95);
}

/* ============================================
   滚动条
   ============================================ */
.nav-steps-list::-webkit-scrollbar,
.navigation-results::-webkit-scrollbar,
.sidebar-content::-webkit-scrollbar,
.suggestions-dropdown::-webkit-scrollbar,
.chat-messages::-webkit-scrollbar {
  width: 4px;
}

.nav-steps-list::-webkit-scrollbar-track,
.navigation-results::-webkit-scrollbar-track,
.sidebar-content::-webkit-scrollbar-track,
.suggestions-dropdown::-webkit-scrollbar-track,
.chat-messages::-webkit-scrollbar-track {
  background: #2a2d35;
}

.nav-steps-list::-webkit-scrollbar-thumb,
.navigation-results::-webkit-scrollbar-thumb,
.sidebar-content::-webkit-scrollbar-thumb,
.suggestions-dropdown::-webkit-scrollbar-thumb,
.chat-messages::-webkit-scrollbar-thumb {
  background: #4a4d55;
  border-radius: 2px;
}

/* ============================================
   右侧楼层快捷导航 - iOS 26 Glassmorphism
   ============================================ */
.floor-quick-nav {
  position: absolute;
  right: 20px;
  top: 50%;
  transform: translateY(-50%);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  z-index: 20;
  padding: 20px 14px;
  padding-top: 36px;
  background: linear-gradient(
    165deg,
    rgba(255, 255, 255, 0.1) 0%,
    rgba(255, 255, 255, 0.04) 50%,
    rgba(224, 25, 50, 0.05) 100%
  );
  backdrop-filter: blur(50px) saturate(180%);
  -webkit-backdrop-filter: blur(50px) saturate(180%);
  border: 1px solid rgba(255, 255, 255, 0.15);
  border-radius: 22px;
  box-shadow:
    0 8px 40px rgba(0, 0, 0, 0.35),
    inset 0 1px 0 rgba(255, 255, 255, 0.15),
    inset 0 -1px 0 rgba(0, 0, 0, 0.1);
}

/* 快捷导航滑入动画 */
.quick-nav-slide-enter-active {
  animation: quickNavSlideIn 0.5s cubic-bezier(0.22, 1, 0.36, 1);
}

.quick-nav-slide-leave-active {
  animation: quickNavSlideOut 0.3s cubic-bezier(0.22, 1, 0.36, 1);
}

@keyframes quickNavSlideIn {
  0% {
    opacity: 0;
    transform: translateY(-50%) translateX(30px) scale(0.9);
    filter: blur(8px);
  }
  100% {
    opacity: 1;
    transform: translateY(-50%) translateX(0) scale(1);
    filter: blur(0);
  }
}

@keyframes quickNavSlideOut {
  0% {
    opacity: 1;
    transform: translateY(-50%) translateX(0) scale(1);
  }
  100% {
    opacity: 0;
    transform: translateY(-50%) translateX(20px) scale(0.95);
  }
}

/* 关闭按钮 */
.quick-nav-close {
  position: absolute;
  top: 8px;
  right: 8px;
  width: 24px;
  height: 24px;
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.15);
  border-radius: 8px;
  color: rgba(255, 255, 255, 0.6);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.3s cubic-bezier(0.22, 1, 0.36, 1);
}

.quick-nav-close:hover {
  background: rgba(224, 25, 50, 0.2);
  border-color: rgba(224, 25, 50, 0.4);
  color: #e01932;
  transform: scale(1.1) rotate(90deg);
}

.quick-nav-close:active {
  transform: scale(0.9) rotate(90deg);
}

/* 展开按钮 */
.quick-nav-expand-btn {
  position: absolute;
  right: 20px;
  top: 50%;
  transform: translateY(-50%);
  width: 48px;
  height: 48px;
  background: linear-gradient(
    135deg,
    rgba(255, 255, 255, 0.12) 0%,
    rgba(255, 255, 255, 0.05) 100%
  );
  backdrop-filter: blur(40px) saturate(180%);
  -webkit-backdrop-filter: blur(40px) saturate(180%);
  border: 1px solid rgba(255, 255, 255, 0.15);
  border-radius: 14px;
  color: rgba(149, 204, 255, 0.9);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 20;
  transition: all 0.4s cubic-bezier(0.22, 1, 0.36, 1);
  box-shadow:
    0 4px 20px rgba(0, 0, 0, 0.3),
    inset 0 1px 0 rgba(255, 255, 255, 0.12);
  animation: expandBtnPulse 3s ease-in-out infinite;
}

@keyframes expandBtnPulse {
  0%, 100% { box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3), inset 0 1px 0 rgba(255, 255, 255, 0.12); }
  50% { box-shadow: 0 6px 28px rgba(149, 204, 255, 0.2), inset 0 1px 0 rgba(255, 255, 255, 0.15); }
}

.quick-nav-expand-btn:hover {
  background: linear-gradient(
    135deg,
    rgba(224, 25, 50, 0.2) 0%,
    rgba(224, 25, 50, 0.08) 100%
  );
  border-color: rgba(224, 25, 50, 0.35);
  color: #e01932;
  transform: translateY(-50%) scale(1.1);
  box-shadow:
    0 8px 32px rgba(224, 25, 50, 0.25),
    inset 0 1px 0 rgba(255, 255, 255, 0.2);
}

.quick-nav-expand-btn:active {
  transform: translateY(-50%) scale(0.95);
  transition: transform 0.1s ease;
}

.quick-nav-title {
  font-size: 10px;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.45);
  text-transform: uppercase;
  letter-spacing: 1.5px;
  margin-bottom: 6px;
}

.quick-nav-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.quick-nav-btn {
  position: relative;
  width: 52px;
  height: 44px;
  background: linear-gradient(
    135deg,
    rgba(255, 255, 255, 0.08) 0%,
    rgba(255, 255, 255, 0.03) 100%
  );
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 12px;
  color: rgba(255, 255, 255, 0.75);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.35s cubic-bezier(0.22, 1, 0.36, 1);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.08);
}

.quick-nav-btn:hover {
  background: linear-gradient(
    135deg,
    rgba(149, 204, 255, 0.15) 0%,
    rgba(149, 204, 255, 0.05) 100%
  );
  border-color: rgba(149, 204, 255, 0.3);
  color: #fff;
  transform: scale(1.1) translateX(-6px);
  box-shadow:
    0 6px 24px rgba(149, 204, 255, 0.2),
    inset 0 1px 0 rgba(255, 255, 255, 0.15);
}

.quick-nav-btn:active {
  transform: scale(0.92) translateX(-2px);
  transition: transform 0.1s ease;
}

.quick-nav-btn.active {
  background: linear-gradient(135deg, #e01932 0%, #c4162b 100%);
  border-color: rgba(255, 255, 255, 0.2);
  color: #fff;
  box-shadow:
    0 6px 24px rgba(224, 25, 50, 0.45),
    inset 0 1px 0 rgba(255, 255, 255, 0.25);
  animation: activeFloorGlow 2.5s ease-in-out infinite;
}

@keyframes activeFloorGlow {
  0%, 100% {
    box-shadow: 0 6px 24px rgba(224, 25, 50, 0.45), inset 0 1px 0 rgba(255, 255, 255, 0.25);
    transform: scale(1);
  }
  50% {
    box-shadow: 0 8px 32px rgba(224, 25, 50, 0.6), inset 0 1px 0 rgba(255, 255, 255, 0.35);
    transform: scale(1.03);
  }
}

.quick-nav-btn.has-route {
  border-color: rgba(224, 25, 50, 0.5);
}

.quick-nav-btn.has-route::before {
  content: '';
  position: absolute;
  top: -3px;
  right: -3px;
  width: 8px;
  height: 8px;
  background: #e01932;
  border-radius: 50%;
  box-shadow: 0 0 8px rgba(224, 25, 50, 0.6);
}

.floor-badge {
  position: absolute;
  top: -6px;
  right: -6px;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  font-size: 9px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
}

.floor-badge.start {
  background: linear-gradient(135deg, #95ccff 0%, #6bb3ff 100%);
  color: #0a0a10;
}

.floor-badge.end {
  background: linear-gradient(135deg, #e01932 0%, #c4162b 100%);
  color: #fff;
}

/* ============================================
   底部信息栏 - iOS 26 Glassmorphism
   ============================================ */
.bottom-info-bar {
  position: absolute;
  bottom: 24px;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  align-items: center;
  gap: 32px;
  padding: 16px 32px;
  background: linear-gradient(
    135deg,
    rgba(255, 255, 255, 0.1) 0%,
    rgba(255, 255, 255, 0.04) 100%
  );
  backdrop-filter: blur(50px) saturate(180%);
  -webkit-backdrop-filter: blur(50px) saturate(180%);
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 20px;
  box-shadow:
    0 8px 40px rgba(0, 0, 0, 0.35),
    inset 0 1px 0 rgba(255, 255, 255, 0.12),
    inset 0 -1px 0 rgba(0, 0, 0, 0.08);
  z-index: 20;
  animation: bottomBarSlideIn 0.7s cubic-bezier(0.22, 1, 0.36, 1) 0.45s backwards;
}

@keyframes bottomBarSlideIn {
  0% {
    opacity: 0;
    transform: translateX(-50%) translateY(40px) scale(0.95);
    filter: blur(8px);
  }
  100% {
    opacity: 1;
    transform: translateX(-50%) translateY(0) scale(1);
    filter: blur(0);
  }
}

.info-section {
  display: flex;
  align-items: center;
  gap: 16px;
}

.info-item {
  display: flex;
  align-items: center;
  gap: 8px;
  color: rgba(255, 255, 255, 0.7);
  font-size: 13px;
}

.info-item svg {
  color: #95ccff;
}

.info-divider {
  width: 1px;
  height: 20px;
  background: rgba(255, 255, 255, 0.15);
}

.legend-section {
  display: flex;
  align-items: center;
  gap: 20px;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 8px;
  color: rgba(255, 255, 255, 0.6);
  font-size: 12px;
}

.legend-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
}

.legend-dot.start {
  background: linear-gradient(135deg, #95ccff 0%, #6bb3ff 100%);
  box-shadow: 0 0 8px rgba(149, 204, 255, 0.5);
}

.legend-dot.end {
  background: linear-gradient(135deg, #e01932 0%, #c4162b 100%);
  box-shadow: 0 0 8px rgba(224, 25, 50, 0.5);
}

.legend-line {
  width: 24px;
  height: 3px;
  background: linear-gradient(90deg, #95ccff 0%, #e01932 100%);
  border-radius: 2px;
}

/* ============================================
   响应式
   ============================================ */
@media (max-width: 1200px) {
  .nav-sidebar {
    width: 340px;
    min-width: 340px;
  }
  
  .scene {
    width: 550px;
    height: 400px;
  }
}

@media (max-width: 900px) {
  .nav-sidebar {
    width: 300px;
    min-width: 300px;
  }
  
  .scene {
    width: 450px;
    height: 320px;
  }
  
  .photo-grid {
    grid-template-columns: repeat(2, 1fr);
    gap: 12px;
  }
  
  .expanded-map-overlay {
    padding: 20px;
  }
}
</style>
