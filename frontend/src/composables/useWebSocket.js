import { ref } from 'vue'
import { auth } from '@/utils/auth'

const API_BASE = import.meta.env.VITE_API_BASE_URL || ''
// API_BASE 已包含 /api/v1，WebSocket 端点在 /api/v1/ws
const WS_URL = API_BASE.replace(/^http/, 'ws') + '/ws'

// 全局单例状态 — 所有组件共享同一个 WebSocket 连接
const connected = ref(false)
const lastMessage = ref(null)
let ws = null
let reconnectTimer = null
let heartbeatTimer = null
let subscribedChannels = new Set()

function connect() {
  const token = auth.getToken()
  if (!token) return

  // 防止重复连接
  if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) return

  try {
    ws = new WebSocket(`${WS_URL}?token=${token}`)

    ws.onopen = () => {
      console.log('[WS] Connected to', WS_URL)
      connected.value = true
      startHeartbeat()
      // 重新订阅之前的频道
      if (subscribedChannels.size > 0) {
        sendSubscribe([...subscribedChannels])
      }
    }

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        lastMessage.value = data
        console.log('[WS] Received:', data.type, data.channel)

        // 分发事件到 window，各组件可监听
        if (data.type === 'new_message' && data.channel === 'im') {
          window.dispatchEvent(new CustomEvent('ws:im_message', { detail: data.data }))
        } else if (data.type === 'read_status' && data.channel === 'im') {
          window.dispatchEvent(new CustomEvent('ws:im_read', { detail: data.data }))
        } else if (data.type === 'task_status_update') {
          window.dispatchEvent(new CustomEvent('ws:task_update', { detail: data }))
        } else if (data.type === 'new_notification' && data.channel === 'notification') {
          window.dispatchEvent(new CustomEvent('ws:new_notification', { detail: data.data }))
        } else if (data.workspace_id) {
          window.dispatchEvent(new CustomEvent('ws:workspace_event', { detail: data }))
        }
      } catch {}
    }

    ws.onclose = (e) => {
      console.log('[WS] Disconnected:', e.code, e.reason)
      connected.value = false
      stopHeartbeat()
      scheduleReconnect()
    }

    ws.onerror = (e) => {
      console.error('[WS] Error:', e)
      ws?.close()
    }
  } catch {}
}

function disconnect() {
  clearTimeout(reconnectTimer)
  stopHeartbeat()
  subscribedChannels.clear()
  ws?.close()
  ws = null
  connected.value = false
}

function sendSubscribe(channels) {
  if (ws?.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ action: 'subscribe', channels }))
  }
}

function subscribe(channels) {
  channels.forEach(ch => subscribedChannels.add(ch))
  sendSubscribe(channels)
}

function unsubscribe(channels) {
  channels.forEach(ch => subscribedChannels.delete(ch))
  if (ws?.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ action: 'unsubscribe', channels }))
  }
}

function scheduleReconnect() {
  reconnectTimer = setTimeout(connect, 5000)
}

function startHeartbeat() {
  heartbeatTimer = setInterval(() => {
    if (ws?.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ action: 'ping' }))
    }
  }, 30000)
}

function stopHeartbeat() {
  clearInterval(heartbeatTimer)
  heartbeatTimer = null
}

// 全局 composable — 调用多次返回相同的状态引用
export function useWebSocket() {
  return { connected, lastMessage, connect, disconnect, subscribe, unsubscribe }
}
