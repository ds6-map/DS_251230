<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { showToast, showLoadingToast, closeToast } from 'vant'
import { useNavigationStore } from '@/stores/navigation'
import { recognizeLocation } from '@/api'
import type { PathNode } from '@/api'

const router = useRouter()
const store = useNavigationStore()

// 搜索相关
const searchKeyword = ref('')
const showSearchPopup = ref(false)

// 当前位置
const currentLocationName = computed(() => {
  if (store.currentLocation) {
    return `${store.currentLocation.name} (${store.currentLocation.floor}楼)`
  }
  return '点击设置起点'
})

// 搜索节点
const handleSearch = async () => {
  if (!searchKeyword.value.trim()) return
  await store.search(searchKeyword.value)
}

// 选择搜索结果作为目的地
const selectDestination = (node: PathNode) => {
  store.setDestination(node)
  showSearchPopup.value = false
  searchKeyword.value = ''
  store.searchResults = []
  
  // 如果已有起点，直接导航
  if (store.currentLocation) {
    startNavigation()
  }
}

// 选择搜索结果作为起点
const selectAsStart = (node: PathNode) => {
  store.setCurrentLocation(node)
  showSearchPopup.value = false
  searchKeyword.value = ''
  store.searchResults = []
}

// 开始导航
const startNavigation = async () => {
  if (!store.currentLocation) {
    showToast('请先设置起点')
    return
  }
  if (!store.destination) {
    showToast('请先设置目的地')
    return
  }
  
  showLoadingToast({ message: '规划路线中...', forbidClick: true })
  
  const success = await store.navigate()
  closeToast()
  
  if (success) {
    router.push('/navigation')
  } else {
    showToast(store.error || '路径规划失败')
  }
}

// 拍照定位
const fileInput = ref<HTMLInputElement | null>(null)

const takePhoto = () => {
  fileInput.value?.click()
}

const handleFileChange = async (event: Event) => {
  const target = event.target as HTMLInputElement
  const file = target.files?.[0]
  
  if (!file) return
  
  showLoadingToast({ message: '识别中...', forbidClick: true })
  
  try {
    const response = await recognizeLocation(file)
    closeToast()
    
    if (response.success && response.candidates.length > 0) {
      store.setLocationCandidates(response.candidates)
      router.push('/recognition')
    } else {
      showToast('未能识别位置，请重试')
    }
  } catch (e: any) {
    closeToast()
    showToast(e.message || '识别失败')
  }
  
  // 清空文件输入
  target.value = ''
}

// 显示选择起点的弹窗
const showStartPopup = ref(false)

const openStartSelection = () => {
  showStartPopup.value = true
  searchKeyword.value = ''
  store.searchResults = []
}
</script>

