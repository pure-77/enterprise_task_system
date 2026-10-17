<template>
  <div class="im-page">
    <!-- ============ 会话列表 ============ -->
    <div class="conv-panel">
      <div class="conv-header">
        <h3>消息</h3>
        <el-button type="primary" size="small" :icon="Plus" @click="showCreate = true">新建</el-button>
      </div>

      <!-- 搜索框 -->
      <div class="conv-search">
        <el-input v-model="searchKey" placeholder="搜索会话" :prefix-icon="Search" clearable size="small" />
      </div>

      <div class="conv-list" v-loading="convLoading">
        <div
          v-for="c in filteredConversations"
          :key="c.id"
          :class="['conv-item', { active: activeConv === c.id }]"
          @click="openConv(c)"
        >
          <el-avatar :size="40" :src="appendToken(c.avatar)">{{ c.name?.[0] || '#' }}</el-avatar>
          <div class="conv-info">
            <div class="conv-name">{{ c.name || '单聊' }}</div>
            <div class="conv-preview">
              {{ c.last_message ? (c.last_message.sender_name + ': ' + formatPreview(c.last_message)) : '暂无消息' }}
            </div>
          </div>
          <el-badge v-if="c.unread_count > 0" :value="c.unread_count" :max="99" class="conv-badge" />
        </div>
        <el-empty v-if="!convLoading && filteredConversations.length === 0" description="暂无会话" :image-size="60" />
      </div>
    </div>

    <!-- ============ 聊天窗口 ============ -->
    <div class="chat-panel" v-if="activeConv">
      <div class="chat-header">
        <div class="chat-title-wrap">
          <span class="chat-title">{{ activeConvName }}</span>
          <span v-if="activeConvType" class="chat-type">{{ activeConvType }}</span>
        </div>
        <div class="chat-actions">
          <el-tooltip content="成员列表" placement="bottom">
            <el-button text :icon="User" @click="showMembers = !showMembers" />
          </el-tooltip>
        </div>
      </div>

      <div class="chat-messages" ref="msgBox" @scroll="onScroll">
        <div v-if="loadingMore" class="loading-more">加载中...</div>
        <template v-for="(m, idx) in messages" :key="m.id">
          <!-- 日期分隔符 -->
          <div v-if="shouldShowDateDivider(idx)" class="date-divider">
            {{ formatDateDivider(m.created_at) }}
          </div>
          <div
            :class="['msg-row', { mine: m.sender_id === currentUserId }]"
            @contextmenu.prevent="showContextMenu($event, m)"
          >
            <el-avatar :size="32" :src="appendToken(m.sender_avatar)">{{ m.sender_name?.[0] }}</el-avatar>
            <div class="msg-bubble">
              <div class="msg-sender" v-if="m.sender_id !== currentUserId">{{ m.sender_name }}</div>
              <!-- 撤回消息显示 -->
              <div v-if="m.is_recalled" class="msg-recalled">
                <span v-if="m.sender_id === currentUserId">你撤回了一条消息</span>
                <span v-else>对方撤回了一条消息</span>
              </div>
              <!-- 正常消息内容 -->
              <div v-else>
                <!-- 根据有效类型渲染消息 -->
                <!-- 图片消息 -->
                <div v-if="getEffectiveType(m) === 'image'" class="msg-image" @click="previewImage(m)">
                  <img :src="appendToken(getMsgUrl(m))" alt="image" />
                </div>
                <!-- 文件消息 -->
                <div v-else-if="getEffectiveType(m) === 'file'" class="msg-file" @click="openFile(m)">
                  <el-icon :size="32" class="file-icon"><Document /></el-icon>
                  <div class="file-info">
                    <div class="file-name">{{ parseMsgContent(m.content).name || '文件' }}</div>
                    <div class="file-size">{{ formatSize(parseMsgContent(m.content).size) }}</div>
                  </div>
                </div>
                <!-- 文本消息 -->
                <div v-else class="msg-text">{{ m.content }}</div>
              </div>
              <div class="msg-time">{{ formatMsgTime(m.created_at) }}</div>
              <!-- 已读状态 -->
              <div v-if="m.sender_id === currentUserId && !m.is_recalled" class="msg-read">
                <!-- 单聊：只显示对方已读 -->
                <template v-if="activeConvType === '单聊'">
                  <span v-if="m.read_count > 0">
                    <el-icon :size="12"><CircleCheck /></el-icon> 已读
                  </span>
                </template>
                <!-- 群聊：显示已读人数 -->
                <template v-else>
                  <span v-if="m.read_count > 0">
                    <el-icon :size="12"><CircleCheck /></el-icon> 已读 {{ m.read_count }}人
                  </span>
                </template>
              </div>
            </div>
          </div>
        </template>
        <el-empty v-if="messages.length === 0" description="暂无消息，发送第一条消息吧" :image-size="80" />
      </div>

      <div class="chat-input">
        <div class="input-actions">
          <el-tooltip content="发送图片" placement="top">
            <el-button circle :icon="Picture" @click="triggerUpload('image')" :disabled="sending" />
          </el-tooltip>
          <el-tooltip content="发送文件" placement="top">
            <el-button circle :icon="FolderOpened" @click="triggerUpload('file')" :disabled="sending" />
          </el-tooltip>
          <input ref="imageInputRef" type="file" accept="image/*" style="display:none" @change="handleFileSelect($event, 'image')" />
          <input ref="fileInputRef" type="file" style="display:none" @change="handleFileSelect($event, 'file')" />
        </div>
        <el-input
          v-model="inputMsg"
          placeholder="输入消息，回车发送"
          @keyup.enter="sendMsg"
          :disabled="sending"
          type="textarea"
          :autosize="{ minRows: 1, maxRows: 4 }"
          resize="none"
        />
        <el-button type="primary" @click="sendMsg" :loading="sending" :icon="Promotion" :disabled="!inputMsg.trim()">发送</el-button>
      </div>
    </div>

    <div class="chat-placeholder" v-else>
      <el-empty description="选择会话开始聊天，或点击新建发起对话" :image-size="120" />
    </div>

    <!-- ============ 创建会话弹窗（含成员列表） ============ -->
    <el-dialog v-model="showCreate" title="发起对话" width="520px">
      <el-tabs v-model="createType">
        <el-tab-pane label="单聊（选择成员）" name="single">
          <div class="member-pick-list" v-loading="membersLoading">
            <el-input v-model="memberSearch" placeholder="搜索成员" :prefix-icon="Search" clearable size="small" style="margin-bottom: 12px" />
            <div
              v-for="m in filteredMembers"
              :key="m.user_id"
              class="member-pick-item"
              @click="startSingleChat(m)"
            >
              <el-avatar :size="36" :src="appendToken(m.avatar)">{{ (m.nickname || m.real_name || '?')[0] }}</el-avatar>
              <div class="member-info">
                <div class="member-name">{{ m.nickname || m.real_name || '未命名' }}</div>
                <div class="member-sub">{{ m.role || '成员' }}{{ m.department_name ? ' · ' + m.department_name : '' }}</div>
              </div>
              <el-icon class="member-arrow"><ArrowRight /></el-icon>
            </div>
            <el-empty v-if="!membersLoading && filteredMembers.length === 0" description="暂无可选成员" :image-size="60" />
          </div>
        </el-tab-pane>

        <el-tab-pane label="创建群聊" name="group">
          <el-form label-width="80px">
            <el-form-item label="群名称">
              <el-input v-model="createName" placeholder="请输入群聊名称" />
            </el-form-item>
            <el-form-item label="群成员">
              <div class="member-pick-list compact">
                <el-checkbox-group v-model="selectedMemberIds">
                  <el-checkbox
                    v-for="m in filteredMembers"
                    :key="m.user_id"
                    :value="m.user_id"
                    class="member-checkbox"
                  >
                    {{ m.nickname || m.real_name || '未命名' }}
                  </el-checkbox>
                </el-checkbox-group>
                <el-empty v-if="filteredMembers.length === 0" description="暂无成员" :image-size="60" />
              </div>
            </el-form-item>
          </el-form>
        </el-tab-pane>
      </el-tabs>

      <template #footer v-if="createType === 'group'">
        <el-button @click="showCreate = false">取消</el-button>
        <el-button type="primary" @click="createGroup" :loading="creating" :disabled="!createName.trim()">创建群聊</el-button>
      </template>
    </el-dialog>

    <!-- ============ 会话成员抽屉 ============ -->
    <el-drawer v-model="showMembers" title="成员列表" direction="rtl" size="320px">
      <div class="member-drawer-list">
        <div v-for="m in convMembers" :key="m.id" class="member-drawer-item">
          <el-avatar :size="36" :src="appendToken(m.avatar)">{{ (m.nickname || '?')[0] }}</el-avatar>
          <div class="member-info">
            <div class="member-name">{{ m.nickname || '未命名' }}</div>
            <div class="member-sub">{{ m.role || '成员' }}</div>
          </div>
        </div>
        <el-empty v-if="convMembers.length === 0" description="暂无成员" :image-size="60" />
      </div>
    </el-drawer>

    <!-- ============ 图片预览 ============ -->
    <el-dialog v-model="showImagePreview" width="auto" align-center :show-close="true" :close-on-click-modal="true">
      <img :src="previewImageUrl" class="preview-image" @click="showImagePreview = false" />
    </el-dialog>

    <!-- ============ 右键菜单 ============ -->
    <div
      v-if="contextMenu.visible"
      class="context-menu"
      :style="{ left: contextMenu.x + 'px', top: contextMenu.y + 'px' }"
      @click.stop
    >
      <div class="context-menu-item" @click="handleRecall">
        <el-icon><Delete /></el-icon>
        <span>撤回</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Promotion, Plus, Search, User, ArrowRight, Picture, FolderOpened, Document, CircleCheck, Delete } from '@element-plus/icons-vue'
