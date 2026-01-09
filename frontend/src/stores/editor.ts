import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { MapInfo, NodeInfo } from '@/api'
import { getAllMaps, getNodesForEditor, uploadMap, updateNodePosition, batchUpdateNodePositions, getAvailableFloors } from '@/api'

// 导入本地地图图片（与 Map3DInterface 保持一致）
import MapL1 from '@/assets/maps/Map_NS_L1.png'
import MapL2 from '@/assets/maps/Map_NS_L2.png'
import MapL3 from '@/assets/maps/Map_NS_L3.png'
import MapL4 from '@/assets/maps/Map_NS_L4.png'
import MapL5 from '@/assets/maps/Map_NS_L5.png'

// 本地底图配置（用于编辑器，与 Map3D 保持一致）
interface LocalMapConfig {
  floor: number
  name: string
  image: string
  width: number
  height: number
}

// 预设的本地地图（width/height 设为 0 表示自动检测）
const LOCAL_MAPS: LocalMapConfig[] = [
  { floor: 1, name: 'L1', image: MapL1, width: 0, height: 0 },
  { floor: 2, name: 'L2', image: MapL2, width: 0, height: 0 },
  { floor: 3, name: 'L3', image: MapL3, width: 0, height: 0 },
  { floor: 4, name: 'L4', image: MapL4, width: 0, height: 0 },
  { floor: 5, name: 'L5', image: MapL5, width: 0, height: 0 },
]

