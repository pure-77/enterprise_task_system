<template>
  <div class="page">
    <div class="page-head">
      <h2>通知中心</h2>
      <el-button @click="markAll" :disabled="unread === 0">全部已读</el-button>
    </div>
    <el-card class="notif-card" v-loading="loading">
      <div v-if="list.length === 0" style="text-align:center;padding:40px;color:var(--text-light)">暂无通知</div>
      <div v-for="n in list" :key="n.id" :class="['notif-item', { unread: !n.is_read }]">
        <div class="notif-dot" v-if="!n.is_read"></div>
        <div class="notif-body">
          <div class="notif-title">{{ n.title }}</div>
          <div class="notif-content">{{ n.content }}</div>
          <div class="notif-time">{{ n.created_at?.slice(0,16) }}</div>
        </div>
        <el-tag :type="typeTag(n.type)" size="small">{{ n.type }}</el-tag>
      </div>
    </el-card>
    <el-pagination v-model:current-page="p" :total="total" layout="prev,next,total" @current-change="load" style="margin-top:16px" />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { notificationApi } from '@/api/notification'
const list = ref([]); const loading = ref(false); const unread = ref(0)
const p = ref(1); const total = ref(0)

function typeTag(t) { return { task: '', approval: 'warning', chat: 'success', system: 'info' }[t] || '' }

async function load() {
  loading.value = true
  try {
    const [n, u] = await Promise.all([
      notificationApi.getList({ page: p.value }),
      notificationApi.getUnreadCount()
    ])
    const d = n
    list.value = d.items || d || []; total.value = d.total || 0
    unread.value = u?.unread_count || 0
  } finally { loading.value = false }
}

async function markAll() {
  try { await notificationApi.markAllRead(); ElMessage.success('已全部标记已读'); load() }
  catch {}
}

onMounted(() => load())
</script>
<style scoped>
.page { padding: 0; } .page-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; } .page-head h2 { font-size: 22px; font-weight: 700; }
.notif-card { border-radius: var(--radius-lg); }
.notif-item { display: flex; align-items: flex-start; gap: 12px; padding: 14px 16px; border-bottom: 1px solid var(--border-light); transition: background 0.2s; }
.notif-item.unread { background: var(--primary-gradient-soft); }
.notif-dot { width: 8px; height: 8px; border-radius: 50%; background: var(--primary-color); margin-top: 6px; flex-shrink: 0; }
.notif-body { flex: 1; } .notif-title { font-weight: 600; font-size: 14px; } .notif-content { font-size: 13px; color: var(--text-secondary); margin-top: 4px; } .notif-time { font-size: 12px; color: var(--text-light); margin-top: 4px; }
</style>