import { imApi } from '@/api/im'
import { workspaceApi } from '@/api/workspace'
import { useWorkspaceStore } from '@/pinia/workspaceStore'
import { useUserStore } from '@/pinia/userStore'
import { formatChatTime, formatTime } from '@/utils/format'
import { appendToken } from '@/utils/auth'

const wsStore = useWorkspaceStore()
const userStore = useUserStore()
const currentUserId = ref(userStore.userInfo?.id)

// ====== 会话列表 ======
const conversations = ref([])
const convLoading = ref(false)
const searchKey = ref('')

const filteredConversations = computed(() => {
  if (!searchKey.value.trim()) return conversations.value
  const k = searchKey.value.toLowerCase()
  return conversations.value.filter(c =>
    (c.name || '').toLowerCase().includes(k) ||
    (c.last_message?.content || '').toLowerCase().includes(k)
  )
})

// ====== 当前会话 ======
const activeConv = ref(null)
const activeConvName = ref('')
const activeConvType = ref('')
const messages = ref([])
const inputMsg = ref('')
const sending = ref(false)
const msgBox = ref(null)

// ====== 创建会话 ======
const showCreate = ref(false)
const createType = ref('single')
const createName = ref('')
const creating = ref(false)
const members = ref([])
const membersLoading = ref(false)
const memberSearch = ref('')
const selectedMemberIds = ref([])

