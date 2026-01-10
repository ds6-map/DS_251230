<script setup lang="ts">
import { ref, onMounted, onUnmounted, nextTick } from 'vue'

interface Message {
  id: string
  role: 'user' | 'bot'
  text: string
  tool?: string | null
  data?: any
  mapOpen?: boolean
}

const text = ref('')
const messages = ref<Message[]>([])
const ui = ref({ busy: false, progress: '处理中…' })
const status = ref({ llmReady: false, gmapsReady: false })
const gmapsReady = ref(false)
const sessionId = ref<string | null>(null)
const aborter = ref<AbortController | null>(null)
const timer = ref<number | null>(null)
const camera = ref({ open: false, stream: MediaStream | null })
const messagesEl = ref<HTMLElement | null>(null)
const imgInput = ref<HTMLInputElement | null>(null)
const camInput = ref<HTMLInputElement | null>(null)
const videoEl = ref<HTMLVideoElement | null>(null)

function id() {
  return String(Date.now()) + '-' + String(Math.random()).slice(2)
}

function sessionKey() {
  return 'agent_nav_chat_session_id'
}

function getOrCreateSessionId() {
  try {
    const k = sessionKey()
    const existing = (sessionStorage.getItem(k) || '').trim()
    if (existing) return existing
    const created = id()
    sessionStorage.setItem(k, created)
    return created
  } catch (e) {
    return id()
  }
}

function setBusy(on: boolean, label?: string) {
  ui.value.busy = !!on
  ui.value.progress = label || '处理中…'
}

function pushMessage(role: 'user' | 'bot', text: string, tool?: string | null, data?: any) {
  const m: Message = { id: id(), role, text, tool: tool || null, data: data || null }
  if (m.tool === 'navigate') m.mapOpen = true
  messages.value.push(m)
  nextTick(() => {
    if (messagesEl.value) {
      messagesEl.value.scrollTop = messagesEl.value.scrollHeight
    }
  })
  return m
}

async function refreshStatus() {
  try {
    const r = await fetch('/api/status')
    if (!r.ok) {
      throw new Error(`HTTP ${r.status}`)
    }
    const s = await r.json()
    status.value.llmReady = !!s.llmReady
    status.value.gmapsReady = !!s.gmapsReady
  } catch (e) {
    console.warn('Failed to refresh status:', e)
    status.value.llmReady = false
    status.value.gmapsReady = false
  }
}

function loadGMaps(key: string) {
  return new Promise<void>((resolve) => {
    const s = document.createElement('script')
    s.src = `https://maps.googleapis.com/maps/api/js?key=${encodeURIComponent(key)}&libraries=geometry`
    s.onload = () => {
      gmapsReady.value = true
      resolve()
    }
    document.head.appendChild(s)
  })
}

async function ensureGMaps() {
  if (gmapsReady.value) return
  try {
    const r = await fetch('/api/config')
    if (!r.ok) {
      throw new Error(`HTTP ${r.status}`)
    }
    const c = await r.json()
    const key = typeof c.gmapsKey === 'string' ? c.gmapsKey : ''
    if (key) await loadGMaps(key)
  } catch (e) {
    console.warn('Failed to load GMaps config:', e)
  }
}

async function postChat(payload: any, label?: string) {
  if (aborter.value) {
    try {
      aborter.value.abort()
    } catch (e) {}
    aborter.value = null
  }
  const controller = new AbortController()
  aborter.value = controller
  setBusy(true, label)
  const bodyPayload = Object.assign({}, payload || {}, {
    session_id: sessionId.value || undefined,
  })
  const res = await fetch('/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(bodyPayload),
    signal: controller.signal,
  })
  if (!res.ok) {
    const errorText = await res.text()
    throw new Error(`HTTP ${res.status}: ${errorText}`)
  }
  const data = await res.json()
  aborter.value = null
  setBusy(false)
  if (data && typeof data.session_id === 'string' && data.session_id) {
    sessionId.value = data.session_id
    try {
      sessionStorage.setItem(sessionKey(), sessionId.value)
    } catch (e) {}
  }
  return data
}

