<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { showToast, showLoadingToast, closeToast, showConfirmDialog } from 'vant'
import { useEditorStore } from '@/stores/editor'
import ZoomableMapCanvas from '@/components/ZoomableMapCanvas.vue'

const store = useEditorStore()

// 文件上传
const fileInput = ref<HTMLInputElement | null>(null)

// 当前选中的节点
const selectedNodeId = ref<string | null>(null)

// 地图画布引用
const mapCanvasRef = ref<InstanceType<typeof ZoomableMapCanvas> | null>(null)

// 计算属性
const currentMap = computed(() => store.currentMap)
const currentFloorNodes = computed(() => store.currentFloorNodes)
const hasUnsavedChanges = computed(() => store.hasUnsavedChanges)

// 统计信息
const nodeStats = computed(() => {
  const total = currentFloorNodes.value.length
  const located = currentFloorNodes.value.filter(n => n.has_coordinates).length
  return { total, located, unlocated: total - located }
})

// 初始化
onMounted(async () => {
  showLoadingToast({ message: '加载中...', forbidClick: true })
  await store.initialize()
  closeToast()
})

// 切换楼层
const handleFloorChange = async (floor: number) => {
  if (hasUnsavedChanges.value) {
    try {
      await showConfirmDialog({
        title: '提示',
        message: '有未保存的更改，是否放弃？',
      })
      store.discardChanges()
    } catch {
      return
    }
  }
  
  showLoadingToast({ message: '加载中...', forbidClick: true })
  await store.selectFloor(floor)
  selectedNodeId.value = null
  closeToast()
}

// 上传底图
const triggerUpload = () => {
  fileInput.value?.click()
}

const handleFileChange = async (event: Event) => {
  const target = event.target as HTMLInputElement
  const file = target.files?.[0]
  
  if (!file) return
  
  if (store.currentFloor === null) {
    showToast('请先选择楼层')
    return
  }
  
  showLoadingToast({ message: '上传中...', forbidClick: true })
  
  const success = await store.uploadFloorMap(store.currentFloor, file)
  closeToast()
  
  if (success) {
    showToast({ message: '上传成功', icon: 'success' })
  } else {
    showToast(store.error || '上传失败')
  }
  
  target.value = ''
}

// 节点拖拽结束
const handleNodeDragEnd = (nodeId: string, x: number, y: number) => {
  store.updateNodePositionLocal(nodeId, x, y)
}

// 选择节点
const handleNodeSelect = (nodeId: string) => {
  selectedNodeId.value = nodeId
}

// 定位节点到地图中心
const locateNode = (nodeId: string) => {
  selectedNodeId.value = nodeId
  const node = currentFloorNodes.value.find(n => n.id === nodeId)
  if (node && !node.has_coordinates) {
    const centerX = (currentMap.value?.width || 300) / 2
    const centerY = (currentMap.value?.height || 300) / 2
    node.x = centerX
    node.y = centerY
    store.updateNodePositionLocal(nodeId, centerX, centerY)
    showToast('节点已定位到地图中心，请拖拽调整位置')
  }
  mapCanvasRef.value?.resetView()
}

// 保存所有更改
const saveAllChanges = async () => {
  showLoadingToast({ message: '保存中...', forbidClick: true })
  
  const success = await store.saveAllChanges()
  closeToast()
  
  if (success) {
    showToast({ message: '保存成功', icon: 'success' })
  } else {
    showToast(store.error || '保存失败')
  }
}

// 放弃更改
const discardChanges = async () => {
  try {
    await showConfirmDialog({
      title: '提示',
      message: '确定要放弃所有未保存的更改吗？',
    })
    store.discardChanges()
    showToast('已放弃更改')
  } catch {
    // 用户取消
  }
}

// 格式化坐标
const formatCoord = (value?: number) => {
  if (value === undefined || value === null) return '-'
  return Math.round(value)
}
</script>