const filteredMembers = computed(() => {
  const k = memberSearch.value.trim().toLowerCase()
  if (!k) return members.value
  return members.value.filter(m =>
    (m.nickname || '').toLowerCase().includes(k) ||
    (m.real_name || '').toLowerCase().includes(k)
  )
})

// ====== 会话成员抽屉 ======
const showMembers = ref(false)
const convMembers = ref([])

// ====== 右键菜单 ======
const contextMenu = ref({
  visible: false,
  x: 0,
  y: 0,
  message: null
})

function showContextMenu(event, msg) {
  // 只有自己发送的消息且在2分钟内才显示撤回选项
  if (msg.sender_id === currentUserId.value && !msg.is_recalled && canRecall(msg)) {
    contextMenu.value = {
      visible: true,
      x: event.clientX,
      y: event.clientY,
      message: msg
    }
  }
}

function hideContextMenu() {
  contextMenu.value.visible = false
  contextMenu.value.message = null
}

async function handleRecall() {
  if (!contextMenu.value.message) return
  await recallMessage(contextMenu.value.message)
  hideContextMenu()
}

// 点击其他地方关闭菜单
function handleClickOutside() {
  if (contextMenu.value.visible) {
    hideContextMenu()
  }
}

// ====== 文件上传相关 ======
const imageInputRef = ref(null)
const fileInputRef = ref(null)
const showImagePreview = ref(false)
const previewImageUrl = ref('')

function triggerUpload(type) {
  if (type === 'image') {
    imageInputRef.value?.click()
  } else {
    fileInputRef.value?.click()
  }
}

