<template>
  <div class="workspace-settings">
    <div class="page-header">
      <el-button text @click="$router.push('/workspaces')">
        <el-icon><ArrowLeft /></el-icon> 返回空间列表
      </el-button>
    </div>

    <div v-if="loading" class="loading-box">
      <el-skeleton :rows="6" animated />
    </div>

    <template v-if="ws">
      <h2>{{ ws.name }}</h2>

      <el-tabs v-model="activeTab">
        <!-- 基本信息 -->
        <el-tab-pane label="基本信息" name="info">
          <el-card shadow="never">
            <el-form :model="infoForm" label-width="100px" @submit.prevent="handleUpdateInfo">
              <el-form-item label="空间名称">
                <el-input v-model="infoForm.name" maxlength="100" />
              </el-form-item>
              <el-form-item label="空间描述">
                <el-input v-model="infoForm.description" type="textarea" :rows="3" maxlength="500" />
              </el-form-item>
              <el-form-item>
                <el-button type="primary" @click="handleUpdateInfo" :loading="saving">保存</el-button>
                <el-button type="danger" plain @click="handleDelete" v-if="ws.role === 'owner'" :disabled="saving">解散空间</el-button>
              </el-form-item>
            </el-form>
          </el-card>
        </el-tab-pane>

        <!-- 成员管理 -->
        <el-tab-pane label="成员管理" name="members">
          <el-card shadow="never">
            <div class="section-header">
              <span>共 {{ members.length }} 位成员</span>
              <el-button type="primary" size="small" @click="showInvite = true" v-if="canManage">
                <el-icon><Plus /></el-icon> 邀请成员
              </el-button>
            </div>
            <el-table :data="members" style="width: 100%">
              <el-table-column prop="nickname" label="昵称" />
              <el-table-column prop="email" label="邮箱" />
              <el-table-column prop="role" label="角色" width="120">
                <template #default="{ row }">
                  <el-tag :type="roleType(row.role)" size="small">{{ roleLabel(row.role) }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column label="操作" width="200" v-if="canManage">
                <template #default="{ row }">
                  <template v-if="row.role !== 'owner'">
                    <el-dropdown @command="(role) => handleRoleChange(row.user_id, role)">
                      <el-button size="small">修改角色</el-button>
                      <template #dropdown>
                        <el-dropdown-menu>
                          <el-dropdown-item command="admin">管理员</el-dropdown-item>
                          <el-dropdown-item command="member">成员</el-dropdown-item>
                        </el-dropdown-menu>
                      </template>
                    </el-dropdown>
                    <el-button size="small" type="danger" @click="handleRemoveMember(row.user_id)">移除</el-button>
                  </template>
                </template>
              </el-table-column>
            </el-table>
            <div v-if="!canManage && ws.role !== 'owner'" style="margin-top: 16px;">
              <el-button type="danger" plain @click="handleLeave">退出空间</el-button>
            </div>
          </el-card>
        </el-tab-pane>

        <!-- 邀请记录 -->
        <el-tab-pane label="邀请记录" name="invitations" v-if="canManage">
          <el-card shadow="never">
            <el-table :data="invitations" style="width: 100%">
              <el-table-column prop="invitee_email" label="邮箱" />
              <el-table-column prop="inviter_nickname" label="邀请人" />
              <el-table-column prop="role" label="角色" width="100">
                <template #default="{ row }">
                  <el-tag size="small">{{ roleLabel(row.role) }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="status" label="状态" width="80">
                <template #default="{ row }">
                  <el-tag :type="row.status === 'pending' ? 'warning' : 'info'" size="small">
                    {{ row.status === 'pending' ? '待处理' : row.status }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column label="操作" width="80">
                <template #default="{ row }">
                  <el-button v-if="row.status === 'pending'" size="small" type="danger" @click="handleCancelInvitation(row.id)">取消</el-button>
                </template>
              </el-table-column>
            </el-table>
          </el-card>
        </el-tab-pane>

        <!-- 动态 -->
        <el-tab-pane label="空间动态" name="activities">
          <el-card shadow="never">
            <div v-if="!activities.length" style="text-align: center; padding: 40px; color: var(--text-secondary);">暂无动态</div>
            <el-timeline v-else>
              <el-timeline-item
                v-for="act in activities"
                :key="act.id"
                :timestamp="formatTime(act.created_at)"
                placement="top"
              >
                <strong>{{ act.user_nickname }}</strong> {{ actionLabel(act.action) }}
              </el-timeline-item>
            </el-timeline>
          </el-card>
        </el-tab-pane>
      </el-tabs>
    </template>

    <!-- 邀请弹窗 -->
    <el-dialog v-model="showInvite" title="邀请成员" width="400px">
      <el-form :model="inviteForm" @submit.prevent="handleInvite">
        <el-form-item label="邮箱">
          <el-input v-model="inviteForm.invitee_email" placeholder="请输入对方注册邮箱" />
        </el-form-item>
        <el-form-item label="角色">
          <el-select v-model="inviteForm.role">
            <el-option label="成员" value="member" />
            <el-option label="管理员" value="admin" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleInvite" :loading="inviting">发送邀请</el-button>
        </el-form-item>
      </el-form>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useWorkspaceStore } from '@/pinia/workspaceStore'
import { workspaceApi } from '@/api/workspace'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowLeft, Plus } from '@element-plus/icons-vue'
import { validate } from '@/utils/validate'
import { formatTime } from '@/utils/format'

const route = useRoute()
const router = useRouter()
const workspaceStore = useWorkspaceStore()

const workspaceId = computed(() => parseInt(route.params.id))
const ws = ref(null)
const members = ref([])
const invitations = ref([])
const activities = ref([])
const loading = ref(true)
const saving = ref(false)
const inviting = ref(false)
const activeTab = ref('info')
const showInvite = ref(false)

const infoForm = ref({ name: '', description: '' })
const inviteForm = ref({ invitee_email: '', role: 'member' })

const canManage = computed(() => ws.value && (ws.value.role === 'owner' || ws.value.role === 'admin'))

const roleLabel = (role) => {
  const map = { owner: '拥有者', admin: '管理员', member: '成员' }
  return map[role] || role
}
const roleType = (role) => {
  const map = { owner: 'danger', admin: 'warning', member: 'info' }
  return map[role] || 'info'
}
const actionLabel = (action) => {
  const map = {
    workspace_created: '创建了空间',
    member_joined: '加入了空间',
    member_left: '退出了空间',
    member_removed: '被移出空间',
    task_created: '创建了任务',
    task_status_changed: '更新了任务状态',
    invitation_rejected: '拒绝了邀请'
  }
  return map[action] || action
}

onMounted(async () => {
  loading.value = true
  try {
    ws.value = await workspaceApi.getWorkspace(workspaceId.value)
    infoForm.value = { name: ws.value.name, description: ws.value.description || '' }
    await Promise.all([
      loadMembers(),
      canManage.value ? loadInvitations() : Promise.resolve(),
      loadActivities()
    ])
  } finally {
    loading.value = false
  }
})

const loadMembers = async () => { members.value = await workspaceApi.getMembers(workspaceId.value) }
const loadInvitations = async () => { invitations.value = await workspaceApi.getWorkspaceInvitations(workspaceId.value) }
const loadActivities = async () => { activities.value = await workspaceApi.getActivities(workspaceId.value) }

const handleUpdateInfo = async () => {
  saving.value = true
  try {
    await workspaceStore.updateWorkspace(workspaceId.value, infoForm.value)
    ws.value.name = infoForm.value.name
    ws.value.description = infoForm.value.description
  } finally {
    saving.value = false
  }
}

const handleDelete = async () => {
  try {
    await ElMessageBox.confirm('确定要解散该空间吗？所有空间数据将被保留但无法访问。', '警告', {
      confirmButtonText: '确定解散', type: 'warning'
    })
    await workspaceStore.deleteWorkspace(workspaceId.value)
    router.push('/workspaces')
  } catch {}
}

const handleRoleChange = async (userId, role) => {
  try {
    await workspaceApi.updateMemberRole(workspaceId.value, userId, { role })
    ElMessage.success('角色已更新')
    loadMembers()
  } catch {
    ElMessage.error('角色更新失败')
  }
}

const handleRemoveMember = async (userId) => {
  try {
    await ElMessageBox.confirm('确定要移除该成员吗？', '提示', { type: 'warning' })
    await workspaceApi.removeMember(workspaceId.value, userId)
    ElMessage.success('成员已移除')
    loadMembers()
  } catch {}
}

const handleLeave = async () => {
  try {
    await ElMessageBox.confirm('确定要退出该空间吗？', '提示', { type: 'warning' })
    await workspaceApi.leaveWorkspace(workspaceId.value)
    ElMessage.success('已退出空间')
    router.push('/workspaces')
  } catch {}
}

const handleInvite = async () => {
  const email = inviteForm.value.invitee_email.trim()
  if (!email) { ElMessage.warning('请输入邮箱'); return }
  if (!validate.email(email)) { ElMessage.warning('邮箱格式不正确'); return }
  inviteForm.value.invitee_email = email
  inviting.value = true
  try {
    await workspaceApi.createInvitation(workspaceId.value, inviteForm.value)
    ElMessage.success('邀请已发送')
    showInvite.value = false
    inviteForm.value = { invitee_email: '', role: 'member' }
    loadInvitations()
  } catch {
    ElMessage.error('邀请失败')
  } finally {
    inviting.value = false
  }
}

const handleCancelInvitation = async (invId) => {
  try {
    await workspaceApi.cancelInvitation(workspaceId.value, invId)
    ElMessage.success('已取消邀请')
    loadInvitations()
  } catch {
    ElMessage.error('取消失败')
  }
}
</script>

<style scoped>
.workspace-settings { padding: 0; }
.page-header { margin-bottom: 8px; }
.page-header h2 { margin: 0 0 16px; }
.section-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.loading-box { padding: 40px; }
</style>
