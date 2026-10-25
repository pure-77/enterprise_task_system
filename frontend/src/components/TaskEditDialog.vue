<!--<template>-->
<!--  <el-dialog-->
<!--    v-model="dialogVisible"-->
<!--    :title="isEdit ? '编辑任务' : '新建任务'"-->
<!--    width="600px"-->
<!--    @close="handleClose"-->
<!--  >-->
<!--    <el-form-->
<!--      ref="formRef"-->
<!--      :model="formData"-->
<!--      :rules="formRules"-->
<!--      label-width="100px"-->
<!--    >-->
<!--      <el-form-item label="任务标题" prop="title">-->
<!--        <el-input-->
<!--          v-model="formData.title"-->
<!--          placeholder="请输入任务标题"-->
<!--          maxlength="255"-->
<!--          show-word-limit-->
<!--        />-->
<!--      </el-form-item>-->
<!--      -->
<!--      <el-form-item label="任务描述" prop="description">-->
<!--        <el-input-->
<!--          v-model="formData.description"-->
<!--          type="textarea"-->
<!--          :rows="4"-->
<!--          placeholder="请输入任务描述"-->
<!--          maxlength="1000"-->
<!--          show-word-limit-->
<!--        />-->
<!--      </el-form-item>-->
<!--      -->
<!--      <el-form-item label="任务分类" prop="category_id">-->
<!--        <el-select-->
<!--          v-model="formData.category_id"-->
<!--          placeholder="请选择任务分类"-->
<!--          style="width: 100%"-->
<!--        >-->
<!--          <el-option-->
<!--            v-for="category in categoryStore.categories"-->
<!--            :key="category.id"-->
<!--            :label="category.name"-->
<!--            :value="category.id"-->
<!--          />-->
<!--        </el-select>-->
<!--      </el-form-item>-->
<!--      -->
<!--      <el-form-item label="优先级" prop="priority">-->
<!--        <el-radio-group v-model="formData.priority">-->
<!--          <el-radio label="low">低</el-radio>-->
<!--          <el-radio label="medium">中</el-radio>-->
<!--          <el-radio label="high">高</el-radio>-->
<!--          <el-radio label="urgent">紧急</el-radio>-->
<!--        </el-radio-group>-->
<!--      </el-form-item>-->
<!--      -->
<!--      <el-form-item label="截止日期" prop="due_date">-->
<!--        <el-date-picker-->
<!--          v-model="formData.due_date"-->
<!--          type="datetime"-->
<!--          placeholder="请选择截止日期"-->
<!--          style="width: 100%"-->
<!--          :disabled-date="disabledDate"-->
<!--        />-->
<!--      </el-form-item>-->
<!--      -->
<!--      <el-form-item label="标签" prop="tags">-->
<!--        <el-select-->
<!--          v-model="formData.tags"-->
<!--          multiple-->
<!--          placeholder="请选择标签"-->
<!--          style="width: 100%"-->
<!--        >-->
<!--          <el-option-->
<!--            v-for="tag in tags"-->
<!--            :key="tag.id"-->
<!--            :label="tag.name"-->
<!--            :value="tag.id"-->
<!--          >-->
<!--            <div class="tag-option">-->
<!--              <span class="tag-color" :style="{ backgroundColor: tag.color }"></span>-->
<!--              <span>{{ tag.name }}</span>-->
<!--            </div>-->
<!--          </el-option>-->
<!--        </el-select>-->
<!--      </el-form-item>-->
<!--      -->
<!--      <el-form-item label="任务状态" prop="status" v-if="isEdit">-->
<!--        <el-select-->
<!--          v-model="formData.status"-->
<!--          placeholder="请选择任务状态"-->
<!--          style="width: 100%"-->
<!--        >-->
<!--          <el-option label="待办" value="pending" />-->
<!--          <el-option label="进行中" value="in_progress" />-->
<!--          <el-option label="已完成" value="completed" />-->
<!--          <el-option label="已取消" value="cancelled" />-->
<!--        </el-select>-->
<!--      </el-form-item>-->
<!--    </el-form>-->
<!--    -->
<!--    <template #footer>-->
<!--      <div class="dialog-footer">-->
<!--        <el-button @click="handleClose">取消</el-button>-->
<!--        <el-button type="primary" @click="handleSubmit" :loading="submitting">-->
<!--          {{ isEdit ? '保存' : '创建' }}-->
<!--        </el-button>-->
<!--      </div>-->
<!--    </template>-->
<!--  </el-dialog>-->
<!--</template>-->

