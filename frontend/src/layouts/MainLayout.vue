<template>
  <div class="ding-layout">
    <!-- ============ 第一栏：图标导航栏（最左） ============ -->
    <aside class="rail">
      <div class="rail-brand" @click="router.push('/')">
        <div class="brand-icon"><span class="brand-grad">E</span></div>
      </div>

      <nav class="rail-nav">
        <div
          v-for="group in menuGroups"
          :key="group.key"
          class="rail-item"
          :class="{ active: activeGroup === group.key }"
          @click="switchGroup(group.key)"
        >
          <el-icon :size="20"><component :is="group.icon" /></el-icon>
          <span class="rail-label">{{ group.label }}</span>
          <span v-if="group.badge" class="rail-badge">{{ group.badge }}</span>
        </div>
      </nav>

      <div class="rail-footer">
        <div class="rail-item" @click="themeStore.toggleTheme()">
          <el-icon :size="20"><MoonNight v-if="themeStore.isDark" /><Sunny v-else /></el-icon>
          <span class="rail-label">{{ themeStore.isDark ? '深色' : '浅色' }}</span>
        </div>
      </div>
    </aside>

    <!-- ============ 第二栏：二级菜单 ============ -->
    <aside
      class="sub-menu"
      :class="{ collapsed: subMenuCollapsed, 'mobile-open': mobileMenuOpen }"
    >
      <div class="sub-menu-header">
        <h3>{{ currentGroupLabel }}</h3>
        <el-icon class="collapse-btn" @click="toggleSubMenu">
          <Fold v-if="!subMenuCollapsed" /><Expand v-else />
        </el-icon>
      </div>

      <div class="sub-menu-body">
        <div
          v-for="item in currentMenuItems"
          :key="item.path"
          class="sub-item"
          :class="{ active: isMenuActive(item) }"
          @click="onMenuClick(item)"
        >
          <el-icon :size="16"><component :is="item.icon" /></el-icon>
          <span class="sub-label">{{ item.label }}</span>
          <el-badge v-if="item.badge" :value="item.badge" class="sub-badge" />
        </div>
      </div>

      <WorkspaceSwitcher v-if="activeGroup === 'work'" class="sub-menu-switcher" />
    </aside>

    <!-- ============ 主区域 ============ -->
    <main class="main">
      <!-- 顶部栏：搜索 + 通知 + 用户 -->
      <header class="topbar">
        <div class="topbar-left">
          <div class="mobile-menu-btn" @click="mobileMenuOpen = !mobileMenuOpen">
            <el-icon :size="20"><Menu /></el-icon>
          </div>
          <h2 class="page-title">{{ pageTitle }}</h2>
        </div>

        <div class="topbar-center">
          <el-input
            v-model="searchKeyword"
            placeholder="搜索任务、消息、审批、文件..."
            class="search-input"
            :prefix-icon="Search"
            clearable
          />
        </div>

        <div class="topbar-right">
          <!-- 通知中心 -->
          <el-dropdown trigger="click" placement="bottom-end" @visible-change="onNotifDropdownToggle">
            <div class="topbar-icon-btn">
              <el-badge :value="unreadNotifCount || ''" :hidden="!unreadNotifCount" :max="99">
                <el-icon :size="20"><Bell /></el-icon>
              </el-badge>
            </div>
            <template #dropdown>
              <el-dropdown-menu class="notif-dropdown">
                <div class="notif-header">
                  <span>通知中心</span>
                  <el-button text size="small" @click="markAllNotifRead">全部已读</el-button>
                </div>
                <div class="notif-list">
                  <div v-if="!notifList.length" class="notif-empty">暂无通知</div>
                  <div
                    v-for="n in notifList.slice(0, 6)"
                    :key="n.id"
                    class="notif-item"
                    :class="{ unread: !n.is_read }"
                    @click="goNotifDetail(n)"
                  >
                    <div class="notif-title">{{ n.title }}</div>
                    <div class="notif-content">{{ n.content }}</div>
                    <div class="notif-time">{{ formatTime(n.created_at) }}</div>
                  </div>
                </div>
                <div class="notif-footer" @click="router.push('/notifications')">
                  查看全部通知
                </div>
              </el-dropdown-menu>
            </template>
          </el-dropdown>

          <!-- 用户头像 -->
          <el-dropdown trigger="click" @command="handleDropdownCommand">
            <div class="user-chip">
              <img v-if="userStore.getAvatar" :src="appendToken(userStore.getAvatar)" class="user-avatar-img">
              <el-icon v-else class="user-avatar-icon"><User /></el-icon>
              <span class="user-name">{{ userStore.getNickname || '用户' }}</span>
              <el-icon :size="12"><ArrowDown /></el-icon>
            </div>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="profile">
                  <el-icon><User /></el-icon>个人中心
                </el-dropdown-item>
                <el-dropdown-item command="notifications">
                  <el-icon><Bell /></el-icon>通知中心
                </el-dropdown-item>
                <el-dropdown-item command="logout" divided>
                  <el-icon><SwitchButton /></el-icon>退出登录
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </header>

      <!-- 主内容区 -->
      <div class="content-area">
        <router-view v-if="ready" />
        <div v-else class="loading-state">
          <el-icon class="is-loading" :size="32"><Loading /></el-icon>
          <span>加载中...</span>
        </div>
      </div>
    </main>

    <!-- 移动端遮罩 -->
    <div v-if="mobileMenuOpen" class="mobile-overlay" @click="mobileMenuOpen = false"></div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUserStore } from '@/pinia/userStore'
