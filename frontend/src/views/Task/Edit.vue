<!--<template>-->
<!--  <div class="task-edit-container">-->
<!--    <el-card>-->
<!--      <template #header>-->
<!--        <div class="card-header">-->
<!--          <span>{{ isEdit ? '编辑任务' : '新建任务' }}</span>-->
<!--          <el-button @click="goBack">返回</el-button>-->
<!--        </div>-->
<!--      </template>-->
<!--      -->
<!--      <el-form-->
<!--        ref="taskForm"-->
<!--        :model="formData"-->
<!--        :rules="rules"-->
<!--        label-width="100px"-->
<!--      >-->
<!--        <el-form-item label="任务标题" prop="title">-->
<!--          <el-input v-model="formData.title" placeholder="请输入任务标题" />-->
<!--        </el-form-item>-->
<!--        -->
<!--        <el-form-item label="分类" prop="category">-->
<!--          <el-select v-model="formData.category_id" placeholder="请选择分类" style="width: 100%">-->
<!--            <el-option-->
<!--              v-for="cat in categories"-->
<!--              :key="cat.id"-->
<!--              :label="cat.name"-->
<!--              :value="cat.id"-->
<!--            />-->
<!--          </el-select>-->
<!--        </el-form-item>-->
<!--        -->
<!--        <el-form-item label="优先级" prop="priority">-->
<!--          <el-select v-model="formData.priority" placeholder="请选择优先级" style="width: 100%">-->
<!--            <el-option label="低" value="low" />-->
<!--            <el-option label="中" value="medium" />-->
<!--            <el-option label="高" value="high" />-->
<!--          </el-select>-->
<!--        </el-form-item>-->
<!--        -->
<!--        <el-form-item label="状态" prop="status">-->
<!--          <el-select v-model="formData.status" placeholder="请选择状态" style="width: 100%">-->
<!--            <el-option label="未开始" value="pending" />-->
<!--            <el-option label="进行中" value="in_progress" />-->
<!--            <el-option label="已完成" value="completed" />-->
<!--            <el-option label="已取消" value="cancelled" />-->
<!--          </el-select>-->
<!--        </el-form-item>-->
<!--        -->
<!--        <el-form-item label="标签" prop="tags">-->
<!--          <el-select-->
<!--            v-model="formData.tags"-->
<!--            multiple-->
<!--            placeholder="请选择标签"-->
<!--            style="width: 100%"-->
<!--          >-->
<!--            <el-option-->
<!--              v-for="tag in tags"-->
<!--              :key="tag.id"-->
<!--              :label="tag.name"-->
<!--              :value="tag.id"-->
<!--            >-->
<!--              <div class="tag-option">-->
<!--                <span class="tag-color" :style="{ backgroundColor: tag.color }"></span>-->
<!--                <span>{{ tag.name }}</span>-->
<!--              </div>-->
<!--            </el-option>-->
<!--          </el-select>-->
<!--        </el-form-item>-->
<!--        -->
<!--        <el-form-item label="截止日期" prop="due_date">-->
<!--          <el-date-picker-->
<!--            v-model="formData.due_date"-->
<!--            type="date"-->
<!--            placeholder="选择截止日期"-->
<!--            style="width: 100%"-->
<!--            format="YYYY-MM-DD"-->
<!--            value-format="YYYY-MM-DD"-->
<!--          />-->
<!--        </el-form-item>-->
<!--        -->
<!--        <el-form-item label="描述" prop="description">-->
<!--          <el-input-->
<!--            v-model="formData.description"-->
<!--            type="textarea"-->
<!--            :rows="4"-->
<!--            placeholder="请输入任务描述"-->
<!--          />-->
<!--        </el-form-item>-->
<!--        -->
<!--        <el-form-item>-->
<!--          <el-button type="primary" @click="handleSubmit">保存</el-button>-->
<!--          <el-button @click="goBack">取消</el-button>-->
<!--        </el-form-item>-->
<!--      </el-form>-->
<!--    </el-card>-->
<!--  </div>-->
<!--</template>-->

<!--<script setup>-->
<!--import { ref, reactive, computed, onMounted } from 'vue'-->
<!--import { useRouter, useRoute } from 'vue-router'-->
<!--import { ElMessage } from 'element-plus'-->
<!--import { categoryApi } from '@/api/category'-->
<!--import { tagApi } from '@/api/tag'-->
<!--import { taskApi } from '@/api/task'-->

