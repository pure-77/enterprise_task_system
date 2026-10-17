<template>
  <div class="agent-page">
    <!-- 左侧栏：深色主题（与系统 sidebar 一致） -->
    <aside class="agent-sidebar">
      <div class="sidebar-header">
        <div class="brand">
          <div class="brand-icon">✨</div>
          <div class="brand-text">
            <div class="brand-title">AI 助手</div>
            <div class="brand-sub">企业办公智能体</div>
          </div>
        </div>
      </div>

      <div class="sidebar-actions">
        <button class="new-chat-btn" @click="handleNewChat">
          <el-icon><Plus /></el-icon>
          新建对话
        </button>
      </div>

      <div class="sessions-list">
        <div
          v-for="s in store.sortedSessions"
          :key="s.id"
          class="session-item"
          :class="{ active: s.id === store.currentSession?.id }"
          @click="store.switchSession(s)"
        >
          <el-icon class="session-icon"><ChatLineRound /></el-icon>
          <span class="session-title">{{ s.title }}</span>
          <el-icon class="del-btn" @click.stop="handleDelete(s.id)"><Delete /></el-icon>
        </div>
        <div v-if="!store.sessions.length" class="empty-hint">
          还没有对话记录
        </div>
      </div>

      <div class="sidebar-footer">
        <div class="tools-info">
          <el-icon><Connection /></el-icon>
          <span>{{ store.toolGroups.length }} 个模块 · {{ store.tools.length }} 个工具</span>
        </div>
      </div>
    </aside>

    <!-- 右侧对话区：浅色主题（与系统主区一致） -->
    <main class="agent-main">
      <!-- 顶栏 -->
      <header class="chat-header">
        <div class="header-title">
          <span>智能对话</span>
        </div>
        <div class="header-right">
          <el-tooltip content="开发者模式：显示工具调用详情" placement="bottom">
            <button
              class="dev-toggle"
              :class="{ active: showToolCalls }"
              @click="toggleDevMode"
              title="开发者模式"
            >⚙️</button>
          </el-tooltip>
          <el-tag type="info" effect="light" round>
            <el-icon><MagicStick /></el-icon>
            {{ workspaceStore.currentWorkspace?.name || '个人模式' }}
          </el-tag>
        </div>
      </header>
      <div class="topbar-accent"></div>

      <!-- 消息区 -->
      <div class="messages-area" ref="messagesRef">
        <!-- 空状态 -->
        <div v-if="!store.messages.length" class="empty-state">
          <div class="empty-icon">🤖</div>
          <h3>你好，我是你的办公智能助手</h3>
          <p>可以帮你操作任务、日程、消息、考勤等 {{ store.tools.length }} 项能力</p>
          <div class="quick-prompts">
            <div v-for="p in quickPrompts" :key="p" class="prompt-chip" @click="sendQuick(p)">
              {{ p }}
            </div>
          </div>
        </div>

        <!-- 消息列表 -->
        <template v-else>
          <template v-for="(msg, idx) in store.messages" :key="idx">
          <div v-if="!isPendingAssistant(msg, idx)" class="message-row" :class="msg.role">
            <!-- 用户消息 -->
            <div v-if="msg.role === 'user'" class="msg-avatar user-avatar">
              <el-icon><User /></el-icon>
            </div>
            <div v-if="msg.role === 'user'" class="msg-bubble user-bubble">
              {{ msg.content }}
            </div>

            <!-- Agent 消息 -->
            <div v-if="msg.role === 'assistant'" class="msg-avatar agent-avatar">
              <span class="agent-emoji">🤖</span>
            </div>
            <div v-if="msg.role === 'assistant'" class="msg-bubble agent-bubble">
              <!-- 错误 -->
              <div v-if="msg.error" class="error-text">{{ msg.content }}</div>

              <!-- 正常回复 -->
              <template v-else>
                <!-- 任务规划确认卡片（产品级交互，所有用户可见，与开发者模式无关） -->
                <template v-for="pc in planCards(msg)" :key="`plan-${idx}-${pc.ti}`">
                  <div class="plan-card" :class="pc.plan.status">
                    <div class="plan-header">
                      <span class="plan-icon">🗺️</span>
                      <span class="plan-title">任务规划：{{ pc.plan.goal }}</span>
                    </div>

                    <!-- 待确认：可勾选清单 -->
                    <template v-if="pc.plan.status === 'pending'">
                      <div class="plan-items">
                        <label v-for="task in (pc.plan.tasks || [])" :key="task.index" class="plan-item">
                          <input
                            type="checkbox"
                            class="plan-checkbox"
                            :checked="isPlanItemChecked(`plan-${idx}-${pc.ti}`, task.index)"
                            :disabled="!!planBusy[`plan-${idx}-${pc.ti}`]"
                            @change="togglePlanItem(`plan-${idx}-${pc.ti}`, task.index, $event.target.checked)"
                          />
                          <span class="plan-item-main">
                            <span class="plan-item-title">{{ task.title }}</span>
                            <span class="plan-item-meta">
                              <span class="prio-tag" :class="task.priority">{{ priorityLabel(task.priority) }}</span>
                              <span v-if="task.deadline" class="meta-text">🕐 {{ task.deadline }}</span>
                              <span v-if="task.assignee_name" class="meta-text">👤 {{ task.assignee_name }}</span>
                            </span>
                            <span v-if="task.warning" class="plan-item-warn">⚠ {{ task.warning }}</span>
                          </span>
                        </label>
                      </div>
                      <div class="plan-actions">
                        <button
                          class="plan-btn primary"
                          :disabled="!!planBusy[`plan-${idx}-${pc.ti}`] || checkedCount(pc.plan, `plan-${idx}-${pc.ti}`) === 0"
                          @click="handleConfirmPlan(`plan-${idx}-${pc.ti}`, msg, pc.tc)"
                        >
                          {{ planBusy[`plan-${idx}-${pc.ti}`] === 'confirm' ? '创建中...' : `确认创建（${checkedCount(pc.plan, `plan-${idx}-${pc.ti}`)}）` }}
                        </button>
                        <button
                          class="plan-btn ghost"
                          :disabled="!!planBusy[`plan-${idx}-${pc.ti}`]"
                          @click="handleCancelPlan(`plan-${idx}-${pc.ti}`, pc.tc)"
                        >
                          {{ planBusy[`plan-${idx}-${pc.ti}`] === 'cancel' ? '取消中...' : '取消计划' }}
                        </button>
                        <span class="plan-hint">计划 30 分钟内有效，确认后才会创建任务</span>
                      </div>
                    </template>

                    <!-- 已确认：创建结果 -->
                    <template v-else-if="pc.plan.status === 'confirmed'">
                      <ul v-if="(pc.plan.created || []).length || (pc.plan.failed || []).length" class="plan-done-list">
                        <li v-for="t in (pc.plan.created || [])" :key="`c-${t.task_id}`" class="done ok">
                          ✅ 「{{ t.title }}」<a href="/task/detail" target="_blank" class="tc-link">#{{ t.task_id }}</a>
                        </li>
                        <li v-for="t in (pc.plan.failed || [])" :key="`f-${t.index}`" class="done fail">
                          ❌ 「{{ t.title }}」：{{ t.error }}
                        </li>
                      </ul>
                      <div v-else class="plan-final">该计划已确认，任务已创建（明细见下方汇总）</div>
                    </template>

                    <!-- 已取消 / 已过期 -->
                    <div v-else-if="pc.plan.status === 'cancelled'" class="plan-final cancelled">计划已取消，未创建任何任务</div>
                    <div v-else-if="pc.plan.status === 'expired'" class="plan-final expired">计划已过期（超过 30 分钟未确认），请重新让我规划</div>
                  </div>
                </template>

                <!-- 工具调用卡片（仅在开发者模式下显示，符合"不向用户暴露工具调用"的偏好） -->
                <div v-if="showToolCalls && msg.tool_calls?.length" class="tool-cards">
                  <div class="tool-cards-title">
                    <el-icon class="title-icon"><Connection /></el-icon>
                    <span>Agent 执行了 {{ msg.tool_calls.length }} 个操作</span>
                  </div>
                  <div
                    v-for="(tc, i) in msg.tool_calls"
                    :key="i"
                    class="tool-card"
                    :class="[
                      tc.success ? 'success' : 'fail',
                      (tc.meta?.danger_level || 'safe')
                    ]"
                  >
                    <div class="tool-card-header">
                      <span class="tc-icon">{{ tc.meta?.icon || '🔧' }}</span>
                      <span class="tc-action">{{ tc.meta?.action || tc.tool_name }}</span>
                      <span v-if="tc.meta?.danger_level === 'danger'" class="tc-danger-tag">⚠ 高风险</span>
                      <span v-else-if="tc.meta?.danger_level === 'warn'" class="tc-warn-tag">⚡ 有副作用</span>
                      <span class="tc-status">
                        <el-icon :size="14">
                          <CircleCheckFilled v-if="tc.success" />
                          <CircleCloseFilled v-else />
                        </el-icon>
                      </span>
                    </div>
                    <!-- 参数摘要 -->
                    <div v-if="parseToolArgs(tc)" class="tc-args">{{ parseToolArgs(tc) }}</div>
                    <!-- 结果摘要（可点击 ID） -->
                    <div v-if="formatToolResult(tc)" class="tc-result" v-html="formatToolResult(tc)"></div>
                    <!-- 开发者模式：原始 JSON -->
                    <div v-if="showToolCalls && tc.arguments && tc.arguments !== '{}'" class="tc-raw-args">
                      <details>
                        <summary>原始参数 JSON</summary>
                        <pre>{{ tc.arguments }}</pre>
                      </details>
                    </div>
                  </div>
                </div>
                <!-- Markdown 渲染 -->
                <div class="reply-content markdown-body" v-html="renderMd(msg.content)"></div>
                <!-- 模型标签 -->
                <div v-if="msg.model_used" class="model-tag">
                  {{ msg.model_used }}
                </div>
              </template>
            </div>
          </div>
          </template>

          <!-- 加载中：仅在没有流式内容时显示，避免与空气泡同时出现 -->
          <div v-if="showThinking" class="message-row assistant">
            <div class="msg-avatar agent-avatar"><span>🤖</span></div>
            <div class="msg-bubble agent-bubble loading">
              <div class="typing-dots">
                <span></span><span></span><span></span>
              </div>
              <div class="typing-text">正在思考...</div>
            </div>
          </div>
        </template>
      </div>

      <!-- 输入区 -->
      <footer class="input-area">
        <div class="input-wrapper">
          <el-input
            v-model="inputText"
            type="textarea"
            :autosize="{ minRows: 1, maxRows: 4 }"
            placeholder="自然语言操作办公系统... Enter 发送 · Shift+Enter 换行"
            @keydown.enter.exact.prevent="handleSend"
            :disabled="store.isLoading"
            resize="none"
            class="agent-input"
          />
          <el-tooltip :content="store.isLoading ? '正在思考...' : '发送'" placement="top">
            <button
              class="send-btn"
              :class="{ active: canSend }"
              :disabled="!canSend"
              @click="handleSend"
            >
              <el-icon :size="18"><Promotion /></el-icon>
            </button>
          </el-tooltip>
        </div>
      </footer>
    </main>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { useAgentStore } from '@/pinia/agentStore'