function handleFileSelect(event, type) {
  const file = event.target.files?.[0]
  if (!file) return
  event.target.value = ''
  uploadAndSend(file, type)
}

// 解析消息内容 — 仅当 JSON 解析成功且包含 url 字段时才视为文件/图片
function parseMsgContent(content) {
  try {
    const parsed = JSON.parse(content)
    if (parsed && typeof parsed === 'object' && parsed.url) {
      return parsed
    }
    return null
  } catch {
    return null
  }
}

function formatSize(bytes) {
  if (!bytes) return '0 B'
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / 1048576).toFixed(2) + ' MB'
}

// 判断消息的有效类型 — 优先用 msg_type，不匹配时从内容推断
function getEffectiveType(m) {
  const rawType = (m.msg_type || '').toLowerCase()
  if (rawType === 'image') return 'image'
  if (rawType === 'file') return 'file'
  // msg_type 不匹配时，检查内容是否为包含 url 的 JSON
  const parsed = parseMsgContent(m.content)
  if (parsed && parsed.url) {
    const ext = (parsed.url.split('.').pop() || '').toLowerCase()
    const imageExts = ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp', 'svg', 'ico']
    if (imageExts.includes(ext)) return 'image'
    return 'file'
  }
  return 'text'
}

// 获取消息中的文件URL
function getMsgUrl(m) {
  const parsed = parseMsgContent(m.content)
  return parsed ? parsed.url : m.content
}

// 格式化会话列表中的预览消息
function formatPreview(msg) {
  if (!msg) return ''
  const type = (msg.msg_type || '').toLowerCase()
  if (type === 'image') return '[图片]'
  if (type === 'file') return '[文件]'
  // 检查内容是否为包含 url 的 JSON
  const parsed = parseMsgContent(msg.content || '')
  if (parsed && parsed.url) {
    const ext = (parsed.url.split('.').pop() || '').toLowerCase()
    const imageExts = ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp', 'svg', 'ico']
    return imageExts.includes(ext) ? '[图片]' : '[文件]'
  }
  return msg.content || ''
}

function previewImage(msg) {
  const url = appendToken(getMsgUrl(msg))
  previewImageUrl.value = url
  showImagePreview.value = true
}

function openFile(msg) {
  const url = appendToken(getMsgUrl(msg))
  window.open(url, '_blank')
}

async function uploadAndSend(file, type) {
  if (!activeConv.value) {
    ElMessage.warning('请先选择会话')
    return
  }
  sending.value = true
  try {
    const res = await imApi.uploadFile(wsStore.currentWorkspaceId, file)
    const contentData = {
      url: res.url,
      name: res.name,
      size: res.size,
      mime_type: res.mime_type,
    }
    const msgType = res.msg_type || type
    const msg = await imApi.sendMessage(activeConv.value, {
      content: JSON.stringify(contentData),
      msg_type: msgType,
    })
    messages.value.push(msg)
    await nextTick()
    scrollToBottom()

    const conv = conversations.value.find(c => c.id === activeConv.value)
    if (conv) {
      conv.last_message = {
        content: msgType === 'image' ? '[图片]' : '[文件]',
        sender_name: msg.sender_name,
        created_at: msg.created_at,
        msg_type: msgType,
      }
      conv.last_message_at = msg.created_at
    }
    ElMessage.success(type === 'image' ? '图片已发送' : '文件已发送')
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || '上传失败')
  } finally {
    sending.value = false
  }
}

// ====== 分页加载 ======
const loadingMore = ref(false)
const hasMore = ref(true)
const oldestMsgId = ref(null)

function formatMsgTime(t) {
  if (!t) return ''
  return formatChatTime(t)
}

// 判断是否需要显示日期分隔符
function shouldShowDateDivider(idx) {
  if (idx === 0) return true
  const current = messages.value[idx]
  const prev = messages.value[idx - 1]
  if (!current || !prev) return false

  const curDate = formatTime(current.created_at).split(' ')[0]
  const prevDate = formatTime(prev.created_at).split(' ')[0]
  return curDate !== prevDate
}