<!--const router = useRouter()-->
<!--const route = useRoute()-->

<!--const taskForm = ref(null)-->

<!--const isEdit = computed(() => !!route.params.id)-->

<!--const categories = ref([])-->
<!--const tags = ref([])-->

<!--const formData = reactive({-->
<!--  title: '',-->
<!--  category_id: null,-->
<!--  priority: 'medium',-->
<!--  status: 'pending',-->
<!--  due_date: '',-->
<!--  description: '',-->
<!--  tags: []-->
<!--})-->

<!--const rules = {-->
<!--  title: [-->
<!--    { required: true, message: '请输入任务标题', trigger: 'blur' }-->
<!--  ],-->
<!--  category_id: [-->
<!--    { required: true, message: '请选择分类', trigger: 'change' }-->
<!--  ],-->
<!--  status: [-->
<!--    { required: true, message: '请选择状态', trigger: 'change' }-->
<!--  ],-->
<!--  due_date: [-->
<!--    { required: true, message: '请选择截止日期', trigger: 'change' }-->
<!--  ]-->
<!--}-->

<!--const loadCategories = async () => {-->
<!--  try {-->
<!--    categories.value = await categoryApi.getCategories()-->
<!--  } catch (error) {-->
<!--    ElMessage.error('加载分类失败')-->
<!--  }-->
<!--}-->

<!--const loadTags = async () => {-->
<!--  try {-->
<!--    tags.value = await tagApi.getTags()-->
<!--  } catch (error) {-->
<!--    ElMessage.error('加载标签失败')-->
<!--  }-->
<!--}-->

<!--const loadTaskDetail = async () => {-->
<!--  try {-->
<!--    const task = await taskApi.getTask(route.params.id)-->
<!--    formData.title = task.title-->
<!--    formData.category_id = task.category_id-->
<!--    formData.priority = task.priority-->
<!--    formData.status = task.status-->
<!--    formData.due_date = task.due_date-->
<!--    formData.description = task.description-->
<!--    formData.tags = task.tags ? task.tags.map(t => t.id) : []-->
<!--  } catch (error) {-->
<!--    ElMessage.error('加载任务详情失败')-->
<!--  }-->
<!--}-->

<!--const goBack = () => {-->
<!--  router.back()-->
<!--}-->

<!--const handleSubmit = async () => {-->
<!--  try {-->
<!--    await taskForm.value.validate()-->
<!--    -->
<!--    const submitData = {-->
<!--      title: formData.title,-->
<!--      category_id: formData.category_id,-->
<!--      priority: formData.priority,-->
<!--      status: formData.status,-->
<!--      due_date: formData.due_date,-->
<!--      description: formData.description,-->
<!--      tags: formData.tags-->
<!--    }-->
<!--    -->
<!--    if (isEdit.value) {-->
<!--      await taskApi.updateTask(route.params.id, submitData)-->
<!--      ElMessage.success('更新成功')-->
<!--    } else {-->
<!--      await taskApi.createTask(submitData)-->
<!--      ElMessage.success('创建成功')-->
<!--    }-->
<!--    router.push('/tasks')-->
<!--  } catch (error) {-->
<!--    console.error('表单验证失败:', error)-->
<!--    ElMessage.error(isEdit.value ? '更新失败' : '创建失败')-->
<!--  }-->
<!--}-->

<!--onMounted(async () => {-->
<!--  await Promise.all([-->
<!--    loadCategories(),-->
<!--    loadTags()-->
<!--  ])-->
<!--  -->
<!--  if (isEdit.value) {-->
<!--    await loadTaskDetail()-->
<!--  }-->
<!--})-->
<!--</script>-->

<!--<style scoped>-->
<!--.task-edit-container {-->
<!--  padding: 20px;-->
<!--}-->

<!--.card-header {-->
<!--  display: flex;-->
<!--  justify-content: space-between;-->
<!--  align-items: center;-->
<!--}-->

<!--.tag-option {-->
<!--  display: flex;-->
<!--  align-items: center;-->
<!--  gap: 8px;-->
<!--}-->

