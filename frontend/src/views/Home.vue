<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { showToast, showLoadingToast, closeToast } from 'vant'
import { useNavigationStore } from '@/stores/navigation'
import { recognizeLocation } from '@/api'
import type { PathNode } from '@/api'
import AgentChat from '@/components/AgentChat.vue'

const router = useRouter()
const store = useNavigationStore()

// 搜索相关
const searchKeyword = ref('')
const showSearchPopup = ref(false)
const searchMode = ref<'start' | 'destination'>('destination')

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
  // 不再自动跳转，让用户手动点击"开始导航"按钮
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
    console.log('📤 [识别请求] 开始上传图片识别', {
      fileName: file.name,
      fileSize: file.size,
      fileType: file.type
    })
    
    const response = await recognizeLocation(file)
    closeToast()
    
    console.log('✅ [识别响应] 收到识别结果', {
      success: response.success,
      method: response.method,
      candidates_count: response.candidates.length,
      message: response.message,
      debug_info: response.debug_info,
      candidates: response.candidates.map((c, i) => 
        `[${i+1}] ${c.node_name} (楼层: ${c.floor}, 置信度: ${c.confidence})`
      )
    })
    
    if (response.success && response.candidates.length > 0) {
      store.setLocationCandidates(response.candidates)
      router.push('/recognition')
    } else {
      const errorMsg = response.message || '未能识别位置，请重试'
      console.warn('⚠️ [识别结果]', errorMsg, response.debug_info)
      showToast(errorMsg)
    }
  } catch (e: any) {
    closeToast()
    console.error('❌ [识别错误]', {
      error: e,
      message: e.message,
      stack: e.stack
    })
    showToast(e.message || '识别失败')
  }
  
  target.value = ''
}

// 显示选择起点的弹窗
const openStartSelection = () => {
  searchMode.value = 'start'
  showSearchPopup.value = true
  searchKeyword.value = ''
  store.searchResults = []
}

// 显示选择终点的弹窗
const openDestinationSelection = () => {
  searchMode.value = 'destination'
  showSearchPopup.value = true
  searchKeyword.value = ''
  store.searchResults = []
}
</script>

<template>
  <div class="home-page">
    <!-- 顶部工具栏 -->
    <header class="nav-toolbar">
      <div class="toolbar-brand">
        <div class="brand-icon">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/>
            <circle cx="12" cy="10" r="3"/>
          </svg>
        </div>
        <h1 class="brand-title">室内导航</h1>
        <button class="photo-btn" @click="takePhoto" title="拍照定位">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"/>
            <circle cx="12" cy="13" r="4"/>
          </svg>
        </button>
      </div>
      
      <div class="route-selector">
        <!-- 起点 -->
        <div class="location-input" @click="openStartSelection">
          <div class="input-indicator start"></div>
          <div class="input-content">
            <span class="input-label">起点</span>
            <span class="input-value">{{ currentLocationName }}</span>
          </div>
          <svg class="input-arrow" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M9 18l6-6-6-6"/>
          </svg>
        </div>
        
        <!-- 连接箭头 -->
        <div class="route-arrow">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M5 12h14M12 5l7 7-7 7"/>
          </svg>
        </div>
        
        <!-- 终点 -->
        <div class="location-input" @click="openDestinationSelection">
          <div class="input-indicator end"></div>
          <div class="input-content">
            <span class="input-label">终点</span>
            <span class="input-value">
              {{ store.destination ? `${store.destination.name} (${store.destination.floor}楼)` : '点击设置终点' }}
            </span>
          </div>
          <svg class="input-arrow" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M9 18l6-6-6-6"/>
          </svg>
        </div>
      </div>
      
      <!-- 操作按钮 -->
      <div class="toolbar-actions">
        <button
          class="action-btn primary"
          @click="startNavigation"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polygon points="3 11 22 2 13 21 11 13 3 11"/>
          </svg>
          开始导航
        </button>
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
    </header>
    
    <!-- Agent对话界面 -->
    <main class="chat-main">
      <AgentChat />
    </main>
    
    <!-- 搜索弹窗 -->
    <van-popup
      v-model:show="showSearchPopup"
      position="bottom"
      :style="{ height: '75%' }"
      round
    >
      <div class="search-popup">
        <div class="popup-header">
          <h3 class="popup-title">{{ searchMode === 'start' ? '选择起点' : '搜索目的地' }}</h3>
          <button class="popup-close" @click="showSearchPopup = false">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="18" y1="6" x2="6" y2="18"/>
              <line x1="6" y1="6" x2="18" y2="18"/>
            </svg>
          </button>
        </div>
        
        <div class="search-input-wrap">
          <svg class="search-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="11" cy="11" r="8"/>
            <line x1="21" y1="21" x2="16.65" y2="16.65"/>
          </svg>
          <input
            v-model="searchKeyword"
            type="text"
            class="search-input"
            :placeholder="searchMode === 'start' ? '搜索起点位置' : '输入教室号、地点名称'"
            @input="handleSearch"
          />
          <button v-if="searchKeyword" class="search-clear" @click="searchKeyword = ''">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="10"/>
              <line x1="15" y1="9" x2="9" y2="15"/>
              <line x1="9" y1="9" x2="15" y2="15"/>
            </svg>
          </button>
        </div>
        
        <div class="search-results">
          <div v-if="store.searchResults.length > 0" class="results-list">
            <div
              v-for="node in store.searchResults"
              :key="node.id"
              class="result-item"
              @click="searchMode === 'start' ? selectAsStart(node) : selectDestination(node)"
            >
              <div class="result-icon">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/>
                  <circle cx="12" cy="10" r="3"/>
                </svg>
              </div>
              <div class="result-info">
                <span class="result-name">{{ node.name }}</span>
                <span class="result-detail">{{ node.detail || '' }} · {{ node.floor }}楼</span>
              </div>
              <svg class="result-arrow" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M9 18l6-6-6-6"/>
              </svg>
            </div>
          </div>
          
          <div v-else-if="searchKeyword" class="empty-results">
            <div class="empty-icon">
              <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" opacity="0.4">
                <circle cx="11" cy="11" r="8"/>
                <line x1="21" y1="21" x2="16.65" y2="16.65"/>
              </svg>
            </div>
            <span>未找到匹配结果</span>
          </div>
          
          <div v-else class="empty-results">
            <div class="empty-icon">
              <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" opacity="0.4">
                <circle cx="12" cy="12" r="10"/>
                <line x1="12" y1="16" x2="12" y2="12"/>
                <line x1="12" y1="8" x2="12.01" y2="8"/>
              </svg>
            </div>
            <span>输入关键词开始搜索</span>
          </div>
        </div>
      </div>
    </van-popup>
  </div>