import { useWorkspaceStore } from '@/pinia/workspaceStore'
import { agentApi } from '@/api/agent'
import { renderMarkdown } from '@/utils/markdown'
import {
  ChatLineRound, Plus, Delete, Connection, CircleCheckFilled,
  CircleCloseFilled, Promotion, User, MagicStick
} from '@element-plus/icons-vue'

const store = useAgentStore()
const workspaceStore = useWorkspaceStore()
const inputText = ref('')
const messagesRef = ref(null)
// 流式请求控制器（可在用户点击"停止"时 abort）
const streamController = ref(null)
// 开发者模式：是否显示工具调用卡片（给开发者/调试用，默认关闭）
const showToolCalls = ref(localStorage.getItem('agent_dev_mode') === '1')

function toggleDevMode() {
  showToolCalls.value = !showToolCalls.value
  localStorage.setItem('agent_dev_mode', showToolCalls.value ? '1' : '0')
}

const canSend = computed(() => !store.isLoading && inputText.value.trim())

const quickPrompts = [
  '你好，你是谁？',
  '帮我创建一个任务【写周报】，明天下午6点截止',
  '帮我规划一下下周五的产品上线准备',
  '我今天和明天有什么会议？',
  '本月任务完成率多少？',
  '有多少未读通知？',
]