<template>
  <div class="editor-page">
    <!-- 顶部导航栏 -->
    <header class="editor-header">
      <div class="header-left">
        <button class="back-btn" @click="$router.back()">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M19 12H5M12 19l-7-7 7-7"/>
          </svg>
        </button>
        <h1 class="header-title">
          <svg class="title-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polygon points="1 6 1 22 8 18 16 22 23 18 23 2 16 6 8 2 1 6"/>
            <line x1="8" y1="2" x2="8" y2="18"/>
            <line x1="16" y1="6" x2="16" y2="22"/>
          </svg>
          地图编辑器
        </h1>
      </div>
      <div class="header-actions">
        <button v-if="hasUnsavedChanges" class="btn btn-ghost" @click="discardChanges">
          放弃更改
        </button>
        <button v-if="hasUnsavedChanges" class="btn btn-primary" @click="saveAllChanges">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M19 21H5a2 2 0 01-2-2V5a2 2 0 012-2h11l5 5v11a2 2 0 01-2 2z"/>
            <polyline points="17 21 17 13 7 13 7 21"/>
            <polyline points="7 3 7 8 15 8"/>
          </svg>
          保存
        </button>
      </div>
    </header>
    
    <!-- 工具栏 -->
    <div class="toolbar">
      <div class="toolbar-group">
        <span class="toolbar-label">楼层选择</span>
        <div class="floor-tabs">
          <button
            v-for="floor in store.floors"
            :key="floor"
            :class="['floor-tab', { active: store.currentFloor === floor }]"
            @click="handleFloorChange(floor)"
          >
            {{ floor }}F
          </button>
        </div>
      </div>
      
      <div class="toolbar-divider"></div>
      
      <button class="btn btn-secondary" @click="triggerUpload">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <rect x="3" y="3" width="18" height="18" rx="2" ry="2"/>
          <circle cx="8.5" cy="8.5" r="1.5"/>
          <polyline points="21 15 16 10 5 21"/>
        </svg>
        上传底图
      </button>
      <input
        ref="fileInput"
        type="file"
        accept="image/png,image/jpeg,image/webp"
        style="display: none"
        @change="handleFileChange"
      />
    </div>
    
    <!-- 未保存提示 -->
    <div v-if="hasUnsavedChanges" class="unsaved-alert slide-up">
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <circle cx="12" cy="12" r="10"/>
        <line x1="12" y1="8" x2="12" y2="12"/>
        <line x1="12" y1="16" x2="12.01" y2="16"/>
      </svg>
      <span>有 <strong>{{ nodeStats.located }}</strong> 个节点位置已更改</span>
      <button class="alert-btn" @click="saveAllChanges">立即保存</button>
    </div>
    
    <!-- 主内容区 -->
    <div class="main-content">
      <!-- 地图卡片 -->
      <div class="map-card glass-card">
        <div class="card-header">
          <h2 class="card-title">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polygon points="1 6 1 22 8 18 16 22 23 18 23 2 16 6 8 2 1 6"/>
              <line x1="8" y1="2" x2="8" y2="18"/>
              <line x1="16" y1="6" x2="16" y2="22"/>
            </svg>
            地图预览
          </h2>
          <span class="card-hint">滚轮缩放 · 拖拽平移 · 点击选中节点后拖动</span>
        </div>
        <div class="map-container">
          <ZoomableMapCanvas
            v-if="currentMap"
            ref="mapCanvasRef"
            :map-info="currentMap"
            :nodes="currentFloorNodes"
            :editable="true"
            :selected-node-id="selectedNodeId"
            @node-drag-end="handleNodeDragEnd"
            @node-click="handleNodeSelect"
          />
          
          <div v-else class="empty-state">
            <div class="empty-icon">
              <svg width="56" height="56" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" opacity="0.3">
                <polygon points="1 6 1 22 8 18 16 22 23 18 23 2 16 6 8 2 1 6"/>
                <line x1="8" y1="2" x2="8" y2="18"/>
                <line x1="16" y1="6" x2="16" y2="22"/>
              </svg>
            </div>
            <h3 class="empty-title">暂无底图</h3>
            <p class="empty-desc">请选择楼层并上传对应的底图</p>
            <button class="btn btn-primary" @click="triggerUpload">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/>
                <polyline points="17 8 12 3 7 8"/>
                <line x1="12" y1="3" x2="12" y2="15"/>
              </svg>
              上传底图
            </button>
          </div>
        </div>
      </div>
      
      <!-- 节点列表卡片 -->
      <div class="node-card glass-card">
        <div class="card-header">
          <h2 class="card-title">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/>
              <circle cx="12" cy="10" r="3"/>
            </svg>
            节点列表
            <span class="node-badge">{{ nodeStats.total }}</span>
          </h2>
          <div class="stats-group">
            <span class="stat-tag success">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3">
                <polyline points="20 6 9 17 4 12"/>
              </svg>
              {{ nodeStats.located }}
            </span>
            <span class="stat-tag warning">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3">
                <circle cx="12" cy="12" r="10"/>
              </svg>
              {{ nodeStats.unlocated }}
            </span>
          </div>
        </div>
        
        <div class="node-list">
          <div
            v-for="node in currentFloorNodes"
            :key="node.id"
            :class="['node-item', { selected: selectedNodeId === node.id }]"
            @click="handleNodeSelect(node.id)"
          >
            <div class="node-info">
              <div class="node-name">{{ node.name || node.id }}</div>
              <div class="node-detail">{{ node.detail || node.id }}</div>
            </div>
            <div class="node-action">
              <span v-if="node.has_coordinates" class="coord-badge">
                ({{ formatCoord(node.x) }}, {{ formatCoord(node.y) }})
              </span>
              <button v-else class="btn-mini" @click.stop="locateNode(node.id)">
                定位
              </button>
            </div>
          </div>
          
          <div v-if="currentFloorNodes.length === 0" class="empty-list">
            <span>该楼层暂无节点数据</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* ========== 夜间极简灰主题 ========== */