<template>
  <div class="home-page page-container">
    <!-- 顶部标题 -->
    <div class="header">
      <h1 class="title">校园导航</h1>
      <p class="subtitle">室内定位与路径规划</p>
    </div>
    
    <!-- 主操作区 -->
    <div class="main-actions">
      <!-- 我在哪 -->
      <div class="action-card location-card" @click="takePhoto">
        <van-icon name="location-o" size="48" color="#1989fa" />
        <div class="action-text">
          <h3>我在哪？</h3>
          <p>拍照识别当前位置</p>
        </div>
      </div>
      
      <!-- 隐藏的文件输入 -->
      <input
        ref="fileInput"
        type="file"
        accept="image/*"
        capture="environment"
        style="display: none"
        @change="handleFileChange"
      />
      
      <!-- 去哪里 -->
      <div class="action-card search-card" @click="showSearchPopup = true">
        <van-icon name="search" size="48" color="#07c160" />
        <div class="action-text">
          <h3>去哪里？</h3>
          <p>搜索目的地</p>
        </div>
      </div>
    </div>
    
    <!-- 当前状态 -->
    <div class="status-section">
      <div class="status-item" @click="openStartSelection">
        <van-icon name="aim" size="20" color="#1989fa" />
        <span class="status-label">起点:</span>
        <span class="status-value">{{ currentLocationName }}</span>
        <van-icon name="arrow" size="16" color="#969799" />
      </div>
      
      <div v-if="store.destination" class="status-item">
        <van-icon name="location" size="20" color="#ee0a24" />
        <span class="status-label">终点:</span>
        <span class="status-value">{{ store.destination.name }} ({{ store.destination.floor }}楼)</span>
      </div>
    </div>
    
    <!-- 开始导航按钮 -->
    <div class="nav-button-container" v-if="store.currentLocation && store.destination">
      <van-button type="primary" size="large" block @click="startNavigation">
        开始导航
      </van-button>
    </div>
    
    <!-- 搜索弹窗 -->
    <van-popup
      v-model:show="showSearchPopup"
      position="bottom"
      :style="{ height: '70%' }"
      round
    >
      <div class="search-popup">
        <div class="popup-header">
          <h3>搜索目的地</h3>
        </div>
        
        <van-search
          v-model="searchKeyword"
          placeholder="输入教室号、地点名称"
          @search="handleSearch"
          @update:model-value="handleSearch"
        />
        
        <div class="search-results">
          <van-cell-group v-if="store.searchResults.length > 0">
            <van-cell
              v-for="node in store.searchResults"
              :key="node.id"
              :title="node.name"
              :label="`${node.detail || ''} · ${node.floor}楼`"
              is-link
              @click="selectDestination(node)"
            />
          </van-cell-group>
          
          <van-empty v-else-if="searchKeyword && store.searchResults.length === 0" description="未找到匹配结果" />
          <van-empty v-else description="输入关键词搜索" />
        </div>
      </div>
    </van-popup>
    
    <!-- 选择起点弹窗 -->
    <van-popup
      v-model:show="showStartPopup"
      position="bottom"
      :style="{ height: '70%' }"
      round
    >
      <div class="search-popup">
        <div class="popup-header">
          <h3>选择起点</h3>
        </div>
        
        <van-search
          v-model="searchKeyword"
          placeholder="搜索起点位置"
          @search="handleSearch"
          @update:model-value="handleSearch"
        />
        
        <div class="search-results">
          <van-cell-group v-if="store.searchResults.length > 0">
            <van-cell
              v-for="node in store.searchResults"
              :key="node.id"
              :title="node.name"
              :label="`${node.detail || ''} · ${node.floor}楼`"
              is-link
              @click="selectAsStart(node)"
            />
          </van-cell-group>
          
          <van-empty v-else-if="searchKeyword && store.searchResults.length === 0" description="未找到匹配结果" />
          <van-empty v-else description="输入关键词搜索" />
        </div>
      </div>
    </van-popup>
  </div>
</template>

<style scoped>
.home-page {
  padding: 20px 16px;
  padding-bottom: 80px;
}

.header {
  text-align: center;
  margin-bottom: 32px;
}

.title {
  font-size: 28px;
  font-weight: 700;
  color: #323233;
  margin-bottom: 8px;
}

.subtitle {
  font-size: 14px;
  color: #969799;
}

.main-actions {
  display: flex;
  gap: 12px;
  margin-bottom: 24px;
}

.action-card {
  flex: 1;
  background: #fff;
  border-radius: 16px;
  padding: 24px 16px;
  text-align: center;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
  cursor: pointer;
  transition: transform 0.2s, box-shadow 0.2s;
}

.action-card:active {
  transform: scale(0.98);
}

.action-text {
  margin-top: 12px;
}

.action-text h3 {
  font-size: 16px;
  font-weight: 600;
  color: #323233;
  margin-bottom: 4px;
}

.action-text p {
  font-size: 12px;
  color: #969799;
}

.status-section {
  background: #fff;
  border-radius: 12px;
  padding: 16px;
  margin-bottom: 20px;
}

.status-item {
  display: flex;
  align-items: center;
  padding: 12px 0;
  border-bottom: 1px solid #ebedf0;
  cursor: pointer;
}

.status-item:last-child {
  border-bottom: none;
}

.status-label {
  font-size: 14px;
  color: #969799;
  margin-left: 8px;
  margin-right: 8px;
}

.status-value {
  flex: 1;
  font-size: 14px;
  color: #323233;
}

.nav-button-container {
  margin-top: 24px;
}

.search-popup {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.popup-header {
  padding: 16px;
  text-align: center;
  border-bottom: 1px solid #ebedf0;
}

.popup-header h3 {
  font-size: 16px;
  font-weight: 600;
  color: #323233;
}

.search-results {
  flex: 1;
  overflow-y: auto;
}
</style>