function renderMd(text) {
  return renderMarkdown(text)
}

/** 把 tool 参数解析成人类可读摘要 */
function parseToolArgs(tc) {
  if (!tc?.arguments) return null
  let args = tc.arguments
  // 历史会话里 arguments 可能是 string，新的是 dict
  if (typeof args === 'string') {
    try { args = JSON.parse(args) } catch { return args }
  }
  if (!args || typeof args !== 'object') return null
  if (Object.keys(args).length === 0) return null
  const tool = tc.tool_name || ''
  const highlights = []
  const pick = (key) => args[key] !== undefined && args[key] !== null && args[key] !== '' ? args[key] : null
  // 不同工具挑重点字段
  if (tool.includes('task')) {
    const t = pick('title'); if (t) highlights.push(`「${t}」`)
    const sid = pick('task_id'); if (sid) highlights.push(`#${sid}`)
    const st = pick('status'); if (st) highlights.push(`→ ${st}`)
    const did = pick('deadline'); if (did) highlights.push(`截止 ${did}`)
  } else if (tool.includes('file')) {
    const fid = pick('file_id'); if (fid) highlights.push(`#${fid}`)
    const fn = pick('name'); if (fn) highlights.push(`「${fn}」`)
    const kw = pick('keyword'); if (kw) highlights.push(`搜索「${kw}」`)
  } else if (tool.includes('approval')) {
    const iid = pick('instance_id'); if (iid) highlights.push(`#${iid}`)
    const tid = pick('template_id'); if (tid) highlights.push(`模板#${tid}`)
    const t = pick('title'); if (t) highlights.push(`「${t}」`)
    const c = pick('comment'); if (c) highlights.push(`备注: ${c}`)
  } else if (tool.includes('calendar')) {
    const t = pick('title') || pick('name'); if (t) highlights.push(`「${t}」`)
    const d = pick('start_time') || pick('date'); if (d) highlights.push(`时间 ${d}`)
  } else if (tool.includes('im')) {
    const r = pick('receiver_id') || pick('conversation_id'); if (r) highlights.push(`接收方#${r}`)
    const m = pick('message'); if (m) highlights.push(`"${String(m).slice(0, 30)}${String(m).length > 30 ? '...' : ''}"`)
  } else {
    Object.entries(args).forEach(([k, v]) => {
      if (v !== null && v !== undefined && v !== '' && highlights.length < 3) {
        highlights.push(`${k}=${typeof v === 'object' ? JSON.stringify(v).slice(0, 30) : v}`)
      }
    })
  }
  return highlights.length ? highlights.join('  ·  ') : null
}

/** HTML 转义：工具结果里会回显用户输入（如任务标题），避免 XSS 注入 */
function escapeHtml(str) {
  return String(str ?? '').replace(/[&<>"']/g, c => (
    { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]
  ))
}