</template>

<style scoped>
.home-page {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: #000000;
  overflow: hidden;
}

/* ========== 顶部工具栏 ========== */
.nav-toolbar {
  flex-shrink: 0;
  padding: 10px 16px;
  background: rgba(30, 35, 50, 0.9);
  backdrop-filter: blur(40px) saturate(150%);
  -webkit-backdrop-filter: blur(40px) saturate(150%);
  border-bottom: 1px solid rgba(0, 229, 255, 0.2);
}

.toolbar-brand {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
  justify-content: space-between;
}

.brand-icon {
  width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #ffffff;
  opacity: 0.9;
  flex-shrink: 0;
}

.brand-title {
  font-size: 17px;
  font-weight: 600;
  color: #ffffff;
  margin: 0;
  letter-spacing: -0.03em;
  flex: 1;
}

.photo-btn {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: none;
  border-radius: 8px;
  background: rgba(30, 35, 50, 0.4);
  color: #ffffff;
  cursor: pointer;
  transition: all 0.2s;
  flex-shrink: 0;
  padding: 0;
}

.photo-btn:hover {
  background: rgba(0, 229, 255, 0.3);
  transform: scale(1.05);
}

.photo-btn:active {
  transform: scale(0.95);
}

/* ========== 路线选择器 ========== */
.route-selector {
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
}

.location-input {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  background: rgba(30, 35, 50, 0.3);
  border: 1px solid rgba(0, 229, 255, 0.2);
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  min-width: 0;
}

.location-input:hover {
  background: rgba(21, 81, 80, 0.5);
  border-color: rgba(0, 229, 255, 0.4);
}

.location-input:active {
  transform: scale(0.99);
}

