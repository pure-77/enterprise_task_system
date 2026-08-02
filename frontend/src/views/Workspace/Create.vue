<template>
  <div class="workspace-create">
    <div class="page-header">
      <h2>创建工作空间</h2>
    </div>
    <el-card class="form-card" shadow="never">
      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-width="100px"
        @submit.prevent="handleCreate"
      >
        <el-form-item label="空间名称" prop="name">
          <el-input v-model="form.name" placeholder="请输入空间名称" maxlength="100" />
        </el-form-item>
        <el-form-item label="空间描述" prop="description">
          <el-input
            v-model="form.description"
            type="textarea"
            :rows="4"
            placeholder="请输入空间描述（可选）"
            maxlength="500"
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleCreate" :loading="submitting">
            创建空间
          </el-button>
          <el-button @click="$router.push('/workspaces')">取消</el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useWorkspaceStore } from '@/pinia/workspaceStore'
import { ElMessage } from 'element-plus'

const router = useRouter()
const workspaceStore = useWorkspaceStore()

const formRef = ref(null)
const submitting = ref(false)
const form = ref({ name: '', description: '' })
const rules = {
  name: [{ required: true, message: '请输入空间名称', trigger: 'blur' }]
}

const handleCreate = async () => {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return
  submitting.value = true
  try {
    const ws = await workspaceStore.createWorkspace(form.value)
    ElMessage.success('空间创建成功，已自动生成默认分类')
    router.push(`/workspaces/${ws.id}/settings`)
  } catch {
    // error handled in store
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.workspace-create { padding: 0; }
.page-header { margin-bottom: 24px; }
.page-header h2 { margin: 0; font-size: 20px; }
.form-card { max-width: 600px; }
</style>
