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
  background: var(--bg);
  position: relative;
}

/* 背景光效 */
.recognition-page::before {
  content: '';
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  height: 400px;
  background: radial-gradient(ellipse at 50% -10%, rgba(0, 229, 255, 0.1) 0%, transparent 60%);
  pointer-events: none;
  z-index: 0;
}

/* ========== 顶部导航 - iOS 26 玻璃态 ========== */
.nav-header {
  display: flex;
  align-items: center;
  padding: 18px 20px;
  padding-top: max(18px, env(safe-area-inset-top));
  background: linear-gradient(180deg,
    rgba(15, 25, 50, 0.9) 0%,
    rgba(10, 20, 40, 0.8) 100%
  );
  backdrop-filter: blur(40px) saturate(180%);
  -webkit-backdrop-filter: blur(40px) saturate(180%);
  border-bottom: 1px solid rgba(0, 229, 255, 0.1);
  position: sticky;
  top: 0;
  z-index: 100;
}

.nav-header::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(0, 229, 255, 0.2), transparent);
}

.back-btn {
  width: 42px;
  height: 42px;
  border: 1px solid rgba(0, 229, 255, 0.12);
  border-radius: 12px;
  background: linear-gradient(135deg, rgba(15, 30, 55, 0.6) 0%, rgba(10, 25, 45, 0.5) 100%);
  backdrop-filter: blur(10px);
  color: var(--text);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 280ms cubic-bezier(0.25, 0.46, 0.45, 0.94);
}

.back-btn:hover {
  background: linear-gradient(135deg, rgba(20, 40, 70, 0.7) 0%, rgba(15, 35, 60, 0.6) 100%);
  border-color: rgba(0, 229, 255, 0.25);
  transform: translateX(-3px);
  box-shadow: 0 0 15px rgba(0, 229, 255, 0.15);
}

.header-title {
  flex: 1;
  text-align: center;
  font-size: 18px;
  font-weight: 700;
  background: linear-gradient(135deg, #ffffff 0%, #00e5ff 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  margin: 0;
  letter-spacing: -0.02em;
}

.header-spacer {
  width: 42px;
}

.content {
  padding: 20px;
  position: relative;
  z-index: 1;
}

/* ========== 提示卡片 - 玻璃态 ========== */
.hint-card {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 18px 20px;
  background: linear-gradient(135deg, rgba(15, 30, 55, 0.5) 0%, rgba(10, 25, 45, 0.4) 100%);
  backdrop-filter: blur(16px);
  border: 1px solid rgba(0, 229, 255, 0.1);
  border-radius: 18px;
  margin-bottom: 24px;
  color: var(--text-muted);
  font-size: 14px;
  position: relative;
  overflow: hidden;
}

.hint-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.06), transparent);
}

.hint-icon {
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, rgba(0, 229, 255, 0.12) 0%, rgba(0, 255, 200, 0.08) 100%);
  border: 1px solid rgba(0, 229, 255, 0.15);
  border-radius: 12px;
  flex-shrink: 0;
  color: var(--primary);
}

/* ========== 候选列表 - 高级玻璃卡片 ========== */
.candidates-list {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.candidate-card {
  display: flex;
  align-items: center;
  background: linear-gradient(135deg, rgba(15, 30, 60, 0.55) 0%, rgba(10, 25, 50, 0.45) 100%);
  backdrop-filter: blur(24px) saturate(180%);
  -webkit-backdrop-filter: blur(24px) saturate(180%);
  border: 1px solid rgba(0, 229, 255, 0.08);
  border-radius: 22px;
  padding: 22px 24px;
  cursor: pointer;
  transition: all 350ms cubic-bezier(0.25, 0.46, 0.45, 0.94);
  position: relative;
  overflow: hidden;
}

.candidate-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 1px;
  background: linear-gradient(90deg,
    transparent 0%,
    rgba(255, 255, 255, 0.06) 20%,
    rgba(0, 229, 255, 0.15) 50%,
    rgba(255, 255, 255, 0.06) 80%,
    transparent 100%
  );
  opacity: 0.6;
}

.candidate-card::after {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 4px;
  background: linear-gradient(180deg, #00e5ff 0%, #00ffc8 100%);
  opacity: 0;
  transition: opacity 280ms ease;
}

.candidate-card:hover {
  background: linear-gradient(135deg, rgba(20, 40, 70, 0.65) 0%, rgba(15, 35, 60, 0.55) 100%);
  border-color: rgba(0, 229, 255, 0.2);
  transform: translateX(8px) translateY(-2px);
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.4), 0 0 25px rgba(0, 229, 255, 0.12);
}

.candidate-card:hover::after {
  opacity: 1;
}

