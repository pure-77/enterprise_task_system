import { defineStore } from 'pinia'
import { agentApi } from '@/api/agent'

/**
 * Agent 会话 Store — 全部持久化在后端 MySQL
 *
 * 存储分工：
 *   后端 Redis:   AgentMemory 短期对话上下文（24h TTL，推理时加载）
 *   后端 MySQL:    AgentSession + AgentMessage 持久化历史（跨设备同步）
 *   前端:          只有当前会话消息的运行时缓存（页面关闭就丢，刷新重新拉）
 */
export const useAgentStore = defineStore('agent', {
  state: () => ({
    // 当前会话（DB record）
    currentSession: null,   // { id, session_key, title, message_count, ... }
    messages: [],           // [{ role, content, tool_calls, thinking, timestamp, _seq }]
    isLoading: false,

    // 会话列表（从后端拉）
    sessions: [],           // [{ id, title, updated_at, message_count, ... }]

    // 已注册工具
    tools: [],
    toolGroups: []
  }),

  getters: {
    sortedSessions: (state) => {
      return [...state.sessions].sort((a, b) => new Date(b.updated_at) - new Date(a.updated_at))
    }
  },

  actions: {
    /** 初始化：从后端拉会话列表 + 工具 */
    async init(workspaceId = null) {
      try {
        const data = await agentApi.listSessions(workspaceId)
        this.sessions = data.sessions || []
      } catch {
        this.sessions = []
      }
      try {
        const tools = await agentApi.listTools()
        this.tools = tools.tools || []
        this.toolGroups = tools.groups || []
      } catch { /* ignore */ }
    },

    /** 创建新会话 */
    newSession() {
      // 不立即写 DB，等第一次 sendMessage 时后端自动 get_or_create
      this.currentSession = {
        id: null,
        session_key: `session-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
        title: '新对话'
      }
      this.messages = []
    },

    /** 切换会话 — 从后端 MySQL 拉完整消息历史 */
    async switchSession(sessionOrId) {
      // 兼容：传 session 对象 或 传 id
      const session = typeof sessionOrId === 'object' ? sessionOrId : this.sessions.find(s => s.id === sessionOrId)
      if (!session?.id) return
      this.currentSession = session
      try {
        const data = await agentApi.getSessionMessages(session.id)
        this.messages = (data.messages || []).map(m => ({
          role: m.role,
          content: m.content,
          tool_calls: m.tool_calls || [],
          thinking: m.thinking,
          timestamp: new Date(m.created_at).getTime(),
          _seq: m.seq,
          _db_id: m.id,
        }))
      } catch (err) {
        this.messages = []
        console.warn('[Agent] 加载会话消息失败', err)
      }
    },

    /** 删除会话（后端级联删消息） */
    async deleteSession(sessionId) {
      try {
        await agentApi.deleteSession(sessionId)
      } catch { /* ignore */ }
      this.sessions = this.sessions.filter(s => s.id !== sessionId)
      if (this.currentSession?.id === sessionId) {
        this.currentSession = null
        this.messages = []
      }
    },

    /** 发送消息（非流式，兼容性保留） */
    async sendMessage(message, workspaceId) {
      if (!message?.trim()) return
      if (!this.currentSession) this.newSession()

      const wid = (workspaceId && workspaceId > 0) ? workspaceId : 0

      this.messages.push({ role: 'user', content: message, timestamp: Date.now() })
      this.isLoading = true

      try {
        const res = await agentApi.chat({
          message,
          workspace_id: wid,
          session_id: this.currentSession.session_key
        })

        this.messages.push({
          role: 'assistant',
          content: res.reply || '',
          tool_calls: res.tool_calls || [],
          thinking: res.thinking || null,
          model_used: res.model_used,
          timestamp: Date.now()
        })

        // 刷新当前会话信息（后端已自动创建/更新）
        await this._refreshCurrentSession(wid)
      } catch (err) {
        this.messages.push({
          role: 'assistant',
          content: `❌ 抱歉，出错了：${err.message || '未知错误'}`,
          timestamp: Date.now(),
          error: true
        })
      } finally {
        this.isLoading = false
      }
    },

    /** 发送消息（SSE 流式，打字机效果） — 推荐用 */
    sendMessageStream(message, workspaceId) {
      if (!message?.trim()) return null
      if (!this.currentSession) this.newSession()

      const wid = (workspaceId && workspaceId > 0) ? workspaceId : 0

      this.messages.push({ role: 'user', content: message, timestamp: Date.now() })
      const assistantIdx = this.messages.length
      this.messages.push({
        role: 'assistant',
        content: '',
        tool_calls: [],
        timestamp: Date.now()
      })
      this.isLoading = true

      // 更新会话列表标题（乐观更新）
      const title = message.slice(0, 20) || '新对话'
      if (this.currentSession.title === '新对话') {
        this.currentSession.title = title
      }

      const controller = agentApi.streamChat(
        {
          message,
          workspace_id: wid,
          session_id: this.currentSession.session_key
        },
        {
          onToolCall: (toolCalls) => {
            this.messages[assistantIdx].tool_calls = toolCalls
          },
          onMessage: (chunk) => {
            this.messages[assistantIdx].content += chunk
          },
          onDone: async (meta) => {
            this.messages[assistantIdx].model_used = meta.model_used
            this.isLoading = false
            // 流式结束后刷新会话列表（后端已持久化）
            await this._refreshCurrentSession(wid)
          },
          onError: (err) => {
            if (!this.messages[assistantIdx].content) {
              this.messages[assistantIdx].content = `❌ 出错了：${err.message}`
            } else {
              this.messages[assistantIdx].content += `\n\n❌ 连接中断：${err.message}`
            }
            this.isLoading = false
          }
        }
      )

      return controller
    },

    /** 清空当前会话内存（不删后端 DB 记录） */
    clearCurrent() {
      this.currentSession = null
      this.messages = []
    },

    /** 切换 workspace 时重置会话状态，避免跨空间会话/消息混显 */
    resetForWorkspace(workspaceId = null) {
      this.currentSession = null
      this.messages = []
      return this.init(workspaceId)
    },

    /** 刷新当前会话（从后端拉最新 title / message_count / session_key） */
    async _refreshCurrentSession(workspaceId = null) {
      try {
        // 显式使用当前 workspace 过滤，避免拉回其它空间的会话
        const wid = (workspaceId && workspaceId > 0) ? workspaceId : 0
        const data = await agentApi.listSessions(wid)
        this.sessions = data.sessions || []

        // 用 session_key 匹配（前端 newSession 时生成的 key 后端会存）
        const key = this.currentSession?.session_key
        const matched = this.sessions.find(s => s.session_key === key)
        if (matched) {
          this.currentSession = matched
        } else if (this.sessions.length > 0) {
          // fallback: 拿最新的一条
          this.currentSession = this.sessions[0]
        }
      } catch { /* ignore */ }
    }
  }
})