/** 把 tool 结果解析成带可点击链接的 HTML */
function formatToolResult(tc) {
  if (!tc?.result) return null
  let obj = null
  try { obj = typeof tc.result === 'string' ? JSON.parse(tc.result) : tc.result }
  catch { return escapeHtml(tc.result) }
  if (!obj || typeof obj !== 'object') return escapeHtml(tc.result)

  const parts = []
  if (obj.message) parts.push(escapeHtml(obj.message))
  else if (obj.error) parts.push(`❌ ${escapeHtml(obj.error)}`)

  const linkMap = [
    { key: 'task_id',     label: '任务',   href: `/task/detail` },
    { key: 'file_id',     label: '文件',   href: `/files` },
    { key: 'instance_id', label: '审批',   href: `/approval` },
    { key: 'folder_id',   label: '文件夹', href: `/files` },
    { key: 'workspace_id',label: '空间',   href: `/workspace` },
  ]
  for (const m of linkMap) {
    if (obj[m.key] !== undefined && obj[m.key] !== null) {
      parts.push(`${m.label} <a href="${m.href}" target="_blank" class="tc-link">#${escapeHtml(obj[m.key])}</a>`)
    }
  }
  if (obj.total !== undefined && Array.isArray(obj.items)) {
    parts.push(`共 ${obj.total} 条`)
  }
  if (obj.count !== undefined && !obj.total) {
    parts.push(`共 ${obj.count} 条`)
  }
  return parts.length ? parts.join('  ·  ') : null
}

// ==================== 任务规划卡片（plan_tasks） ====================

const PRIORITY_LABELS = { low: '低', medium: '中', high: '高', urgent: '紧急' }
// 每张卡片的请求中状态：{ [cardKey]: 'confirm' | 'cancel' | null }
const planBusy = ref({})
// 勾选状态：{ [cardKey]: { [taskIndex]: boolean } }，未记录默认勾选
const planChecked = ref({})

function priorityLabel(p) {
  return PRIORITY_LABELS[p] || '中'
}

/** 从 tool_call 结果中解析计划对象，非 plan_tasks / 无 plan_id 返回 null */
function parsePlanCard(tc) {
  if (!tc || tc.tool_name !== 'plan_tasks' || !tc.result) return null
  let obj = null
  try {
    obj = typeof tc.result === 'string' ? JSON.parse(tc.result) : tc.result
  } catch { return null }
  if (!obj || typeof obj !== 'object' || !obj.plan_id) return null
  return obj
}

/** 提取一条 assistant 消息中的全部计划卡片 */
function planCards(msg) {
  return (msg.tool_calls || [])
    .map((tc, ti) => ({ tc, ti, plan: parsePlanCard(tc) }))
    .filter(x => x.plan)
}

/**
 * 判断是否为"等待首字"的流式占位消息。
 * 流式请求会先 push 一条空的 assistant 消息作为占位，此时应显示"正在思考"指示器，
 * 而不是把这个空消息渲染成一个空气泡（否则会出现两个回复框）。
 * 一旦内容到达、出现错误、或已有可视化卡片（规划卡片/开发者模式的工具卡片），就不再隐藏。
 */
function isThinkingMsg(msg) {
  return !!msg
    && msg.role === 'assistant'
    && !msg.content
    && !msg.error
    && planCards(msg).length === 0
    && !(showToolCalls.value && msg.tool_calls?.length)
}

/** 该气泡是否是需要隐藏的流式占位（仅针对最后一条消息） */
function isPendingAssistant(msg, idx) {
  return store.isLoading && idx === store.messages.length - 1 && isThinkingMsg(msg)
}

/** 是否显示"正在思考"加载行：加载中且最后一条消息尚未产出可见内容 */
const showThinking = computed(() => {
  if (!store.isLoading) return false
  const last = store.messages[store.messages.length - 1]
  // 非流式等待时最后一条是用户消息；流式等待时是空的助手占位消息
  return !last || last.role === 'user' || isThinkingMsg(last)
})

function isPlanItemChecked(cardKey, index) {
  const map = planChecked.value[cardKey]
  return map ? map[index] !== false : true
}

function togglePlanItem(cardKey, index, checked) {
  if (!planChecked.value[cardKey]) planChecked.value[cardKey] = {}
  planChecked.value[cardKey][index] = checked
}

function checkedCount(plan, cardKey) {
  return (plan.tasks || []).filter(t => isPlanItemChecked(cardKey, t.index)).length
}

/** 统一读取后端错误文案（约定 data.message || data.detail） */
function pickErrMsg(err, fallback = '操作失败，请稍后重试') {
  return err?.response?.data?.message || err?.response?.data?.detail || err?.message || fallback
}

/** 根据 409/404 错误文案把卡片就地同步为终态（刷新页面后点旧卡片的场景） */
function syncPlanTerminal(tc, plan, detail) {
  let next = null
  if (/已确认/.test(detail)) next = 'confirmed'
  else if (/已取消/.test(detail)) next = 'cancelled'
  else if (/过期|不存在/.test(detail)) next = 'expired'
  if (next) {
    tc.result = JSON.stringify({ ...plan, status: next, created: [], failed: [] })
    return true
  }
  return false
}