async function sendImageDataUrl(dataUrl: string, metaText?: string) {
  if (metaText) pushMessage('user', metaText)
  try {
    const data = await postChat({ message: '', image_base64: dataUrl }, '正在识别图片…')
    pushMessage('bot', data.reply || '', data.tool, data.data)
  } catch (e: any) {
    if (e && e.name === 'AbortError') {
      pushMessage('bot', '已取消')
      return
    }
    pushMessage('bot', '请求失败')
  }
}

function renderMap(message: Message) {
  if (!message || !message.data || !message.data.overview_polyline) return
  if (!(window as any).google || !(window as any).google.maps || !(window as any).google.maps.geometry) return
  const mapEl = document.getElementById('map-' + message.id)
  if (!mapEl) return
  const google = (window as any).google
  const path = google.maps.geometry.encoding.decodePath(message.data.overview_polyline)
  const bounds = new google.maps.LatLngBounds()
  path.forEach((p: any) => bounds.extend(p))
  const center = bounds.getCenter()
  const map = new google.maps.Map(mapEl, {
    center,
    zoom: 12,
    mapTypeControl: false,
    streetViewControl: false,
    fullscreenControl: false,
  })
  const pl = new google.maps.Polyline({
    path,
    geodesic: true,
    strokeColor: '#a1a1a6',
    strokeOpacity: 1,
    strokeWeight: 4,
  })
  pl.setMap(map)
  new google.maps.Marker({ position: message.data.start_location, map, title: '起点' })
  new google.maps.Marker({ position: message.data.end_location, map, title: '终点' })
  map.fitBounds(bounds)
}

async function toggleMap(message: Message) {
  if (!message) return
  message.mapOpen = !message.mapOpen
  if (message.mapOpen) {
    await ensureGMaps()
    await nextTick()
    renderMap(message)
  }
}

async function sendText() {
  const msg = (text.value || '').trim()
  if (!msg) return
  pushMessage('user', msg)
  text.value = ''
  await ensureGMaps()
  try {
    const data = await postChat({ message: msg }, '正在思考…')
    const bot = pushMessage('bot', data.reply || '', data.tool, data.data)
    if (data.tool === 'navigate') {
      await nextTick()
      renderMap(bot)
    }
  } catch (e: any) {
    if (e && e.name === 'AbortError') {
      pushMessage('bot', '已取消')
      return
    }
    pushMessage('bot', '请求失败')
  }
}

function openPicker() {
  if (ui.value.busy) return
  if (imgInput.value) imgInput.value.click()
}

async function onPickImage(ev: Event) {
  const target = ev.target as HTMLInputElement
  const file = target.files?.[0]
  if (!file) return
  const dataUrl = await new Promise<string>((resolve, reject) => {
    const reader = new FileReader()
    reader.onerror = () => reject(new Error('read_failed'))
    reader.onload = () => resolve(reader.result as string)
    reader.readAsDataURL(file)
  })
  try {
    await sendImageDataUrl(dataUrl, `已选择图片：${file.name}`)
  } finally {
    if (imgInput.value) imgInput.value.value = ''
  }
}

async function onPickCameraFile(ev: Event) {
  const target = ev.target as HTMLInputElement
  const file = target.files?.[0]
  if (!file) return
  const dataUrl = await new Promise<string>((resolve, reject) => {
    const reader = new FileReader()
    reader.onerror = () => reject(new Error('read_failed'))
    reader.onload = () => resolve(reader.result as string)
    reader.readAsDataURL(file)
  })
  try {
    await sendImageDataUrl(dataUrl, '已拍照')
  } finally {
    if (camInput.value) camInput.value.value = ''
  }
}

async function openCamera() {
  if (ui.value.busy) return
  const md = navigator && navigator.mediaDevices
  if (!md || !md.getUserMedia) {
    useCameraFileFallback()
    return
  }
  camera.value.open = true
  await nextTick()
  try {
    const stream = await md.getUserMedia({
      video: { facingMode: { ideal: 'environment' } },
      audio: false,
    })
    camera.value.stream = stream
    if (videoEl.value) {
      videoEl.value.srcObject = stream
      await videoEl.value.play()
    }
  } catch (e) {
    closeCamera()
    useCameraFileFallback()
  }
}

