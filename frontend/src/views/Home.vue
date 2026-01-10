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
  background: var(--bg);
  overflow: hidden;
  position: relative;
}

/* 背景光效 */
.home-page::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 300px;
  background: radial-gradient(ellipse at 50% -20%, rgba(0, 229, 255, 0.08) 0%, transparent 70%);
  pointer-events: none;
  z-index: 0;
}

/* ========== 顶部工具栏 - iOS 26 玻璃态 ========== */
.nav-toolbar {
  flex-shrink: 0;
  padding: 12px 16px;
  padding-top: max(12px, env(safe-area-inset-top));
  background: linear-gradient(180deg,
    rgba(15, 25, 50, 0.85) 0%,
    rgba(10, 20, 40, 0.75) 100%
  );
  backdrop-filter: blur(40px) saturate(180%);
  -webkit-backdrop-filter: blur(40px) saturate(180%);
  border-bottom: 1px solid rgba(0, 229, 255, 0.12);
  position: relative;
  z-index: 10;
}

/* 工具栏顶部高光 */
.nav-toolbar::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 1px;
  background: linear-gradient(90deg,
    transparent 0%,
    rgba(255, 255, 255, 0.06) 20%,
    rgba(0, 229, 255, 0.2) 50%,
    rgba(255, 255, 255, 0.06) 80%,
    transparent 100%
  );
}

.toolbar-brand {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
  justify-content: space-between;
}

.brand-icon {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, rgba(0, 229, 255, 0.15) 0%, rgba(0, 255, 200, 0.1) 100%);
  border: 1px solid rgba(0, 229, 255, 0.2);
  border-radius: 10px;
  color: var(--primary);
  flex-shrink: 0;
  box-shadow: 0 0 15px rgba(0, 229, 255, 0.15);
}

.brand-title {
  font-size: 18px;
  font-weight: 700;
  background: linear-gradient(135deg, #ffffff 0%, #00e5ff 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  margin: 0;
  letter-spacing: -0.03em;
  flex: 1;
}

.photo-btn {
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid rgba(0, 229, 255, 0.15);
  border-radius: 12px;
  background: linear-gradient(135deg, rgba(15, 30, 55, 0.6) 0%, rgba(10, 25, 45, 0.5) 100%);
  backdrop-filter: blur(10px);
  color: var(--text);
  cursor: pointer;
  transition: all 280ms cubic-bezier(0.25, 0.46, 0.45, 0.94);
  flex-shrink: 0;
  padding: 0;
  position: relative;
  overflow: hidden;
}

.photo-btn::before {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(135deg, rgba(0, 229, 255, 0.2) 0%, rgba(0, 255, 200, 0.1) 100%);
  opacity: 0;
  transition: opacity 280ms ease;
}

.photo-btn:hover {
  border-color: rgba(0, 229, 255, 0.35);
  box-shadow: 0 0 20px rgba(0, 229, 255, 0.2);
  transform: translateY(-1px);
}

.photo-btn:hover::before {
  opacity: 1;
}

.photo-btn:active {
  transform: scale(0.95);
}

/* ========== 路线选择器 - 高级玻璃卡片 ========== */
.route-selector {
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
}

.location-input {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 14px;
  background: linear-gradient(135deg, rgba(15, 30, 55, 0.5) 0%, rgba(10, 25, 45, 0.4) 100%);
  backdrop-filter: blur(16px);
  border: 1px solid rgba(0, 229, 255, 0.1);
  border-radius: 14px;
  cursor: pointer;
  transition: all 280ms cubic-bezier(0.25, 0.46, 0.45, 0.94);
  min-width: 0;
  position: relative;
  overflow: hidden;
}

.location-input::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.06), transparent);
}

.location-input:hover {
  background: linear-gradient(135deg, rgba(20, 40, 70, 0.6) 0%, rgba(15, 35, 60, 0.5) 100%);
  border-color: rgba(0, 229, 255, 0.25);
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3), 0 0 15px rgba(0, 229, 255, 0.1);
  transform: translateY(-1px);
}

.location-input:active {
  transform: scale(0.99);
}

.input-indicator {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  flex-shrink: 0;
  position: relative;
}

.input-indicator::after {
  content: '';
  position: absolute;
  inset: -3px;
  border-radius: 50%;
  opacity: 0.3;
}

