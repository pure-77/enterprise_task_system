<template>
  <div class="workspace-switcher">
    <el-select
      :model-value="workspaceStore.isPersonalMode ? '' : workspaceStore.currentWorkspaceId"
      placeholder="个人空间"
      @change="handleSwitch"
      size="default"
      class="ws-select"
    >
      <el-option value="" label="个人空间">
        <span class="ws-option">
          <el-icon><User /></el-icon>
          <span>个人空间</span>
        </span>
      </el-option>
      <el-option-group label="工作空间">
        <el-option
          v-for="ws in workspaceStore.workspaces"
          :key="ws.id"
          :value="ws.id"
          :label="ws.name"
        >
          <span class="ws-option">
            <el-icon><OfficeBuilding /></el-icon>
            <span>{{ ws.name }}</span>
            <el-tag size="small" type="info" class="role-tag">{{ roleLabel(ws.role) }}</el-tag>
          </span>
        </el-option>
      </el-option-group>
    </el-select>
  </div>
</template>

<script setup>
import { useWorkspaceStore } from '@/pinia/workspaceStore'
import { useRouter } from 'vue-router'
import { User, OfficeBuilding } from '@element-plus/icons-vue'

const workspaceStore = useWorkspaceStore()
const router = useRouter()

const roleLabel = (role) => {
  const map = { owner: 'Owner', admin: 'Admin', member: 'Member' }
  return map[role] || role
}

const handleSwitch = (workspaceId) => {
  // el-select 使用空字符串表示个人模式，转换为 null
  const id = workspaceId === '' ? null : workspaceId
  workspaceStore.switchWorkspace(id)
}
</script>

<style scoped>
.workspace-switcher {
  padding: 16px 12px 0;
}
.ws-select {
  width: 100%;
}
.ws-option {
  display: flex;
  align-items: center;
  gap: 8px;
}
.role-tag {
  margin-left: auto;
}
</style>