function useCameraFileFallback() {
  if (ui.value.busy) return
  if (camInput.value) camInput.value.click()
}

function closeCamera() {
  if (camera.value && camera.value.stream) {
    try {
      const tracks = camera.value.stream.getTracks ? camera.value.stream.getTracks() : []
      tracks.forEach((t) => {
        try {
          t.stop()
        } catch (e) {}
      })
    } catch (e) {}
  }
  camera.value.stream = null
  camera.value.open = false
}

async function capturePhoto() {
  const v = videoEl.value
  if (!v) return
  const w = v.videoWidth || 1280
  const h = v.videoHeight || 720
  if (!w || !h) return
  const canvas = document.createElement('canvas')
  canvas.width = w
  canvas.height = h
  const ctx = canvas.getContext('2d')
  if (!ctx) return
  ctx.drawImage(v, 0, 0, w, h)
  const dataUrl = canvas.toDataURL('image/jpeg', 0.92)
  closeCamera()
  await sendImageDataUrl(dataUrl, '已拍照')
}

function cancel() {
  if (!aborter.value) return
  try {
    aborter.value.abort()
  } catch (e) {}
}

onMounted(() => {
  sessionId.value = getOrCreateSessionId()
  refreshStatus()
  timer.value = window.setInterval(refreshStatus, 4000)
  pushMessage('bot', '你好！你可以让我导航、聊天，或上传/拍照图片做位置识别。')
  window.addEventListener('keydown', (e) => {
    if (
      e.key === 'Enter' &&
      !e.shiftKey &&
      document.activeElement &&
      document.activeElement.id === 'agent-chat-text'
    ) {
      e.preventDefault()
      sendText()
    }
  })
})

onUnmounted(() => {
  if (timer.value) clearInterval(timer.value)
})
</script>

