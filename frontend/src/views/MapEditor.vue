<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { showToast, showLoadingToast, closeToast, showConfirmDialog } from 'vant'
import { useEditorStore } from '@/stores/editor'
import MapCanvas from '@/components/MapCanvas.vue'

const store = useEditorStore()

// 文件上传
const fileInput = ref<HTMLInputElement | null>(null)

// 当前选中的节点
const selectedNodeId = ref<string | null>(null)

// 计算属性
const currentMap = computed(() => store.currentMap)
const currentFloorNodes = computed(() => store.currentFloorNodes)
const hasUnsavedChanges = computed(() => store.hasUnsavedChanges)

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
  <div class="editor-page page-container">
    <van-nav-bar title="地图编辑器">
      <template #right>
        <van-button
          v-if="hasUnsavedChanges"
          type="primary"
          size="small"
          @click="saveAllChanges"
        >
          保存
        </van-button>
      </template>
    </van-nav-bar>
    
    <div class="content">
      <!-- 工具栏 -->
      <div class="toolbar">
        <!-- 楼层选择 -->
        <div class="floor-selector">
          <span class="label">楼层:</span>
          <van-button
            v-for="floor in store.floors"
            :key="floor"
            :type="store.currentFloor === floor ? 'primary' : 'default'"
            size="small"
            @click="handleFloorChange(floor)"
          >
            {{ floor }}楼
          </van-button>
        </div>
        
        <!-- 上传底图 -->
        <van-button size="small" icon="photograph" @click="triggerUpload">
          上传底图
        </van-button>
        <input
          ref="fileInput"
          type="file"
          accept="image/png,image/jpeg"
          style="display: none"
          @change="handleFileChange"
        />
      </div>
      
      <!-- 未保存提示 -->
      <div v-if="hasUnsavedChanges" class="unsaved-hint">
        <van-icon name="warning-o" />
        <span>有未保存的更改</span>
        <van-button type="default" size="mini" @click="discardChanges">放弃</van-button>
        <van-button type="primary" size="mini" @click="saveAllChanges">保存</van-button>
      </div>
      
      <!-- 地图画布 -->
      <div class="map-container">
        <MapCanvas
          v-if="currentMap"
          :map-info="currentMap"
          :nodes="currentFloorNodes"
          :editable="true"
          :selected-node-id="selectedNodeId"
          @node-drag-end="handleNodeDragEnd"
          @node-click="(id) => selectedNodeId = id"
        />
        
        <van-empty v-else description="请先上传该楼层的底图">
          <van-button type="primary" @click="triggerUpload">上传底图</van-button>
        </van-empty>
      </div>
      
      <!-- 节点列表 -->
      <div class="node-list">
        <div class="list-header">
          <span>节点列表 ({{ currentFloorNodes.length }})</span>
        </div>
        
        <van-cell-group>
          <van-cell
            v-for="node in currentFloorNodes"
            :key="node.id"
            :title="node.name"
            :label="node.detail || node.id"
            :class="{ 'node-cell': true, 'selected': selectedNodeId === node.id }"
            @click="selectedNodeId = node.id"
          >
            <template #value>
              <span :class="{ 'coord-set': node.has_coordinates, 'coord-unset': !node.has_coordinates }">
                {{ node.has_coordinates ? `(${formatCoord(node.x)}, ${formatCoord(node.y)})` : '未设置' }}
              </span>
            </template>
          </van-cell>
        </van-cell-group>
        
        <van-empty v-if="currentFloorNodes.length === 0" description="该楼层暂无节点" />
      </div>
    </div>
  </div>
</template>

<style scoped>
.editor-page {
  background: #f7f8fa;
  padding-bottom: 80px;
}

.content {
  padding: 16px;
}

.toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  background: #fff;
  border-radius: 12px;
  padding: 12px 16px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}

.floor-selector {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.floor-selector .label {
  font-size: 14px;
  color: #969799;
}

.unsaved-hint {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  background: #fffbe8;
  border-radius: 8px;
  margin-bottom: 16px;
  font-size: 13px;
  color: #ed6a0c;
}

.unsaved-hint span {
  flex: 1;
}

.map-container {
  background: #fff;
  border-radius: 12px;
  padding: 16px;
  margin-bottom: 16px;
  min-height: 300px;
}

.node-list {
  background: #fff;
  border-radius: 12px;
  overflow: hidden;
}

.list-header {
  padding: 12px 16px;
  font-size: 14px;
  font-weight: 600;
  color: #323233;
  border-bottom: 1px solid #ebedf0;
}

.node-cell.selected {
  background: #e6f7ff;
}

.coord-set {
  color: #07c160;
  font-size: 12px;
}

.coord-unset {
  color: #ee0a24;
  font-size: 12px;
}
</style>

