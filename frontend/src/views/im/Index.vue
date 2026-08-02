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
          <el-avatar :size="40" :src="c.avatar">{{ c.name?.[0] || '#' }}</el-avatar>
          <div class="conv-info">
            <div class="conv-name">{{ c.name || '单聊' }}</div>
            <div class="conv-preview">
              {{ c.last_message ? (c.last_message.sender_name + ': ' + (c.last_message.content || '')) : '暂无消息' }}
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
        <div
          v-for="m in messages"
          :key="m.id"
          :class="['msg-row', { mine: m.sender_id === currentUserId }]"
        >
          <el-avatar :size="32" :src="m.sender_avatar">{{ m.sender_name?.[0] }}</el-avatar>
          <div class="msg-bubble">
            <div class="msg-sender" v-if="m.sender_id !== currentUserId">{{ m.sender_name }}</div>
            <div class="msg-text">{{ m.content }}</div>
            <div class="msg-time">{{ formatMsgTime(m.created_at) }}</div>
          </div>
        </div>
        <el-empty v-if="messages.length === 0" description="暂无消息，发送第一条消息吧" :image-size="80" />
      </div>

      <div class="chat-input">
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
              <el-avatar :size="36" :src="m.avatar">{{ (m.nickname || m.real_name || '?')[0] }}</el-avatar>
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
          <el-avatar :size="36" :src="m.avatar">{{ (m.nickname || '?')[0] }}</el-avatar>
          <div class="member-info">
            <div class="member-name">{{ m.nickname || '未命名' }}</div>
            <div class="member-sub">{{ m.role || '成员' }}</div>
          </div>
        </div>
        <el-empty v-if="convMembers.length === 0" description="暂无成员" :image-size="60" />
      </div>
    </el-drawer>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Promotion, Plus, Search, User, ArrowRight } from '@element-plus/icons-vue'
import { imApi } from '@/api/im'
import { workspaceApi } from '@/api/workspace'
import { useWorkspaceStore } from '@/pinia/workspaceStore'
import { useUserStore } from '@/pinia/userStore'
import { formatTime } from '@/utils/format'

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

// ====== 分页加载 ======
const loadingMore = ref(false)
const currentPage = ref(1)
const hasMore = ref(true)

function formatMsgTime(t) {
  if (!t) return ''
  return formatTime(t).slice(11, 19)  // HH:MM:SS
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
  if (activeConv.value === c.id) return
  activeConv.value = c.id
  activeConvName.value = c.name || (c.type === 'single' ? '私聊' : '群聊')
  activeConvType.value = c.type === 'group' ? '群聊' : '单聊'
  messages.value = []
  currentPage.value = 1
  hasMore.value = true
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
    // 后端 items 已是旧→新正序（最新消息在最后），无需再 reverse
    messages.value = data.items || []
    await nextTick()
    scrollToBottom()
  } catch (e) {
    console.error('加载消息失败', e)
  }
}

// ====== 滚动到顶部加载更多 ======
async function onScroll() {
  const box = msgBox.value
  if (!box || loadingMore.value || !hasMore.value) return
  // 滚动到顶部时加载更多
  if (box.scrollTop < 50) {
    loadingMore.value = true
    const oldScrollHeight = box.scrollHeight
    try {
      currentPage.value += 1
      const res = await imApi.getMessages(activeConv.value, { page: currentPage.value, page_size: 50 })
      const items = res?.items || []
      if (items.length === 0) {
        hasMore.value = false
      } else {
        // 后端返回的 items 已是旧→新正序，page 越大消息越旧
        // 直接在前面插入更旧的消息
        messages.value = [...items, ...messages.value]
        await nextTick()
        // 保持滚动位置
        box.scrollTop = box.scrollHeight - oldScrollHeight
      }
    } catch (e) {
      currentPage.value -= 1
    } finally { loadingMore.value = false }
  }
}

function scrollToBottom() {
  const box = msgBox.value
  if (box) box.scrollTop = box.scrollHeight
}

// ====== 标记会话已读（去除红色 Badge） ======
async function markConvRead(convId) {
  try {
    await imApi.markRead(convId, {})
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

onMounted(() => {
  loadConvs()
  loadMembers()
})
</script>

<style scoped>
.im-page {
  display: flex;
  height: calc(100vh - 124px);
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
.msg-row {
  display: flex;
  gap: 10px;
  margin-bottom: 16px;
  max-width: 70%;
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
.msg-time {
  font-size: 10px;
  color: var(--text-light);
  margin-top: 4px;
  text-align: right;
}
.mine .msg-time { color: rgba(255,255,255,0.7); }

.chat-input {
  padding: 12px 20px;
  border-top: 1px solid var(--border-light);
  display: flex;
  gap: 12px;
  align-items: flex-end;
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

/* ====== 响应式 ====== */
@media (max-width: 768px) {
  .im-page { flex-direction: column; margin: -16px; }
  .conv-panel { width: 100%; height: 200px; border-right: none; border-bottom: 1px solid var(--border-light); }
  .chat-panel { flex: 1; }
  .msg-row { max-width: 85%; }
}
</style>