<template>
  <div class="agent-chat">
    <div class="card">
      <div class="messages" ref="messagesEl">
        <transition-group name="fadeUp" tag="div">
          <div v-for="m in messages" :key="m.id" :class="['row', m.role]">
            <div :class="['bubble', m.role]">
              <div class="bubbleTitle">
                <span>{{ m.role === 'user' ? '你' : '助手' }}</span>
                <span v-if="m.tool" class="meta">工具：{{ m.tool }}</span>
              </div>
              <div class="bubbleText">{{ m.text }}</div>

              <div v-if="m.tool === 'location' && m.data && m.data.matches && m.data.matches.length">
                <div v-if="m.data.query_image_data_url" class="locationQuery">
                  <img :src="m.data.query_image_data_url" alt="query" />
                </div>
                <ol class="matches">
                  <li v-for="(x, idx) in m.data.matches" :key="idx">
                    <div class="matchRow">
                      <img v-if="x.image_data_url" class="matchThumb" :src="x.image_data_url" alt="match" />
                      <div class="matchMeta">
                        <div>
                          <span v-if="x.label">{{ x.label }}</span>
                          <span v-if="typeof x.score === 'number'">（{{ x.score.toFixed(4) }}）</span>
                        </div>
                        <div class="matchPath">{{ x.path }}</div>
                      </div>
                    </div>
                  </li>
                </ol>
              </div>

              <div v-if="m.tool === 'navigate' && m.data && m.data.overview_polyline">
                <div class="navCard">
                  <div class="navHeader">
                    <div>
                      <div class="navTitle">路线已生成</div>
                      <div class="navSub">{{ m.data.start_address }} → {{ m.data.end_address }}</div>
                    </div>
                    <button class="btn ghost" @click="toggleMap(m)">
                      {{ m.mapOpen ? '收起地图' : '展开地图' }}
                    </button>
                  </div>
                  <div class="navChips">
                    <span class="chip">
                      <span class="chipIcon"></span>
                      <strong>{{ m.data.distance_text }}</strong>
                      <span class="chipLabel">距离</span>
                    </span>
                    <span class="chip">
                      <span class="chipIcon alt"></span>
                      <strong>{{ m.data.duration_text }}</strong>
                      <span class="chipLabel">用时</span>
                    </span>
                    <span class="chip">
                      <span class="chipIcon ok"></span>
                      <strong>{{ m.data.summary || '推荐路线' }}</strong>
                      <span class="chipLabel">概览</span>
                    </span>
                  </div>
                  <div :class="['collapse', m.mapOpen ? 'open' : '']">
                    <div class="mapInset" :id="'map-' + m.id"></div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </transition-group>
      </div>

      <div class="composer">
        <div class="inputBar">
          <input
            id="agent-chat-text"
            class="input"
            v-model="text"
            :disabled="ui.busy"
            type="text"
            placeholder="例如：从NTU到樟宜机场导航 / 讲个笑话"
          />
          <input
            id="img"
            ref="imgInput"
            type="file"
            accept="image/*"
            style="display: none"
            @change="onPickImage"
          />
          <input
            id="cam"
            ref="camInput"
            type="file"
            accept="image/*"
            capture="environment"
            style="display: none"
            @change="onPickCameraFile"
          />
          <button class="btn ghost" :disabled="ui.busy" @click="openPicker">选择图片</button>
          <button class="btn ghost" :disabled="ui.busy" @click="openCamera">拍照</button>
          <button class="btn primary" :disabled="ui.busy" @click="sendText">发送</button>
        </div>
        <div class="toolsRow">
          <div class="hint">Enter 发送；请求中可取消</div>
          <div class="progress" v-if="ui.busy">
            <div class="spinner"></div>
            <div class="progressText">{{ ui.progress }}</div>
            <button class="btn danger" @click="cancel">取消</button>
          </div>
        </div>
      </div>
    </div>

    <div v-if="camera.open" class="modalMask" @click.self="closeCamera">
      <div class="modalCard">
        <div class="modalHeader">
          <div class="modalTitle">拍照上传</div>
          <button class="btn danger" @click="closeCamera">关闭</button>
        </div>
        <div class="modalBody">
          <div class="videoWrap">
            <video ref="videoEl" autoplay playsinline></video>
          </div>
          <div class="modalActions">
            <button class="btn ghost" :disabled="ui.busy" @click="useCameraFileFallback">改用系统相机</button>
            <button class="btn primary" :disabled="ui.busy" @click="capturePhoto">拍照并识别</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.agent-chat {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

/* ========== 主卡片 - iOS 26 高级玻璃态 ========== */
.card {
  flex: 1;
  border: 1px solid rgba(0, 229, 255, 0.1);
  border-radius: 24px;
  background: linear-gradient(135deg, rgba(15, 30, 60, 0.6) 0%, rgba(10, 25, 50, 0.5) 100%);
  backdrop-filter: blur(40px) saturate(180%);
  -webkit-backdrop-filter: blur(40px) saturate(180%);
  overflow: hidden;
  display: flex;
  flex-direction: column;
  min-height: 0;
  position: relative;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.35);
}

.card::before {
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

/* ========== 消息区域 ========== */
.messages {
  flex: 1;
  overflow-y: auto;
  padding: 20px 18px 14px;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.01), transparent);
}

.row {
  display: flex;
  margin: 14px 0;
}
.row.user {
  justify-content: flex-end;
}

/* ========== 聊天气泡 - 玻璃态 ========== */
.bubble {
  max-width: min(760px, 90%);
  border-radius: 20px;
  border: 1px solid rgba(0, 229, 255, 0.1);
  padding: 16px 18px;
  line-height: 1.65;
  background: linear-gradient(135deg, rgba(15, 30, 55, 0.6) 0%, rgba(10, 25, 45, 0.5) 100%);
  backdrop-filter: blur(16px);
  position: relative;
  transition: all 280ms ease;
}

.bubble::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.04), transparent);
  border-radius: 20px 20px 0 0;
}