import { useThemeStore } from '@/pinia/themeStore'
import { useWorkspaceStore } from '@/pinia/workspaceStore'
import { useTaskStore } from '@/pinia/taskStore'
import { useCategoryStore } from '@/pinia/categoryStore'
import {
  House, List, Collection, User, DataAnalysis, PriceTag, Download,
  SwitchButton, MoonNight, Sunny, Menu, OfficeBuilding, Bell, ArrowDown,
  Odometer, ChatDotRound, Calendar, DocumentChecked, Clock, Notification,
  Folder, Grid, Search, Fold, Expand, Loading, ChatLineSquare
} from '@element-plus/icons-vue'
import { ElMessageBox, ElMessage, ElNotification } from 'element-plus'
import { workspaceApi } from '@/api/workspace'
import { notificationApi } from '@/api/notification'
import { formatTime } from '@/utils/format'
import { appendToken } from '@/utils/auth'
import WorkspaceSwitcher from '@/components/Workspace/WorkspaceSwitcher.vue'
import { useWebSocket } from '@/composables/useWebSocket'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const themeStore = useThemeStore()
const workspaceStore = useWorkspaceStore()
const taskStore = useTaskStore()
const categoryStore = useCategoryStore()

// workspace 切换时清空并刷新所有 store，防止不同空间数据残留
watch(
  () => workspaceStore.currentWorkspaceId,
  async () => {
    // taskStore
    taskStore.tasks = []
    taskStore.total = 0
    taskStore.selectedTaskIds = []
    // categoryStore
    categoryStore.categories = []
    await Promise.all([
      taskStore.loadTasks(),
      categoryStore.loadCategories()
    ])
  }
)

const subMenuCollapsed = ref(false)
const mobileMenuOpen = ref(false)
const invitationCount = ref(0)
const ready = ref(false)
const searchKeyword = ref('')

// 全局 WebSocket 连接
const { connect: wsConnect, subscribe: wsSubscribe } = useWebSocket()

// 通知相关
const notifList = ref([])
const unreadNotifCount = ref(0)

const pageTitle = computed(() => route.meta?.title || '工作台')

// ====== 菜单分组（钉钉风格：一级图标 + 二级列表） ======
const menuGroups = [
  { key: 'agent',    label: 'AI助手', icon: ChatLineSquare },
  { key: 'work',     label: '工作台', icon: Odometer },
  { key: 'comm',     label: '沟通',   icon: ChatDotRound, badge: 0 },
  { key: 'office',   label: '办公',   icon: DocumentChecked },
  { key: 'collab',   label: '协作',   icon: Folder },
  { key: 'manage',   label: '管理',   icon: OfficeBuilding },
  { key: 'personal', label: '个人',   icon: User }
]