.editor-page {
  min-height: 100vh;
  background: #000000;
  padding-bottom: 24px;
  position: relative;
  overflow-x: hidden;
}

/* ========== 顶部导航 ========== */
.editor-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 18px 20px;
  background: rgba(28, 28, 30, 0.9);
  backdrop-filter: blur(40px) saturate(150%);
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
  position: sticky;
  top: 0;
  z-index: 100;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 14px;
}

.back-btn {
  width: 40px;
  height: 40px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.04);
  color: #a1a1a6;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}

.back-btn:hover {
  border-color: rgba(255, 255, 255, 0.15);
  color: #f5f5f7;
  transform: translateX(-2px);
}

.header-title {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 20px;
  font-weight: 600;
  color: #f5f5f7;
  margin: 0;
  letter-spacing: -0.02em;
}

.title-icon {
  color: #a1a1a6;
}

.header-actions {
  display: flex;
  gap: 12px;
}

/* ========== 工具栏 ========== */
.toolbar {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 14px 20px;
  background: rgba(28, 28, 30, 0.7);
  backdrop-filter: blur(16px);
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
  flex-wrap: wrap;
}

.toolbar-group {
  display: flex;
  align-items: center;
  gap: 12px;
}

.toolbar-label {
  font-size: 12px;
  font-weight: 500;
  color: #636366;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.toolbar-divider {
  width: 1px;
  height: 28px;
  background: rgba(255, 255, 255, 0.06);
}

.floor-tabs {
  display: flex;
  gap: 8px;
}

.floor-tab {
  padding: 10px 18px;
  font-size: 14px;
  font-weight: 600;
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.04);
  color: #636366;
  cursor: pointer;
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}

.floor-tab:hover {
  border-color: rgba(255, 255, 255, 0.12);
  color: #a1a1a6;
}

.floor-tab.active {
  background: #f5f5f7;
  border-color: transparent;
  color: #000;
}

/* ========== 未保存提示 ========== */
.unsaved-alert {
  display: flex;
  align-items: center;
  gap: 14px;
  margin: 16px 20px 0;
  padding: 16px 20px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 14px;
  color: #a1a1a6;
  font-size: 14px;
  backdrop-filter: blur(10px);
}

.unsaved-alert svg {
  flex-shrink: 0;
  color: #a1a1a6;
}

.unsaved-alert span {
  flex: 1;
}

.unsaved-alert strong {
  color: #f5f5f7;
  font-weight: 600;
}

.alert-btn {
  padding: 8px 16px;
  font-size: 13px;
  font-weight: 600;
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.06);
  color: #f5f5f7;
  cursor: pointer;
  transition: all 0.25s;
}

.alert-btn:hover {
  background: rgba(255, 255, 255, 0.1);
  border-color: rgba(255, 255, 255, 0.15);
}

/* ========== 主内容区 ========== */
.main-content {
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 20px;
  position: relative;
  z-index: 1;
}

/* ========== 玻璃卡片 ========== */
.glass-card {
  background: rgba(28, 28, 30, 0.85);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 18px;
  backdrop-filter: blur(40px) saturate(150%);
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.3);
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}

.glass-card:hover {
  border-color: rgba(255, 255, 255, 0.08);
}

/* ========== 卡片头部 ========== */
.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 18px;
  flex-wrap: wrap;
  gap: 12px;
}

.card-title {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 16px;
  font-weight: 600;
  color: #f5f5f7;
  margin: 0;
}

.card-title svg {
  color: #a1a1a6;
}

.card-hint {
  font-size: 12px;
  color: #636366;
  padding: 6px 12px;
  background: rgba(255, 255, 255, 0.04);
  border-radius: 20px;
  border: 1px solid rgba(255, 255, 255, 0.06);
}

/* ========== 地图卡片 ========== */
.map-card {
  padding: 22px;
}

.map-container {
  height: 420px;
  border-radius: 14px;
  overflow: hidden;
  background: #0a0a0a;
  border: 1px solid rgba(255, 255, 255, 0.06);
  position: relative;
}

/* ========== 空状态 ========== */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  text-align: center;
  padding: 40px 20px;
  position: relative;
}

.empty-icon {
  margin-bottom: 20px;
  color: #3a3a3c;
}

.empty-title {
  font-size: 20px;
  font-weight: 600;
  color: #f5f5f7;
  margin: 0 0 10px;
}