.bubble.user {
  background: linear-gradient(135deg, rgba(0, 229, 255, 0.15) 0%, rgba(0, 255, 200, 0.1) 100%);
  border-color: rgba(0, 229, 255, 0.2);
}

.bubble.user::before {
  background: linear-gradient(90deg, transparent, rgba(0, 229, 255, 0.15), transparent);
}

.bubble.bot {
  background: linear-gradient(135deg, rgba(20, 35, 60, 0.7) 0%, rgba(15, 30, 55, 0.6) 100%);
}

.bubbleTitle {
  font-size: 12px;
  color: var(--text-muted);
  margin-bottom: 10px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-weight: 600;
}

.bubbleText {
  white-space: pre-wrap;
  color: var(--text);
  font-size: 15px;
}

.meta {
  margin-top: 8px;
  font-size: 12px;
  color: var(--text-muted);
  padding: 4px 10px;
  background: rgba(0, 229, 255, 0.08);
  border-radius: 6px;
  display: inline-block;
}

/* ========== 输入区域 - 玻璃态 ========== */
.composer {
  border-top: 1px solid rgba(0, 229, 255, 0.1);
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 14px;
  background: linear-gradient(180deg, rgba(15, 25, 50, 0.8) 0%, rgba(10, 20, 40, 0.85) 100%);
  backdrop-filter: blur(24px);
  position: relative;
}

.composer::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(0, 229, 255, 0.15), transparent);
}

.inputBar {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.input {
  flex: 1;
  min-width: 220px;
  padding: 15px 18px;
  border-radius: 16px;
  border: 1px solid rgba(0, 229, 255, 0.12);
  background: linear-gradient(135deg, rgba(15, 30, 55, 0.5) 0%, rgba(10, 25, 45, 0.4) 100%);
  backdrop-filter: blur(10px);
  outline: none;
  font-size: 16px;
  font-weight: 500;
  color: var(--text);
  transition: all 280ms ease;
}

.input:focus {
  border-color: rgba(0, 229, 255, 0.3);
  box-shadow: 0 0 0 4px rgba(0, 229, 255, 0.08), 0 0 20px rgba(0, 229, 255, 0.1);
  background: linear-gradient(135deg, rgba(20, 35, 60, 0.6) 0%, rgba(15, 30, 50, 0.5) 100%);
}

.input::placeholder {
  color: var(--text-light);
}

/* ========== 按钮系统 - iOS 26 风格 ========== */
.btn {
  padding: 13px 18px;
  border-radius: 14px;
  border: 1px solid rgba(0, 229, 255, 0.12);
  background: linear-gradient(135deg, rgba(15, 30, 55, 0.5) 0%, rgba(10, 25, 45, 0.4) 100%);
  backdrop-filter: blur(10px);
  color: var(--text);
  cursor: pointer;
  transition: all 280ms cubic-bezier(0.25, 0.46, 0.45, 0.94);
  white-space: nowrap;
  font-size: 14px;
  font-weight: 600;
  position: relative;
  overflow: hidden;
}

.btn:hover {
  border-color: rgba(0, 229, 255, 0.25);
  background: linear-gradient(135deg, rgba(20, 40, 70, 0.6) 0%, rgba(15, 35, 60, 0.5) 100%);
  box-shadow: 0 0 15px rgba(0, 229, 255, 0.12);
}

.btn:active {
  transform: scale(0.96);
}

.btn:disabled {
  opacity: 0.35;
  cursor: not-allowed;
}

.btn.primary {
  color: #050810;
  border: none;
  background: linear-gradient(135deg, #00e5ff 0%, #00ffc8 100%);
  font-weight: 700;
  box-shadow: 0 4px 16px rgba(0, 229, 255, 0.3), inset 0 1px 0 rgba(255, 255, 255, 0.2);
}

.btn.primary::before {
  content: '';
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.3), transparent);
  transition: left 400ms ease;
}

.btn.primary:hover {
  box-shadow: 0 6px 24px rgba(0, 229, 255, 0.4), inset 0 1px 0 rgba(255, 255, 255, 0.25);
  transform: translateY(-1px);
}

