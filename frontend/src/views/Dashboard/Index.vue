
<template>
  <div class="dashboard-wrapper">
    <!-- 统计卡片 -->
    <el-row :gutter="20">
      <el-col :span="6">
        <el-card class="stat-card total-card" @click="goToTasksWithStatus('')">
          <div class="stat-inner">
            <div class="stat-icon">
              <el-icon :size="26"><List /></el-icon>
            </div>
            <div class="stat-text">
              <p class="stat-label">总任务数</p>
              <h3 class="stat-value">{{ taskStats.total }}</h3>
            </div>
          </div>
        </el-card>
      </el-col>

      <el-col :span="6">
        <el-card class="stat-card completed-card" @click="goToTasksWithStatus('completed')">
          <div class="stat-inner">
            <div class="stat-icon">
              <el-icon :size="26"><CircleCheck /></el-icon>
            </div>
            <div class="stat-text">
              <p class="stat-label">已完成</p>
              <h3 class="stat-value">{{ taskStats.completed }}</h3>
            </div>
          </div>
        </el-card>
      </el-col>

      <el-col :span="6">
        <el-card class="stat-card pending-card" @click="goToTasksWithStatus('pending')">
          <div class="stat-inner">
            <div class="stat-icon">
              <el-icon :size="26"><Clock /></el-icon>
            </div>
            <div class="stat-text">
              <p class="stat-label">待办</p>
              <h3 class="stat-value">{{ taskStats.pending }}</h3>
            </div>
          </div>
        </el-card>
      </el-col>

      <el-col :span="6">
        <el-card class="stat-card overdue-card" @click="goToTasksWithStatus('overdue')">
          <div class="stat-inner">
            <div class="stat-icon">
              <el-icon :size="26"><CircleClose /></el-icon>
            </div>
            <div class="stat-text">
              <p class="stat-label">已逾期</p>
              <h3 class="stat-value">{{ taskStats.overdue }}</h3>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 最近任务 -->
    <el-row style="margin-top: 24px">
      <el-col :span="24">
        <el-card class="task-table-card">
          <template #header>
            <div class="table-header">
              <h3>最近任务</h3>
              <el-button type="primary" size="default" @click="goToTasks">
                查看全部
              </el-button>
            </div>
          </template>

          <el-table :data="recentTasks" style="width: 100%" border-none>
            <el-table-column prop="title" label="任务标题" />
            <el-table-column prop="status" label="状态" width="110">
              <template #default="{ row }">
                <el-tag :type="getStatusType(row.status)" class="status-tag">
                  {{ getStatusText(row.status) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="截止日期" width="190">
              <template #default="{ row }">
                {{ formatDate(row.due_date) }}
              </template>
            </el-table-column>
            <el-table-column label="操作" width="120">
              <template #default="{ row }">
                <el-button type="text" size="small" @click="viewTask(row.id)">
                  查看详情
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { List, CircleCheck, Clock, CircleClose } from '@element-plus/icons-vue'
import { useWorkspaceStore } from '@/pinia/workspaceStore'
import { taskApi } from '@/api/task'
import { statisticsApi } from '@/api/statistics'
import { ElMessage } from 'element-plus'
import { formatTime } from '@/utils/format'

const router = useRouter()
const workspaceStore = useWorkspaceStore()

const taskStats = ref({
  total: 0,
  completed: 0,
  pending: 0,
  overdue: 0
})

const recentTasks = ref([])

const getStatusType = (status) => {
  const typeMap = { 
    completed: 'success', 
    pending: 'warning', 
    overdue: 'danger',
    in_progress: 'primary',
    cancelled: 'info'
  }
  return typeMap[status] || 'info'
}

const getStatusText = (status) => {
  const textMap = { 
    completed: '已完成', 
    pending: '待办', 
    overdue: '已逾期',
    in_progress: '进行中',
    cancelled: '已取消'
  }
  return textMap[status] || '未知'
}

const formatDate = formatTime

const goToTasks = () => router.push('/tasks')
const goToTasksWithStatus = (status) => {
  if (status) {
    router.push(`/tasks?status=${status}`)
  } else {
    router.push('/tasks')
  }
}
const viewTask = (id) => id && router.push(`/tasks/${id}`)

const loadStats = async () => {
  try {
    const wsId = workspaceStore.currentWorkspaceId

    // 1. 概览统计（总数 + 完成率）
    let overview = {}
    try {
      overview = await statisticsApi.getOverview(wsId) || {}
    } catch (e) {
      console.warn('获取概览统计失败，降级处理', e)
    }

    // 2. 状态分组统计
    let statusList = []
    try {
      statusList = await statisticsApi.getStatusStats(wsId) || []
    } catch (e) {
      console.warn('获取状态统计失败', e)
    }

    // 3. 转换为前端格式 — 兼容 done/completed、todo/pending 两种状态名
    if (Object.keys(overview).length > 0 || statusList.length > 0) {
      const statusMap = {}
      statusList.forEach(s => {
        // 后端返回 { status, task_d1count, status_name }
        statusMap[s.status] = s.task_count
      })
      taskStats.value = {
        total: overview.total_tasks || 0,
        completed: statusMap['done'] ?? statusMap['completed'] ?? 0,
        pending: statusMap['todo'] ?? statusMap['pending'] ?? 0,
        overdue: statusMap['overdue'] ?? 0
      }
    } else {
      // 降级方案：使用任务列表计算（仅前 100 条）
      const params = { page: 1, page_size: 100 }
      if (wsId) params.workspace_id = wsId
      const data = await taskApi.getTasks(params)
      const tasks = data.tasks || data.items || []
      taskStats.value = {
        total: data.total || tasks.length,
        completed: tasks.filter(t => t.status === 'done' || t.status === 'completed').length,
        pending: tasks.filter(t => t.status === 'todo' || t.status === 'pending').length,
        overdue: tasks.filter(t => t.status === 'overdue').length
      }
      recentTasks.value = tasks.slice(0, 5)
      return
    }

    // 4. 获取最近任务（独立请求）
    try {
      const params = { page: 1, page_size: 5 }
      if (wsId) params.workspace_id = wsId
      const recentData = await taskApi.getTasks(params)
      recentTasks.value = recentData.tasks || recentData.items || []
    } catch (e) {
      recentTasks.value = []
    }
  } catch (error) {
    ElMessage.error('获取统计数据失败')
  }
}

onMounted(() => {
  loadStats()
})

// 切换工作空间时重新加载
watch(() => workspaceStore.currentWorkspaceId, () => {
  loadStats()
})
</script>

<style scoped>
.dashboard-wrapper {
  padding: 28px;
  background: var(--bg-secondary);
  min-height: calc(100vh - 65px);
}

/* 统计卡片 */
.stat-card {
  border-radius: 16px;
  border: none;
  overflow: hidden;
  transition: all 0.3s ease;
  background: var(--bg-primary);
}

.stat-card:hover {
  transform: translateY(-4px);
  box-shadow: var(--shadow-lg);
}

.stat-inner {
  display: flex;
  align-items: center;
  gap: 18px;
  padding: 8px 0;
}

.stat-icon {
  width: 56px;
  height: 56px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
}

.total-card .stat-icon { background: linear-gradient(135deg, #7C3AED, #A78BFA); }
.completed-card .stat-icon { background: linear-gradient(135deg, #10B981, #34D399); }
.pending-card .stat-icon { background: linear-gradient(135deg, #F59E0B, #FBBF24); }
.overdue-card .stat-icon { background: linear-gradient(135deg, #EF4444, #F87171); }

.stat-text {
  flex: 1;
}

.stat-label {
  font-size: 14px;
  color: var(--text-secondary);
  margin: 0 0 4px 0;
}

.stat-value {
  font-size: 28px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0;
  line-height: 1.2;
}

/* 表格卡片 */
.task-table-card {
  border-radius: 16px;
  border: none;
  overflow: hidden;
  box-shadow: var(--shadow-md);
  background: var(--bg-primary);
}

.table-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.table-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
}

:deep(.el-table) {
  --el-table-header-text-color: var(--text-secondary);
  --el-table-row-hover-bg-color: var(--bg-secondary);
  --el-table-bg-color: var(--bg-primary);
  --el-table-tr-bg-color: var(--bg-primary);
  --el-table-text-color: var(--text-primary);
  border: none;
}

:deep(.el-table__header) {
  background: var(--bg-secondary) !important;
}

:deep(.el-table__cell) {
  border-bottom: 1px solid var(--border-light);
  padding: 14px 0;
}

.status-tag {
  border-radius: 6px;
  font-weight: 500;
}
</style>