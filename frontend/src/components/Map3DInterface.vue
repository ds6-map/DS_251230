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

// 路线数据接口
interface RouteData {
  summary?: string
  distance_text?: string
  distance_value?: number
  duration_text?: string
  duration_value?: number
  start_address?: string
  end_address?: string
  start_location?: { lat: number; lng: number }
  end_location?: { lat: number; lng: number }
  overview_polyline?: string
}

// 聊天消息列表
interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
  debug?: string[]  // 调试信息
  routeData?: RouteData  // 导航路线数据
}

// 展开的调试信息ID集合
const expandedDebugIds = ref<Set<string>>(new Set())

// 切换调试信息展开/收起
const toggleDebug = (msgId: string) => {
  if (expandedDebugIds.value.has(msgId)) {
    expandedDebugIds.value.delete(msgId)
  } else {
    expandedDebugIds.value.add(msgId)
  }
}

// 生成 Google Maps 嵌入 URL（显示路线）
const getGoogleMapsEmbedUrl = (routeData: RouteData): string => {
  if (!routeData.start_address && !routeData.end_address) {
    return ''
  }
  
  const { start_address, end_address } = routeData
  
  const origin = start_address || ''
  const destination = end_address || ''
  
  // 编码起终点
  const encodedOrigin = encodeURIComponent(origin)
  const encodedDest = encodeURIComponent(destination)
  
  // 使用 Google Maps 的路线查询嵌入
  // 这种格式可以在 iframe 中显示带路线的地图
  return `https://www.google.com/maps?saddr=${encodedOrigin}&daddr=${encodedDest}&output=embed`
}

