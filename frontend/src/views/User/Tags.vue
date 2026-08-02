<!--<template>-->
<!--  <div class="tags-container">-->
<!--    <el-card>-->
<!--      <template #header>-->
<!--        <div class="card-header">-->
<!--          <span>标签管理</span>-->
<!--          <el-button type="primary" @click="showCreateDialog">新增标签</el-button>-->
<!--        </div>-->
<!--      </template>-->
<!--      -->
<!--      <el-table :data="tags" style="width: 100%">-->
<!--        <el-table-column prop="name" label="标签名称" />-->
<!--        <el-table-column label="标签颜色" width="200">-->
<!--          <template #default="{ row }">-->
<!--            <div class="color-preview">-->
<!--              <div class="color-box" :style="{ backgroundColor: row.color }"></div>-->
<!--              <span>{{ row.color }}</span>-->
<!--            </div>-->
<!--          </template>-->
<!--        </el-table-column>-->
<!--        <el-table-column prop="created_at" label="创建时间" width="180">-->
<!--          <template #default="{ row }">-->
<!--            {{ formatDate(row.created_at) }}-->
<!--          </template>-->
<!--        </el-table-column>-->
<!--        <el-table-column label="操作" width="150">-->
<!--          <template #default="{ row }">-->
<!--            <el-button link type="primary" @click="showEditDialog(row)">编辑</el-button>-->
<!--            <el-button link type="danger" @click="handleDelete(row)">删除</el-button>-->
<!--          </template>-->
<!--        </el-table-column>-->
<!--      </el-table>-->
<!--    </el-card>-->
<!--    -->
<!--    &lt;!&ndash; 新增/编辑标签对话框 &ndash;&gt;-->
<!--    <el-dialog-->
<!--      v-model="dialogVisible"-->
<!--      :title="dialogTitle"-->
<!--      width="500px"-->
<!--    >-->
<!--      <el-form :model="tagForm" :rules="rules" label-width="100px">-->
<!--        <el-form-item label="标签名称" prop="name">-->
<!--          <el-input v-model="tagForm.name" placeholder="请输入标签名称" />-->
<!--        </el-form-item>-->
<!--        -->
<!--        <el-form-item label="标签颜色" prop="color">-->
<!--          <el-color-picker v-model="tagForm.color" />-->
<!--          <span class="color-value">{{ tagForm.color }}</span>-->
<!--        </el-form-item>-->
<!--      </el-form>-->
<!--      -->
<!--      <template #footer>-->
<!--        <el-button @click="dialogVisible = false">取消</el-button>-->
<!--        <el-button type="primary" @click="handleSubmit">确定</el-button>-->
<!--      </template>-->
<!--    </el-dialog>-->
<!--  </div>-->
<!--</template>-->

<!--<script setup>-->
<!--import { ref, onMounted } from 'vue'-->
<!--import { ElMessage, ElMessageBox } from 'element-plus'-->
<!--import { tagApi } from '@/api/tag'-->

<!--const tags = ref([])-->
<!--const dialogVisible = ref(false)-->
<!--const dialogTitle = ref('新增标签')-->
<!--const isEdit = ref(false)-->
<!--const currentTagId = ref(null)-->

<!--const tagForm = ref({-->
<!--  name: '',-->
<!--  color: '#409EFF'-->
<!--})-->

<!--const rules = {-->
<!--  name: [-->
<!--    { required: true, message: '请输入标签名称', trigger: 'blur' }-->
<!--  ],-->
<!--  color: [-->
<!--    { required: true, message: '请选择标签颜色', trigger: 'change' }-->
<!--  ]-->
<!--}-->

<!--const loadTags = async () => {-->
<!--  try {-->
<!--    const data = await tagApi.getTags()-->
<!--    tags.value = data-->
<!--  } catch (error) {-->
<!--    ElMessage.error('加载标签列表失败')-->
<!--  }-->
<!--}-->

<!--const showCreateDialog = () => {-->
<!--  dialogTitle.value = '新增标签'-->
<!--  isEdit.value = false-->
<!--  tagForm.value = {-->
<!--    name: '',-->
<!--    color: '#409EFF'-->
<!--  }-->
<!--  dialogVisible.value = true-->
<!--}-->