async function handleConfirmPlan(cardKey, msg, tc) {
  const plan = parsePlanCard(tc)
  if (!plan || planBusy.value[cardKey]) return
  const all = plan.tasks || []
  const indexes = all.map(t => t.index).filter(i => isPlanItemChecked(cardKey, i))
  if (!indexes.length) {
    ElMessage.warning('请至少勾选一个任务')
    return
  }
  planBusy.value[cardKey] = 'confirm'
  try {
    const res = await agentApi.confirmPlan(plan.plan_id, {
      session_id: store.currentSession?.session_key,
      // 全选时不传下标，后端按全量处理
      task_indexes: indexes.length === all.length ? undefined : indexes,
    })
    // 卡片就地切换为终态
    tc.result = JSON.stringify({
      ...plan,
      status: 'confirmed',
      created: res.created || [],
      failed: res.failed || [],
      created_count: res.created_count,
      failed_count: res.failed_count,
    })
    tc.success = res.success
    // 同步补一对本地消息（后端已持久化同样内容，刷新后历史一致）
    store.messages.push({ role: 'user', content: `📋 确认执行任务计划：${plan.goal}`, timestamp: Date.now() })
    store.messages.push({ role: 'assistant', content: res.summary, tool_calls: [], timestamp: Date.now() })
    ElMessage.success(res.failed_count
      ? `已创建 ${res.created_count} 个任务，${res.failed_count} 个失败`
      : `已创建 ${res.created_count} 个任务`)
    setTimeout(scrollToBottom, 50)
  } catch (err) {
    const detail = pickErrMsg(err)
    syncPlanTerminal(tc, plan, detail)
    ElMessage.error(detail)
  } finally {
    planBusy.value[cardKey] = null
  }
}

async function handleCancelPlan(cardKey, tc) {
  const plan = parsePlanCard(tc)
  if (!plan || planBusy.value[cardKey]) return
  planBusy.value[cardKey] = 'cancel'
  try {
    await agentApi.cancelPlan(plan.plan_id)
    tc.result = JSON.stringify({ ...plan, status: 'cancelled' })
  } catch (err) {
    const detail = pickErrMsg(err)
    syncPlanTerminal(tc, plan, detail)
    ElMessage.error(detail)
  } finally {
    planBusy.value[cardKey] = null
  }
}

async function handleSend() {
  if (!canSend.value) return
  const text = inputText.value.trim()
  inputText.value = ''
  // 优先用 SSE 流式（打字机效果），如果想退回非流式调 store.sendMessage
  streamController.value = store.sendMessageStream(text, workspaceStore.currentWorkspace?.id)
  // 滚动到底（流式逐字追加时 watch 会自动滚动）
  setTimeout(scrollToBottom, 100)
}

function sendQuick(text) {
  inputText.value = text
  handleSend()
}

function handleNewChat() {
  store.newSession()
}

function handleDelete(id) {
  store.deleteSession(id)
}

function scrollToBottom() {
  nextTick(() => {
    if (messagesRef.value) {
      messagesRef.value.scrollTop = messagesRef.value.scrollHeight
    }
  })
}

watch(() => store.messages.length, () => scrollToBottom())

// 记录 Agent 会话当前绑定的 workspace id。
// 注意：workspaceStore.currentWorkspaceId 初始是 null，由父布局 MainLayout 异步执行
// restoreWorkspaceContext() 才落定成具体 id。若直接拿它判断"是否切换空间"，首次加载时
// null→id 的落定会被误判为切换，从而把刚加载（或正在流式接收）的会话清空。
// 因此以 localStorage 中已保存的空间作为初始基准，只有真正变化时才重置。
const savedWs = localStorage.getItem('currentWorkspaceId')
const boundWsId = ref(savedWs ? parseInt(savedWs) : 0)

// 切换工作空间时重置会话与消息，避免跨空间混显
watch(() => workspaceStore.currentWorkspaceId, async (id) => {
  const wid = id || 0
  if (wid === boundWsId.value) return   // 首次加载的 id 落定，不是真正的切换
  boundWsId.value = wid
  await store.resetForWorkspace(wid)
})

onMounted(async () => {
  // 用已保存的空间初始化，避免先按个人模式加载再被重置
  await store.init(boundWsId.value)
})
</script>

<style scoped>
/* =============================================
   Agent 页面 — 完全匹配系统全局主题
   紫粉渐变主色 · 深色 sidebar · 浅色主区
   ============================================= */

.agent-page {
  display: flex;
  height: 100vh;
  background: var(--bg-page);
  overflow: hidden;
}

/* ========== 左侧栏 ========== */
.agent-sidebar {
  width: 260px;
  flex-shrink: 0;
  background: var(--bg-sidebar);
  color: #fff;
  display: flex;
  flex-direction: column;
  border-right: 1px solid rgba(255,255,255,0.04);
}

.sidebar-header {
  padding: 20px 16px 12px;
}

.brand {
  display: flex;
  align-items: center;
  gap: 10px;
}

.brand-icon {
  width: 36px; height: 36px;
  background: var(--primary-gradient);
  border-radius: var(--radius-md);
  display: flex; align-items: center; justify-content: center;
  font-size: 18px;
  flex-shrink: 0;
  box-shadow: 0 2px 8px rgba(124,58,237,0.4);
}

.brand-title {
  font-weight: 600;
  font-size: 15px;
  color: #fff;
  line-height: 1.2;
}

.brand-sub {
  font-size: 11px;
  color: rgba(255,255,255,0.45);
  margin-top: 2px;
}

.sidebar-actions {
  padding: 8px 12px 12px;
}