// 生成 Google Maps 路线导航 URL（在新窗口打开）
const getGoogleMapsDirectionsUrl = (routeData: RouteData): string => {
  if (!routeData.start_address && !routeData.start_location) {
    return 'https://maps.google.com'
  }
  
  const { start_location, end_location, start_address, end_address } = routeData
  
  const origin = start_address || (start_location ? `${start_location.lat},${start_location.lng}` : '')
  const destination = end_address || (end_location ? `${end_location.lat},${end_location.lng}` : '')
  
  // 使用 Google Maps Directions URL
  // 格式: https://www.google.com/maps/dir/起点/终点
  const encodedOrigin = encodeURIComponent(origin)
  const encodedDest = encodeURIComponent(destination)
  
  return `https://www.google.com/maps/dir/${encodedOrigin}/${encodedDest}`
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
      console.error('Search start failed:', e)
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
      console.error('Search end failed:', e)
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
    showToast('Please select start and destination first')
    return
  }
  
  showLoadingToast({ message: 'Planning route...', forbidClick: true })
  
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
      showToast(response.message || 'Route planning failed')
    }
  } catch (e: any) {
    closeToast()
    showToast(e.message || 'Route planning failed')
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

// Format distance
const formatDistance = (distance: number): string => {
  if (distance < 1000) {
    return `${Math.round(distance)} M`
  }
  return `${(distance / 1000).toFixed(1)} KM`
}

// 计算每层的Z轴偏移
const getFloorTransform = (index: number) => {
  const zOffset = index * 50
  return `translateZ(${zOffset}px)`
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
    console.log('📤 [Recognition] Starting image recognition', {
      fileName: file.name,
      fileSize: file.size,
      fileType: file.type
    })
    
    const response = await recognizeLocation(file)
    
    console.log('✅ [Recognition] Received results', {
      success: response.success,
      method: response.method,
      candidates_count: response.candidates.length,
      message: response.message,
      candidates: response.candidates.map((c, i) => 
        `[${i+1}] ${c.node_name} (Floor: ${c.floor}, Confidence: ${c.confidence})`
      )
    })
    
    if (response.success && response.candidates.length > 0) {
      recognitionCandidates.value = response.candidates.slice(0, 3)
    } else {
      showToast(response.message || 'Failed to recognize location, please retry')
    }
  } catch (e: any) {
    console.error('❌ [Recognition Error]', e)
    showToast(e.message || 'Recognition failed')
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
    showToast('Please select a location first')
    return
  }
  
  // Set as start point
  startNode.value = {
    id: selectedCandidate.value.node_id,
    name: selectedCandidate.value.node_name,
    detail: selectedCandidate.value.detail,
    floor: selectedCandidate.value.floor,
  }
  startInput.value = selectedCandidate.value.node_name
  
  closePhotoSearch()
  showToast({
    message: 'Start point set',
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
  const newZoom = Math.max(0.05, Math.min(8, mapZoom.value * zoomFactor))  // 最小 5%
  
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
  mapZoom.value = Math.max(0.05, mapZoom.value / 1.3)  // 最小 5%
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
  
  is3dDragging.value = true
  drag3dStart.value = { x: e.clientX, y: e.clientY }
  last3dRotation.value = { x: scene3dRotateX.value, z: scene3dRotateZ.value }
}

const handle3dMouseMove = (e: MouseEvent) => {
  if (!is3dDragging.value) return
  
  const deltaX = e.clientX - drag3dStart.value.x
  const deltaY = e.clientY - drag3dStart.value.y
  
  scene3dRotateZ.value = last3dRotation.value.z + deltaX * 0.3
  scene3dRotateX.value = Math.max(20, Math.min(80, last3dRotation.value.x - deltaY * 0.3))
}

const handle3dMouseUp = () => {
  is3dDragging.value = false
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
    console.log('📤 Sending message:', userMessage)
    const response = await api.post('/chat', {
      message: userMessage,
      session_id: 'map3d-session'
    })
    
    console.log('📥 Received response:', response)
    
    // Output debug info to console
    if (response.debug && response.debug.length > 0) {
      console.group('🔍 Debug Info')
      response.debug.forEach((info: string, index: number) => {
        console.log(`${index + 1}. ${info}`)
      })
      console.groupEnd()
    }
    
    // Process response
    let replyContent = response.reply || 'Received'
    let routeData: RouteData | undefined = undefined
    
    // 如果返回了导航数据，格式化显示
    if (response.tool === 'navigate' && response.data) {
      const data = response.data
      console.log('🗺️ 导航数据:', data)
      routeData = data as RouteData
      replyContent = response.reply || ''
      if (data.distance_text && data.duration_text) {
        // If LLM didn't return a detailed reply, build a short one
        if (!replyContent || replyContent.length < 20) {
          replyContent = `🗺️ Route planned!`
        }
      }
    }
    
    // 添加助手回复
    chatMessages.value.push({
      id: (Date.now() + 1).toString(),
      role: 'assistant',
      content: replyContent,
      timestamp: new Date(),
      debug: response.debug || [],
      routeData: routeData
    })
    
    scrollChatToBottom()
  } catch (e: any) {
    console.error('❌ Chat error:', e)
    // Error reply
    chatMessages.value.push({
      id: (Date.now() + 1).toString(),
      role: 'assistant',
      content: `Sorry, unable to connect to the assistant service.\n\nError: ${e.message || 'Unknown error'}\n\nPlease check your network and try again.`,
      timestamp: new Date(),
      debug: [`❌ Request failed: ${e.message || 'Unknown error'}`]
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
})
</script>

<template>
  <div class="map3d-container" :class="{ 'photo-search-active': isPhotoSearchOpen }" @click="handleContainerClick">
    
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
        <!-- Start Point Input -->
        <div class="input-group">
          <div class="input-icon start-icon"></div>
          <div class="input-wrapper">
            <input
              v-model="startInput"
              type="text"
              placeholder="Enter start..."
              class="nav-input"
              @focus="startFocused = true"
              @blur="setTimeout(() => startFocused = false, 200)"
              @input="searchStart"
            />
            <button class="camera-btn" @click="openPhotoSearch" title="Photo Recognition">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"/>
                <circle cx="12" cy="13" r="4"/>
              </svg>
            </button>
          </div>
          <!-- Start Suggestions -->
          <div v-if="startFocused && (startSearchResults.length > 0 || isSearchingStart)" class="suggestions-dropdown">
            <div v-if="isSearchingStart" class="suggestion-loading">
              <span>Searching...</span>
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
              No results found
            </div>
          </div>
        </div>

        <!-- 连接线 -->
        <div class="connector-line">
          <div class="dot"></div>
          <div class="dot"></div>
          <div class="dot"></div>
        </div>

        <!-- Destination Input -->
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
              placeholder="Enter destination..."
              class="nav-input"
              @focus="endFocused = true"
              @blur="setTimeout(() => endFocused = false, 200)"
              @input="searchEnd"
            />
          </div>
          <!-- Destination Suggestions -->
          <div v-if="endFocused && (endSearchResults.length > 0 || isSearchingEnd)" class="suggestions-dropdown">
            <div v-if="isSearchingEnd" class="suggestion-loading">
              <span>Searching...</span>
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
              No results found
            </div>
          </div>
        </div>

        <!-- Action Buttons -->
        <div class="action-row">
          <div class="time-icon">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="10"/>
              <polyline points="12 6 12 12 16 14"/>
            </svg>
          </div>
          <button class="btn-secondary" @click="resetInputs">Reset</button>
          <button 
            class="btn-primary" 
            :disabled="!startNode || !endNode"
            @click="startNavigation"
          >
            Start Navigation
          </button>
        </div>

        <!-- Navigation Results -->
        <div v-if="isNavigating" class="navigation-results">
          <!-- Route Overview -->
          <div class="route-overview">
            <div class="route-stat">
              <span class="stat-value">{{ formatDistance(totalDistance) }}</span>
              <span class="stat-label">Distance</span>
            </div>
            <div class="route-stat">
              <span class="stat-value">{{ floorsInvolved.join(', ') }}F</span>
              <span class="stat-label">Floors</span>
            </div>
          </div>
          
          <!-- Start Location Info -->
          <div class="location-info start">
            <div class="location-dot green"></div>
            <div class="location-details">
              <div class="location-name">{{ startNode?.name }}</div>
              <div class="location-address">{{ startNode?.detail || `Floor ${startNode?.floor}` }}</div>
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

          <!-- Destination Info -->
          <div class="location-info end">
            <div class="location-dot red">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor">
                <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/>
              </svg>
            </div>
            <div class="location-details">
              <div class="location-name">{{ endNode?.name }}</div>
              <div class="location-address">{{ endNode?.detail || `Floor ${endNode?.floor}` }}</div>
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
      <!-- 3D Controls -->
      <div class="viewport-controls">
        <button class="viewport-ctrl-btn" @click="zoom3dIn" title="Zoom In">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>
          </svg>
        </button>
        <button class="viewport-ctrl-btn" @click="zoom3dOut" title="Zoom Out">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="5" y1="12" x2="19" y2="12"/>
          </svg>
        </button>
        <button class="viewport-ctrl-btn" @click="reset3dView" title="Reset View">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/>
            <path d="M3 3v5h5"/>
          </svg>
        </button>
      </div>
      
      <div class="scene-wrapper" :style="scene3dStyle">
        <div class="scene">
          <div
            v-for="(floor, index) in floors"
            :key="floor.id"
            :class="['floor-layer', { 
              'selected': selectedFloor?.id === floor.id,
              'has-route': getFloorPathNodes(floor.id).length > 0
            }]"
            :style="{
              transform: getFloorTransform(index),
              '--floor-index': index
            }"
            @click="handleFloorClick(floor)"
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
            <!-- Floor Route Indicator -->
            <div v-if="isNavigating && floorsInvolved.includes(floor.id)" class="floor-route-indicator">
              <span v-if="startNode?.floor === floor.id">S</span>
              <span v-else-if="endNode?.floor === floor.id">E</span>
              <span v-else>T</span>
            </div>
          </div>
        </div>
      </div>
      
      <div class="viewport-hint">Drag to rotate · Scroll to zoom · Click floor for details</div>
    </div>

    <!-- 右侧楼层详情栏 -->
    <transition name="slide-right">
      <div v-if="isMapExpanded && expandedFloor" class="detail-sidebar">
        <!-- Header -->
        <div class="detail-header">
          <h3>{{ expandedFloor.name }} - {{ isNavigating ? 'Navigation Route' : 'Detailed Map' }}</h3>
          <button class="close-btn" @click="closeExpandedMap" title="Close">
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
          <!-- Floor Switcher -->
          <div class="floor-switcher" v-if="floorsInvolved.length > 1">
            <span class="switcher-label">Switch Floor:</span>
            <div class="floor-tabs">
              <button 
                v-for="floorId in floorsInvolved" 
                :key="floorId"
                :class="['floor-tab', { active: expandedFloor.id === floorId }]"
                @click="switchDetailFloor(floorId)"
              >
                L{{ floorId }}
                <span v-if="startNode?.floor === floorId" class="tab-badge start">S</span>
                <span v-else-if="endNode?.floor === floorId" class="tab-badge end">E</span>
              </button>
            </div>
          </div>
        </template>
        
        <!-- Non-navigation state: use original image view -->
        <template v-else>
          <!-- Control bar -->
          <div class="detail-controls">
            <button class="ctrl-btn" @click="zoomIn" title="Zoom In">
              <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="11" cy="11" r="8"/>
                <line x1="21" y1="21" x2="16.65" y2="16.65"/>
                <line x1="11" y1="8" x2="11" y2="14"/>
                <line x1="8" y1="11" x2="14" y2="11"/>
              </svg>
            </button>
            <button class="ctrl-btn" @click="zoomOut" title="Zoom Out">
              <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="11" cy="11" r="8"/>
                <line x1="21" y1="21" x2="16.65" y2="16.65"/>
                <line x1="8" y1="11" x2="14" y2="11"/>
              </svg>
            </button>
            <button class="ctrl-btn" @click="resetMapView" title="Reset">
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
          
          <!-- Hint -->
          <div class="detail-hint">
            <span>Scroll to zoom · Drag to pan</span>
          </div>
        </template>
      </div>
    </transition>

    <!-- Bottom Chat Component -->
    <div class="chat-container" :class="{ 'expanded': isChatExpanded }" @click.stop>
      <!-- Chat bubble area -->
      <transition name="chat-panel">
        <div v-if="isChatExpanded" class="chat-panel">
          <div class="chat-header">
            <span class="chat-title">Smart Assistant</span>
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
              <span>How can I help you?</span>
            </div>
            <!-- 正常顺序：最新消息在底部 -->
            <transition-group name="bubble-up" tag="div" class="chat-messages-list">
              <div 
                v-for="msg in chatMessages" 
                :key="msg.id"
                :class="['chat-bubble', msg.role, { 'with-map': msg.routeData }]"
              >
                <div class="bubble-content">{{ msg.content }}</div>
                
                <!-- 导航地图卡片 -->
                <div v-if="msg.routeData" class="route-map-card">
                  <!-- 路线信息摘要 -->
                  <div class="route-summary">
                    <div class="route-endpoints">
                      <div class="endpoint start">
                        <span class="marker">📍</span>
                        <span class="address">{{ msg.routeData.start_address || 'Start' }}</span>
                      </div>
                      <div class="route-arrow">↓</div>
                      <div class="endpoint end">
                        <span class="marker">🏁</span>
                        <span class="address">{{ msg.routeData.end_address || 'End' }}</span>
                      </div>
                    </div>
                    <div class="route-stats">
                      <div class="stat">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                          <path d="M12 22s-8-4.5-8-11.8A8 8 0 0 1 12 2a8 8 0 0 1 8 8.2c0 7.3-8 11.8-8 11.8z"/>
                          <circle cx="12" cy="10" r="3"/>
                        </svg>
                        <span>{{ msg.routeData.distance_text || '--' }}</span>
                      </div>
                      <div class="stat">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                          <circle cx="12" cy="12" r="10"/>
                          <polyline points="12,6 12,12 16,14"/>
                        </svg>
                        <span>{{ msg.routeData.duration_text || '--' }}</span>
                      </div>
                      <div v-if="msg.routeData.summary" class="stat route-name">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                          <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>
                        </svg>
                        <span>{{ msg.routeData.summary }}</span>
                      </div>
                    </div>
                  </div>
                  
                  <!-- Google 地图嵌入 -->
                  <div class="route-map-container">
                    <iframe
                      class="route-map-iframe"
                      :src="getGoogleMapsEmbedUrl(msg.routeData)"
                      allowfullscreen
                      loading="lazy"
                      referrerpolicy="no-referrer-when-downgrade"
                    ></iframe>
                  </div>
                  
                  <!-- 操作按钮 -->
                  <div class="route-actions">
                    <a 
                      :href="getGoogleMapsDirectionsUrl(msg.routeData)" 
                      target="_blank" 
                      class="route-action-btn"
                    >
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>
                        <polyline points="15,3 21,3 21,9"/>
                        <line x1="10" y1="14" x2="21" y2="3"/>
                      </svg>
                      <span>Open in Google Maps</span>
                    </a>
                  </div>
                </div>
                
                <!-- Debug info (only for assistant messages) -->
                <div v-if="msg.role === 'assistant' && msg.debug && msg.debug.length > 0" class="debug-info">
                  <button 
                    class="debug-toggle"
                    @click="toggleDebug(msg.id)"
                    :title="expandedDebugIds.has(msg.id) ? 'Collapse debug info' : 'Expand debug info'"
                  >
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <path v-if="!expandedDebugIds.has(msg.id)" d="M9 18l6-6-6-6"/>
                      <path v-else d="M18 15l-6-6-6 6"/>
                    </svg>
                    <span>Debug Info ({{ msg.debug.length }})</span>
                  </button>
                  <transition name="debug-expand">
                    <div v-if="expandedDebugIds.has(msg.id)" class="debug-content">
                      <div 
                        v-for="(info, index) in msg.debug" 
                        :key="index"
                        class="debug-item"
                      >
                        {{ info }}
                      </div>
                    </div>
                  </transition>
                </div>
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
              placeholder="Type a message..." 
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

    <!-- Photo Recognition Modal -->
    <transition name="modal">
      <div v-if="isPhotoSearchOpen" class="photo-search-modal" @click.self="closePhotoSearch">
        <div class="photo-search-content">
          <button class="close-modal" @click="closePhotoSearch">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M18 6L6 18M6 6l12 12"/>
            </svg>
          </button>
          
          <h2 class="modal-title">Photo Location Recognition</h2>
          
          <div class="photo-grid">
            <!-- User uploaded photo -->
            <div class="photo-card your-photo" :class="{ 'selected': selectedCandidate === null }">
              <div class="photo-placeholder cyan-border" v-if="!uploadedImage">
                <div v-if="isRecognizing" class="loading-spinner"></div>
                <svg v-else width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1">
                  <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"/>
                  <circle cx="12" cy="13" r="4"/>
                </svg>
              </div>
              <div v-else class="photo-preview">
                <img :src="uploadedImage" alt="Your Photo" />
              </div>
              <div class="photo-label">Your Photo</div>
            </div>
            
            <!-- Recognition results -->
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
                    <div class="result-floor">Floor {{ candidate.floor }}</div>
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
            
            <!-- Recognizing -->
            <template v-else-if="isRecognizing">
              <div class="photo-card loading-card" v-for="i in 3" :key="i">
                <div class="photo-placeholder">
                  <div class="loading-pulse"></div>
                </div>
                <div class="photo-label skeleton"></div>
              </div>
            </template>
            
            <!-- No results -->
            <div v-else-if="!isRecognizing && uploadedImage" class="no-results">
              <p>No matching location found</p>
              <p class="hint">Try taking a clearer photo</p>
            </div>
          </div>
          
          <div class="photo-actions">
            <button class="btn-secondary" @click="retakePhoto">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"/>
                <circle cx="12" cy="13" r="4"/>
              </svg>
              Re-upload
            </button>
            <button 
              class="btn-primary" 
              :disabled="!selectedCandidate"
              @click="confirmRecognizedLocation"
            >
              Confirm Location
            </button>
          </div>
        </div>
      </div>
    </transition>
  </div>