<!--.tag-color {-->
<!--  width: 12px;-->
<!--  height: 12px;-->
<!--  border-radius: 2px;-->
<!--  display: inline-block;-->
<!--}-->
<!--</style>-->


<template>
  <div class="task-edit-wrapper">
    <el-card class="edit-card">
      <template #header>
        <div class="card-header">
          <h2>{{ isEdit ? '编辑任务' : '新建任务' }}</h2>
          <el-button size="default" @click="goBack">返回</el-button>
        </div>
      </template>

      <el-form
        ref="taskForm"
        :model="formData"
        :rules="rules"
        label-width="100px"
        class="task-form"
      >
        <el-form-item label="任务标题" prop="title">
          <el-input
            v-model="formData.title"
            placeholder="请输入任务标题"
            size="default"
            clearable
          />
        </el-form-item>

        <el-form-item label="分类" prop="category_id">
          <el-select
            v-model="formData.category_id"
            placeholder="请选择分类"
            size="default"
            style="width: 100%"
          >
            <el-option
              v-for="cat in categories"
              :key="cat.id"
              :label="cat.name"
              :value="cat.id"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="优先级" prop="priority">
          <el-select
            v-model="formData.priority"
            placeholder="请选择优先级"
            size="default"
            style="width: 100%"
          >
            <el-option label="低" value="low" />
            <el-option label="中" value="medium" />
            <el-option label="高" value="high" />
          </el-select>
        </el-form-item>

        <el-form-item label="状态" prop="status">
          <el-select
            v-model="formData.status"
            placeholder="请选择状态"
            size="default"
            style="width: 100%"
          >
            <el-option label="未开始" value="pending" />
            <el-option label="进行中" value="in_progress" />
            <el-option label="已完成" value="completed" />
            <el-option label="已取消" value="cancelled" />
          </el-select>
        </el-form-item>

        <el-form-item label="标签" prop="tags">
          <el-select
            v-model="formData.tags"
            multiple
            placeholder="请选择标签"
            size="default"
            style="width: 100%"
          >
            <el-option
              v-for="tag in tags"
              :key="tag.id"
              :label="tag.name"
              :value="tag.id"
            >
              <div class="tag-option">
                <span class="tag-dot" :style="{ backgroundColor: tag.color }"></span>
                <span>{{ tag.name }}</span>
              </div>
            </el-option>
          </el-select>
        </el-form-item>

        <el-form-item label="指派人" prop="assignee_ids" v-if="isWorkspaceMode && canAssign && !formData.is_team_wide">
          <el-select
            v-model="formData.assignee_ids"
            multiple
            placeholder="不选 = 仅自己可见；选多人 = 多人任务"
            size="default"
            style="width: 100%"
            clearable
          >
            <el-option
              v-for="m in members"
              :key="m.user_id"
              :label="m.nickname || m.email"
              :value="m.user_id"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="团队公开" prop="is_team_wide" v-if="isWorkspaceMode && canAssign">
          <el-switch v-model="formData.is_team_wide" />
          <span class="field-hint">所有成员可见、可编辑</span>
        </el-form-item>

        <el-form-item label="截止日期" prop="due_date">
          <el-date-picker
            v-model="formData.due_date"
            type="date"
            placeholder="选择截止日期"
            style="width: 100%"
            format="YYYY-MM-DD"
            value-format="YYYY-MM-DD"
            size="default"
          />
        </el-form-item>

        <el-form-item label="描述" prop="description">
          <el-input
            v-model="formData.description"
            type="textarea"
            :rows="4"
            placeholder="请输入任务描述"
            size="default"
          />
        </el-form-item>

        <el-form-item class="form-buttons">
          <el-button type="primary" size="default" @click="handleSubmit">
            保存任务
          </el-button>
          <el-button size="default" @click="goBack">取消</el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { categoryApi } from '@/api/category'
import { tagApi } from '@/api/tag'
import { taskApi } from '@/api/task'
import { useWorkspaceStore } from '@/pinia/workspaceStore'
import { workspaceApi } from '@/api/workspace'

const router = useRouter()
const route = useRoute()
const taskForm = ref(null)
const workspaceStore = useWorkspaceStore()

const isEdit = computed(() => !!route.params.id)
const isWorkspaceMode = computed(() => !!workspaceStore.currentWorkspaceId)
const canAssign = computed(() => {
  if (!workspaceStore.currentWorkspaceId) return false
  const role = workspaceStore.currentRole
  return role === 'owner' || role === 'admin'
})

