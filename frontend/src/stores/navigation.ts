import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { PathNode, NavigationStep, LocationCandidate, MapInfo } from '@/api'
import { calculateRoute, searchNodes, getAllNodes, getMapByFloor } from '@/api'

// 导入本地地图图片（与 Map3DInterface 保持一致）
import MapL1 from '@/assets/maps/Map_NS_L1.png'
import MapL2 from '@/assets/maps/Map_NS_L2.png'
import MapL3 from '@/assets/maps/Map_NS_L3.png'
import MapL4 from '@/assets/maps/Map_NS_L4.png'
import MapL5 from '@/assets/maps/Map_NS_L5.png'

// 本地底图映射
const LOCAL_MAP_IMAGES: Record<number, string> = {
  1: MapL1,
  2: MapL2,
  3: MapL3,
  4: MapL4,
  5: MapL5,
}

export const useNavigationStore = defineStore('navigation', () => {
  // 状态
  const currentLocation = ref<PathNode | null>(null)
  const destination = ref<PathNode | null>(null)
  const path = ref<string[]>([])
  const pathNodes = ref<PathNode[]>([])
  const steps = ref<NavigationStep[]>([])
  const totalDistance = ref(0)
  const floorsInvolved = ref<number[]>([])
  const isLoading = ref(false)
  const error = ref<string | null>(null)
  
  // 搜索结果
  const searchResults = ref<PathNode[]>([])
  
  // 位置识别结果
  const locationCandidates = ref<LocationCandidate[]>([])
  
  // 地图信息缓存
  const mapsCache = ref<Map<number, MapInfo>>(new Map())
  
  // 计算属性
  const hasRoute = computed(() => path.value.length > 0)
  const currentFloor = computed(() => currentLocation.value?.floor)
  
  // 设置当前位置
  function setCurrentLocation(location: PathNode | null) {
    currentLocation.value = location
  }
  
  // 设置目的地
  function setDestination(dest: PathNode | null) {
    destination.value = dest
  }
  
  // 设置位置识别候选
  function setLocationCandidates(candidates: LocationCandidate[]) {
    locationCandidates.value = candidates
  }
  
  // 搜索节点
  async function search(keyword: string) {
    if (!keyword.trim()) {
      searchResults.value = []
      return
    }
    
    try {
      console.log('🔍 搜索关键词:', keyword)
      const response = await searchNodes(keyword)
      console.log('✅ 搜索结果:', response)
      searchResults.value = response.nodes
      console.log('📊 结果数量:', response.nodes.length)
    } catch (e) {
      console.error('Search failed:', e)
      searchResults.value = []
    }
  }
  
  // 获取所有节点
  async function fetchAllNodes(floor?: number) {
    try {
      const response = await getAllNodes(floor)
      return response.nodes
    } catch (e) {
      console.error('Fetch nodes failed:', e)
      return []
    }
  }
  
  // 计算路线
  async function navigate() {
    if (!currentLocation.value || !destination.value) {
      error.value = '请先设置起点和终点'
      return false
    }
    
    isLoading.value = true
    error.value = null
    
    try {
      const response = await calculateRoute(
        currentLocation.value.id,
        undefined,
        destination.value.id
      )
      
      if (response.success) {
        path.value = response.path
        pathNodes.value = response.path_nodes
        steps.value = response.steps
        totalDistance.value = response.total_distance
        floorsInvolved.value = response.floors_involved
        return true
      } else {
        error.value = response.message
        return false
      }
    } catch (e: any) {
      error.value = e.message || '路径规划失败'
      return false
    } finally {
      isLoading.value = false
    }
  }
  
  // 获取底图信息（优先使用本地底图）
  async function getMapInfo(floor: number): Promise<MapInfo | null> {
    // 检查缓存
    if (mapsCache.value.has(floor)) {
      return mapsCache.value.get(floor)!
    }
    
    // 优先使用本地底图（Map3D 使用的底图）
    const localImage = LOCAL_MAP_IMAGES[floor]
    if (localImage) {
      const localMapInfo: MapInfo = {
        id: floor,
        floor: floor,
        image_url: localImage,
        image_filename: `Map_NS_L${floor}.png`,
        width: 0,  // 0 表示自动检测
        height: 0,
        created_at: '',
        updated_at: '',
      }
      mapsCache.value.set(floor, localMapInfo)
      return localMapInfo
    }
    
    // 回退到数据库底图
    try {
      const mapInfo = await getMapByFloor(floor)
      mapsCache.value.set(floor, mapInfo)
      return mapInfo
    } catch (e) {
      console.error('Get map info failed:', e)
      return null
    }
  }
  
  // 清除路线
  function clearRoute() {
    path.value = []
    pathNodes.value = []
    steps.value = []
    totalDistance.value = 0
    floorsInvolved.value = []
    error.value = null
  }
  
  // 重置所有状态
  function reset() {
    currentLocation.value = null
    destination.value = null
    searchResults.value = []
    locationCandidates.value = []
    clearRoute()
  }
  
  return {
    // 状态
    currentLocation,
    destination,
    path,
    pathNodes,
    steps,
    totalDistance,
    floorsInvolved,
    isLoading,
    error,
    searchResults,
    locationCandidates,
    
    // 计算属性
    hasRoute,
    currentFloor,
    
    // 方法
    setCurrentLocation,
    setDestination,
    setLocationCandidates,
    search,
    fetchAllNodes,
    navigate,
    getMapInfo,
    clearRoute,
    reset,
  }
})

