<template>
  <div class="task-detail-container">
    <el-card v-loading="loading">
      <template #header>
        <div class="card-header">
          <span>任务详情</span>
          <el-button @click="goBack">返回</el-button>
        </div>
      </template>
      
      <el-descriptions :column="1" border>
        <el-descriptions-item label="任务标题">{{ task.title }}</el-descriptions-item>
        <el-descriptions-item label="分类">{{ task.category?.name || '' }}</el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag :type="getStatusType(task.status)">{{ getStatusText(task.status) }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="优先级">{{ getPriorityText(task.priority) }}</el-descriptions-item>
        <el-descriptions-item label="指派人" v-if="task.assignee_nickname">
          {{ task.assignee_nickname }}
        </el-descriptions-item>
        <el-descriptions-item label="多人分配" v-if="task.assignee_nicknames?.length">
          <el-tag v-for="name in task.assignee_nicknames" :key="name" size="small" style="margin-right: 6px">{{ name }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="团队公开" v-if="task.is_team_wide">
          <el-tag type="info" size="small">所有成员可见可编辑</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="截止日期">{{ formatDate(task.due_date) }}</el-descriptions-item>
        <el-descriptions-item label="创建时间">{{ formatDate(task.created_at) }}</el-descriptions-item>
        <el-descriptions-item label="更新时间">{{ formatDate(task.updated_at) }}</el-descriptions-item>
        <el-descriptions-item label="描述">{{ task.description }}</el-descriptions-item>
        <el-descriptions-item label="标签">
          <el-tag v-for="tag in task.tags" :key="tag.id" :style="{ backgroundColor: tag.color + '20', borderColor: tag.color, color: tag.color }">
            {{ tag.name }}
          </el-tag>
          <span v-if="!task.tags || task.tags.length === 0">无</span>
        </el-descriptions-item>
      </el-descriptions>
      
      <!-- 团队任务完成进度 -->
      <div class="completion-section" v-if="task.is_team_wide">
        <el-divider />
        <h4>完成进度</h4>
        <div class="completion-progress">
          <el-progress
            :percentage="task.total_members ? Math.round(task.completed_count / task.total_members * 100) : 0"
            :format="() => `${task.completed_count || 0} / ${task.total_members || 0} 人完成`"
            :status="task.completed_count === task.total_members && task.total_members > 0 ? 'success' : ''"
          />
        </div>
        <!-- 已完成成员列表 -->
        <div class="completion-list" v-if="task.completions?.length">
          <el-tag
            v-for="c in task.completions"
            :key="c.user_id"
            type="success"
            size="small"
            style="margin: 4px"
          >
            {{ c.nickname || c.user_id }} ✓ {{ formatDate(c.completed_at) }}
          </el-tag>
        </div>
        <div class="completion-actions" style="margin-top: 12px">
          <el-button type="success" @click="markComplete" :loading="completing">
            我完成了
          </el-button>
        </div>
      </div>

      <div class="action-buttons">
        <el-button type="primary" @click="editTask">编辑</el-button>
        <el-button type="danger" @click="deleteTask">删除</el-button>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { taskApi } from '@/api/task'
import { formatTime } from '@/utils/format'

const router = useRouter()
const route = useRoute()
const loading = ref(false)
const completing = ref(false)

const task = ref({
  id: '',
  title: '',
  category_name: '',
  status: '',
  priority: '',
  due_date: '',
  description: '',
  created_at: '',
  updated_at: ''
})

const getStatusType = (status) => {
  const typeMap = {
    completed: 'success',
    pending: 'warning',
    in_progress: 'info',
    cancelled: 'danger',
    overdue: 'danger'
  }
  return typeMap[status] || 'info'
}

const getStatusText = (status) => {
  const textMap = {
    completed: '已完成',
    pending: '待办',
    in_progress: '进行中',
    cancelled: '已取消',
    overdue: '已逾期'
  }
  return textMap[status] || '未知'
}

const getPriorityText = (priority) => {
  const textMap = {
    low: '低',
    medium: '中',
    high: '高',
    urgent: '紧急'
  }
  return textMap[priority] || '未知'
}

const formatDate = formatTime

const goBack = () => {
  router.back()
}

const editTask = () => {
  router.push(`/tasks/edit/${route.params.id}`)
}

const deleteTask = async () => {
  try {
    await ElMessageBox.confirm('确定要删除这个任务吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    await taskApi.deleteTask(route.params.id)
    ElMessage.success('删除成功')
    router.push('/tasks')
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

const loadTaskDetail = async () => {
  try {
    loading.value = true
    const data = await taskApi.getTask(route.params.id)
    task.value = data
  } catch (error) {
    ElMessage.error('获取任务详情失败')
  } finally {
    loading.value = false
  }
}

const markComplete = async () => {
  try {
    completing.value = true
    await taskApi.completeTeamTask(task.value.id)
    ElMessage.success('已标记完成')
    await loadTaskDetail()  // 刷新进度
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '操作失败')
  } finally {
    completing.value = false
  }
}

onMounted(() => {
  loadTaskDetail()
})
</script>

<style scoped>
.task-detail-container {
  padding: 20px;
  background: var(--bg-secondary);
  min-height: calc(100vh - 65px);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.completion-section h4 {
  margin: 0 0 10px;
  font-size: 14px;
  color: var(--text-primary);
}

.completion-progress {
  margin-bottom: 10px;
}

.completion-list {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.action-buttons {
  margin-top: 20px;
  display: flex;
  gap: 10px;
}

:deep(.el-card) {
  background: var(--bg-primary);
  border: none;
  box-shadow: var(--shadow-md);
}

:deep(.el-descriptions__label) {
  color: var(--text-secondary);
}

:deep(.el-descriptions__content) {
  color: var(--text-primary);
}
</style>
