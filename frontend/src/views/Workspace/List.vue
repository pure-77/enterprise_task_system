<template>
  <div class="workspace-list">
    <div class="page-header">
      <h2>我的工作空间</h2>
      <el-button type="primary" @click="$router.push('/workspaces/create')">
        <el-icon><Plus /></el-icon> 创建空间
      </el-button>
    </div>

    <div v-if="loading" class="loading-box">
      <el-skeleton :rows="3" animated />
    </div>

    <el-empty v-else-if="!workspaces.length" description="还没有加入任何工作空间">
      <el-button type="primary" @click="$router.push('/workspaces/create')">创建第一个空间</el-button>
    </el-empty>

    <div v-else class="ws-grid">
      <el-card
        v-for="ws in workspaces"
        :key="ws.id"
        class="ws-card"
        shadow="hover"
        @click="$router.push(`/workspaces/${ws.id}/settings`)"
      >
        <div class="ws-card-header">
          <h3>{{ ws.name }}</h3>
          <el-tag :type="roleType(ws.role)" size="small">{{ roleLabel(ws.role) }}</el-tag>
        </div>
        <p class="ws-desc">{{ ws.description || '暂无描述' }}</p>
        <div class="ws-meta">
          <span><el-icon><User /></el-icon> {{ ws.member_count }} 人</span>
          <span class="ws-owner">创建者: {{ ws.owner_nickname || '未知' }}</span>
        </div>
      </el-card>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useWorkspaceStore } from '@/pinia/workspaceStore'
import { Plus, User } from '@element-plus/icons-vue'

const workspaceStore = useWorkspaceStore()
const workspaces = ref([])
const loading = ref(true)

const roleLabel = (role) => {
  const map = { owner: '拥有者', admin: '管理员', member: '成员' }
  return map[role] || role
}
const roleType = (role) => {
  const map = { owner: 'danger', admin: 'warning', member: 'info' }
  return map[role] || 'info'
}

onMounted(async () => {
  loading.value = true
  workspaces.value = await workspaceStore.loadWorkspaces()
  loading.value = false
})
</script>

<style scoped>
.workspace-list { padding: 0; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; }
.page-header h2 { margin: 0; font-size: 20px; }
.ws-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 16px; }
.ws-card { cursor: pointer; transition: transform .2s; }
.ws-card:hover { transform: translateY(-2px); }
.ws-card-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
.ws-card-header h3 { margin: 0; font-size: 16px; }
.ws-desc { color: var(--text-secondary); font-size: 14px; margin-bottom: 16px; min-height: 40px; }
.ws-meta { display: flex; justify-content: space-between; font-size: 13px; color: var(--text-secondary); }
.loading-box { padding: 40px; }
</style>
