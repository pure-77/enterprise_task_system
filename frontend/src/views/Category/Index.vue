<!--<template>-->
<!--  <div class="category-container">-->
<!--    <el-card>-->
<!--      <template #header>-->
<!--        <div class="card-header">-->
<!--          <span>分类管理</span>-->
<!--          <el-button type="primary" @click="showCreateDialog">新建分类</el-button>-->
<!--        </div>-->
<!--      </template>-->
<!--      -->
<!--      <el-table :data="categoryStore.categories" style="width: 100%" v-loading="categoryStore.loading">-->
<!--        <el-table-column prop="name" label="分类名称" />-->
<!--        <el-table-column label="颜色" width="120">-->
<!--          <template #default="{ row }">-->
<!--            <div class="color-block" :style="{ backgroundColor: row.color }"></div>-->
<!--          </template>-->
<!--        </el-table-column>-->
<!--        <el-table-column prop="task_count" label="任务数量" width="120" />-->
<!--        <el-table-column label="操作" width="200">-->
<!--          <template #default="{ row }">-->
<!--            <el-button type="text" size="small" @click="editCategory(row)">编辑</el-button>-->
<!--            <el-button type="text" size="small" @click="deleteCategory(row)">删除</el-button>-->
<!--          </template>-->
<!--        </el-table-column>-->
<!--      </el-table>-->
<!--    </el-card>-->
<!--    -->
<!--    <el-dialog-->
<!--      v-model="dialogVisible"-->
<!--      :title="dialogTitle"-->
<!--      width="500px"-->
<!--    >-->
<!--      <el-form-->
<!--        ref="categoryForm"-->
<!--        :model="formData"-->
<!--        :rules="rules"-->
<!--        label-width="100px"-->
<!--      >-->
<!--        <el-form-item label="分类名称" prop="name">-->
<!--          <el-input v-model="formData.name" placeholder="请输入分类名称" />-->
<!--        </el-form-item>-->
<!--        -->
<!--        <el-form-item label="颜色" prop="color">-->
<!--          <el-color-picker v-model="formData.color" show-alpha />-->
<!--        </el-form-item>-->
<!--      </el-form>-->
<!--      -->
<!--      <template #footer>-->
<!--        <el-button @click="dialogVisible = false">取消</el-button>-->
<!--        <el-button type="primary" @click="handleSubmit">确定</el-button>-->
<!--      </template>-->
<!--    </el-dialog>-->
<!--    -->
<!--    <el-dialog-->
<!--      v-model="deleteDialogVisible"-->
<!--      title="删除分类"-->
<!--      width="500px"-->
<!--    >-->
<!--      <p>确定要删除分类 "{{ currentDeleteCategory?.name }}" 吗？</p>-->
<!--      <p v-if="currentDeleteCategory?.task_count > 0">-->
<!--        该分类下有 {{ currentDeleteCategory?.task_count }} 个任务，是否将这些任务迁移到其他分类？-->
<!--      </p>-->
<!--      <el-form v-if="currentDeleteCategory?.task_count > 0">-->
<!--        <el-form-item label="迁移到">-->
<!--          <el-select v-model="moveToCategoryId" placeholder="请选择分类">-->
<!--            <el-option-->
<!--              v-for="category in categoryStore.categories"-->
<!--              :key="category.id"-->
<!--              :label="category.name"-->
<!--              :value="category.id"-->
<!--              :disabled="category.id === currentDeleteCategory?.id"-->
<!--            />-->
<!--          </el-select>-->
<!--        </el-form-item>-->
<!--      </el-form>-->
<!--      -->
<!--      <template #footer>-->
<!--        <el-button @click="deleteDialogVisible = false">取消</el-button>-->
<!--        <el-button type="danger" @click="handleDelete">确定删除</el-button>-->
<!--      </template>-->
<!--    </el-dialog>-->
<!--  </div>-->
<!--</template>-->

<!--<script setup>-->
<!--import { ref, reactive, computed, onMounted } from 'vue'-->
<!--import { ElMessage, ElMessageBox } from 'element-plus'-->
<!--import { useCategoryStore } from '@/pinia/categoryStore'-->

<!--const categoryStore = useCategoryStore()-->

<!--const dialogVisible = ref(false)-->
<!--const deleteDialogVisible = ref(false)-->
<!--const categoryForm = ref(null)-->
<!--const isEdit = ref(false)-->
<!--const currentEditId = ref(null)-->
<!--const currentDeleteCategory = ref(null)-->
<!--const moveToCategoryId = ref(null)-->