<!--<script setup>-->
<!--import { ref, computed, watch, onMounted } from 'vue'-->
<!--import { ElMessage } from 'element-plus'-->
<!--import { useTaskStore } from '@/pinia/taskStore'-->
<!--import { useCategoryStore } from '@/pinia/categoryStore'-->
<!--import { tagApi } from '@/api/tag'-->

<!--const props = defineProps({-->
<!--  modelValue: {-->
<!--    type: Boolean,-->
<!--    default: false-->
<!--  },-->
<!--  task: {-->
<!--    type: Object,-->
<!--    default: null-->
<!--  }-->
<!--})-->

<!--const emit = defineEmits(['update:modelValue', 'success'])-->

<!--const taskStore = useTaskStore()-->
<!--const categoryStore = useCategoryStore()-->

<!--const formRef = ref(null)-->
<!--const submitting = ref(false)-->
<!--const tags = ref([])-->
<!--const formData = ref({-->
<!--  title: '',-->
<!--  description: '',-->
<!--  category_id: null,-->
<!--  priority: 'medium',-->
<!--  due_date: null,-->
<!--  status: 'pending',-->
<!--  tags: []-->
<!--})-->

<!--const formRules = {-->
<!--  title: [-->
<!--    { required: true, message: '请输入任务标题', trigger: 'blur' },-->
<!--    { min: 1, max: 255, message: '标题长度在 1 到 255 个字符', trigger: 'blur' }-->
<!--  ],-->
<!--  category_id: [-->
<!--    { required: true, message: '请选择任务分类', trigger: 'change' }-->
<!--  ]-->
<!--}-->

<!--const dialogVisible = computed({-->
<!--  get: () => props.modelValue,-->
<!--  set: (value) => emit('update:modelValue', value)-->
<!--})-->

<!--const isEdit = computed(() => !!props.task)-->

<!--const disabledDate = (time) => {-->
<!--  return time.getTime() < Date.now() - 8.64e7-->
<!--}-->

<!--const resetForm = () => {-->
<!--  formData.value = {-->
<!--    title: '',-->
<!--    description: '',-->
<!--    category_id: null,-->
<!--    priority: 'medium',-->
<!--    due_date: null,-->
<!--    status: 'pending',-->
<!--    tags: []-->
<!--  }-->
<!--  if (formRef.value) {-->
<!--    formRef.value.resetFields()-->
<!--  }-->
<!--}-->

<!--const loadTags = async () => {-->
<!--  try {-->
<!--    tags.value = await tagApi.getTags()-->
<!--  } catch (error) {-->
<!--    ElMessage.error('加载标签失败')-->
<!--  }-->
<!--}-->

<!--const loadFormData = () => {-->
<!--  if (props.task) {-->
<!--    formData.value = {-->
<!--      title: props.task.title || '',-->
<!--      description: props.task.description || '',-->
<!--      category_id: props.task.category_id || null,-->
<!--      priority: props.task.priority || 'medium',-->
<!--      due_date: props.task.due_date || null,-->
<!--      status: props.task.status || 'pending',-->
<!--      tags: props.task.tags ? props.task.tags.map(t => t.id) : []-->
<!--    }-->
<!--  } else {-->
<!--    resetForm()-->
<!--  }-->
<!--}-->

<!--onMounted(() => {-->
<!--  loadTags()-->
<!--})-->

<!--const handleSubmit = async () => {-->
<!--  if (!formRef.value) return-->
<!--  -->
<!--  try {-->
<!--    await formRef.value.validate()-->
<!--    submitting.value = true-->
<!--    -->
<!--    const submitData = {-->
<!--      ...formData.value,-->
<!--      category_id: Number(formData.value.category_id)-->
<!--    }-->
<!--    -->
<!--    if (isEdit.value) {-->
<!--      await taskStore.updateTask(props.task.id, submitData)-->
<!--    } else {-->
<!--      await taskStore.createTask(submitData)-->
<!--    }-->
<!--    -->
<!--    emit('success')-->
<!--    resetForm()-->
<!--  } catch (error) {-->
<!--    if (error !== false) {-->
<!--      console.error('提交失败:', error)-->
<!--    }-->
<!--  } finally {-->
<!--    submitting.value = false-->
<!--  }-->
<!--}-->

