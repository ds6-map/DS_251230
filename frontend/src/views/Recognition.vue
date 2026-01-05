<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { showToast } from 'vant'
import { useNavigationStore } from '@/stores/navigation'
import type { LocationCandidate } from '@/api'

const router = useRouter()
const store = useNavigationStore()

const candidates = computed(() => store.locationCandidates)

// 确认位置
const confirmLocation = (candidate: LocationCandidate) => {
  store.setCurrentLocation({
    id: candidate.node_id,
    name: candidate.node_name,
    detail: candidate.detail,
    floor: candidate.floor,
  })
  
  showToast({
    message: '位置已确认',
    icon: 'success',
  })
  
  router.push('/')
}

// 重新拍照
const retakePhoto = () => {
  router.back()
}

// 格式化置信度
const formatConfidence = (confidence: number) => {
  return `${Math.round(confidence * 100)}%`
}
</script>

<template>
  <div class="recognition-page">
    <!-- 顶部导航 -->
    <header class="nav-header">
      <button class="back-btn" @click="router.back()">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M19 12H5M12 19l-7-7 7-7"/>
        </svg>
      </button>
      <h1 class="header-title">确认位置</h1>
      <div class="header-spacer"></div>
    </header>
    
    <div class="content">
      <div class="hint-card slide-up">
        <div class="hint-icon">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="10"/>
            <line x1="12" y1="16" x2="12" y2="12"/>
            <line x1="12" y1="8" x2="12.01" y2="8"/>
          </svg>
        </div>
        <span>系统识别到以下可能的位置，请选择正确的一个</span>
      </div>
      
      <!-- 候选位置列表 -->
      <div class="candidates-list">
        <div
          v-for="(candidate, index) in candidates"
          :key="candidate.node_id"
          class="candidate-card slide-up"
          :style="{ animationDelay: `${index * 0.08}s` }"
          @click="confirmLocation(candidate)"
        >
          <div class="candidate-rank">{{ index + 1 }}</div>
          <div class="candidate-info">
            <h3 class="candidate-name">{{ candidate.node_name }}</h3>
            <p class="candidate-detail">
              {{ candidate.detail || '暂无详细位置' }} · {{ candidate.floor }}楼
            </p>
          </div>
          <div class="candidate-confidence">
            <div class="confidence-ring">
              <svg viewBox="0 0 36 36">
                <circle
                  cx="18" cy="18" r="16"
                  fill="none"
                  stroke="rgba(255, 255, 255, 0.06)"
                  stroke-width="3"
                />
                <circle
                  cx="18" cy="18" r="16"
                  fill="none"
                  stroke="#a1a1a6"
                  stroke-width="3"
                  stroke-linecap="round"
                  :stroke-dasharray="`${candidate.confidence * 100}, 100`"
                  transform="rotate(-90 18 18)"
                />
              </svg>
              <span class="confidence-value">{{ formatConfidence(candidate.confidence) }}</span>
            </div>
            <span class="confidence-label">置信度</span>
          </div>
        </div>
      </div>
      
      <!-- 没有结果 -->
      <div v-if="candidates.length === 0" class="empty-state">
        <div class="empty-icon">
          <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" opacity="0.3">
            <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"/>
            <circle cx="12" cy="13" r="4"/>
          </svg>
        </div>
        <h3 class="empty-title">未识别到位置</h3>
        <p class="empty-desc">请尝试拍摄更清晰的照片</p>
        <button class="btn btn-primary" @click="retakePhoto">重新拍照</button>
      </div>
      
      <!-- 操作按钮 -->
      <div class="actions" v-if="candidates.length > 0">
        <button class="btn btn-secondary" @click="retakePhoto">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"/>
            <circle cx="12" cy="13" r="4"/>
          </svg>
          都不对，重新拍照
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.recognition-page {
  min-height: 100vh;
  background: #000000;
}

/* ========== 顶部导航 ========== */
.nav-header {
  display: flex;
  align-items: center;
  padding: 18px 20px;
  background: rgba(28, 28, 30, 0.9);
  backdrop-filter: blur(40px) saturate(150%);
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
  position: sticky;
  top: 0;
  z-index: 100;
}

.back-btn {
  width: 40px;
  height: 40px;
  border: none;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.06);
  color: #f5f5f7;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.25s;
}

.back-btn:hover {
  background: rgba(255, 255, 255, 0.1);
  transform: translateX(-2px);
}

.header-title {
  flex: 1;
  text-align: center;
  font-size: 18px;
  font-weight: 600;
  color: #f5f5f7;
  margin: 0;
  letter-spacing: -0.02em;
}

.header-spacer {
  width: 40px;
}

.content {
  padding: 20px;
}

/* ========== 提示卡片 ========== */
.hint-card {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 16px 18px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 14px;
  margin-bottom: 20px;
  color: #a1a1a6;
  font-size: 14px;
}

.hint-icon {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.06);
  border-radius: 10px;
  flex-shrink: 0;
  color: #a1a1a6;
}

/* ========== 候选列表 ========== */
.candidates-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.candidate-card {
  display: flex;
  align-items: center;
  background: rgba(28, 28, 30, 0.7);
  backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.04);
  border-radius: 18px;
  padding: 20px;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.candidate-card:hover {
  background: rgba(28, 28, 30, 0.9);
  border-color: rgba(255, 255, 255, 0.1);
  transform: translateX(6px);
}

.candidate-card:active {
  transform: scale(0.98) translateX(6px);
}

.candidate-rank {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.08);
  color: #f5f5f7;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 15px;
  margin-right: 16px;
  flex-shrink: 0;
}

.candidate-info {
  flex: 1;
  min-width: 0;
}

.candidate-name {
  font-size: 17px;
  font-weight: 600;
  color: #f5f5f7;
  margin: 0 0 6px;
}

.candidate-detail {
  font-size: 14px;
  color: #636366;
  margin: 0;
}

.candidate-confidence {
  display: flex;
  flex-direction: column;
  align-items: center;
  margin-left: 16px;
}

.confidence-ring {
  position: relative;
  width: 48px;
  height: 48px;
}

.confidence-ring svg {
  width: 100%;
  height: 100%;
}

.confidence-value {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  font-size: 12px;
  font-weight: 700;
  color: #a1a1a6;
}

.confidence-label {
  font-size: 10px;
  color: #636366;
  margin-top: 4px;
}

/* ========== 空状态 ========== */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 80px 20px;
  text-align: center;
}

.empty-icon {
  margin-bottom: 20px;
  color: #3a3a3c;
}

.empty-title {
  font-size: 22px;
  font-weight: 600;
  color: #f5f5f7;
  margin: 0 0 10px;
}

.empty-desc {
  font-size: 15px;
  color: #636366;
  margin: 0 0 28px;
}

/* ========== 操作按钮 ========== */
.actions {
  margin-top: 28px;
}

.btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  width: 100%;
  padding: 16px 24px;
  font-size: 16px;
  font-weight: 600;
  border: none;
  border-radius: 14px;
  cursor: pointer;
  transition: all 0.25s;
}

.btn-primary {
  background: #f5f5f7;
  color: #000;
}

.btn-primary:hover {
  background: #e5e5e7;
  transform: translateY(-2px);
}

.btn-secondary {
  background: rgba(28, 28, 30, 0.8);
  border: 1px solid rgba(255, 255, 255, 0.08);
  color: #f5f5f7;
}

.btn-secondary:hover {
  background: rgba(38, 38, 40, 0.9);
  border-color: rgba(255, 255, 255, 0.12);
}

/* ========== 动画 ========== */
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
</style>