.input-indicator.start {
  background: linear-gradient(135deg, #7a8ba8 0%, #5a6b88 100%);
  box-shadow: 0 0 10px rgba(122, 139, 168, 0.4);
}

.input-indicator.start::after {
  background: #7a8ba8;
  animation: pulse-soft 2s ease-in-out infinite;
}

.input-indicator.end {
  background: linear-gradient(135deg, #00e5ff 0%, #00ffc8 100%);
  box-shadow: 0 0 12px rgba(0, 229, 255, 0.5);
}

.input-indicator.end::after {
  background: #00e5ff;
  animation: pulse-glow 2s ease-in-out infinite;
}

@keyframes pulse-soft {
  0%, 100% { transform: scale(1); opacity: 0.3; }
  50% { transform: scale(1.5); opacity: 0; }
}

@keyframes pulse-glow {
  0%, 100% { transform: scale(1); opacity: 0.4; }
  50% { transform: scale(1.8); opacity: 0; }
}

.input-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  gap: 2px;
}

.input-label {
  font-size: 10px;
  color: var(--text-muted);
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.8px;
  line-height: 1;
}

.input-value {
  font-size: 14px;
  font-weight: 500;
  color: var(--text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.input-arrow {
  color: var(--text-muted);
  flex-shrink: 0;
  transition: all 280ms ease;
}

.location-input:hover .input-arrow {
  transform: translateX(4px);
  color: var(--primary);
}

.route-arrow {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  background: linear-gradient(135deg, rgba(0, 229, 255, 0.1) 0%, rgba(0, 255, 200, 0.05) 100%);
  border-radius: 8px;
  color: var(--primary);
  flex-shrink: 0;
}

/* ========== 操作按钮 - 渐变玻璃效果 ========== */
.toolbar-actions {
  display: flex;
  gap: 10px;
  margin-top: 0;
}

.action-btn {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 12px 16px;
  font-size: 14px;
  font-weight: 600;
  border: 1px solid rgba(0, 229, 255, 0.15);
  border-radius: 14px;
  background: linear-gradient(135deg, rgba(15, 30, 55, 0.5) 0%, rgba(10, 25, 45, 0.4) 100%);
  backdrop-filter: blur(16px);
  color: var(--text);
  cursor: pointer;
  transition: all 280ms cubic-bezier(0.25, 0.46, 0.45, 0.94);
  position: relative;
  overflow: hidden;
}

.action-btn::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.08), transparent);
}

.action-btn:hover {
  background: linear-gradient(135deg, rgba(20, 40, 70, 0.6) 0%, rgba(15, 35, 60, 0.5) 100%);
  border-color: rgba(0, 229, 255, 0.3);
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
}

.action-btn:active {
  transform: scale(0.97);
}

.action-btn.primary {
  background: linear-gradient(135deg, #00e5ff 0%, #00ffc8 100%);
  border: none;
  color: #050810;
  font-weight: 700;
  box-shadow: 0 4px 20px rgba(0, 229, 255, 0.35),
              inset 0 1px 0 rgba(255, 255, 255, 0.2);
}

.action-btn.primary::before {
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.3), transparent);
  left: -100%;
  width: 100%;
  height: 100%;
  transition: left 400ms ease;
}

.action-btn.primary:hover {
  box-shadow: 0 6px 28px rgba(0, 229, 255, 0.45),
              inset 0 1px 0 rgba(255, 255, 255, 0.25);
  transform: translateY(-2px);
}

.action-btn.primary:hover::before {
  left: 100%;
}

/* ========== 聊天主区域 ========== */
.chat-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
  padding: 12px 16px;
  overflow: hidden;
  position: relative;
  z-index: 1;
}

/* ========== 搜索弹窗 - iOS 26 风格 ========== */
.search-popup {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: linear-gradient(180deg, rgba(15, 25, 50, 0.98) 0%, rgba(10, 20, 40, 1) 100%);
}

.popup-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 24px 20px 20px;
  background: linear-gradient(180deg, rgba(20, 35, 60, 0.9) 0%, rgba(15, 30, 50, 0.8) 100%);
  backdrop-filter: blur(40px);
  border-bottom: 1px solid rgba(0, 229, 255, 0.1);
  position: relative;
}

.popup-header::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(0, 229, 255, 0.25), transparent);
}

.popup-title {
  font-size: 20px;
  font-weight: 700;
  background: linear-gradient(135deg, #ffffff 0%, #00e5ff 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  margin: 0;
  letter-spacing: -0.02em;
}

.popup-close {
  width: 38px;
  height: 38px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.04);
  backdrop-filter: blur(10px);
  color: var(--text-muted);
  cursor: pointer;
  transition: all 280ms ease;
}