.input-indicator {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.input-indicator.start {
  background: #8b95a8;
  box-shadow: 0 0 8px rgba(0, 229, 255, 0.3);
}

.input-indicator.end {
  background: #00e5ff;
  box-shadow: 0 0 8px rgba(0, 229, 255, 0.4);
}

.input-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.input-label {
  font-size: 10px;
  color: #8b95a8;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  line-height: 1;
}

.input-value {
  font-size: 13px;
  font-weight: 500;
  color: #ffffff;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  margin-top: 2px;
}

.input-arrow {
  color: #8b95a8;
  flex-shrink: 0;
  transition: transform 0.2s;
}

.location-input:hover .input-arrow {
  transform: translateX(3px);
  color: #00e5ff;
}

.route-arrow {
  display: flex;
  align-items: center;
  justify-content: center;
  color: #8b95a8;
  flex-shrink: 0;
  padding: 0 4px;
}

/* ========== 操作按钮 ========== */
.toolbar-actions {
  display: flex;
  gap: 8px;
  margin-top: 0;
}

.action-btn {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 10px 14px;
  font-size: 13px;
  font-weight: 500;
  border: 1px solid rgba(0, 229, 255, 0.2);
  border-radius: 10px;
  background: rgba(30, 35, 50, 0.3);
  color: #ffffff;
  cursor: pointer;
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}

.action-btn:hover {
  background: rgba(21, 81, 80, 0.5);
  border-color: rgba(0, 229, 255, 0.4);
}

.action-btn:active {
  transform: scale(0.97);
}

.action-btn.primary {
  background: #00e5ff;
  border: none;
  color: #000;
  font-weight: 600;
  box-shadow: 0 0 12px rgba(0, 229, 255, 0.3);
}

.action-btn.primary:hover {
  background: #00d4ff;
  color: #000;
  box-shadow: 0 0 16px rgba(0, 229, 255, 0.5);
}

/* ========== 聊天主区域 ========== */
.chat-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
  padding: 12px;
  overflow: hidden;
}

/* ========== 搜索弹窗 ========== */
.search-popup {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: #151b2e;
}

.popup-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 22px 20px 18px;
  background: rgba(30, 35, 50, 0.98);
  border-bottom: 1px solid rgba(0, 229, 255, 0.2);
}

.popup-title {
  font-size: 18px;
  font-weight: 600;
  color: #ffffff;
  margin: 0;
  letter-spacing: -0.02em;
}

.popup-close {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: none;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.06);
  color: #8b95a8;
  cursor: pointer;
  transition: all 0.2s;
}

.popup-close:hover {
  background: rgba(255, 255, 255, 0.1);
  color: #ffffff;
}

.search-input-wrap {
  display: flex;
  align-items: center;
  gap: 12px;
  margin: 18px 20px;
  padding: 16px 18px;
  background: rgba(30, 35, 50, 0.6);
  border: 1px solid rgba(0, 229, 255, 0.2);
  border-radius: 14px;
  transition: all 0.2s;
}

.search-input-wrap:focus-within {
  border-color: rgba(39, 165, 162, 0.5);
  box-shadow: 0 0 0 4px rgba(39, 165, 162, 0.1);
}

.search-icon {
  color: #8b95a8;
  flex-shrink: 0;
}

.search-input {
  flex: 1;
  border: none;
  background: none;
  font-size: 16px;
  color: #ffffff;
  outline: none;
}

.search-input::placeholder {
  color: #8b95a8;
}

.search-clear {
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: none;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.08);
  color: #8b95a8;
  cursor: pointer;
  transition: all 0.2s;
}

.search-clear:hover {
  background: rgba(21, 81, 80, 0.6);
}

.search-results {
  flex: 1;
  overflow-y: auto;
  padding: 0 20px 20px;
}

.results-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.result-item {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 16px 18px;
  background: rgba(30, 35, 50, 0.4);
  border: 1px solid rgba(0, 229, 255, 0.15);
  border-radius: 14px;
  cursor: pointer;
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}

.result-item:hover {
  background: rgba(30, 35, 50, 0.5);
  border-color: rgba(0, 229, 255, 0.4);
  transform: translateX(4px);
}

.result-icon {
  width: 44px;
  height: 44px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.06);
  border-radius: 12px;
  color: #00e5ff;
  flex-shrink: 0;
}

.result-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.result-name {
  font-size: 16px;
  font-weight: 500;
  color: #ffffff;
}

.result-detail {
  font-size: 13px;
  color: #8b95a8;
  margin-top: 2px;
}

.result-arrow {
  color: #8b95a8;
  flex-shrink: 0;
  transition: transform 0.2s;
}

.result-item:hover .result-arrow {
  transform: translateX(3px);
  color: #00e5ff;
}

.empty-results {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 80px 20px;
  text-align: center;
  color: #8b95a8;
}

.empty-icon {
  margin-bottom: 16px;
  color: #3a3a3c;
}

/* ========== 移动端适配 ========== */
@media (max-width: 768px) {
  .nav-toolbar {
    padding: 16px;
  }
  
  .brand-title {
    font-size: 20px;
  }
  
  .chat-main {
    padding: 12px;
  }
}
</style>
