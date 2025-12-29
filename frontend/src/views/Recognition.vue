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
  <div class="recognition-page page-container">
    <van-nav-bar title="确认位置" left-arrow @click-left="router.back()" />
    
    <div class="content">
      <div class="hint-text">
        <van-icon name="info-o" size="16" />
        <span>系统识别到以下可能的位置，请选择正确的一个</span>
      </div>
      
      <!-- 候选位置列表 -->
      <div class="candidates-list">
        <div
          v-for="(candidate, index) in candidates"
          :key="candidate.node_id"
          class="candidate-card"
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
            <span class="confidence-value">{{ formatConfidence(candidate.confidence) }}</span>
            <span class="confidence-label">置信度</span>
          </div>
        </div>
      </div>
      
      <!-- 没有结果 -->
      <van-empty v-if="candidates.length === 0" description="未识别到位置">
        <van-button type="primary" @click="retakePhoto">重新拍照</van-button>
      </van-empty>
      
      <!-- 操作按钮 -->
      <div class="actions" v-if="candidates.length > 0">
        <van-button type="default" block @click="retakePhoto">
          都不对，重新拍照
        </van-button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.recognition-page {
  background: #f7f8fa;
}

.content {
  padding: 16px;
}

.hint-text {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  background: #e6f7ff;
  border-radius: 8px;
  margin-bottom: 16px;
  font-size: 13px;
  color: #1989fa;
}

.candidates-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.candidate-card {
  display: flex;
  align-items: center;
  background: #fff;
  border-radius: 12px;
  padding: 16px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
  cursor: pointer;
  transition: transform 0.2s, box-shadow 0.2s;
}

.candidate-card:active {
  transform: scale(0.98);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.candidate-rank {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: linear-gradient(135deg, #1989fa, #07c160);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  font-size: 14px;
  margin-right: 12px;
  flex-shrink: 0;
}

.candidate-info {
  flex: 1;
  min-width: 0;
}

.candidate-name {
  font-size: 16px;
  font-weight: 600;
  color: #323233;
  margin-bottom: 4px;
}

.candidate-detail {
  font-size: 13px;
  color: #969799;
}

.candidate-confidence {
  text-align: center;
  margin-left: 12px;
}

.confidence-value {
  display: block;
  font-size: 18px;
  font-weight: 700;
  color: #1989fa;
}

.confidence-label {
  font-size: 11px;
  color: #969799;
}

.actions {
  margin-top: 24px;
}
</style>