</template>

<style scoped>
/* ============================================
   主容器
   ============================================ */
.map3d-container {
  position: relative;
  width: 100%;
  height: 100vh;
  min-height: 600px;
  background: #1a1d24;
  overflow: hidden;
  display: flex;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', sans-serif;
}

.map3d-container.photo-search-active::before {
  content: '';
  position: absolute;
  inset: 0;
  background: rgba(0, 0, 0, 0.6);
  z-index: 100;
}

/* ============================================
   左侧导航面板
   ============================================ */
.nav-sidebar {
  position: relative;
  width: 380px;
  min-width: 380px;
  height: 100%;
  background: #2a2d35;
  border-radius: 0 20px 20px 0;
  display: flex;
  flex-direction: column;
  z-index: 50;
  transition: all 0.3s ease;
}

.nav-sidebar.collapsed {
  width: 0;
  min-width: 0;
  padding: 0;
}

.nav-sidebar.collapsed .sidebar-content {
  opacity: 0;
  pointer-events: none;
}

.collapse-btn {
  position: absolute;
  right: -16px;
  top: 50%;
  transform: translateY(-50%);
  width: 32px;
  height: 64px;
  background: #3a3d45;
  border: none;
  border-radius: 0 8px 8px 0;
  color: #fff;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 60;
  transition: background 0.2s;
}