<!--const handleClose = () => {-->
<!--  resetForm()-->
<!--  dialogVisible.value = false-->
<!--}-->

<!--watch(() => props.modelValue, (value) => {-->
<!--  if (value) {-->
<!--    loadFormData()-->
<!--    categoryStore.loadCategories()-->
<!--  }-->
<!--})-->
<!--</script>-->

<!--<style scoped>-->
<!--.dialog-footer {-->
<!--  display: flex;-->
<!--  justify-content: flex-end;-->
<!--  gap: 12px;-->
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
  <el-dialog
    v-model="dialogVisible"
    :title="isEdit ? '编辑任务' : '新建任务'"
    width="580px"
    @close="handleClose"
    class="task-dialog"
  >
    <el-form
      ref="formRef"
      :model="formData"
      :rules="formRules"
      label-width="100px"
      class="task-form"
    >
      <el-form-item label="任务标题" prop="title">
        <el-input
          v-model="formData.title"
          placeholder="请输入任务标题"
          maxlength="255"
          show-word-limit
          clearable
        />
      </el-form-item>

      <el-form-item label="任务描述" prop="description">
        <el-input
          v-model="formData.description"
          type="textarea"
          :rows="4"
          placeholder="请输入任务描述"
          maxlength="1000"
          show-word-limit
        />
      </el-form-item>

      <el-form-item label="任务分类" prop="category_id">
        <el-select
          v-model="formData.category_id"
          placeholder="请选择任务分类"
          style="width: 100%"
          clearable
        >
          <el-option
            v-for="category in categoryStore.categories"
            :key="category.id"
            :label="category.name"
            :value="category.id"
          />
        </el-select>
      </el-form-item>

      <el-form-item label="优先级" prop="priority">
        <el-radio-group v-model="formData.priority" class="priority-group">
          <el-radio label="low">低</el-radio>
          <el-radio label="medium">中</el-radio>
          <el-radio label="high">高</el-radio>
          <el-radio label="urgent">紧急</el-radio>
        </el-radio-group>
      </el-form-item>

      <el-form-item label="截止日期" prop="due_date">
        <el-date-picker
          v-model="formData.due_date"
          type="datetime"
          placeholder="请选择截止日期"
          style="width: 100%"
          :disabled-date="disabledDate"
        />
      </el-form-item>

      <el-form-item label="标签" prop="tags">
        <el-select
          v-model="formData.tags"
          multiple
          placeholder="请选择标签"
          style="width: 100%"
        >
          <el-option
            v-for="tag in tags"
            :key="tag.id"
            :label="tag.name"
            :value="tag.id"
          >
            <div class="tag-option">
              <span class="tag-color" :style="{ backgroundColor: tag.color }"></span>
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

      <el-form-item label="任务状态" prop="status" v-if="isEdit">
        <el-select
          v-model="formData.status"
          placeholder="请选择任务状态"
          style="width: 100%"
        >
          <el-option label="待办" value="pending" />
          <el-option label="进行中" value="in_progress" />
          <el-option label="已完成" value="completed" />
          <el-option label="已取消" value="cancelled" />
        </el-select>
      </el-form-item>
    </el-form>

    <template #footer>
      <div class="dialog-footer">
        <el-button @click="handleClose">取消</el-button>
        <el-button type="primary" @click="handleSubmit" :loading="submitting">
          {{ isEdit ? '保存' : '创建' }}
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { useTaskStore } from '@/pinia/taskStore'
import { useCategoryStore } from '@/pinia/categoryStore'
import { useWorkspaceStore } from '@/pinia/workspaceStore'
import { tagApi } from '@/api/tag'
import { workspaceApi } from '@/api/workspace'

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false
  },
  task: {
    type: Object,
    default: null
  }
})

const emit = defineEmits(['update:modelValue', 'success'])

const taskStore = useTaskStore()
const categoryStore = useCategoryStore()
const workspaceStore = useWorkspaceStore()

const formRef = ref(null)
const submitting = ref(false)
const tags = ref([])
const members = ref([])
const formData = ref({
  title: '',
  description: '',
  category_id: null,
  priority: 'medium',
  due_date: null,
  status: 'pending',
  tags: [],
  assignee_ids: [],  // 多人分配 ID 列表
  is_team_wide: false
})