const menuItems = computed(() => ({
  agent: [
    { path: '/agent',          label: '智能助手',   icon: ChatLineSquare, requiresWorkspace: true }
  ],
  work: [
    { path: '/',              label: '工作台',     icon: Odometer, requiresWorkspace: false }
  ],
  comm: [
    { path: '/im',            label: '即时通讯',   icon: ChatDotRound, requiresWorkspace: true }
  ],
  office: [
    { path: '/tasks',         label: '任务管理',   icon: List, requiresWorkspace: true },
    { path: '/calendar',      label: '日程日历',   icon: Calendar, requiresWorkspace: true },
    { path: '/approval',      label: 'OA审批',     icon: DocumentChecked, requiresWorkspace: true },
    { path: '/attendance',    label: '考勤打卡',   icon: Clock, requiresWorkspace: true }
  ],
  collab: [
    { path: '/announcements', label: '企业公告',   icon: Notification, requiresWorkspace: true },
    { path: '/files',         label: '文件管理',   icon: Folder, requiresWorkspace: true }
  ],
  manage: [
    { path: '/org/departments', label: '组织架构', icon: OfficeBuilding, requiresWorkspace: true },
    { path: '/org/members',     label: '成员花名册', icon: User, requiresWorkspace: true },
    { path: '/workspaces',      label: '工作空间', icon: Grid, requiresWorkspace: false },
    { path: '/invitations',     label: '团队邀请', icon: Bell, badge: invitationCount.value || 0, requiresWorkspace: true },
    { path: '/statistics',      label: '数据统计', icon: DataAnalysis, requiresWorkspace: true }
  ],
  personal: [
    { path: '/profile',       label: '我的资料',   icon: User, requiresWorkspace: false },
    { path: '/categories',    label: '分类管理',   icon: Collection, requiresWorkspace: false },
    { path: '/tags',          label: '标签管理',   icon: PriceTag, requiresWorkspace: false },
    { path: '/backup',        label: '数据备份',   icon: Download, requiresWorkspace: false }
  ]
}))

// 当前激活的一级菜单（根据路由自动判断）
const activeGroup = ref('work')
const currentGroupLabel = computed(() =>
  menuGroups.find(g => g.key === activeGroup.value)?.label || ''
)
const currentMenuItems = computed(() => {
  const items = menuItems.value[activeGroup.value] || []
  // 个人空间模式下，办公模块只保留任务管理和日程日历
  if (activeGroup.value === 'office' && workspaceStore.isPersonalMode) {
    return items.filter(it => ['/tasks', '/calendar'].includes(it.path))
  }
  return items
})

function detectGroupFromRoute(path) {
  for (const [key, items] of Object.entries(menuItems.value)) {
    if (items.some(it => path === it.path || path.startsWith(it.path + '/'))) {
      return key
    }
  }
  return 'work'
}

// 个人空间模式下完全禁用的模块组
const PERSONAL_MODE_DISABLED_GROUPS = ['comm', 'collab', 'manage']

function switchGroup(key) {
  // 个人空间模式下，沟通/协作/管理模块整体禁用
  if (PERSONAL_MODE_DISABLED_GROUPS.includes(key) && workspaceStore.isPersonalMode) {
    ElMessage.warning('个人空间模式下暂不支持该功能，请先加入或创建工作空间')
    return
  }

  activeGroup.value = key
  // 切换分组时自动展开二级菜单（解决折叠后无法弹出的问题）
  subMenuCollapsed.value = false
  // 移动端：切换分组时打开抽屉
  if (window.innerWidth <= 768) {
    mobileMenuOpen.value = true
  }
  // 切换分组时默认跳转到该组第一个菜单（如果当前不在该组内）
  const items = menuItems.value[key]
  if (items && items.length && !items.some(it => route.path === it.path)) {
    const firstItem = items[0]
    router.push(firstItem.path)
  }
}


function isMenuActive(item) {
  if (item.path === '/') return route.path === '/'
  return route.path === item.path || route.path.startsWith(item.path + '/')
}