// 格式化日期分隔符
function formatDateDivider(t) {
  if (!t) return ''
  const result = formatTime(t)
  const [datePart] = result.split(' ')
  const [year, month, day] = datePart.split('-').map(Number)

  const now = new Date()
  const msgDate = new Date(year, month - 1, day)

  const todayStart = new Date(now.getFullYear(), now.getMonth(), now.getDate())
  const yesterdayStart = new Date(todayStart)
  yesterdayStart.setDate(yesterdayStart.getDate() - 1)

  const pad = (n) => String(n).padStart(2, '0')

  if (msgDate.getTime() === todayStart.getTime()) {
    return '今天'
  }
  if (msgDate.getTime() === yesterdayStart.getTime()) {
    return '昨天'
  }
  if (year === now.getFullYear()) {
    return `${pad(month)}月${pad(day)}日`
  }
  return `${year}年${pad(month)}月${pad(day)}日`
}

// ====== 加载会话列表 ======
async function loadConvs() {
  if (!wsStore.currentWorkspaceId) return
  convLoading.value = true
  try {
    const res = await imApi.getConversations(wsStore.currentWorkspaceId)
    conversations.value = res || []
  } catch (e) {
    console.error('加载会话失败', e)
  } finally { convLoading.value = false }
}

// ====== 加载工作区成员（用于新建会话） ======
async function loadMembers() {
  if (!wsStore.currentWorkspaceId) return
  membersLoading.value = true
  try {
    const res = await workspaceApi.getMembers(wsStore.currentWorkspaceId)
    // 排除自己
    members.value = (res.items || res || []).filter(m => m.user_id !== currentUserId.value)
  } catch (e) {
    console.error('加载成员失败', e)
  } finally { membersLoading.value = false }
}

// ====== 打开会话 ======
async function openConv(c) {
  // 如果点击的是当前已打开的会话，则关闭聊天框
  if (activeConv.value === c.id) {
    activeConv.value = null
    activeConvName.value = ''
    activeConvType.value = ''
    messages.value = []
    return
  }

  // 否则打开新会话
  activeConv.value = c.id
  activeConvName.value = c.name || (c.type === 'single' ? '私聊' : '群聊')
  activeConvType.value = c.type === 'group' ? '群聊' : '单聊'
  messages.value = []
  hasMore.value = true
  oldestMsgId.value = null
  showMembers.value = false

  await loadMessages()
  await markConvRead(c.id)
}

// ====== 加载消息 ======
async function loadMessages() {
  if (!activeConv.value) return
  try {
    const res = await imApi.getMessages(activeConv.value, { page: 1, page_size: 50 })
    const data = res || {}
    messages.value = data.items || []
    hasMore.value = data.has_more !== false
    if (data.oldest_id) oldestMsgId.value = data.oldest_id
    await nextTick()
    scrollToBottom()
  } catch (e) {
    console.error('加载消息失败', e)
  }
}

// ====== 滚动到顶部加载更多 ======
async function onScroll() {
  const box = msgBox.value
  if (!box || loadingMore.value || !hasMore.value || !oldestMsgId.value) return
  // 滚动到顶部时加载更多
  if (box.scrollTop < 50) {
    loadingMore.value = true
    const oldScrollHeight = box.scrollHeight
    try {
      const res = await imApi.getMessages(activeConv.value, {
        page: 1,
        page_size: 50,
        before_id: oldestMsgId.value
      })
      const items = res?.items || []
      if (items.length === 0) {
        hasMore.value = false
      } else {
        messages.value = [...items, ...messages.value]
        hasMore.value = res.has_more !== false
        if (res.oldest_id) oldestMsgId.value = res.oldest_id
        await nextTick()
        // 保持滚动位置
        box.scrollTop = box.scrollHeight - oldScrollHeight
      }
    } catch (e) {
      // 加载失败不重置游标，允许重试
    } finally { loadingMore.value = false }
  }
}

function scrollToBottom() {
  const box = msgBox.value
  if (box) box.scrollTop = box.scrollHeight
}

// ====== 消息撤回 ======
function canRecall(msg) {
  if (!msg.created_at) return false
  const msgTime = new Date(msg.created_at).getTime()
  const now = Date.now()
  return (now - msgTime) < 2 * 60 * 1000 // 2分钟内可撤回
}

async function recallMessage(msg) {
  try {
    await imApi.recallMessage(msg.id)
    // 更新本地消息状态
    msg.is_recalled = true
    msg.content = '消息已撤回'
    ElMessage.success('消息已撤回')
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || '撤回失败')
  }
}

