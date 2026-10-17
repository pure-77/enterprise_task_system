/**
 * Agent API
 */
import request from './request'
import axios from 'axios'

// 从 .env 读 baseURL 和 token（和 request.js 保持一致）
const getAuthConfig = () => {
  try {
    const state = JSON.parse(localStorage.getItem('user_state') || '{}')
    const token = state?.token || localStorage.getItem('access_token') || ''
    // 和 request.js 保持一致：直连后端，不走 Vite rewrite 代理
    const baseURL = import.meta.env.VITE_API_BASE_URL || '/api/v1'
    return { baseURL, token }
  } catch {
    return { baseURL: import.meta.env.VITE_API_BASE_URL || '/api/v1', token: '' }
  }
}

export const agentApi = {
  /**
   * Agent 对话
   * @param {Object} data
   * @param {string} data.message - 用户消息
   * @param {number} data.workspace_id - 当前 workspace ID
   * @param {string} [data.session_id] - 会话 ID（用于多轮记忆）
   * @param {Array}  [data.images] - 图片（多模态，base64 数组）
   */
  chat: (data) => {
    return request({
      url: '/agent/chat',
      method: 'post',
      data,
      timeout: 120000  // LLM 调用可能较慢
    })
  },

  /**
   * Agent 对话（SSE 流式）
   * 使用原生 fetch + ReadableStream 解析 SSE，实现打字机效果
   *
   * @param {Object} data - 同 chat()
   * @param {Object} handlers - 事件回调
   * @param {Function} handlers.onMessage - (chunk: string) => void  每收到一段文本
   * @param {Function} handlers.onToolCall - (toolCalls: Array) => void  工具调用通知
   * @param {Function} handlers.onDone - (meta: Object) => void  完整回复结束
   * @param {Function} handlers.onError - (err: Error) => void  错误处理
   * @returns {AbortController} 可用于 abort() 取消请求
   */
  streamChat(data, handlers = {}) {
    const { baseURL, token } = getAuthConfig()
    const controller = new AbortController()

    const run = async () => {
      try {
        const resp = await fetch(`${baseURL}/agent/chat/stream`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': token ? `Bearer ${token}` : ''
          },
          body: JSON.stringify(data),
          signal: controller.signal
        })

        if (!resp.ok || !resp.body) {
          throw new Error(`HTTP ${resp.status}`)
        }

        // SSE 解析：ReadableStream → TextDecoder → 按 \n\n 分隔事件
        const reader = resp.body.getReader()
        const decoder = new TextDecoder()
        let buffer = ''

        while (true) {
          const { done, value } = await reader.read()
          if (done) break

          buffer += decoder.decode(value, { stream: true })
          const events = buffer.split('\n\n')
          buffer = events.pop()  // 最后一个可能不完整，留到下一轮拼

          for (const rawEvent of events) {
            const lines = rawEvent.split('\n').filter(l => l.trim())
            let eventType = 'message'
            let eventData = ''

            for (const line of lines) {
              if (line.startsWith('event:')) {
                eventType = line.slice(6).trim()
              } else if (line.startsWith('data:')) {
                eventData += line.slice(5).trim()
              }
            }

            if (!eventData) continue

            switch (eventType) {
              case 'tool_call':
                handlers.onToolCall?.(JSON.parse(eventData))
                break
              case 'message':
                handlers.onMessage?.(JSON.parse(eventData))
                break
              case 'done':
                handlers.onDone?.(JSON.parse(eventData))
                return
              case 'error':
                handlers.onError?.(new Error(JSON.parse(eventData).error))
                return
            }
          }
        }
      } catch (err) {
        if (err.name !== 'AbortError') {
          handlers.onError?.(err)
        }
      }
    }

    run()
    return controller
  },

  /**
   * 查看已注册工具
   */
  listTools: () => {
    return request({
      url: '/agent/tools',
      method: 'get'
    })
  },

  /**
   * 清空对话记忆
   */
  clearMemory: (sessionId) => {
    return request({
      url: '/agent/memory',
      method: 'delete',
      params: { session_id: sessionId }
    })
  },

  // ==================== 会话持久化（MySQL）====================

  /**
   * 列出当前用户的会话（后端 MySQL 持久化，跨设备同步）
   */
  listSessions: (workspaceId = null, limit = 50) => {
    return request({
      url: '/agent/sessions',
      method: 'get',
      params: { workspace_id: workspaceId, limit }
    })
  },

  /**
   * 获取某个会话的完整消息历史
   */
  getSessionMessages: (sessionId, limit = 200) => {
    return request({
      url: `/agent/sessions/${sessionId}/messages`,
      method: 'get',
      params: { limit }
    })
  },

  /**
   * 删除会话（级联删消息）
   */
  deleteSession: (sessionId) => {
    return request({
      url: `/agent/sessions/${sessionId}`,
      method: 'delete'
    })
  },

  /**
   * 删除单条消息
   */
  deleteMessage: (sessionId, messageId) => {
    return request({
      url: `/agent/sessions/${sessionId}/messages/${messageId}`,
      method: 'delete'
    })
  },

  // ==================== 任务规划（plan_tasks）确认 / 取消 ====================

  /**
   * 确认任务计划 → 后端批量创建任务
   * @param {string} planId - plan_tasks 返回的 plan_id
   * @param {Object} data
   * @param {string} [data.session_id] - 当前会话 key（结果回写同一会话）
   * @param {number[]} [data.task_indexes] - 勾选的任务下标，不传表示全部
   */
  confirmPlan: (planId, data = {}) => {
    return request({
      url: `/agent/plans/${planId}/confirm`,
      method: 'post',
      data
    })
  },

  /**
   * 取消任务计划（不创建任何任务）
   */
  cancelPlan: (planId) => {
    return request({
      url: `/agent/plans/${planId}/cancel`,
      method: 'post'
    })
  }
}
