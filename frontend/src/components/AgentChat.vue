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

.card {
  flex: 1;
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 20px;
  background: rgba(28, 28, 30, 0.7);
  backdrop-filter: blur(40px) saturate(150%);
  overflow: hidden;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.messages {
  flex: 1;
  overflow-y: auto;
  padding: 18px 16px 12px;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.01), transparent);
}

.row {
  display: flex;
  margin: 12px 0;
}
.row.user {
  justify-content: flex-end;
}
.bubble {
  max-width: min(760px, 92%);
  border-radius: 18px;
  border: 1px solid rgba(255, 255, 255, 0.06);
  padding: 14px 16px;
  line-height: 1.6;
  background: rgba(38, 38, 40, 0.8);
}
.bubble.user {
  background: rgba(255, 255, 255, 0.06);
  border-color: rgba(255, 255, 255, 0.08);
}
.bubble.bot {
  background: rgba(38, 38, 40, 0.9);
}
.bubbleTitle {
  font-size: 12px;
  color: #636366;
  margin-bottom: 8px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.bubbleText {
  white-space: pre-wrap;
  color: #f5f5f7;
}
.meta {
  margin-top: 8px;
  font-size: 12px;
  color: #636366;
}

.composer {
  border-top: 1px solid rgba(255, 255, 255, 0.06);
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  background: rgba(28, 28, 30, 0.9);
  backdrop-filter: blur(20px);
}

.inputBar {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.input {
  flex: 1;
  min-width: 220px;
  padding: 14px 16px;
  border-radius: 14px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  background: rgba(255, 255, 255, 0.04);
  outline: none;
  font-size: 16px;
  color: #f5f5f7;
  transition: all 0.25s;
}
.input:focus {
  border-color: rgba(255, 255, 255, 0.15);
  box-shadow: 0 0 0 4px rgba(255, 255, 255, 0.03);
}
.input::placeholder {
  color: #636366;
}

.btn {
  padding: 12px 16px;
  border-radius: 12px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  background: rgba(255, 255, 255, 0.04);
  color: #f5f5f7;
  cursor: pointer;
  transition: all 0.25s;
  white-space: nowrap;
  font-size: 14px;
  font-weight: 500;
}
.btn:hover {
  border-color: rgba(255, 255, 255, 0.12);
  background: rgba(255, 255, 255, 0.08);
}
.btn:active {
  transform: scale(0.97);
}
.btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}
.btn.primary {
  color: #000;
  border: none;
  background: #f5f5f7;
}
.btn.primary:hover {
  background: #e5e5e7;
}
.btn.ghost {
  background: transparent;
  border-color: rgba(255, 255, 255, 0.06);
}
.btn.danger {
  color: #fff;
  border: none;
  background: #48484a;
}
.btn.danger:hover {
  background: #636366;
}

.toolsRow {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  flex-wrap: wrap;
}
.hint {
  font-size: 12px;
  color: #636366;
}
.progress {
  display: flex;
  align-items: center;
  gap: 10px;
}
.progressText {
  font-size: 12px;
  color: #636366;
}
.spinner {
  width: 16px;
  height: 16px;
  border-radius: 50%;
  border: 2px solid rgba(255, 255, 255, 0.1);
  border-top-color: #a1a1a6;
  animation: spin 0.8s linear infinite;
}
@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.navCard {
  margin-top: 12px;
  border-radius: 16px;
  border: 1px solid rgba(255, 255, 255, 0.06);
  background: rgba(28, 28, 30, 0.9);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.3);
  overflow: hidden;
  transition: all 0.25s;
}
.navCard:hover {
  border-color: rgba(255, 255, 255, 0.1);
}
.navHeader {
  padding: 14px 16px 12px;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}
.navTitle {
  font-weight: 700;
  color: #f5f5f7;
  letter-spacing: -0.02em;
}
.navSub {
  margin-top: 4px;
  font-size: 13px;
  color: #636366;
}
.navChips {
  padding: 0 16px 14px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.chip {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border-radius: 10px;
  border: 1px solid rgba(255, 255, 255, 0.06);
  background: rgba(255, 255, 255, 0.03);
  font-size: 13px;
  color: #f5f5f7;
}
.chip strong {
  font-weight: 600;
}
.chipLabel {
  color: #636366;
}
.chipIcon {
  width: 8px;
  height: 8px;
  border-radius: 2px;
  background: #636366;
}
.chipIcon.alt {
  background: #8e8e93;
}
.chipIcon.ok {
  background: #48484a;
}
.collapse {
  overflow: hidden;
  max-height: 0;
  opacity: 0;
  transform: translateY(-4px);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}
.collapse.open {
  max-height: 420px;
  opacity: 1;
  transform: translateY(0);
}
.mapInset {
  margin: 0 16px 16px;
  width: calc(min(760px, 92%) - 32px);
  height: 280px;
  border-radius: 14px;
  border: 1px solid rgba(255, 255, 255, 0.06);
  overflow: hidden;
  background: rgba(28, 28, 30, 0.8);
}

.matches {
  margin: 12px 0 0;
  padding-left: 20px;
}
.matches li {
  margin: 8px 0;
  color: #f5f5f7;
}
.locationQuery {
  margin: 12px 0 0;
  width: min(420px, 100%);
  border-radius: 14px;
  border: 1px solid rgba(255, 255, 255, 0.06);
  overflow: hidden;
  background: rgba(28, 28, 30, 0.8);
}
.locationQuery img {
  width: 100%;
  height: auto;
  display: block;
}
.matchRow {
  display: flex;
  align-items: center;
  gap: 12px;
}
.matchThumb {
  width: 72px;
  height: 72px;
  border-radius: 12px;
  border: 1px solid rgba(255, 255, 255, 0.06);
  object-fit: cover;
  background: rgba(28, 28, 30, 0.8);
  flex: 0 0 auto;
}
.matchMeta {
  min-width: 0;
}
.matchPath {
  font-size: 12px;
  color: #636366;
  word-break: break-all;
}

.fadeUp-enter-active {
  transition: opacity 0.25s ease, transform 0.25s ease;
}
.fadeUp-enter-from {
  opacity: 0;
  transform: translateY(12px);
}

.modalMask {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.8);
  backdrop-filter: blur(8px);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  z-index: 1000;
}
.modalCard {
  width: min(860px, 100%);
  border-radius: 20px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  background: rgba(28, 28, 30, 0.98);
  backdrop-filter: blur(40px);
  overflow: hidden;
}
.modalHeader {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  padding: 16px 18px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
}
.modalTitle {
  font-weight: 700;
  font-size: 17px;
  color: #f5f5f7;
}
.modalBody {
  padding: 18px;
  display: grid;
  gap: 14px;
}
.videoWrap {
  width: 100%;
  aspect-ratio: 16/9;
  border-radius: 14px;
  border: 1px solid rgba(255, 255, 255, 0.06);
  overflow: hidden;
  background: rgba(0, 0, 0, 0.4);
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
  gap: 12px;
  flex-wrap: wrap;
}
</style>