function onMenuClick(item) {
  // 个人空间模式下拦截需要workspace的功能
  if (item.requiresWorkspace && workspaceStore.isPersonalMode) {
    ElMessage.warning('个人空间模式下暂不支持该功能，请先加入或创建工作空间')
    return
  }
  router.push(item.path)
  closeSidebar()
}

function closeSidebar() { mobileMenuOpen.value = false }

function toggleSubMenu() {
  // 移动端用 mobileMenuOpen 控制抽屉，桌面端用 subMenuCollapsed 控制宽度
  if (window.innerWidth <= 768) {
    mobileMenuOpen.value = !mobileMenuOpen.value
  } else {
    subMenuCollapsed.value = !subMenuCollapsed.value
  }
}

// ====== 通知中心 ======
async function loadNotifList() {
  try {
    const res = await notificationApi.getList({ page: 1, page_size: 10 })
    notifList.value = res.items || []
    unreadNotifCount.value = res.unread_count || 0
  } catch {}
}

async function onNotifDropdownToggle(visible) {
  if (visible) await loadNotifList()
}

async function markAllNotifRead() {
  try {
    await notificationApi.markAllRead()
    await loadNotifList()
    ElMessage.success('已全部标记为已读')
  } catch {}
}

function goNotifDetail(n) {
  // 未读通知：标记已读 + 铃铛未读数 -1
  if (n && !n.is_read && n.id) {
    notificationApi.markRead({ notification_ids: [n.id] }).catch(() => {})
    n.is_read = true
    unreadNotifCount.value = Math.max(0, unreadNotifCount.value - 1)
  }
  // deep-link：按 related_type 跳转对应详情页
  const map = {
    task: n?.related_id ? `/tasks/${n.related_id}` : '/tasks',
    approval: n?.related_id ? `/approval/${n.related_id}` : '/approval',
    calendar: '/calendar',
    announcement: n?.related_id ? `/announcements/${n.related_id}` : '/announcements',
    chat: '/im',
  }
  router.push(map[n?.related_type] || '/notifications')
}

// ====== 实时通知（WebSocket 推送 → toast + 铃铛即时更新） ======
function showNotifToast(n) {
  ElNotification({
    title: n.title || '新通知',
    message: n.content || '点击查看详情',
    type: n.type === 'approval' ? 'warning' : 'info',
    duration: 5000,
    onClick: () => goNotifDetail(n),
  })
}

function handleWsNotification(e) {
  const n = e.detail
  if (!n || !n.id) return
  // 防重复（同一通知可能因重连收到多次）
  if (notifList.value.some(x => x.id === n.id)) return
  // 铃铛未读数 +1，列表前插（面板打开时也能即时看到）
  unreadNotifCount.value += 1
  notifList.value = [n, ...notifList.value].slice(0, 10)
  showNotifToast(n)
}

// ====== 初始化 ======
onMounted(async () => {
  activeGroup.value = detectGroupFromRoute(route.path)
  try {
    await workspaceStore.loadWorkspaces()
  } catch (e) {
    console.error('加载工作空间失败:', e)
  }
  workspaceStore.restoreWorkspaceContext()
  ready.value = true
  try {
    const res = await workspaceApi.getPendingCount()
    invitationCount.value = res.count || 0
  } catch {}
  await loadNotifList()
  // 每 60 秒刷新未读数（兜底，实时由 WS 推送驱动）
  setInterval(loadNotifList, 60000)
  // 建立 WebSocket 连接并订阅 IM 频道
  wsConnect()
  wsSubscribe(['im'])
  // 监听实时推送的新通知 → toast + 铃铛即时更新
  window.addEventListener('ws:new_notification', handleWsNotification)
})

onUnmounted(() => {
  window.removeEventListener('ws:new_notification', handleWsNotification)
})

const handleDropdownCommand = async (command) => {
  if (command === 'profile') router.push('/profile')
  else if (command === 'notifications') router.push('/notifications')
  else if (command === 'logout') {
    try {
      await ElMessageBox.confirm('确定要退出登录吗？', '提示', {
        confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning'
      })
      await userStore.logout()
      router.push('/auth/login')
    } catch {}
  }
}
</script>