<!--const showEditDialog = (tag) => {-->
<!--  dialogTitle.value = '编辑标签'-->
<!--  isEdit.value = true-->
<!--  currentTagId.value = tag.id-->
<!--  tagForm.value = {-->
<!--    name: tag.name,-->
<!--    color: tag.color-->
<!--  }-->
<!--  dialogVisible.value = true-->
<!--}-->

<!--const handleSubmit = async () => {-->
<!--  try {-->
<!--    if (isEdit.value) {-->
<!--      await tagApi.updateTag(currentTagId.value, tagForm.value)-->
<!--      ElMessage.success('标签更新成功')-->
<!--    } else {-->
<!--      await tagApi.createTag(tagForm.value)-->
<!--      ElMessage.success('标签创建成功')-->
<!--    }-->
<!--    dialogVisible.value = false-->
<!--    loadTags()-->
<!--  } catch (error) {-->
<!--    ElMessage.error(isEdit.value ? '标签更新失败' : '标签创建失败')-->
<!--  }-->
<!--}-->

<!--const handleDelete = async (tag) => {-->
<!--  try {-->
<!--    await ElMessageBox.confirm('确定要删除该标签吗？', '提示', {-->
<!--      confirmButtonText: '确定',-->
<!--      cancelButtonText: '取消',-->
<!--      type: 'warning'-->
<!--    })-->
<!--    -->
<!--    await tagApi.deleteTag(tag.id)-->
<!--    ElMessage.success('标签删除成功')-->
<!--    loadTags()-->
<!--  } catch (error) {-->
<!--    if (error !== 'cancel') {-->
<!--      ElMessage.error('标签删除失败')-->
<!--    }-->
<!--  }-->
<!--}-->

<!--const formatDate = (dateString) => {-->
<!--  const date = new Date(dateString)-->
<!--  return date.toLocaleString('zh-CN')-->
<!--}-->

<!--onMounted(() => {-->
<!--  loadTags()-->
<!--})-->
<!--</script>-->

<!--<style scoped>-->
<!--.tags-container {-->
<!--  padding: 20px;-->
<!--}-->

<!--.card-header {-->
<!--  display: flex;-->
<!--  justify-content: space-between;-->
<!--  align-items: center;-->
<!--}-->

<!--.color-preview {-->
<!--  display: flex;-->
<!--  align-items: center;-->
<!--  gap: 10px;-->
<!--}-->

<!--.color-box {-->
<!--  width: 20px;-->
<!--  height: 20px;-->
<!--  border-radius: 4px;-->
<!--  border: 1px solid #dcdfe6;-->
<!--}-->

<!--.color-value {-->
<!--  margin-left: 10px;-->
<!--  color: #606266;-->
<!--}-->
<!--</style>-->