.popup-close:hover {
  background: rgba(255, 255, 255, 0.08);
  border-color: rgba(255, 255, 255, 0.15);
  color: var(--text);
  transform: rotate(90deg);
}

.search-input-wrap {
  display: flex;
  align-items: center;
  gap: 14px;
  margin: 20px 20px;
  padding: 16px 20px;
  background: linear-gradient(135deg, rgba(15, 30, 55, 0.6) 0%, rgba(10, 25, 45, 0.5) 100%);
  backdrop-filter: blur(16px);
  border: 1px solid rgba(0, 229, 255, 0.1);
  border-radius: 16px;
  transition: all 280ms ease;
  position: relative;
}

.search-input-wrap::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.06), transparent);
  border-radius: 16px 16px 0 0;
}

.search-input-wrap:focus-within {
  border-color: rgba(0, 229, 255, 0.3);
  box-shadow: 0 0 0 4px rgba(0, 229, 255, 0.08), 0 0 20px rgba(0, 229, 255, 0.1);
}

.search-icon {
  color: var(--text-muted);
  flex-shrink: 0;
  transition: color 280ms ease;
}

.search-input-wrap:focus-within .search-icon {
  color: var(--primary);
}

.search-input {
  flex: 1;
  border: none;
  background: none;
  font-size: 16px;
  font-weight: 500;
  color: var(--text);
  outline: none;
}

.search-input::placeholder {
  color: var(--text-light);
}

.search-clear {
  width: 30px;
  height: 30px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: none;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.06);
  color: var(--text-muted);
  cursor: pointer;
  transition: all 280ms ease;
}

.search-clear:hover {
  background: rgba(0, 229, 255, 0.15);
  color: var(--primary);
}

.search-results {
  flex: 1;
  overflow-y: auto;
  padding: 0 20px 20px;
}

.results-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.result-item {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 18px 20px;
  background: linear-gradient(135deg, rgba(15, 30, 55, 0.5) 0%, rgba(10, 25, 45, 0.4) 100%);
  backdrop-filter: blur(16px);
  border: 1px solid rgba(0, 229, 255, 0.08);
  border-radius: 18px;
  cursor: pointer;
  transition: all 280ms cubic-bezier(0.25, 0.46, 0.45, 0.94);
  position: relative;
  overflow: hidden;
}

.result-item::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 3px;
  background: linear-gradient(180deg, #00e5ff 0%, #00ffc8 100%);
  opacity: 0;
  transition: opacity 280ms ease;
}

.result-item:hover {
  background: linear-gradient(135deg, rgba(20, 40, 70, 0.6) 0%, rgba(15, 35, 60, 0.5) 100%);
  border-color: rgba(0, 229, 255, 0.2);
  transform: translateX(6px);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.35);
}

.result-item:hover::before {
  opacity: 1;
}

.result-icon {
  width: 48px;
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, rgba(0, 229, 255, 0.12) 0%, rgba(0, 255, 200, 0.08) 100%);
  border: 1px solid rgba(0, 229, 255, 0.15);
  border-radius: 14px;
  color: var(--primary);
  flex-shrink: 0;
  transition: all 280ms ease;
}

.result-item:hover .result-icon {
  box-shadow: 0 0 20px rgba(0, 229, 255, 0.25);
}

.result-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  gap: 4px;
}

.result-name {
  font-size: 16px;
  font-weight: 600;
  color: var(--text);
}

.result-detail {
  font-size: 13px;
  color: var(--text-muted);
}

.result-arrow {
  color: var(--text-light);
  flex-shrink: 0;
  transition: all 280ms ease;
}

.result-item:hover .result-arrow {
  transform: translateX(4px);
  color: var(--primary);
}

.empty-results {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 80px 20px;
  text-align: center;
  color: var(--text-muted);
}

.empty-icon {
  margin-bottom: 20px;
  width: 72px;
  height: 72px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, rgba(15, 30, 55, 0.5) 0%, rgba(10, 25, 45, 0.4) 100%);
  border: 1px solid rgba(255, 255, 255, 0.05);
  border-radius: 20px;
  color: var(--text-light);
}

/* ========== 移动端适配 ========== */
@media (max-width: 768px) {
  .nav-toolbar {
    padding: 16px;
    padding-top: max(16px, env(safe-area-inset-top));
  }

  .brand-title {
    font-size: 20px;
  }

  .chat-main {
    padding: 12px;
  }

  .location-input {
    padding: 10px 12px;
  }

  .action-btn {
    padding: 11px 14px;
  }
}
</style>