// ====== 标记会话已读（只标记接收到的消息） ======
async function markConvRead(convId) {
  try {
    // 获取当前会话中接收到的消息ID（不包括自己发送的）
    const receivedMsgIds = messages.value
      .filter(m => m.sender_id !== currentUserId.value && !m.is_recalled)
      .map(m => m.id)

    if (receivedMsgIds.length === 0) return

    await imApi.markRead(convId, { message_ids: receivedMsgIds })
    // 立即更新本地未读数
    const conv = conversations.value.find(c => c.id === convId)
    if (conv) conv.unread_count = 0
  } catch (e) {
    console.error('标记已读失败', e)
  }
}

// ====== 发送消息 ======
async function sendMsg() {
  const content = inputMsg.value.trim()
  if (!content || !activeConv.value) return
  sending.value = true
  try {
    const res = await imApi.sendMessage(activeConv.value, {
      content,
      msg_type: 'text'
    })
    const msg = res
    messages.value.push(msg)
    inputMsg.value = ''
    await nextTick()
    scrollToBottom()

    // 更新会话列表中最后一条消息
    const conv = conversations.value.find(c => c.id === activeConv.value)
    if (conv) {
      conv.last_message = {
        content: msg.content,
        sender_name: msg.sender_name,
        created_at: msg.created_at
      }
      conv.last_message_at = msg.created_at
    }
  } catch (e) {
    ElMessage.error('发送失败')
  } finally { sending.value = false }
}

// ====== 发起单聊 ======
async function startSingleChat(member) {
  creating.value = true
  try {
    const res = await imApi.createConversation({
      workspace_id: wsStore.currentWorkspaceId,
      type: 'single',
      peer_id: member.user_id
    })
    showCreate.value = false
    ElMessage.success('会话已创建')
    await loadConvs()
    // 直接打开新会话
    const newConv = conversations.value.find(c => c.id === res.id)
    if (newConv) await openConv(newConv)
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || '创建会话失败')
  } finally { creating.value = false }
}

// ====== 创建群聊 ======
async function createGroup() {
  if (!createName.value.trim()) {
    ElMessage.warning('请输入群聊名称')
    return
  }
  if (selectedMemberIds.value.length === 0) {
    ElMessage.warning('请至少选择一位成员')
    return
  }
  creating.value = true
  try {
    const res = await imApi.createConversation({
      workspace_id: wsStore.currentWorkspaceId,
      type: 'group',
      name: createName.value,
      member_ids: selectedMemberIds.value
    })
    showCreate.value = false
    createName.value = ''
    selectedMemberIds.value = []
    ElMessage.success('群聊已创建')
    await loadConvs()
    const newConv = conversations.value.find(c => c.id === res.id)
    if (newConv) await openConv(newConv)
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || '创建群聊失败')
  } finally { creating.value = false }
}

// ====== 加载会话成员（用于抽屉显示） ======
async function loadConvMembers() {
  if (!activeConv.value) return
  try {
    const res = await imApi.getConversation(activeConv.value)
    convMembers.value = res.members || []
  } catch (e) {
    console.error('加载会话成员失败', e)
  }
}

watch(showMembers, (v) => {
  if (v) loadConvMembers()
})

// 切换工作空间时重新加载
watch(() => wsStore.currentWorkspaceId, () => {
  activeConv.value = null
  messages.value = []
  loadConvs()
  loadMembers()
})

// ====== WebSocket 实时消息 ======
function handleWsMessage(msg) {
  if (!msg) return

  // 处理撤回消息
  if (msg.is_recalled) {
    const existingMsg = messages.value.find(m => m.id === msg.id)
    if (existingMsg) {
      existingMsg.is_recalled = true
      existingMsg.content = '消息已撤回'
    }
    return
  }

  // 过滤自己发的消息（已通过 API 响应添加）
  if (msg.sender_id === currentUserId.value) return

  const convId = msg.conversation_id
  if (!convId) return

  if (convId === activeConv.value) {
    // 当前会话：追加消息
    const exists = messages.value.some(m => m.id === msg.id)
    if (!exists) {
      messages.value.push(msg)
      nextTick(() => scrollToBottom())
      // 不再自动标记已读，等待用户手动标记
    }
  }

  // 更新会话列表
  const conv = conversations.value.find(c => c.id === convId)
  if (conv) {
    conv.last_message = {
      content: msg.content,
      sender_name: msg.sender_name,
      created_at: msg.created_at,
      msg_type: msg.msg_type,
    }
    conv.last_message_at = msg.created_at
    // 非当前会话增加未读数
    if (convId !== activeConv.value) {
      conv.unread_count = (conv.unread_count || 0) + 1
    }
  } else {
    // 新会话，刷新列表
    loadConvs()
  }
}