.empty-desc {
  font-size: 14px;
  color: #636366;
  margin: 0 0 28px;
}

/* ========== 节点卡片 ========== */
.node-card {
  padding: 22px;
}

.node-badge {
  padding: 4px 12px;
  font-size: 12px;
  font-weight: 600;
  background: rgba(255, 255, 255, 0.06);
  color: #a1a1a6;
  border-radius: 20px;
  border: 1px solid rgba(255, 255, 255, 0.08);
}

.stats-group {
  display: flex;
  gap: 10px;
}

.stat-tag {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  font-size: 12px;
  font-weight: 600;
  border-radius: 20px;
  border: 1px solid;
}

.stat-tag.success {
  background: rgba(72, 72, 74, 0.3);
  color: #a1a1a6;
  border-color: rgba(161, 161, 166, 0.2);
}

.stat-tag.warning {
  background: rgba(255, 255, 255, 0.04);
  color: #636366;
  border-color: rgba(99, 99, 102, 0.2);
}

/* ========== 节点列表 ========== */
.node-list {
  max-height: 340px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding-right: 4px;
}

/* 自定义滚动条 */
.node-list::-webkit-scrollbar {
  width: 6px;
}

.node-list::-webkit-scrollbar-track {
  background: transparent;
}

.node-list::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.08);
  border-radius: 3px;
}

.node-list::-webkit-scrollbar-thumb:hover {
  background: rgba(255, 255, 255, 0.12);
}

.node-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 18px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid transparent;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}

.node-item:hover {
  background: rgba(255, 255, 255, 0.06);
  border-color: rgba(255, 255, 255, 0.08);
  transform: translateX(4px);
}

.node-item.selected {
  background: rgba(255, 255, 255, 0.08);
  border-color: rgba(255, 255, 255, 0.12);
}

.node-info {
  flex: 1;
  min-width: 0;
}

.node-name {
  font-size: 14px;
  font-weight: 600;
  color: #f5f5f7;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.node-detail {
  font-size: 12px;
  color: #636366;
  margin-top: 4px;
}

.node-action {
  flex-shrink: 0;
  margin-left: 14px;
}

.coord-badge {
  padding: 6px 12px;
  font-size: 12px;
  font-weight: 600;
  font-family: 'SF Mono', 'JetBrains Mono', Monaco, monospace;
  background: rgba(255, 255, 255, 0.04);
  color: #a1a1a6;
  border-radius: 8px;
  border: 1px solid rgba(255, 255, 255, 0.08);
}

.btn-mini {
  padding: 8px 14px;
  font-size: 12px;
  font-weight: 600;
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.06);
  color: #f5f5f7;
  cursor: pointer;
  transition: all 0.25s;
}

.btn-mini:hover {
  background: rgba(255, 255, 255, 0.1);
  border-color: rgba(255, 255, 255, 0.15);
}

.empty-list {
  padding: 50px 20px;
  text-align: center;
  color: #636366;
  font-size: 14px;
}

/* ========== 按钮样式 ========== */
.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 12px 20px;
  font-size: 14px;
  font-weight: 600;
  border: none;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}

.btn:active {
  transform: scale(0.97);
}

.btn-primary {
  background: #f5f5f7;
  color: #000;
}

.btn-primary:hover {
  background: #e5e5e7;
}

.btn-secondary {
  background: rgba(255, 255, 255, 0.04);
  color: #a1a1a6;
  border: 1px solid rgba(255, 255, 255, 0.08);
}

.btn-secondary:hover {
  background: rgba(255, 255, 255, 0.08);
  border-color: rgba(255, 255, 255, 0.12);
  color: #f5f5f7;
}

.btn-ghost {
  background: transparent;
  color: #636366;
  border: 1px solid transparent;
}

.btn-ghost:hover {
  background: rgba(255, 255, 255, 0.04);
  color: #a1a1a6;
}

/* ========== 动画类 ========== */
.slide-up {
  animation: slideUp 0.4s cubic-bezier(0.4, 0, 0.2, 1);
}

@keyframes slideUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* ========== 移动端适配 ========== */
@media (max-width: 768px) {
  .editor-header {
    padding: 12px 16px;
  }
  
  .header-title {
    font-size: 17px;
  }
  
  .toolbar {
    padding: 12px 16px;
    gap: 12px;
  }
  
  .toolbar-label {
    display: none;
  }
  
  .main-content {
    padding: 16px;
    gap: 16px;
  }
  
  .map-container {
    height: 320px;
  }
  
  .node-list {
    max-height: 300px;
  }
  
  .glass-card {
    border-radius: 14px;
  }
  
  .map-card,
  .node-card {
    padding: 18px;
  }
}
</style>