.collapse-btn:hover {
  background: #4a4d55;
}

.sidebar-content {
  padding: 24px 20px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  transition: opacity 0.2s;
  overflow-y: auto;
  flex: 1;
}

/* ============================================
   输入框组
   ============================================ */
.input-group {
  position: relative;
  display: flex;
  align-items: center;
  gap: 12px;
}

.input-icon {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.start-icon {
  background: #6b7280;
}

.end-icon {
  color: #ef4444;
}

.input-wrapper {
  flex: 1;
  position: relative;
  display: flex;
  align-items: center;
}

.nav-input {
  width: 100%;
  padding: 14px 50px 14px 16px;
  background: #3a3d45;
  border: 1px solid #4a4d55;
  border-radius: 10px;
  font-size: 14px;
  color: #fff;
  outline: none;
  transition: all 0.2s;
}

.nav-input::placeholder {
  color: #6b7280;
}

.nav-input:focus {
  border-color: #B952FF;
  box-shadow: 0 0 0 2px rgba(185, 82, 255, 0.2);
}

.camera-btn {
  position: absolute;
  right: 8px;
  width: 36px;
  height: 36px;
  background: transparent;
  border: none;
  border-radius: 8px;
  color: #9ca3af;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}

.camera-btn:hover {
  background: #4a4d55;
  color: #fff;
}

/* 连接线 */
.connector-line {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: 4px 0;
  margin-left: 11px;
}

.connector-line .dot {
  width: 4px;
  height: 4px;
  background: #6b7280;
  border-radius: 50%;
}

/* 联想下拉 */
.suggestions-dropdown {
  position: absolute;
  top: 100%;
  left: 36px;
  right: 0;
  margin-top: 4px;
  background: #3a3d45;
  border: 1px solid #4a4d55;
  border-radius: 10px;
  overflow: hidden;
  z-index: 100;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.3);
  max-height: 250px;
  overflow-y: auto;
}

.suggestion-item {
  padding: 12px 16px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  cursor: pointer;
  transition: background 0.15s;
}

.suggestion-item:hover {
  background: #4a4d55;
}

.suggestion-name {
  color: #fff;
  font-size: 14px;
}

.suggestion-floor {
  color: #9ca3af;
  font-size: 12px;
  background: #2a2d35;
  padding: 2px 8px;
  border-radius: 4px;
}

.suggestion-loading,
.suggestion-empty {
  padding: 16px;
  text-align: center;
  color: #9ca3af;
  font-size: 14px;
}

/* ============================================
   按钮组
   ============================================ */
.action-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 8px;
}