const formRules = {
  title: [
    { required: true, message: '请输入任务标题', trigger: 'blur' },
    { min: 1, max: 255, message: '标题长度在 1 到 255 个字符', trigger: 'blur' }
  ],
  // category_id: [
  //   { required: true, message: '请选择任务分类', trigger: 'change' }
  // ]
}

const dialogVisible = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value)
})

const isEdit = computed(() => !!props.task)

const isWorkspaceMode = computed(() => !!workspaceStore.currentWorkspaceId)

const canAssign = computed(() => {
  if (!workspaceStore.currentWorkspaceId) return false
  const role = workspaceStore.currentRole
  return role === 'owner' || role === 'admin'
})

const disabledDate = (time) => {
  return time.getTime() < Date.now() - 8.64e7
}

const resetForm = () => {
  formData.value = {
    title: '',
    description: '',
    category_id: null,
    priority: 'medium',
    due_date: null,
    status: 'pending',
    tags: [],
    assignee_ids: [],
    is_team_wide: false
  }
  if (formRef.value) {
    formRef.value.resetFields()
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

const loadFormData = () => {
  if (props.task) {
    // 构建 assignee_ids：从 assignees (多人) 或 assignee_id (单人) 取
    let existingIds = []
    if (props.task.assignees && props.task.assignees.length > 0) {
      existingIds = props.task.assignees.map(a => a.id || a.user_id)
    }
    if (existingIds.length === 0 && props.task.assignee_id) {
      existingIds = [props.task.assignee_id]
    }
    formData.value = {
      title: props.task.title || '',
      description: props.task.description || '',
      category_id: props.task.category_id || null,
      priority: props.task.priority || 'medium',
      due_date: props.task.due_date || null,
      status: props.task.status || 'pending',
      tags: props.task.tags ? props.task.tags.map(t => t.id) : [],
      assignee_ids: existingIds,
      is_team_wide: props.task.is_team_wide || false
    }
  } else {
    resetForm()
  }
}

onMounted(() => {
  loadTags()
})

const handleSubmit = async () => {
  if (!formRef.value) return

  try {
    await formRef.value.validate()
    submitting.value = true

    const submitData = {
      ...formData.value,
      // 无分类时保持 null；Number(null)=0 会导致后端外键约束失败（categories 无 id=0）
      category_id: formData.value.category_id ? Number(formData.value.category_id) : null
    }

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
      await taskStore.updateTask(props.task.id, submitData)
    } else {
      await taskStore.createTask(submitData)
    }

    emit('success')
    resetForm()
  } catch (error) {
    if (error !== false) {
      console.error('提交失败:', error)
    }
  } finally {
    submitting.value = false
  }
}

const handleClose = () => {
  resetForm()
  dialogVisible.value = false
}

watch(() => props.modelValue, (value) => {
  if (value) {
    loadFormData()
    loadTags()
    loadMembers()
    categoryStore.loadCategories()
  }
})
</script>

<style scoped>
/* 弹窗整体 */
:deep(.task-dialog .el-dialog) {
  border-radius: 16px;
  overflow: hidden;
  background: var(--bg-primary);
}

:deep(.task-dialog .el-dialog__header) {
  padding: 20px 24px;
  border-bottom: 1px solid var(--border-light);
  font-weight: 600;
  color: var(--text-primary);
}

:deep(.task-dialog .el-dialog__body) {
  padding: 24px;
  background: var(--bg-primary);
}

:deep(.task-dialog .el-dialog__footer) {
  padding: 16px 24px;
  border-top: 1px solid var(--border-light);
  background: var(--bg-primary);
}

/* 表单 */
.task-form {
  --el-form-label-color: var(--text-primary);
}

:deep(.task-form .el-form-item) {
  margin-bottom: 20px;
}

/* 优先级选项 */
.priority-group {
  display: flex;
  gap: 16px;
}

/* 底部按钮 */
.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

/* 标签选项 */
.tag-option {
  display: flex;
  align-items: center;
  gap: 8px;
}

.tag-color {
  width: 12px;
  height: 12px;
  border-radius: 4px;
  display: inline-block;
}

.field-hint {
  margin-left: 10px;
  font-size: 12px;
  color: var(--text-secondary);
}
</style>