.new-chat-btn {
  width: 100%;
  display: flex; align-items: center; justify-content: center; gap: 6px;
  padding: 10px;
  border: 1px solid rgba(255,255,255,0.12);
  border-radius: var(--radius-sm);
  background: transparent;
  color: rgba(255,255,255,0.85);
  cursor: pointer;
  font-size: 13px;
  font-family: inherit;
  transition: all .2s;
}

.new-chat-btn:hover {
  background: var(--bg-sidebar-hover);
  border-color: var(--primary-color);
  color: #fff;
}

.sessions-list {
  flex: 1;
  overflow-y: auto;
  padding: 4px 8px;
}

.sessions-list::-webkit-scrollbar { width: 4px; }
.sessions-list::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.1); border-radius: 2px; }

.session-item {
  display: flex; align-items: center; gap: 8px;
  padding: 9px 10px;
  border-radius: var(--radius-sm);
  margin-bottom: 2px;
  cursor: pointer;
  font-size: 13px;
  color: rgba(255,255,255,0.7);
  transition: all .15s;
}

.session-item:hover {
  background: var(--bg-sidebar-hover);
  color: rgba(255,255,255,0.95);
}

.session-item.active {
  background: var(--bg-sidebar-active);
  color: #fff;
}

.session-icon { font-size: 14px; opacity: 0.7; flex-shrink: 0; }
.session-title { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.del-btn { opacity: 0; font-size: 13px; flex-shrink: 0; }
.session-item:hover .del-btn { opacity: 0.5; }
.session-item .del-btn:hover { opacity: 1; color: #fca5a5; }

.empty-hint {
  color: rgba(255,255,255,0.3);
  font-size: 12px;
  text-align: center;
  padding: 24px 12px;
}

.sidebar-footer {
  padding: 10px 16px;
  border-top: 1px solid rgba(255,255,255,0.05);
}

.tools-info {
  display: flex; align-items: center; gap: 6px;
  font-size: 11px;
  color: rgba(255,255,255,0.35);
}

/* ========== 主区 ========== */
.agent-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  background: var(--bg-page);
}

.chat-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 24px;
  background: var(--bg-primary);
  border-bottom: 1px solid var(--border-light);
}

.header-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
}

.header-right { display: flex; align-items: center; gap: 8px; }
.dev-toggle {
  background: transparent; border: none; cursor: pointer;
  font-size: 16px; padding: 4px 6px; border-radius: 6px;
  opacity: 0.4; transition: all .2s;
}
.dev-toggle:hover { opacity: 0.9; background: rgba(102,64,194,0.08); }
.dev-toggle.active { opacity: 1; background: rgba(102,64,194,0.12); }
.topbar-accent { height: 3px; background: var(--primary-gradient); flex-shrink: 0; }

/* ========== 消息区 ========== */
.messages-area {
  flex: 1;
  overflow-y: auto;
  padding: 28px 32px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.messages-area::-webkit-scrollbar { width: 6px; }
.messages-area::-webkit-scrollbar-thumb { background: var(--border-color); border-radius: 3px; }

/* 空状态 */
.empty-state {
  text-align: center;
  padding: 60px 20px;
  align-self: center;
}

.empty-icon {
  font-size: 56px;
  margin-bottom: 12px;
}

.empty-state h3 {
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 6px;
}

.empty-state p {
  color: var(--text-secondary);
  font-size: 13px;
  margin-bottom: 24px;
}

.quick-prompts {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: center;
  max-width: 560px;
}

.prompt-chip {
  padding: 7px 14px;
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: 999px;
  font-size: 12.5px;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all .2s;
}

.prompt-chip:hover {
  border-color: var(--primary-color);
  color: var(--primary-color);
  background: var(--primary-gradient-soft);
  transform: translateY(-1px);
}

/* 消息行 */
.message-row {
  display: flex;
  gap: 12px;
  max-width: 80%;
  animation: msgIn .25s ease;
}

@keyframes msgIn {
  from { opacity: 0; transform: translateY(6px); }
  to { opacity: 1; transform: translateY(0); }
}

.message-row.user { align-self: flex-end; flex-direction: row-reverse; }
.message-row.assistant { align-self: flex-start; }

/* 头像 */
.msg-avatar {
  width: 36px; height: 36px;
  border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: 16px;
  flex-shrink: 0;
}

.user-avatar {
  background: var(--primary-gradient);
  color: #fff;
}

.agent-avatar {
  background: var(--bg-tertiary);
  font-size: 20px;
}

/* 气泡 */
.msg-bubble {
  padding: 12px 16px;
  border-radius: var(--radius-md);
  font-size: 14px;
  line-height: 1.7;
  word-break: break-word;
}

.user-bubble {
  background: var(--primary-gradient);
  color: #fff;
  border-bottom-right-radius: 4px;
  box-shadow: 0 2px 8px rgba(124,58,237,0.25);
}

.agent-bubble {
  background: var(--bg-primary);
  color: var(--text-primary);
  border: 1px solid var(--border-light);
  border-bottom-left-radius: 4px;
  box-shadow: var(--shadow-sm);
  min-width: 200px;
}

/* 错误 */
.error-text { color: var(--error-color); }

/* 加载动画 */
.loading { display: flex; align-items: center; gap: 12px; padding: 14px 20px; }
.typing-dots { display: flex; gap: 4px; }
.typing-dots span {
  width: 7px; height: 7px; border-radius: 50%;
  background: var(--primary-color); opacity: 0.4;
  animation: dotBounce 1.4s infinite;
}
.typing-dots span:nth-child(2) { animation-delay: .2s; }
.typing-dots span:nth-child(3) { animation-delay: .4s; }
@keyframes dotBounce {
  0%, 80%, 100% { transform: scale(0.6); opacity: 0.4; }
  40% { transform: scale(1); opacity: 1; }
}
.typing-text { color: var(--text-light); font-size: 13px; }

/* ========== 工具调用卡片 ========== */
.tool-cards {
  margin-bottom: 12px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-light);
  border-radius: var(--radius-sm);
  padding: 10px 12px;
}