<style scoped>
/* ====== 布局根 ====== */
.ding-layout {
  display: flex;
  width: 100vw;
  height: 100vh;
  overflow: hidden;
  background: var(--bg-page);
}

/* ====== 第一栏：图标导航栏（钉钉风最深色） ====== */
.rail {
  width: 72px;
  flex-shrink: 0;
  background: var(--bg-sidebar);
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 16px 0;
  z-index: 1000;
}

.rail-brand {
  cursor: pointer;
  margin-bottom: 16px;
}
.brand-icon {
  width: 40px; height: 40px;
  border-radius: var(--radius-md);
  background: var(--primary-gradient);
  display: flex; align-items: center; justify-content: center;
}
.brand-grad {
  font-size: 20px; font-weight: 700; color: #fff;
}

.rail-nav {
  flex: 1;
  display: flex; flex-direction: column;
  gap: 4px;
  width: 100%;
  padding: 0 8px;
  overflow-y: auto;
}

.rail-item {
  position: relative;
  display: flex; flex-direction: column; align-items: center;
  gap: 4px;
  padding: 10px 4px;
  border-radius: var(--radius-sm);
  color: rgba(255,255,255,0.55);
  cursor: pointer;
  transition: all 0.2s ease;
}
.rail-item:hover {
  background: var(--bg-sidebar-hover);
  color: rgba(255,255,255,0.9);
}
.rail-item.active {
  background: var(--bg-sidebar-active);
  color: #fff;
}
.rail-item.active::before {
  content: '';
  position: absolute;
  left: -8px;
  top: 50%;
  transform: translateY(-50%);
  width: 3px; height: 18px;
  background: var(--primary-color);
  border-radius: 0 2px 2px 0;
}
.rail-label {
  font-size: 11px;
  font-weight: 500;
  line-height: 1.2;
  text-align: center;
}
.rail-badge {
  position: absolute;
  top: 4px; right: 4px;
  min-width: 16px; height: 16px;
  padding: 0 4px;
  border-radius: 8px;
  background: var(--error-color);
  color: #fff;
  font-size: 10px;
  line-height: 16px;
  text-align: center;
}

.rail-footer {
  margin-top: 8px;
  padding-top: 12px;
  border-top: 1px solid rgba(255,255,255,0.06);
  width: 100%;
}

/* ====== 第二栏：二级菜单 ====== */
.sub-menu {
  width: 220px;
  flex-shrink: 0;
  background: var(--bg-primary);
  border-right: 1px solid var(--border-light);
  display: flex;
  flex-direction: column;
  transition: width 0.25s ease;
  overflow: hidden;
}
.sub-menu.collapsed {
  width: 0;
  border-right: none;
}

.sub-menu-header {
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  border-bottom: 1px solid var(--border-light);
}
.sub-menu-header h3 {
  font-size: 16px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0;
}
.collapse-btn {
  cursor: pointer;
  color: var(--text-light);
  font-size: 16px;
}
.collapse-btn:hover { color: var(--primary-color); }

.sub-menu-body {
  flex: 1;
  padding: 12px 12px;
  overflow-y: auto;
}

.sub-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  border-radius: var(--radius-sm);
  color: var(--text-secondary);
  text-decoration: none;
  font-size: 14px;
  font-weight: 500;
  margin: 2px 0;
  cursor: pointer;
  transition: all 0.2s ease;
}
.sub-item:hover {
  background: var(--bg-secondary);
  color: var(--text-primary);
}
.sub-item.active {
  background: var(--primary-gradient-soft);
  color: var(--primary-color);
  font-weight: 600;
}
.sub-label { flex: 1; }
.sub-badge { margin-left: auto; }

.sub-menu-switcher {
  padding: 12px;
  border-top: 1px solid var(--border-light);
}

/* ====== 主区域 ====== */
.main {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  min-width: 0;
}

/* 顶部栏 */
.topbar {
  height: 60px;
  background: var(--bg-primary);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  border-bottom: 1px solid var(--border-light);
  flex-shrink: 0;
  gap: 24px;
}
.topbar-left {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
}
.mobile-menu-btn {
  display: none;
  cursor: pointer;
  color: var(--text-secondary);
}
.page-title {
  font-size: 16px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0;
  white-space: nowrap;
}