.btn.primary:hover::before {
  left: 100%;
}

.btn.ghost {
  background: transparent;
  border-color: rgba(0, 229, 255, 0.1);
}

.btn.ghost:hover {
  background: rgba(0, 229, 255, 0.08);
  border-color: rgba(0, 229, 255, 0.2);
}

.btn.danger {
  color: #fff;
  border: none;
  background: linear-gradient(135deg, #ff5c72 0%, #ff4757 100%);
  box-shadow: 0 4px 16px rgba(255, 92, 114, 0.3);
}

.btn.danger:hover {
  background: linear-gradient(135deg, #ff7388 0%, #ff5c72 100%);
  box-shadow: 0 6px 20px rgba(255, 92, 114, 0.4);
}

/* ========== 工具行 ========== */
.toolsRow {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}

.hint {
  font-size: 12px;
  color: var(--text-muted);
  font-weight: 500;
}

.progress {
  display: flex;
  align-items: center;
  gap: 12px;
}

.progressText {
  font-size: 12px;
  color: var(--text-muted);
  font-weight: 500;
}

.spinner {
  width: 18px;
  height: 18px;
  border-radius: 50%;
  border: 2px solid rgba(0, 229, 255, 0.15);
  border-top-color: #00e5ff;
  animation: spin 0.8s linear infinite;
  filter: drop-shadow(0 0 4px rgba(0, 229, 255, 0.4));
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

/* ========== 导航卡片 - 高级玻璃态 ========== */
.navCard {
  margin-top: 14px;
  border-radius: 20px;
  border: 1px solid rgba(0, 229, 255, 0.12);
  background: linear-gradient(135deg, rgba(15, 30, 60, 0.7) 0%, rgba(10, 25, 50, 0.6) 100%);
  backdrop-filter: blur(20px);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
  overflow: hidden;
  transition: all 280ms ease;
  position: relative;
}

.navCard::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(0, 229, 255, 0.2), transparent);
}

.navCard:hover {
  border-color: rgba(0, 229, 255, 0.22);
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.45), 0 0 20px rgba(0, 229, 255, 0.1);
}

.navHeader {
  padding: 16px 18px 14px;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 14px;
}

