<template>
  <div class="invitations-page">
    <div class="page-header">
      <h2>邀请通知</h2>
    </div>

    <div v-if="loading" class="loading-box">
      <el-skeleton :rows="3" animated />
    </div>

    <el-empty v-else-if="!invitations.length" description="暂无待处理的邀请" />

    <div v-else class="inv-list">
      <el-card v-for="inv in invitations" :key="inv.id" class="inv-card" shadow="hover">
        <div class="inv-content">
          <div class="inv-info">
            <h4>{{ inv.workspace_name }}</h4>
            <p>
              <strong>{{ inv.inviter_nickname }}</strong> 邀请你加入，角色:
              <el-tag size="small">{{ roleLabel(inv.role) }}</el-tag>
            </p>
            <p class="inv-time">{{ formatTime(inv.created_at) }}</p>
          </div>
          <div class="inv-actions">
            <el-button type="primary" @click="handleAccept(inv.id)" :loading="acting === inv.id">
              接受
            </el-button>
            <el-button @click="handleReject(inv.id)" :disabled="acting === inv.id">
              拒绝
            </el-button>
          </div>
        </div>
      </el-card>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { workspaceApi } from '@/api/workspace'
import { ElMessage } from 'element-plus'
import { formatTime } from '@/utils/format'

const invitations = ref([])
const loading = ref(true)
const acting = ref(null)

const roleLabel = (role) => {
  const map = { admin: '管理员', member: '成员' }
  return map[role] || role
}

onMounted(async () => {
  loading.value = true
  try {
    invitations.value = await workspaceApi.getMyInvitations()
  } finally {
    loading.value = false
  }
})

const handleAccept = async (id) => {
  acting.value = id
  try {
    await workspaceApi.acceptInvitation(id)
    ElMessage.success('已加入空间')
    invitations.value = invitations.value.filter(i => i.id !== id)
  } catch {
    ElMessage.error('操作失败')
  } finally {
    acting.value = null
  }
}

const handleReject = async (id) => {
  try {
    await workspaceApi.rejectInvitation(id)
    invitations.value = invitations.value.filter(i => i.id !== id)
    ElMessage.info('已拒绝邀请')
  } catch {
    ElMessage.error('操作失败')
  }
}
</script>

<style scoped>
.invitations-page { padding: 0; }
.page-header { margin-bottom: 24px; }
.page-header h2 { margin: 0; font-size: 20px; }
.inv-list { display: flex; flex-direction: column; gap: 12px; }
.inv-content { display: flex; justify-content: space-between; align-items: center; }
.inv-info h4 { margin: 0 0 8px; font-size: 16px; }
.inv-info p { margin: 4px 0; font-size: 14px; color: var(--text-secondary); }
.inv-time { font-size: 12px !important; color: var(--text-tertiary) !important; }
.inv-actions { display: flex; gap: 8px; flex-shrink: 0; }
.loading-box { padding: 40px; }
</style>