function handleWsRead(data) {
  if (!data) return
  // 更新消息的已读状态
  const msgIds = data.message_ids || []
  const readerId = data.reader_id

  // 忽略自己标记的已读（只有对方的已读才需要显示）
  if (readerId === currentUserId.value) return

  msgIds.forEach(id => {
    const msg = messages.value.find(m => m.id === id)
    if (msg) {
      // 单聊：如果对方已读，设置 read_count 为1
      // 群聊：增加已读人数
      if (activeConvType.value === '单聊') {
        // 单聊时，只要收到对方的已读推送，就表示对方已读
        msg.read_count = 1
      } else {
        // 群聊时，增加已读人数（避免重复计数）
        if (!msg.read_users) {
          msg.read_users = new Set()
        }
        if (!msg.read_users.has(readerId)) {
          msg.read_users.add(readerId)
          msg.read_count = msg.read_users.size
        }
      }
    }
  })
}

onMounted(() => {
  loadConvs()
  loadMembers()
  // 监听 WebSocket 推送
  window.addEventListener('ws:im_message', (e) => handleWsMessage(e.detail))
  window.addEventListener('ws:im_read', (e) => handleWsRead(e.detail))
  // 监听点击事件关闭右键菜单
  document.addEventListener('click', handleClickOutside)
})

onUnmounted(() => {
  window.removeEventListener('ws:im_message', handleWsMessage)
  window.removeEventListener('ws:im_read', handleWsRead)
  document.removeEventListener('click', handleClickOutside)
})
</script>

<style scoped>
.im-page {
  display: flex;
  height: calc(100vh - 64px);
  margin: -24px;
  background: var(--bg-page);
}

/* ====== 会话列表 ====== */
.conv-panel {
  width: 300px;
  background: var(--bg-primary);
  border-right: 1px solid var(--border-light);
  display: flex;
  flex-direction: column;
}
.conv-header {
  padding: 16px;
  border-bottom: 1px solid var(--border-light);
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.conv-header h3 { margin: 0; font-size: 16px; font-weight: 700; }
.conv-search { padding: 8px 12px; border-bottom: 1px solid var(--border-light); }
.conv-list { flex: 1; overflow-y: auto; }
.conv-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  cursor: pointer;
  transition: background 0.2s;
  border-bottom: 1px solid var(--border-light);
}
.conv-item:hover { background: var(--bg-secondary); }
.conv-item.active { background: var(--primary-gradient-soft); }
.conv-info { flex: 1; min-width: 0; }
.conv-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.conv-preview {
  font-size: 12px;
  color: var(--text-light);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  margin-top: 2px;
}
.conv-badge { margin-left: 8px; }

/* ====== 聊天窗口 ====== */
.chat-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: var(--bg-primary);
  min-width: 0;
}
.chat-placeholder {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-primary);
}

.chat-header {
  padding: 14px 20px;
  border-bottom: 1px solid var(--border-light);
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.chat-title-wrap { display: flex; align-items: center; gap: 8px; }
.chat-title { font-size: 16px; font-weight: 700; }
.chat-type {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 4px;
  background: var(--bg-tertiary);
  color: var(--text-secondary);
}
.chat-actions { color: var(--text-secondary); }

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 16px 20px;
  display: flex;
  flex-direction: column;
}
.loading-more {
  text-align: center;
  font-size: 12px;
  color: var(--text-light);
  padding: 8px;
}

/* 日期分隔符 */
.date-divider {
  text-align: center;
  font-size: 12px;
  color: var(--text-light);
  margin: 12px 0 8px;
  padding: 4px 12px;
  background: var(--bg-tertiary);
  border-radius: 12px;
  align-self: center;
  display: inline-block;
}