<!--const dialogTitle = computed(() => isEdit.value ? '编辑分类' : '新建分类')-->

<!--const formData = reactive({-->
<!--  name: '',-->
<!--  color: '#409EFF'-->
<!--})-->

<!--const rules = {-->
<!--  name: [-->
<!--    { required: true, message: '请输入分类名称', trigger: 'blur' }-->
<!--  ],-->
<!--  color: [-->
<!--    { required: true, message: '请选择分类颜色', trigger: 'blur' }-->
<!--  ]-->
<!--}-->

<!--// 组件挂载时加载分类列表-->
<!--onMounted(async () => {-->
<!--  await categoryStore.loadCategories()-->
<!--})-->

<!--const showCreateDialog = () => {-->
<!--  isEdit.value = false-->
<!--  currentEditId.value = null-->
<!--  formData.name = ''-->
<!--  formData.color = '#409EFF'-->
<!--  dialogVisible.value = true-->
<!--}-->

<!--const editCategory = (category) => {-->
<!--  isEdit.value = true-->
<!--  currentEditId.value = category.id-->
<!--  formData.name = category.name-->
<!--  formData.color = category.color-->
<!--  dialogVisible.value = true-->
<!--}-->

<!--const deleteCategory = (category) => {-->
<!--  currentDeleteCategory.value = category-->
<!--  moveToCategoryId.value = null-->
<!--  deleteDialogVisible.value = true-->
<!--}-->

<!--const handleSubmit = async () => {-->
<!--  try {-->
<!--    await categoryForm.value.validate()-->
<!--    -->
<!--    if (isEdit.value) {-->
<!--      await categoryStore.updateCategory(currentEditId.value, formData)-->
<!--    } else {-->
<!--      await categoryStore.createCategory(formData)-->
<!--    }-->
<!--    -->
<!--    dialogVisible.value = false-->
<!--  } catch (error) {-->
<!--    console.error('表单验证失败:', error)-->
<!--    if (error.response) {-->
<!--      ElMessage.error(error.response.data?.detail || '操作失败，请检查后端服务是否启动')-->
<!--    }-->
<!--  }-->
<!--}-->

<!--const handleDelete = async () => {-->
<!--  try {-->
<!--    await categoryStore.deleteCategory(currentDeleteCategory.value.id, moveToCategoryId.value)-->
<!--    deleteDialogVisible.value = false-->
<!--  } catch (error) {-->
<!--    console.error('删除分类失败:', error)-->
<!--    ElMessage.error(error.response?.data?.detail || '删除失败，请检查后端服务是否启动')-->
<!--  }-->
<!--}-->
<!--</script>-->

<!--<style scoped>-->
<!--.category-container {-->
<!--  padding: 20px;-->
<!--}-->

<!--.card-header {-->
<!--  display: flex;-->
<!--  justify-content: space-between;-->
<!--  align-items: center;-->
<!--}-->

<!--.color-block {-->
<!--  width: 40px;-->
<!--  height: 20px;-->
<!--  border-radius: 4px;-->
<!--}-->
<!--</style>-->