.candidate-card:active {
  transform: scale(0.98) translateX(8px);
}

.candidate-rank {
  width: 44px;
  height: 44px;
  border-radius: 14px;
  background: linear-gradient(135deg, rgba(0, 229, 255, 0.15) 0%, rgba(0, 255, 200, 0.1) 100%);
  border: 1px solid rgba(0, 229, 255, 0.2);
  color: var(--primary);
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 800;
  font-size: 16px;
  margin-right: 18px;
  flex-shrink: 0;
  box-shadow: 0 0 15px rgba(0, 229, 255, 0.15);
  transition: all 280ms ease;
}

.candidate-card:hover .candidate-rank {
  box-shadow: 0 0 25px rgba(0, 229, 255, 0.3);
}

.candidate-info {
  flex: 1;
  min-width: 0;
}

.candidate-name {
  font-size: 18px;
  font-weight: 700;
  color: var(--text);
  margin: 0 0 6px;
  letter-spacing: -0.01em;
}

.candidate-detail {
  font-size: 14px;
  color: var(--text-muted);
  margin: 0;
}

.candidate-confidence {
  display: flex;
  flex-direction: column;
  align-items: center;
  margin-left: 18px;
}

.confidence-ring {
  position: relative;
  width: 56px;
  height: 56px;
}

.confidence-ring svg {
  width: 100%;
  height: 100%;
  filter: drop-shadow(0 0 8px rgba(0, 229, 255, 0.3));
}

.confidence-ring svg circle:first-child {
  stroke: rgba(0, 229, 255, 0.1);
}

.confidence-ring svg circle:last-child {
  stroke: url(#confidence-gradient);
  transition: stroke-dasharray 500ms ease;
}

.confidence-value {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  font-size: 13px;
  font-weight: 800;
  background: linear-gradient(135deg, #00e5ff 0%, #00ffc8 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.confidence-label {
  font-size: 11px;
  color: var(--text-light);
  margin-top: 6px;
  font-weight: 500;
}

/* ========== 空状态 ========== */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 100px 20px;
  text-align: center;
}

.empty-icon {
  width: 100px;
  height: 100px;
  margin-bottom: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, rgba(15, 30, 55, 0.5) 0%, rgba(10, 25, 45, 0.4) 100%);
  border: 1px solid rgba(255, 255, 255, 0.05);
  border-radius: 28px;
  color: var(--text-light);
}

.empty-title {
  font-size: 24px;
  font-weight: 700;
  background: linear-gradient(135deg, #ffffff 0%, #00e5ff 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  margin: 0 0 12px;
}

.empty-desc {
  font-size: 15px;
  color: var(--text-muted);
  margin: 0 0 32px;
}

/* ========== 操作按钮 ========== */
.actions {
  margin-top: 32px;
}

.btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  width: 100%;
  padding: 17px 28px;
  font-size: 16px;
  font-weight: 600;
  border: none;
  border-radius: 16px;
  cursor: pointer;
  transition: all 280ms cubic-bezier(0.25, 0.46, 0.45, 0.94);
  position: relative;
  overflow: hidden;
}

.btn-primary {
  background: linear-gradient(135deg, #00e5ff 0%, #00ffc8 100%);
  color: #050810;
  font-weight: 700;
  box-shadow: 0 4px 20px rgba(0, 229, 255, 0.35),
              inset 0 1px 0 rgba(255, 255, 255, 0.2);
}

.btn-primary::before {
  content: '';
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.3), transparent);
  transition: left 400ms ease;
}

.btn-primary:hover {
  box-shadow: 0 6px 28px rgba(0, 229, 255, 0.45),
              inset 0 1px 0 rgba(255, 255, 255, 0.25);
  transform: translateY(-2px);
}

.btn-primary:hover::before {
  left: 100%;
}

.btn-secondary {
  background: linear-gradient(135deg, rgba(15, 30, 55, 0.6) 0%, rgba(10, 25, 45, 0.5) 100%);
  backdrop-filter: blur(16px);
  border: 1px solid rgba(0, 229, 255, 0.12);
  color: var(--text);
}

.btn-secondary::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.08), transparent);
}

.btn-secondary:hover {
  background: linear-gradient(135deg, rgba(20, 40, 70, 0.7) 0%, rgba(15, 35, 60, 0.6) 100%);
  border-color: rgba(0, 229, 255, 0.25);
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3), 0 0 15px rgba(0, 229, 255, 0.1);
}

/* ========== 动画 ========== */
.slide-up {
  animation: slideUp 0.5s cubic-bezier(0.22, 1, 0.36, 1);
  animation-fill-mode: both;
}

@keyframes slideUp {
  from {
    opacity: 0;
    transform: translateY(28px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
</style>