export const useEditorStore = defineStore('editor', () => {
  // 状态
  const currentFloor = ref<number | null>(null)
  const floors = ref<number[]>([1, 2, 3, 4, 5])  // 固定 1-5 层
  const maps = ref<Map<number, MapInfo>>(new Map())
  const nodes = ref<NodeInfo[]>([])
  const isLoading = ref(false)
  const error = ref<string | null>(null)
  
  // 是否使用本地底图模式（用于 Map3D 编辑）
  const useLocalMaps = ref(true)
  
  // 节点位置变更（未保存的）
  const pendingChanges = ref<Map<string, { x: number; y: number }>>(new Map())
  
  // 计算属性：获取当前底图（优先使用本地底图）
  const currentMap = computed((): MapInfo | null => {
    if (currentFloor.value === null) return null
    
    // 使用本地底图模式
    if (useLocalMaps.value) {
      const localMap = LOCAL_MAPS.find(m => m.floor === currentFloor.value)
      if (localMap) {
        return {
          id: localMap.floor,
          floor: localMap.floor,
          image_url: localMap.image,
          image_filename: `Map_NS_L${localMap.floor}.png`,
          width: localMap.width,
          height: localMap.height,
          created_at: '',
          updated_at: '',
        }
      }
    }
    
    // 回退到数据库底图
    return maps.value.get(currentFloor.value) || null
  })
  
  const currentFloorNodes = computed(() => {
    if (currentFloor.value === null) return []
    return nodes.value.filter(n => n.floor === currentFloor.value)
  })
  
  const hasUnsavedChanges = computed(() => pendingChanges.value.size > 0)
  
  // 加载可用楼层
  async function loadFloors() {
    // 本地底图模式：固定使用 1-5 层
    if (useLocalMaps.value) {
      floors.value = LOCAL_MAPS.map(m => m.floor)
      if (currentFloor.value === null && floors.value.length > 0) {
        currentFloor.value = floors.value[0]
      }
      return
    }
    
    // 数据库模式
    try {
      const response = await getAvailableFloors()
      floors.value = response.floors
      
      // 如果没有选中楼层，选择第一个
      if (currentFloor.value === null && floors.value.length > 0) {
        currentFloor.value = floors.value[0]
      }
    } catch (e: any) {
      console.error('Load floors failed:', e)
      error.value = e.message
    }
  }
  
  // 加载所有底图
  async function loadMaps() {
    // 本地底图模式：不需要从数据库加载
    if (useLocalMaps.value) {
      return
    }
    
    try {
      const allMaps = await getAllMaps()
      maps.value.clear()
      for (const map of allMaps) {
        maps.value.set(map.floor, map)
      }
    } catch (e: any) {
      console.error('Load maps failed:', e)
    }
  }
  
  // 加载节点（本地底图模式：加载所有节点，然后按楼层过滤显示）
  async function loadNodes(floor?: number) {
    isLoading.value = true
    try {
      // 本地底图模式时，加载所有节点
      const response = await getNodesForEditor(useLocalMaps.value ? undefined : floor)
      nodes.value = response.nodes
    } catch (e: any) {
      console.error('Load nodes failed:', e)
      error.value = e.message
    } finally {
      isLoading.value = false
    }
  }
  
  // 切换楼层
  async function selectFloor(floor: number) {
    // 如果有未保存的更改，提示用户
    if (hasUnsavedChanges.value) {
      // 这里可以添加确认逻辑
      console.warn('有未保存的更改')
    }
    
    currentFloor.value = floor
    pendingChanges.value.clear()
    
    // 本地底图模式：不需要重新加载节点（已经全部加载）
    if (!useLocalMaps.value) {
      await loadNodes(floor)
    }
  }
  
  // 上传底图
  async function uploadFloorMap(floor: number, file: File) {
    isLoading.value = true
    error.value = null
    
    try {
      const response = await uploadMap(floor, file)
      maps.value.set(floor, response.map)
      
      // 如果是新楼层，添加到列表
      if (!floors.value.includes(floor)) {
        floors.value.push(floor)
        floors.value.sort((a, b) => a - b)
      }
      
      return true
    } catch (e: any) {
      error.value = e.message
      return false
    } finally {
      isLoading.value = false
    }
  }
  
  // 更新节点位置（本地，未保存）
  function updateNodePositionLocal(nodeId: string, x: number, y: number) {
    pendingChanges.value.set(nodeId, { x, y })
    
    // 更新本地节点数据（确保响应式更新）
    const nodeIndex = nodes.value.findIndex(n => n.id === nodeId)
    if (nodeIndex !== -1) {
      // 创建新对象以触发响应式更新
      const node = nodes.value[nodeIndex]
      nodes.value[nodeIndex] = {
        ...node,
        x,
        y,
        has_coordinates: true,  // 确保标记为已定位
      }
    }
  }
  
  // 保存单个节点位置
  async function saveNodePosition(nodeId: string) {
    const change = pendingChanges.value.get(nodeId)
    if (!change) return true
    
    try {
      await updateNodePosition(nodeId, change.x, change.y)
      pendingChanges.value.delete(nodeId)
      return true
    } catch (e: any) {
      error.value = e.message
      return false
    }
  }
  
  // 保存所有更改
  async function saveAllChanges() {
    if (!hasUnsavedChanges.value) return true
    
    isLoading.value = true
    error.value = null
    
    try {
      const nodesToUpdate = Array.from(pendingChanges.value.entries()).map(([id, pos]) => ({
        id,
        x: pos.x,
        y: pos.y,
      }))
      
      await batchUpdateNodePositions(nodesToUpdate)
      pendingChanges.value.clear()
      return true
    } catch (e: any) {
      error.value = e.message
      return false
    } finally {
      isLoading.value = false
    }
  }
  
  // 丢弃更改
  function discardChanges() {
    pendingChanges.value.clear()
    // 重新加载节点以恢复原始位置
    if (currentFloor.value !== null) {
      loadNodes(currentFloor.value)
    }
  }
  
  // 切换本地底图模式
  function setUseLocalMaps(value: boolean) {
    useLocalMaps.value = value
  }
  
  // 初始化
  async function initialize() {
    await loadFloors()
    if (!useLocalMaps.value) {
      await loadMaps()
    }
    // 加载所有节点
    await loadNodes()
  }
  
  return {
    // 状态
    currentFloor,
    floors,
    maps,
    nodes,
    isLoading,
    error,
    pendingChanges,
    useLocalMaps,
    
    // 计算属性
    currentMap,
    currentFloorNodes,
    hasUnsavedChanges,
    
    // 方法
    loadFloors,
    loadMaps,
    loadNodes,
    selectFloor,
    uploadFloorMap,
    updateNodePositionLocal,
    saveNodePosition,
    saveAllChanges,
    discardChanges,
    initialize,
    setUseLocalMaps,
  }
})