.time-icon {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #9ca3af;
}

.btn-secondary {
  flex: 1;
  padding: 12px 16px;
  background: #3a3d45;
  border: 1px solid #4a4d55;
  border-radius: 10px;
  color: #fff;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.btn-secondary:hover {
  background: #4a4d55;
}

.btn-primary {
  flex: 1;
  padding: 12px 16px;
  background: linear-gradient(135deg, #B952FF 0%, #9333ea 100%);
  border: none;
  border-radius: 10px;
  color: #fff;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-primary:hover {
  opacity: 0.9;
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
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
   3D地图视图
   ============================================ */
.map3d-viewport {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  perspective: 1200px;
  perspective-origin: 50% 50%;
  transition: all 0.5s ease;
  position: relative;
  overflow: hidden;
}

.map3d-viewport.with-nav {
  justify-content: flex-end;
  padding-right: 5%;
}

.map3d-viewport.sidebar-collapsed {
  justify-content: center;
  padding-left: 40px;
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
  padding-left: 40px;
  padding-right: 45%;
}

/* 3D视图控制按钮 */
.viewport-controls {
  position: absolute;
  top: 20px;
  right: 20px;
  display: flex;
  gap: 8px;
  z-index: 10;
}

.viewport-ctrl-btn {
  width: 36px;
  height: 36px;
  background: rgba(58, 61, 69, 0.9);
  border: 1px solid #4a4d55;
  border-radius: 8px;
  color: #9ca3af;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
  backdrop-filter: blur(8px);
}

.viewport-ctrl-btn:hover {
  background: #4a4d55;
  color: #fff;
}

.viewport-hint {
  position: absolute;
  bottom: 20px;
  left: 50%;
  transform: translateX(-50%);
  padding: 8px 16px;
  background: rgba(58, 61, 69, 0.9);
  backdrop-filter: blur(8px);
  border: 1px solid #4a4d55;
  border-radius: 8px;
  font-size: 12px;
  color: #9ca3af;
  pointer-events: none;
}

.scene-wrapper {
  transform-style: preserve-3d;
  transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  cursor: grab;
}

.scene-wrapper:active {
  cursor: grabbing;
}

.scene {
  position: relative;
  width: 700px;
  height: 500px;
  transform-style: preserve-3d;
}

/* ============================================
   楼层
   ============================================ */
.floor-layer {
  position: absolute;
  width: 100%;
  height: 100%;
  cursor: pointer;
  transform-style: preserve-3d;
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
  background: transparent;
}

.floor-layer:hover {
  transform: translateZ(calc(var(--floor-index) * 50px)) translateY(-8px);
}

.floor-layer.selected {
  z-index: 10;
}

.floor-image {
  width: 100%;
  height: 100%;
  object-fit: contain;
  display: block;
}

.floor-label-tag {
  position: absolute;
  top: 10px;
  left: 10px;
  padding: 4px 12px;
  background: rgba(34, 39, 49, 0.9);
  border-radius: 4px;
  color: #fff;
  font-size: 12px;
  font-weight: 600;
  pointer-events: none;
  z-index: 5;
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
  box-shadow: 0 0 20px rgba(255, 68, 68, 0.3);
}

/* 楼层路线指示器 */
.floor-route-indicator {
  position: absolute;
  top: 10px;
  right: 10px;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: linear-gradient(135deg, #ff4444 0%, #cc3333 100%);
  color: #fff;
  font-size: 12px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 2px 8px rgba(255, 68, 68, 0.5);
  z-index: 5;
  pointer-events: none;
}

.floor-route-indicator span {
  line-height: 1;
}

/* ============================================
   右侧楼层详情栏
   ============================================ */
.detail-sidebar {
  position: fixed;
  top: 0;
  right: 0;
  width: 45%;
  min-width: 400px;
  max-width: 700px;
  height: 100vh;
  background: #2a2d35;
  display: flex;
  flex-direction: column;
  z-index: 50;
  box-shadow: -4px 0 32px rgba(0, 0, 0, 0.4);
}

.detail-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  background: #3a3d45;
  border-bottom: 1px solid #4a4d55;
}

.detail-header h3 {
  color: #fff;
  font-size: 16px;
  font-weight: 600;
  margin: 0;
}

.detail-header .close-btn {
  width: 32px;
  height: 32px;
  background: rgba(255, 255, 255, 0.1);
  border: none;
  border-radius: 8px;
  color: #9ca3af;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}

.detail-header .close-btn:hover {
  background: rgba(255, 255, 255, 0.2);
  color: #fff;
}

.detail-controls {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 20px;
  background: #2a2d35;
  border-bottom: 1px solid #3a3d45;
}

.detail-controls .ctrl-btn {
  width: 32px;
  height: 32px;
  background: #4a4d55;
  border: none;
  border-radius: 6px;
  color: #9ca3af;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}

.detail-controls .ctrl-btn:hover {
  background: #5a5d65;
  color: #fff;
}

.detail-controls .zoom-indicator {
  color: #9ca3af;
  font-size: 13px;
  min-width: 45px;
  text-align: center;
  margin-left: auto;
}

.detail-map-view {
  flex: 1;
  overflow: hidden;
  cursor: grab;
  position: relative;
  background: #1a1d24;
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
  transition: transform 0.08s linear;
}

.detail-hint {
  padding: 10px 20px;
  background: #3a3d45;
  border-top: 1px solid #4a4d55;
  text-align: center;
  color: #9ca3af;
  font-size: 11px;
}

/* 导航状态下的地图包装器 */
.detail-map-wrapper {
  flex: 1;
  min-height: 0;
  position: relative;
  background: #1a1d24;
}

/* 楼层切换器 */
.floor-switcher {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 20px;
  background: #3a3d45;
  border-top: 1px solid #4a4d55;
}

.switcher-label {
  color: #9ca3af;
  font-size: 12px;
  white-space: nowrap;
}

.floor-tabs {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.floor-tab {
  position: relative;
  padding: 6px 14px;
  background: #2a2d35;
  border: 1px solid #4a4d55;
  border-radius: 6px;
  color: #9ca3af;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.floor-tab:hover {
  background: #3a3d45;
  color: #fff;
}

.floor-tab.active {
  background: linear-gradient(135deg, #ff4444 0%, #cc3333 100%);
  border-color: #ff4444;
  color: #fff;
}

.tab-badge {
  position: absolute;
  top: -6px;
  right: -6px;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  font-size: 9px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
}

.tab-badge.start {
  background: #22c55e;
  color: #fff;
}

.tab-badge.end {
  background: #ef4444;
  color: #fff;
}

/* 右侧栏滑入动画 */
.slide-right-enter-active,
.slide-right-leave-active {
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
}

.slide-right-enter-from {
  opacity: 0;
  transform: translateX(100%);
}

.slide-right-leave-to {
  opacity: 0;
  transform: translateX(100%);
}

/* ============================================
   聊天组件
   ============================================ */
.chat-container {
  position: fixed;
  bottom: 24px;
  right: 24px;
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
  width: 56px;
  height: 56px;
  background: linear-gradient(135deg, #B952FF 0%, #9333ea 100%);
  border: none;
  border-radius: 50%;
  color: #fff;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 0 4px 20px rgba(185, 82, 255, 0.4);
  position: relative;
  overflow: hidden;
}

.chat-trigger-btn:hover {
  transform: scale(1.1);
  box-shadow: 0 6px 28px rgba(185, 82, 255, 0.5);
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
  width: 360px;
  height: 480px;
  background: transparent;
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border-radius: 20px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  margin-bottom: 16px;
}

.chat-header {
  display: none;
}

.chat-messages {
  flex: 1;
  padding: 20px;
  overflow-y: auto;
  overflow-x: hidden;
  display: flex;
  flex-direction: column;
  min-height: 0;
  max-height: 100%;
  /* 确保可以滚动 */
  -webkit-overflow-scrolling: touch;
  scroll-behavior: smooth;
}

.chat-messages-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  justify-content: flex-end;
  /* 移除 min-height: 100%，让内容自然增长 */
  padding-bottom: 8px;
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
  background: linear-gradient(135deg, rgba(185, 82, 255, 0.9) 0%, rgba(147, 51, 234, 0.9) 100%);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  color: #fff;
  border-bottom-right-radius: 4px;
  box-shadow: 0 2px 12px rgba(185, 82, 255, 0.3);
}

.chat-bubble.assistant {
  align-self: flex-start;
  background: rgba(58, 61, 69, 0.85);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  color: #fff;
  border-bottom-left-radius: 4px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.2);
}

/* 带地图的消息气泡 */
.chat-bubble.with-map {
  max-width: 95%;
  padding: 12px;
}

/* 导航地图卡片 */
.route-map-card {
  margin-top: 10px;
  background: rgba(0, 0, 0, 0.2);
  border-radius: 12px;
  overflow: hidden;
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.route-summary {
  padding: 12px;
}

.route-endpoints {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-bottom: 10px;
}

.endpoint {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  font-size: 12px;
}

.endpoint .marker {
  flex-shrink: 0;
  font-size: 14px;
}

.endpoint .address {
  color: rgba(255, 255, 255, 0.9);
  line-height: 1.4;
  word-break: break-word;
}

.endpoint.start .address {
  color: #4ade80;
}

.endpoint.end .address {
  color: #f87171;
}

.route-arrow {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.4);
  margin-left: 11px;
  line-height: 1;
}

.route-stats {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  padding-top: 10px;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
}

.route-stats .stat {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.8);
}

.route-stats .stat svg {
  color: rgba(255, 255, 255, 0.5);
  flex-shrink: 0;
}

.route-stats .route-name {
  flex-basis: 100%;
  color: rgba(255, 255, 255, 0.6);
}

/* 地图容器 */
.route-map-container {
  width: 100%;
  height: 180px;
  background: rgba(0, 0, 0, 0.3);
  position: relative;
}

.route-map-iframe {
  width: 100%;
  height: 100%;
  border: none;
  filter: saturate(0.9) brightness(0.95);
}

/* 操作按钮 */
.route-actions {
  padding: 8px 12px;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
}

.route-action-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  background: rgba(59, 130, 246, 0.3);
  border: 1px solid rgba(59, 130, 246, 0.5);
  border-radius: 6px;
  color: #93c5fd;
  font-size: 12px;
  text-decoration: none;
  transition: all 0.2s;
}

.route-action-btn:hover {
  background: rgba(59, 130, 246, 0.4);
  color: #bfdbfe;
}

.route-action-btn svg {
  flex-shrink: 0;
}

.chat-bubble.loading {
  padding: 16px 20px;
}

/* 调试信息样式 */
.debug-info {
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
}

.debug-toggle {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 8px;
  background: rgba(255, 255, 255, 0.1);
  border: none;
  border-radius: 4px;
  color: rgba(255, 255, 255, 0.7);
  font-size: 11px;
  cursor: pointer;
  transition: all 0.2s;
  width: 100%;
  text-align: left;
}

.debug-toggle:hover {
  background: rgba(255, 255, 255, 0.15);
  color: rgba(255, 255, 255, 0.9);
}

.debug-toggle svg {
  flex-shrink: 0;
  transition: transform 0.2s;
}

.debug-content {
  margin-top: 8px;
  padding: 8px;
  background: rgba(0, 0, 0, 0.3);
  border-radius: 6px;
  font-size: 11px;
  line-height: 1.6;
  max-height: 300px;
  overflow-y: auto;
}

.debug-item {
  padding: 4px 0;
  color: rgba(255, 255, 255, 0.8);
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}

.debug-item:last-child {
  border-bottom: none;
}

/* 调试信息展开动画 */
.debug-expand-enter-active,
.debug-expand-leave-active {
  transition: all 0.3s ease;
  overflow: hidden;
}

.debug-expand-enter-from {
  opacity: 0;
  max-height: 0;
  margin-top: 0;
  padding-top: 0;
  padding-bottom: 0;
}

.debug-expand-leave-to {
  opacity: 0;
  max-height: 0;
  margin-top: 0;
  padding-top: 0;
  padding-bottom: 0;
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
  padding: 12px 16px;
  background: rgba(58, 61, 69, 0.7);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 24px;
  font-size: 14px;
  color: #fff;
  outline: none;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.chat-input-area .chat-input::placeholder {
  color: rgba(255, 255, 255, 0.5);
}

.chat-input-area .chat-input:focus {
  background: rgba(58, 61, 69, 0.85);
  border-color: rgba(185, 82, 255, 0.6);
  box-shadow: 0 0 0 3px rgba(185, 82, 255, 0.2);
}

.chat-input-area .chat-input:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.chat-send-btn {
  width: 44px;
  height: 44px;
  background: rgba(74, 77, 85, 0.7);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 50%;
  color: rgba(255, 255, 255, 0.6);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  flex-shrink: 0;
}

.chat-send-btn.active {
  background: linear-gradient(135deg, rgba(185, 82, 255, 0.9) 0%, rgba(147, 51, 234, 0.9) 100%);
  border-color: rgba(185, 82, 255, 0.5);
  color: #fff;
  box-shadow: 0 4px 16px rgba(185, 82, 255, 0.4);
}

.chat-send-btn:hover:not(:disabled) {
  transform: scale(1.1);
  box-shadow: 0 6px 20px rgba(185, 82, 255, 0.5);
}

.chat-send-btn:disabled {
  cursor: not-allowed;
  opacity: 0.5;
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
   图片识别弹窗
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
  background: #2a2d35;
  border-radius: 20px;
  padding: 32px;
  border: 1px solid #4a4d55;
}

.close-modal {
  position: absolute;
  top: 16px;
  right: 16px;
  width: 40px;
  height: 40px;
  background: transparent;
  border: none;
  color: #9ca3af;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  transition: all 0.2s;
}

.close-modal:hover {
  background: #4a4d55;
  color: #fff;
}

.modal-title {
  color: #fff;
  font-size: 20px;
  font-weight: 600;
  margin: 0 0 24px;
  text-align: center;
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
  background: #3a3d45;
  border-radius: 16px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #9ca3af;
  font-size: 14px;
  border: 3px solid transparent;
  transition: all 0.2s;
}

.photo-placeholder.cyan-border {
  border-color: #00e5ff;
}

.photo-preview {
  aspect-ratio: 4/3;
  border-radius: 16px;
  overflow: hidden;
  border: 3px solid #00e5ff;
}

.photo-preview img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.result-placeholder {
  background: #3a3d45;
  padding: 20px;
  display: flex;
  align-items: center;
  gap: 16px;
  border: 3px solid transparent;
}

.result-rank {
  width: 48px;
  height: 48px;
  background: #4a4d55;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 20px;
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
  background: linear-gradient(135deg, #B952FF 0%, #9333ea 100%);
  color: #fff;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 600;
}

.check-icon {
  position: absolute;
  top: 12px;
  right: 12px;
  width: 28px;
  height: 28px;
  border: 2px solid #9ca3af;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: transparent;
  background: transparent;
  transition: all 0.2s;
}

.check-icon.active {
  border-color: #61C554;
  background: #61C554;
  color: #fff;
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
  width: 6px;
}

.nav-steps-list::-webkit-scrollbar-track,
.navigation-results::-webkit-scrollbar-track,
.sidebar-content::-webkit-scrollbar-track,
.suggestions-dropdown::-webkit-scrollbar-track,
.chat-messages::-webkit-scrollbar-track {
  background: rgba(42, 45, 53, 0.3);
  border-radius: 3px;
}

.nav-steps-list::-webkit-scrollbar-thumb,
.navigation-results::-webkit-scrollbar-thumb,
.sidebar-content::-webkit-scrollbar-thumb,
.suggestions-dropdown::-webkit-scrollbar-thumb,
.chat-messages::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.3);
  border-radius: 3px;
  transition: background 0.2s;
}

.nav-steps-list::-webkit-scrollbar-thumb:hover,
.navigation-results::-webkit-scrollbar-thumb:hover,
.sidebar-content::-webkit-scrollbar-thumb:hover,
.suggestions-dropdown::-webkit-scrollbar-thumb:hover,
.chat-messages::-webkit-scrollbar-thumb:hover {
  background: rgba(255, 255, 255, 0.5);
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