.navTitle {
  font-weight: 700;
  font-size: 16px;
  background: linear-gradient(135deg, #ffffff 0%, #00e5ff 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  letter-spacing: -0.02em;
}

.navSub {
  margin-top: 5px;
  font-size: 13px;
  color: var(--text-muted);
}

.navChips {
  padding: 0 18px 16px;
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.chip {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  border-radius: 12px;
  border: 1px solid rgba(0, 229, 255, 0.1);
  background: linear-gradient(135deg, rgba(0, 229, 255, 0.08) 0%, rgba(0, 255, 200, 0.05) 100%);
  font-size: 13px;
  color: var(--text);
  transition: all 280ms ease;
}

.chip:hover {
  border-color: rgba(0, 229, 255, 0.2);
  box-shadow: 0 0 12px rgba(0, 229, 255, 0.1);
}

.chip strong {
  font-weight: 700;
  color: var(--primary);
}

.chipLabel {
  color: var(--text-muted);
  font-size: 12px;
}

.chipIcon {
  width: 10px;
  height: 10px;
  border-radius: 3px;
  background: var(--text-muted);
}

.chipIcon.alt {
  background: linear-gradient(135deg, #00e5ff 0%, #00d4ff 100%);
  box-shadow: 0 0 8px rgba(0, 229, 255, 0.4);
}

.chipIcon.ok {
  background: linear-gradient(135deg, #00ffc8 0%, #00e5b0 100%);
  box-shadow: 0 0 8px rgba(0, 255, 200, 0.4);
}

.collapse {
  overflow: hidden;
  max-height: 0;
  opacity: 0;
  transform: translateY(-8px);
  transition: all 350ms cubic-bezier(0.25, 0.46, 0.45, 0.94);
}

.collapse.open {
  max-height: 450px;
  opacity: 1;
  transform: translateY(0);
}

.mapInset {
  margin: 0 18px 18px;
  width: calc(min(760px, 92%) - 36px);
  height: 300px;
  border-radius: 16px;
  border: 1px solid rgba(0, 229, 255, 0.12);
  overflow: hidden;
  background: linear-gradient(135deg, rgba(15, 30, 55, 0.6) 0%, rgba(10, 25, 45, 0.5) 100%);
}

/* ========== 位置识别结果 ========== */
.matches {
  margin: 14px 0 0;
  padding-left: 22px;
}

.matches li {
  margin: 10px 0;
  color: var(--text);
}

.locationQuery {
  margin: 14px 0 0;
  width: min(420px, 100%);
  border-radius: 16px;
  border: 1px solid rgba(0, 229, 255, 0.12);
  overflow: hidden;
  background: linear-gradient(135deg, rgba(15, 30, 55, 0.6) 0%, rgba(10, 25, 45, 0.5) 100%);
}

.locationQuery img {
  width: 100%;
  height: auto;
  display: block;
}

.matchRow {
  display: flex;
  align-items: center;
  gap: 14px;
}

.matchThumb {
  width: 76px;
  height: 76px;
  border-radius: 14px;
  border: 1px solid rgba(0, 229, 255, 0.12);
  object-fit: cover;
  background: linear-gradient(135deg, rgba(15, 30, 55, 0.6) 0%, rgba(10, 25, 45, 0.5) 100%);
  flex: 0 0 auto;
  transition: all 280ms ease;
}

.matchThumb:hover {
  border-color: rgba(0, 229, 255, 0.25);
  box-shadow: 0 0 15px rgba(0, 229, 255, 0.15);
}

.matchMeta {
  min-width: 0;
}

.matchPath {
  font-size: 12px;
  color: var(--text-muted);
  word-break: break-all;
  margin-top: 4px;
}

/* ========== 动画 ========== */
.fadeUp-enter-active {
  transition: opacity 0.35s cubic-bezier(0.22, 1, 0.36, 1), transform 0.35s cubic-bezier(0.22, 1, 0.36, 1);
}

.fadeUp-enter-from {
  opacity: 0;
  transform: translateY(16px);
}

/* ========== 相机弹窗 - iOS 26 风格 ========== */
.modalMask {
  position: fixed;
  inset: 0;
  background: rgba(5, 8, 16, 0.9);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  z-index: 1000;
}

.modalCard {
  width: min(860px, 100%);
  border-radius: 28px;
  border: 1px solid rgba(0, 229, 255, 0.15);
  background: linear-gradient(135deg, rgba(15, 30, 60, 0.95) 0%, rgba(10, 25, 50, 0.98) 100%);
  backdrop-filter: blur(40px) saturate(180%);
  -webkit-backdrop-filter: blur(40px) saturate(180%);
  overflow: hidden;
  box-shadow: 0 24px 80px rgba(0, 0, 0, 0.6), 0 0 40px rgba(0, 229, 255, 0.1);
  position: relative;
}

.modalCard::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(0, 229, 255, 0.25), transparent);
}

.modalHeader {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 20px 22px;
  border-bottom: 1px solid rgba(0, 229, 255, 0.1);
  background: linear-gradient(180deg, rgba(20, 35, 60, 0.5) 0%, transparent 100%);
}

.modalTitle {
  font-weight: 700;
  font-size: 18px;
  background: linear-gradient(135deg, #ffffff 0%, #00e5ff 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.modalBody {
  padding: 22px;
  display: grid;
  gap: 18px;
}

.videoWrap {
  width: 100%;
  aspect-ratio: 16/9;
  border-radius: 18px;
  border: 1px solid rgba(0, 229, 255, 0.12);
  overflow: hidden;
  background: linear-gradient(135deg, rgba(10, 20, 40, 0.8) 0%, rgba(5, 15, 30, 0.9) 100%);
}

video {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.modalActions {
  display: flex;
  justify-content: flex-end;
  gap: 14px;
  flex-wrap: wrap;
}
</style>
