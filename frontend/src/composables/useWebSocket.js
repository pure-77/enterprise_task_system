import { ref, onUnmounted } from 'vue'
import { auth } from '@/utils/auth'

const API_BASE = import.meta.env.VITE_API_BASE_URL || ''
const WS_URL = API_BASE.replace(/^http/, 'ws') + '/ws/task-status'

export function useWebSocket() {
  const connected = ref(false)
  const lastMessage = ref(null)
  let ws = null
  let reconnectTimer = null
  let heartbeatTimer = null

  const connect = () => {
    const token = auth.getToken()
    if (!token) return

    try {
      ws = new WebSocket(`${WS_URL}?token=${token}`)

      ws.onopen = () => {
        connected.value = true
        startHeartbeat()
      }

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          lastMessage.value = data

          // 分发事件 - stores 可以监听这些事件
          if (data.type === 'task_status_update') {
            window.dispatchEvent(new CustomEvent('ws:task_update', { detail: data }))
          } else if (data.workspace_id) {
            window.dispatchEvent(new CustomEvent('ws:workspace_event', { detail: data }))
          }
        } catch {}
      }

      ws.onclose = () => {
        connected.value = false
        stopHeartbeat()
        scheduleReconnect()
      }

      ws.onerror = () => {
        ws?.close()
      }
    } catch {}
  }

  const disconnect = () => {
    clearTimeout(reconnectTimer)
    stopHeartbeat()
    ws?.close()
    ws = null
    connected.value = false
  }

  const scheduleReconnect = () => {
    reconnectTimer = setTimeout(connect, 5000)
  }

  const startHeartbeat = () => {
    heartbeatTimer = setInterval(() => {
      if (ws?.readyState === WebSocket.OPEN) {
        ws.send('ping')
      }
    }, 30000)
  }

  const stopHeartbeat = () => {
    clearInterval(heartbeatTimer)
    heartbeatTimer = null
  }

  onUnmounted(() => disconnect())

  return { connected, lastMessage, connect, disconnect }
}