const categories = ref([])
const tags = ref([])
const members = ref([])

const formData = reactive({
  title: '',
  category_id: null,
  priority: 'medium',
  status: 'pending',
  due_date: '',
  description: '',
  tags: [],
  assignee_ids: [],  // 多人分配
  is_team_wide: false
})

const rules = {
  title: [{ required: true, message: '请输入任务标题', trigger: 'blur' }],
  category_id: [{ required: true, message: '请选择分类', trigger: 'change' }],
  status: [{ required: true, message: '请选择状态', trigger: 'change' }],
  due_date: [{ required: true, message: '请选择截止日期', trigger: 'change' }]
}

const loadCategories = async () => {
  try {
    const params = workspaceStore.currentWorkspaceId
      ? { workspace_id: workspaceStore.currentWorkspaceId }
      : {}
    categories.value = await categoryApi.getCategories(params)
  } catch (error) {
    ElMessage.error('加载分类失败')
  }
}

const loadTags = async () => {
  try {
    const params = workspaceStore.currentWorkspaceId
      ? { workspace_id: workspaceStore.currentWorkspaceId }
      : {}
    tags.value = await tagApi.getTags(params)
  } catch (error) {
    ElMessage.error('加载标签失败')
  }
}

const loadMembers = async () => {
  if (!workspaceStore.currentWorkspaceId) return
  try {
    members.value = await workspaceApi.getMembers(workspaceStore.currentWorkspaceId)
  } catch (error) {
    console.error('加载成员列表失败:', error)
  }
}

const loadTaskDetail = async () => {
  try {
    const task = await taskApi.getTask(route.params.id)
    formData.title = task.title
    formData.category_id = task.category_id
    formData.priority = task.priority
    formData.status = task.status
    formData.due_date = task.due_date
    formData.description = task.description
    formData.tags = task.tags ? task.tags.map(t => t.id) : []
    formData.is_team_wide = task.is_team_wide || false
    // assignee_ids
    if (task.assignees && task.assignees.length > 0) {
      formData.assignee_ids = task.assignees.map(a => a.id || a.user_id)
    } else if (task.assignee_id) {
      formData.assignee_ids = [task.assignee_id]
    } else {
      formData.assignee_ids = []
    }
  } catch (error) {
    ElMessage.error('加载任务详情失败')
  }
}

const goBack = () => router.back()

const handleSubmit = async () => {
  try {
    await taskForm.value.validate()
    const submitData = { ...formData }

    // assignee_ids → assignee_id（单人）+ assignee_ids（多人）
    const ids = submitData.assignee_ids || []
    if (ids.length === 0) {
      submitData.assignee_id = null
      submitData.assignee_ids = []
    } else if (ids.length === 1) {
      submitData.assignee_id = ids[0]
      submitData.assignee_ids = [ids[0]]
    } else {
      submitData.assignee_id = ids[0]
      submitData.assignee_ids = ids
    }

    if (isEdit.value) {
      await taskApi.updateTask(route.params.id, submitData)
      ElMessage.success('更新成功')
    } else {
      await taskApi.createTask(submitData)
      ElMessage.success('创建成功')
    }
    router.push('/tasks')
  } catch (error) {
    ElMessage.error(isEdit.value ? '更新失败' : '创建失败')
  }
}

onMounted(async () => {
  await Promise.all([loadCategories(), loadTags(), loadMembers()])
  if (isEdit.value) await loadTaskDetail()
})
</script>

<style scoped>
.task-edit-wrapper {
  padding: 28px;
  background: #f8fafc;
  min-height: calc(100vh - 65px);
}

.edit-card {
  max-width: 720px;
  margin: 0 auto;
  border-radius: 16px;
  border: none;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06);
  overflow: hidden;
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
  color: #1e293b;
}

.task-form {
  padding: 12px 0;
}

.form-buttons {
  display: flex;
  justify-content: center;
  gap: 12px;
  margin-top: 12px;
}

.tag-option {
  display: flex;
  align-items: center;
  gap: 8px;
}

.tag-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
}

.field-hint {
  margin-left: 10px;
  font-size: 12px;
  color: var(--text-secondary);
}
</style>