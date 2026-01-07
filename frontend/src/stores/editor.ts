import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { MapInfo, NodeInfo } from '@/api'
import { getAllMaps, getNodesForEditor, uploadMap, updateNodePosition, batchUpdateNodePositions, getAvailableFloors } from '@/api'

export const useEditorStore = defineStore('editor', () => {
  // 状态
  const currentFloor = ref<number | null>(null)
  const floors = ref<number[]>([])
  const maps = ref<Map<number, MapInfo>>(new Map())
  const nodes = ref<NodeInfo[]>([])
  const isLoading = ref(false)
  const error = ref<string | null>(null)
  
  // 节点位置变更（未保存的）
  const pendingChanges = ref<Map<string, { x: number; y: number }>>(new Map())
  
  // 计算属性
  const currentMap = computed(() => {
    if (currentFloor.value === null) return null
    return maps.value.get(currentFloor.value) || null
  })
  
  const currentFloorNodes = computed(() => {
    if (currentFloor.value === null) return []
    return nodes.value.filter(n => n.floor === currentFloor.value)
  })
  
  const hasUnsavedChanges = computed(() => pendingChanges.value.size > 0)
  
  // 加载可用楼层
  async function loadFloors() {
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
  
  // 加载节点
  async function loadNodes(floor?: number) {
    isLoading.value = true
    try {
      const response = await getNodesForEditor(floor)
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
    await loadNodes(floor)
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
  
  // 初始化
  async function initialize() {
    await Promise.all([loadFloors(), loadMaps()])
    if (currentFloor.value !== null) {
      await loadNodes(currentFloor.value)
    }
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
  }
})