.topbar-center {
  flex: 1;
  max-width: 480px;
}
.search-input :deep(.el-input__wrapper) {
  border-radius: 999px;
  background: var(--bg-secondary);
  box-shadow: 0 0 0 1px transparent inset;
}
.search-input :deep(.el-input__wrapper:hover) {
  box-shadow: 0 0 0 1px var(--primary-light) inset;
}

.topbar-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.topbar-icon-btn {
  width: 36px; height: 36px;
  border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  cursor: pointer;
  color: var(--text-secondary);
  transition: all 0.2s ease;
}
.topbar-icon-btn:hover {
  background: var(--bg-secondary);
  color: var(--primary-color);
}

.user-chip {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 12px 4px 4px;
  border-radius: 999px;
  cursor: pointer;
  transition: all 0.2s ease;
}
.user-chip:hover { background: var(--bg-secondary); }
.user-avatar-img {
  width: 32px; height: 32px;
  border-radius: 50%;
  object-fit: cover;
}
.user-avatar-icon {
  width: 32px; height: 32px;
  border-radius: 50%;
  background: var(--bg-tertiary);
  color: var(--text-secondary);
  display: flex; align-items: center; justify-content: center;
  font-size: 16px;
}
.user-name {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary);
  white-space: nowrap;
}

/* 主内容区 */
.content-area {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
}

.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  height: 60vh;
  color: var(--text-light);
}

/* ====== 通知下拉 ====== */
.notif-dropdown {
  width: 360px;
  padding: 0 !important;
}
.notif-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-bottom: 1px solid var(--border-light);
  font-weight: 600;
  color: var(--text-primary);
}
.notif-list {
  max-height: 380px;
  overflow-y: auto;
}
.notif-empty {
  padding: 40px 16px;
  text-align: center;
  color: var(--text-light);
  font-size: 13px;
}
.notif-item {
  padding: 12px 16px;
  border-bottom: 1px solid var(--border-light);
  cursor: pointer;
  transition: background 0.2s ease;
}
.notif-item:hover { background: var(--bg-secondary); }
.notif-item.unread {
  background: var(--primary-gradient-soft);
}
.notif-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 4px;
}
.notif-content {
  font-size: 12px;
  color: var(--text-secondary);
  line-height: 1.5;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}
.notif-time {
  font-size: 11px;
  color: var(--text-light);
  margin-top: 4px;
}
.notif-footer {
  padding: 10px 16px;
  text-align: center;
  font-size: 13px;
  color: var(--primary-color);
  cursor: pointer;
  border-top: 1px solid var(--border-light);
}
.notif-footer:hover { background: var(--bg-secondary); }

.mobile-overlay { display: none; }

/* ====== 响应式 ====== */
@media (max-width: 1024px) {
  .topbar-center { max-width: 280px; }
  .content-area { padding: 16px; }
}

@media (max-width: 768px) {
  .rail { width: 56px; }
  .rail-label { font-size: 10px; }
  .brand-icon { width: 32px; height: 32px; }
  .brand-grad { font-size: 16px; }

  /* 移动端：二级菜单变成抽屉，由 mobile-open 控制显示 */
  .sub-menu {
    position: fixed;
    left: 56px;
    top: 0;
    height: 100vh;
    z-index: 999;
    width: 240px;
    transform: translateX(-100%);
    transition: transform 0.25s ease;
    border-right: 1px solid var(--border-light);
  }
  /* 移动端 collapsed 不再隐藏宽度，仅由 mobile-open 控制抽屉 */
  .sub-menu.collapsed { width: 240px; border-right: 1px solid var(--border-light); }
  .sub-menu.mobile-open { transform: translateX(0); }

  .mobile-menu-btn { display: flex; }
  .topbar { padding: 0 16px; gap: 12px; }
  .topbar-center { display: none; }
  .user-name { display: none; }
  .page-title { font-size: 14px; }

  .mobile-overlay {
    display: block;
    position: fixed;
    inset: 0;
    background: rgba(0,0,0,0.4);
    z-index: 998;
  }
}
</style>