<template>
  <div class="category-wrapper">
    <el-card class="category-card">
      <template #header>
        <div class="card-header">
          <div class="header-left">
            <h2>分类管理</h2>
            <el-tag v-if="workspaceStore.currentWorkspaceId" type="warning" effect="plain" size="small">
              {{ currentWorkspaceName }}
            </el-tag>
          </div>
          <el-button type="primary" @click="showCreateDialog">+ 新建分类</el-button>
        </div>
      </template>

      <el-table
        :data="categoryStore.categories"
        style="width: 100%"
        v-loading="categoryStore.loading"
        border-none
      >
        <el-table-column prop="name" label="分类名称" min-width="180" />
        <el-table-column label="颜色" width="140">
          <template #default="{ row }">
            <div class="color-preview" :style="{ backgroundColor: row.color }"></div>
          </template>
        </el-table-column>
        <el-table-column prop="task_count" label="任务数量" width="130" />
        <el-table-column label="操作" width="180">
          <template #default="{ row }">
            <el-button type="text" size="default" @click="editCategory(row)">
              编辑
            </el-button>
            <el-button type="text" danger size="default" @click="deleteCategory(row)">
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 新建/编辑弹窗 -->
    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="460px" class="modal">
      <el-form ref="categoryForm" :model="formData" :rules="rules" label-width="90px">
        <el-form-item label="分类名称" prop="name">
          <el-input v-model="formData.name" placeholder="请输入分类名称" clearable />
        </el-form-item>
        <el-form-item label="颜色" prop="color">
          <el-color-picker v-model="formData.color" show-alpha style="width:100%" />
        </el-form-item>
      </el-form>

      <template #footer>
        <div class="dialog-footer">
          <el-button @click="dialogVisible = false">取消</el-button>
          <el-button type="primary" @click="handleSubmit">保存</el-button>
        </div>
      </template>
    </el-dialog>

    <!-- 删除弹窗 -->
    <el-dialog v-model="deleteDialogVisible" title="删除分类" width="460px">
      <div class="delete-tip">
        确定要删除分类
        <span class="text-bold">{{ currentDeleteCategory?.name }}</span>
        吗？
      </div>

      <div v-if="currentDeleteCategory?.task_count > 0" class="move-tip">
        该分类下有 {{ currentDeleteCategory?.task_count }} 个任务，请选择迁移目标：
      </div>

      <el-form v-if="currentDeleteCategory?.task_count > 0">
        <el-form-item label="迁移到">
          <el-select v-model="moveToCategoryId" placeholder="请选择分类" style="width:100%">
            <el-option
              v-for="category in categoryStore.categories"
              :key="category.id"
              :label="category.name"
              :value="category.id"
              :disabled="category.id === currentDeleteCategory?.id"
            />
          </el-select>
        </el-form-item>
      </el-form>

      <template #footer>
        <div class="dialog-footer">
          <el-button @click="deleteDialogVisible = false">取消</el-button>
          <el-button type="danger" @click="handleDelete">确认删除</el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { useCategoryStore } from '@/pinia/categoryStore'
import { useWorkspaceStore } from '@/pinia/workspaceStore'

const categoryStore = useCategoryStore()
const workspaceStore = useWorkspaceStore()

const currentWorkspaceName = computed(() => {
  if (!workspaceStore.currentWorkspaceId) return ''
  const ws = workspaceStore.workspaces.find(w => w.id === workspaceStore.currentWorkspaceId)
  return ws ? ws.name : ''
})

const dialogVisible = ref(false)
const deleteDialogVisible = ref(false)
const categoryForm = ref(null)
const isEdit = ref(false)
const currentEditId = ref(null)
const currentDeleteCategory = ref(null)
const moveToCategoryId = ref(null)

const dialogTitle = computed(() => isEdit.value ? '编辑分类' : '新建分类')

const formData = reactive({
  name: '',
  color: '#409EFF'
})

const rules = {
  name: [{ required: true, message: '请输入分类名称', trigger: 'blur' }],
  color: [{ required: true, message: '请选择分类颜色', trigger: 'change' }]
}

onMounted(async () => {
  await categoryStore.loadCategories()
})

const showCreateDialog = () => {
  isEdit.value = false
  currentEditId.value = null
  formData.name = ''
  formData.color = '#409EFF'
  dialogVisible.value = true
}

const editCategory = (category) => {
  isEdit.value = true
  currentEditId.value = category.id
  formData.name = category.name
  formData.color = category.color
  dialogVisible.value = true
}

const deleteCategory = (category) => {
  currentDeleteCategory.value = category
  moveToCategoryId.value = null
  deleteDialogVisible.value = true
}

const handleSubmit = async () => {
  try {
    await categoryForm.value.validate()
    if (isEdit.value) {
      await categoryStore.updateCategory(currentEditId.value, formData)
    } else {
      await categoryStore.createCategory(formData)
    }
    dialogVisible.value = false
  } catch (error) {
    if (error?.response) {
      ElMessage.error(error.response.data?.detail || '操作失败')
    }
  }
}

const handleDelete = async () => {
  try {
    await categoryStore.deleteCategory(currentDeleteCategory.value.id, moveToCategoryId.value)
    deleteDialogVisible.value = false
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '删除失败')
  }
}
</script>

<style scoped>
.category-wrapper {
  padding: 28px;
  background: var(--bg-secondary);
  min-height: calc(100vh - 65px);
}

.category-card {
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
  width: 44px;
  height: 24px;
  border-radius: 6px;
}

/* 弹窗 */
.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

.delete-tip {
  font-size: 14px;
  color: var(--text-primary);
  padding: 10px 0;
}

.move-tip {
  font-size: 13px;
  color: var(--text-secondary);
  margin: 8px 0 16px;
}

.text-bold {
  font-weight: 600;
  color: #f54848;
}
</style>