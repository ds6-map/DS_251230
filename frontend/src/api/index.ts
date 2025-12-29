import axios from 'axios'

// 创建 axios 实例
const api = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// 请求拦截器
api.interceptors.request.use(
  (config) => {
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// 响应拦截器
api.interceptors.response.use(
  (response) => {
    return response.data
  },
  (error) => {
    const message = error.response?.data?.detail || error.message || '请求失败'
    console.error('API Error:', message)
    return Promise.reject(new Error(message))
  }
)

export default api

// ==================== 导航相关 API ====================

export interface PathNode {
  id: string
  name: string
  detail?: string
  floor: number
  x?: number
  y?: number
  node_type?: string
}

export interface NavigationStep {
  step_number: number
  instruction: string
  from_node_id: string
  to_node_id: string
  distance: number
  edge_type: string
  floor_change?: number
}

export interface RouteResponse {
  success: boolean
  path: string[]
  path_nodes: PathNode[]
  total_distance: number
  steps: NavigationStep[]
  floors_involved: number[]
  message: string
}

export interface SearchNodeResponse {
  nodes: PathNode[]
  total: number
}

// 计算导航路径
export const calculateRoute = (startNodeId: string, targetName?: string, targetNodeId?: string): Promise<RouteResponse> => {
  return api.post('/navigation/route', {
    start_node_id: startNodeId,
    target_name: targetName,
    target_node_id: targetNodeId,
  })
}

// 搜索节点
export const searchNodes = (keyword: string): Promise<SearchNodeResponse> => {
  return api.get('/navigation/search', { params: { keyword } })
}

// 获取所有节点
export const getAllNodes = (floor?: number): Promise<SearchNodeResponse> => {
  return api.get('/navigation/nodes', { params: { floor } })
}

// 重新加载图结构
export const reloadGraph = (): Promise<{ message: string; nodes_count: number; edges_count: number }> => {
  return api.post('/navigation/reload')
}

// ==================== 图像识别 API ====================

export interface LocationCandidate {
  node_id: string
  node_name: string
  detail?: string
  floor: number
  confidence: number
}

export interface RecognitionResponse {
  success: boolean
  candidates: LocationCandidate[]
  message: string
  method: string
}

// 识别位置
export const recognizeLocation = (file: File): Promise<RecognitionResponse> => {
  const formData = new FormData()
  formData.append('file', file)
  return api.post('/recognition/recognize', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

// ==================== 地图管理 API ====================

export interface MapInfo {
  id: number
  floor: number
  image_url: string
  image_filename: string
  width?: number
  height?: number
  created_at: string
  updated_at: string
}

export interface NodeInfo {
  id: string
  name: string
  detail?: string
  floor: number
  x?: number
  y?: number
  node_type?: string
  has_coordinates: boolean
  created_at: string
  updated_at: string
}

export interface NodeListResponse {
  nodes: NodeInfo[]
  total: number
}

// 上传底图
export const uploadMap = (floor: number, file: File): Promise<{ message: string; map: MapInfo }> => {
  const formData = new FormData()
  formData.append('floor', floor.toString())
  formData.append('file', file)
  return api.post('/maps/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

// 获取指定楼层底图
export const getMapByFloor = (floor: number): Promise<MapInfo> => {
  return api.get(`/maps/${floor}`)
}

// 获取所有底图
export const getAllMaps = (): Promise<MapInfo[]> => {
  return api.get('/maps/')
}

// 删除底图
export const deleteMap = (floor: number): Promise<{ message: string }> => {
  return api.delete(`/maps/${floor}`)
}

// 获取节点列表（编辑器用）
export const getNodesForEditor = (floor?: number): Promise<NodeListResponse> => {
  return api.get('/maps/nodes/list', { params: { floor } })
}

// 更新节点坐标
export const updateNodePosition = (nodeId: string, x: number, y: number): Promise<{ message: string }> => {
  return api.put(`/maps/nodes/${nodeId}/position`, { x, y })
}

// 批量更新节点坐标
export const batchUpdateNodePositions = (nodes: { id: string; x: number; y: number }[]): Promise<{ message: string; updated_count: number }> => {
  return api.put('/maps/nodes/batch-update', { nodes })
}

// 获取可用楼层列表
export const getAvailableFloors = (): Promise<{ floors: number[]; total: number }> => {
  return api.get('/maps/floors/list')
}