<template>
  <div class="tags-wrapper">
    <el-card class="tag-card">
      <template #header>
        <div class="card-header">
          <div class="header-left">
            <h2>标签管理</h2>
            <el-tag v-if="workspaceStore.currentWorkspaceId" type="warning" effect="plain" size="small">
              {{ currentWorkspaceName }}
            </el-tag>
          </div>
          <el-button type="primary" @click="showCreateDialog">+ 新增标签</el-button>
        </div>
      </template>

      <el-table
        :data="tags"
        style="width: 100%"
        v-loading="loading"
        border-none
      >
        <el-table-column prop="name" label="标签名称" min-width="160" />
        <el-table-column label="标签颜色" width="200">
          <template #default="{ row }">
            <div class="color-preview">
              <div class="color-dot" :style="{ backgroundColor: row.color }"></div>
              <span class="color-text">{{ row.color }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="180">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="160">
          <template #default="{ row }">
            <el-button type="text" size="default" @click="showEditDialog(row)">
              编辑
            </el-button>
            <el-button type="text" danger size="default" @click="handleDelete(row)">
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 新增/编辑弹窗 -->
    <el-dialog
      v-model="dialogVisible"
      :title="dialogTitle"
      width="460px"
      class="modal"
    >
      <el-form
        :model="tagForm"
        :rules="rules"
        label-width="90px"
        class="tag-form"
      >
        <el-form-item label="标签名称" prop="name">
          <el-input v-model="tagForm.name" placeholder="请输入标签名称" clearable />
        </el-form-item>

        <el-form-item label="标签颜色" prop="color">
          <div class="color-picker-row">
            <el-color-picker v-model="tagForm.color" style="flex:1" />
            <span class="color-value">{{ tagForm.color }}</span>
          </div>
        </el-form-item>
      </el-form>

      <template #footer>
        <div class="dialog-footer">
          <el-button @click="dialogVisible = false">取消</el-button>
          <el-button type="primary" @click="handleSubmit">保存</el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { tagApi } from '@/api/tag'
import { useWorkspaceStore } from '@/pinia/workspaceStore'
import { formatTime } from '@/utils/format'

const workspaceStore = useWorkspaceStore()
const tags = ref([])
const loading = ref(false)
const dialogVisible = ref(false)
const dialogTitle = ref('新增标签')
const isEdit = ref(false)
const currentTagId = ref(null)

const currentWorkspaceName = computed(() => {
  if (!workspaceStore.currentWorkspaceId) return ''
  const ws = workspaceStore.workspaces.find(w => w.id === workspaceStore.currentWorkspaceId)
  return ws ? ws.name : ''
})

const tagForm = ref({
  name: '',
  color: '#409EFF'
})

const rules = {
  name: [{ required: true, message: '请输入标签名称', trigger: 'blur' }],
  color: [{ required: true, message: '请选择标签颜色', trigger: 'change' }]
}

const loadTags = async () => {
  try {
    loading.value = true
    const params = workspaceStore.currentWorkspaceId ? { workspace_id: workspaceStore.currentWorkspaceId } : {}
    const data = await tagApi.getTags(params)
    tags.value = data
  } catch (error) {
    ElMessage.error('加载标签列表失败')
  } finally {
    loading.value = false
  }
}

const showCreateDialog = () => {
  dialogTitle.value = '新增标签'
  isEdit.value = false
  tagForm.value = { name: '', color: '#409EFF' }
  dialogVisible.value = true
}

const showEditDialog = (tag) => {
  dialogTitle.value = '编辑标签'
  isEdit.value = true
  currentTagId.value = tag.id
  tagForm.value = { name: tag.name, color: tag.color }
  dialogVisible.value = true
}

const handleSubmit = async () => {
  try {
    const wsCtx = workspaceStore.currentWorkspaceId ? { workspace_id: workspaceStore.currentWorkspaceId } : {}
    if (isEdit.value) {
      await tagApi.updateTag(currentTagId.value, { ...tagForm.value, ...wsCtx })
      ElMessage.success('标签更新成功')
    } else {
      await tagApi.createTag({ ...tagForm.value, ...wsCtx })
      ElMessage.success('标签创建成功')
    }
    dialogVisible.value = false
    loadTags()
  } catch (error) {
    ElMessage.error(isEdit.value ? '更新失败' : '创建失败')
  }
}

const handleDelete = async (tag) => {
  try {
    await ElMessageBox.confirm('确定要删除该标签吗？', '提示', {
      type: 'warning'
    })
    await tagApi.deleteTag(tag.id)
    ElMessage.success('删除成功')
    loadTags()
  } catch (error) {
    if (error !== 'cancel') ElMessage.error('删除失败')
  }
}

const formatDate = formatTime

onMounted(() => {
  loadTags()
})
</script>

<style scoped>
.tags-wrapper {
  padding: 28px;
  background: var(--bg-secondary);
  min-height: calc(100vh - 65px);
}

.tag-card {
  border-radius: 16px;
  border: none;
  box-shadow: var(--shadow-md);
  overflow: hidden;
  background: var(--bg-primary);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-header h2 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
}

/* 表格样式 */
:deep(.el-table) {
  --el-table-header-text-color: var(--text-secondary);
  --el-table-row-hover-bg-color: var(--bg-secondary);
  --el-table-bg-color: var(--bg-primary);
  --el-table-tr-bg-color: var(--bg-primary);
  --el-table-text-color: var(--text-primary);
}

:deep(.el-table__cell) {
  border-bottom: 1px solid var(--border-light);
  padding: 14px 0;
}

.color-preview {
  display: flex;
  align-items: center;
  gap: 10px;
}

.color-dot {
  width: 22px;
  height: 22px;
  border-radius: 6px;
  border: 1px solid var(--border-light);
}

.color-text {
  color: var(--text-secondary);
  font-size: 13px;
}

/* 表单 */
.tag-form {
  padding: 8px 0;
}

.color-picker-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.color-value {
  color: var(--text-secondary);
  font-size: 13px;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}
</style>