.msg-row {
  display: flex;
  gap: 10px;
  margin-bottom: 16px;
  max-width: 70%;
  align-items: flex-start;
}
.msg-row :deep(.el-avatar) {
  flex-shrink: 0;
}
.msg-row.mine {
  flex-direction: row-reverse;
  align-self: flex-end;
}
.msg-bubble {
  padding: 10px 14px;
  border-radius: 12px;
  background: var(--bg-secondary);
  max-width: 100%;
  min-width: 0;
  overflow-wrap: break-word;
  word-break: break-word;
}
.mine .msg-bubble {
  background: var(--primary-gradient);
  color: #fff;
}
.msg-sender {
  font-size: 12px;
  color: var(--text-secondary);
  margin-bottom: 4px;
}
.msg-text {
  font-size: 14px;
  line-height: 1.5;
  word-break: break-word;
}

.msg-recalled {
  font-size: 13px;
  color: var(--text-light);
  padding: 4px 0;
  text-align: center;
}

.msg-image {
  cursor: pointer;
  max-width: 200px;
  max-height: 200px;
  border-radius: 8px;
  overflow: hidden;
}
.msg-image img {
  max-width: 200px;
  max-height: 200px;
  display: block;
  border-radius: 8px;
}

.msg-file {
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
  padding: 4px 0;
}
.file-icon { color: var(--primary-color); }
.mine .file-icon { color: rgba(255,255,255,0.9); }
.file-info { min-width: 0; }
.file-name {
  font-size: 13px;
  font-weight: 500;
  max-width: 160px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.file-size { font-size: 11px; opacity: 0.7; margin-top: 2px; }

.preview-image {
  max-width: 80vw;
  max-height: 80vh;
  display: block;
  margin: 0 auto;
  border-radius: 8px;
  cursor: zoom-out;
}
.msg-time {
  font-size: 10px;
  color: var(--text-light);
  margin-top: 4px;
  text-align: right;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 4px;
}
.mine .msg-time { color: rgba(255,255,255,0.7); }
.msg-read {
  font-size: 10px;
  color: var(--primary-color);
  margin-top: 2px;
  text-align: right;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 2px;
}
.mine .msg-read { color: rgba(255,255,255,0.8); }

.chat-input {
  padding: 12px 20px;
  border-top: 1px solid var(--border-light);
  display: flex;
  gap: 12px;
  align-items: flex-end;
}
.input-actions {
  display: flex;
  gap: 8px;
  padding-bottom: 4px;
}
.chat-input :deep(.el-textarea__inner) {
  border-radius: var(--radius-sm);
  background: var(--bg-secondary);
  box-shadow: 0 0 0 1px var(--border-color) inset;
  resize: none;
}

/* ====== 创建会话弹窗 ====== */
.member-pick-list {
  max-height: 360px;
  overflow-y: auto;
}
.member-pick-list.compact {
  max-height: 240px;
  border: 1px solid var(--border-light);
  border-radius: var(--radius-sm);
  padding: 8px;
}
.member-pick-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: background 0.2s;
}
.member-pick-item:hover { background: var(--bg-secondary); }
.member-info { flex: 1; min-width: 0; }
.member-name {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary);
}
.member-sub {
  font-size: 12px;
  color: var(--text-light);
  margin-top: 2px;
}
.member-arrow { color: var(--text-light); }
.member-checkbox {
  margin: 4px 8px;
  display: flex;
}

/* ====== 成员抽屉 ====== */
.member-drawer-list { padding: 8px; }
.member-drawer-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 8px;
  border-radius: var(--radius-sm);
}
.member-drawer-item:hover { background: var(--bg-secondary); }

/* ====== 右键菜单 ====== */
.context-menu {
  position: fixed;
  z-index: 9999;
  background: var(--bg-primary);
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  padding: 4px 0;
  min-width: 120px;
}

.context-menu-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 16px;
  cursor: pointer;
  font-size: 14px;
  color: var(--text-primary);
  transition: background 0.2s;
}

.context-menu-item:hover {
  background: var(--bg-secondary);
}

.context-menu-item .el-icon {
  font-size: 16px;
  color: var(--text-secondary);
}

/* ====== 响应式 ====== */
@media (max-width: 768px) {
  .im-page { flex-direction: column; margin: -16px; }
  .conv-panel { width: 100%; height: 200px; border-right: none; border-bottom: 1px solid var(--border-light); }
  .chat-panel { flex: 1; }
  .msg-row { max-width: 85%; }
}
</style>