.tool-cards-title {
  display: flex; align-items: center; gap: 6px;
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary);
  margin-bottom: 8px;
}
.tool-cards-title .title-icon { color: var(--primary-color); }

.tool-card {
  padding: 8px 10px;
  border-radius: 6px;
  background: var(--bg-primary);
  margin-bottom: 6px;
  border-left: 3px solid var(--border-color);
  font-size: 12.5px;
  transition: all .15s;
}
.tool-card:last-child { margin-bottom: 0; }

/* danger_level 视觉 */
.tool-card.safe   { border-left-color: var(--success-color); }
.tool-card.warn   { border-left-color: #f59e0b; }
.tool-card.danger { border-left-color: var(--error-color); background: rgba(239,68,68,0.06); }

.tool-card.success.fail-override { border-left-color: var(--error-color); }

.tool-card-header {
  display: flex; align-items: center; gap: 8px;
}
.tc-icon { font-size: 15px; line-height: 1; }
.tc-action { font-weight: 600; color: var(--text-primary); }
.tc-status { margin-left: auto; display: flex; align-items: center; }
.tool-card.success .tc-status { color: var(--success-color); }
.tool-card.fail    .tc-status { color: var(--error-color); }

.tc-danger-tag {
  font-size: 10px;
  padding: 1px 6px;
  border-radius: 999px;
  background: rgba(239,68,68,0.12);
  color: var(--error-color);
  font-weight: 600;
}
.tc-warn-tag {
  font-size: 10px;
  padding: 1px 6px;
  border-radius: 999px;
  background: rgba(245,158,11,0.12);
  color: #d97706;
  font-weight: 600;
}

.tc-args {
  color: var(--text-secondary);
  margin-top: 4px;
  font-size: 11.5px;
}
.tc-result {
  color: var(--text-secondary);
  margin-top: 4px;
  padding: 6px 8px;
  background: var(--bg-secondary);
  border-radius: 4px;
  font-size: 11.5px;
  word-break: break-all;
}
.tool-card.fail .tc-result { color: var(--error-color); }

.tc-link {
  color: var(--primary-color);
  text-decoration: none;
  font-weight: 600;
}
.tc-link:hover { text-decoration: underline; }

.tc-raw-args {
  margin-top: 6px;
  font-size: 11px;
}
.tc-raw-args summary {
  color: var(--text-light);
  cursor: pointer;
  user-select: none;
}
.tc-raw-args pre {
  margin-top: 4px;
  padding: 6px 8px;
  background: var(--bg-secondary);
  border-radius: 4px;
  font-size: 10.5px;
  font-family: var(--font-mono);
  overflow-x: auto;
  max-height: 120px;
  overflow-y: auto;
}

/* ========== 任务规划卡片 ========== */
.plan-card {
  margin-bottom: 12px;
  border: 1px solid var(--border-color);
  border-left: 3px solid var(--primary-color);
  border-radius: var(--radius-sm);
  background: var(--primary-gradient-soft, rgba(124,58,237,0.05));
  padding: 12px 14px;
}
.plan-card.confirmed { border-left-color: var(--success-color); }
.plan-card.cancelled,
.plan-card.expired { border-left-color: var(--border-color); opacity: 0.75; }

.plan-header {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13.5px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 10px;
}
.plan-icon { font-size: 16px; }

.plan-items { display: flex; flex-direction: column; gap: 4px; }
.plan-item {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 7px 8px;
  border-radius: 6px;
  background: var(--bg-primary);
  border: 1px solid var(--border-light);
  cursor: pointer;
  transition: border-color .15s;
}
.plan-item:hover { border-color: var(--primary-color); }
.plan-checkbox {
  margin-top: 3px;
  width: 14px;
  height: 14px;
  accent-color: var(--primary-color);
  cursor: pointer;
  flex-shrink: 0;
}
.plan-item-main { display: flex; flex-direction: column; gap: 3px; min-width: 0; }
.plan-item-title { font-size: 13px; color: var(--text-primary); font-weight: 500; }
.plan-item-meta { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.meta-text { font-size: 11.5px; color: var(--text-light); }
.plan-item-warn { font-size: 11.5px; color: #d97706; }

.prio-tag {
  display: inline-block;
  font-size: 10.5px;
  padding: 0 6px;
  border-radius: 999px;
  line-height: 17px;
  font-weight: 600;
}
.prio-tag.low    { background: rgba(107,114,128,0.12); color: #6b7280; }
.prio-tag.medium { background: rgba(59,130,246,0.12);  color: #2563eb; }
.prio-tag.high   { background: rgba(245,158,11,0.14); color: #d97706; }
.prio-tag.urgent { background: rgba(239,68,68,0.14);  color: var(--error-color); }

.plan-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 10px;
  flex-wrap: wrap;
}
.plan-btn {
  padding: 6px 16px;
  border-radius: 6px;
  font-size: 12.5px;
  font-family: inherit;
  cursor: pointer;
  border: 1px solid transparent;
  transition: all .15s;
}
.plan-btn.primary {
  background: var(--primary-gradient);
  color: #fff;
  box-shadow: 0 2px 6px rgba(124,58,237,0.3);
}
.plan-btn.primary:hover:not(:disabled) { transform: translateY(-1px); }
.plan-btn.ghost {
  background: transparent;
  border-color: var(--border-color);
  color: var(--text-secondary);
}
.plan-btn.ghost:hover:not(:disabled) {
  border-color: var(--error-color);
  color: var(--error-color);
}
.plan-btn:disabled { opacity: 0.55; cursor: not-allowed; }
.plan-hint { font-size: 11.5px; color: var(--text-light); }

.plan-done-list { margin: 0; padding: 0; list-style: none; display: flex; flex-direction: column; gap: 5px; }
.plan-done-list .done { font-size: 12.5px; color: var(--text-secondary); }
.plan-done-list .done.ok { color: var(--success-color); }
.plan-done-list .done.fail { color: var(--error-color); }

.plan-final { font-size: 12.5px; color: var(--text-light); padding: 2px 0; }
.plan-final.expired { color: #d97706; }

/* ========== Markdown 渲染 ========== */
.reply-content { line-height: 1.7; }

.markdown-body :deep(h1),
.markdown-body :deep(h2),
.markdown-body :deep(h3) {
  margin: 12px 0 8px;
  font-weight: 600;
  color: var(--text-primary);
}
.markdown-body :deep(h1) { font-size: 16px; }
.markdown-body :deep(h2) { font-size: 15px; }
.markdown-body :deep(h3) { font-size: 14px; }

.markdown-body :deep(p) { margin: 6px 0; }

.markdown-body :deep(strong) { color: var(--primary-color); font-weight: 600; }
.markdown-body :deep(em) { color: var(--text-secondary); }

.markdown-body :deep(ul),
.markdown-body :deep(ol) {
  padding-left: 20px;
  margin: 6px 0;
}
.markdown-body :deep(li) { margin: 3px 0; }

.markdown-body :deep(a) { color: var(--primary-color); text-decoration: none; }
.markdown-body :deep(a:hover) { text-decoration: underline; }

.markdown-body :deep(code) {
  background: var(--bg-secondary);
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 12.5px;
  font-family: var(--font-mono);
  color: var(--primary-color);
}

.markdown-body :deep(pre) {
  background: #1F1A37;
  padding: 12px 14px;
  border-radius: var(--radius-sm);
  overflow-x: auto;
  margin: 8px 0;
}
.markdown-body :deep(pre code) {
  background: transparent;
  color: #E4DEF2;
  padding: 0;
  font-size: 12.5px;
}

.markdown-body :deep(blockquote) {
  border-left: 3px solid var(--primary-light);
  padding: 4px 12px;
  margin: 8px 0;
  color: var(--text-secondary);
  background: var(--primary-gradient-soft);
  border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
}

.markdown-body :deep(table) {
  border-collapse: collapse;
  width: 100%;
  margin: 10px 0;
  font-size: 13px;
}
.markdown-body :deep(th),
.markdown-body :deep(td) {
  border: 1px solid var(--border-color);
  padding: 8px 12px;
  text-align: left;
}
.markdown-body :deep(th) {
  background: var(--bg-secondary);
  font-weight: 600;
  color: var(--text-primary);
}

.model-tag {
  display: inline-block;
  margin-top: 10px;
  padding: 2px 10px;
  font-size: 11px;
  color: var(--text-light);
  background: var(--bg-secondary);
  border-radius: 999px;
}

/* ========== 输入区 ========== */
.input-area {
  padding: 16px 32px 24px;
  background: var(--bg-primary);
  border-top: 1px solid var(--border-light);
}

.input-wrapper {
  display: flex;
  align-items: flex-end;
  gap: 10px;
}

.input-wrapper :deep(.el-textarea__inner) {
  border-radius: var(--radius-md);
  border-color: var(--border-color);
  padding: 10px 14px 50px;
  background: var(--bg-page);
  font-family: inherit;
  font-size: 14px;
  resize: none;
  transition: all .25s;
}

.input-wrapper :deep(.el-textarea__inner:focus) {
  border-color: var(--primary-color);
  box-shadow: 0 0 0 3px rgba(124,58,237,0.15);
  background: var(--bg-primary);
}

.send-btn {
  width: 42px; height: 42px;
  border-radius: 50%;
  border: none;
  cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
  background: var(--border-color);
  color: #fff;
  transition: all .25s;
}

.send-btn.active {
  background: var(--primary-gradient);
  box-shadow: 0 2px 8px rgba(124,58,237,0.35);
}

.send-btn.active:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 14px rgba(124,58,237,0.5);
}

.send-btn:disabled { cursor: not-allowed; opacity: 0.6; }
</style>

<!-- highlight.js 主题（放在这是 scoped 里也要生效） -->
<style>
.hljs { background: #1F1A37 !important; padding: 12px 14px; border-radius: 8px; font-size: 12.5px; }
</style>
