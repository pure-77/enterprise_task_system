<!--<template>-->
<!--  <div class="task-list-container">-->
<!--    <el-card>-->
<!--      <template #header>-->
<!--        <div class="card-header">-->
<!--          <span>任务列表</span>-->
<!--          <el-button type="primary" @click="createTask">新建任务</el-button>-->
<!--        </div>-->
<!--      </template>-->
<!--      -->
<!--      &lt;!&ndash; 筛选和搜索区域 - 面试考点：筛选条件联动 &ndash;&gt;-->
<!--      <div class="filter-section">-->
<!--        <el-row :gutter="16">-->
<!--          <el-col :span="6">-->
<!--            <el-input-->
<!--              v-model="taskStore.filters.keyword"-->
<!--              placeholder="搜索任务标题或描述"-->
<!--              clearable-->
<!--              @input="handleSearch"-->
<!--            >-->
<!--              <template #prefix>-->
<!--                <el-icon><Search /></el-icon>-->
<!--              </template>-->
<!--            </el-input>-->
<!--          </el-col>-->
<!--          -->
<!--          <el-col :span="4">-->
<!--            <el-select-->
<!--              v-model="taskStore.filters.status"-->
<!--              placeholder="任务状态"-->
<!--              clearable-->
<!--              @change="handleFilterChange"-->
<!--            >-->
<!--              <el-option label="全部状态" :value="null" />-->
<!--              <el-option label="待办" value="pending" />-->
<!--              <el-option label="进行中" value="in_progress" />-->
<!--              <el-option label="已完成" value="completed" />-->
<!--              <el-option label="已取消" value="cancelled" />-->
<!--            </el-select>-->
<!--          </el-col>-->
<!--          -->
<!--          <el-col :span="4">-->
<!--            <el-select-->
<!--              v-model="taskStore.filters.priority"-->
<!--              placeholder="优先级"-->
<!--              clearable-->
<!--              @change="handleFilterChange"-->
<!--            >-->
<!--              <el-option label="全部优先级" :value="null" />-->
<!--              <el-option label="低" value="low" />-->
<!--              <el-option label="中" value="medium" />-->
<!--              <el-option label="高" value="high" />-->
<!--              <el-option label="紧急" value="urgent" />-->
<!--            </el-select>-->
<!--          </el-col>-->
<!--          -->
<!--          <el-col :span="4">-->
<!--            <el-select-->
<!--              v-model="taskStore.filters.category_id"-->
<!--              placeholder="分类"-->
<!--              clearable-->
<!--              @change="handleFilterChange"-->
<!--            >-->
<!--              <el-option label="全部分类" :value="null" />-->
<!--              <el-option-->
<!--                v-for="category in categoryStore.categories"-->
<!--                :key="category.id"-->
<!--                :label="category.name"-->
<!--                :value="category.id"-->
<!--              />-->
<!--            </el-select>-->
<!--          </el-col>-->
<!--          -->
<!--          <el-col :span="4">-->
<!--            <el-select-->
<!--              v-model="taskStore.filters.tag_id"-->
<!--              placeholder="标签"-->
<!--              clearable-->
<!--              @change="handleFilterChange"-->
<!--            >-->
<!--              <el-option label="全部标签" :value="null" />-->
<!--              <el-option-->
<!--                v-for="tag in tags"-->
<!--                :key="tag.id"-->
<!--                :label="tag.name"-->
<!--                :value="tag.id"-->
<!--              >-->
<!--                <div class="tag-option">-->
<!--                  <span class="tag-color" :style="{ backgroundColor: tag.color }"></span>-->
<!--                  <span>{{ tag.name }}</span>-->
<!--                </div>-->
<!--              </el-option>-->
<!--            </el-select>-->
<!--          </el-col>-->
<!--          -->
<!--          <el-col :span="4">-->
<!--            <el-date-picker-->
<!--              v-model="dueDateRange"-->
<!--              type="daterange"-->
<!--              range-separator="至"-->
<!--              start-placeholder="开始日期"-->
<!--              end-placeholder="结束日期"-->
<!--              @change="handleDateRangeChange"-->
<!--            />-->
<!--          </el-col>-->
<!--          -->
<!--          <el-col :span="6">-->
<!--            <div class="filter-actions">-->
<!--              <el-button @click="resetFilters">重置筛选</el-button>-->
<!--            </div>-->
<!--          </el-col>-->
<!--        </el-row>-->
<!--      </div>-->
<!--      -->
<!--      &lt;!&ndash; 批量操作栏 - 面试考点：批量选择逻辑 &ndash;&gt;-->
<!--      <div class="batch-actions" v-if="taskStore.selectedTaskIds.length > 0">-->
<!--        <el-checkbox-->
<!--          :indeterminate="taskStore.isIndeterminate()"-->
<!--          v-model="isAllSelected"-->
<!--          @change="handleSelectAll"-->
<!--        >-->
<!--          已选择 {{ taskStore.selectedTaskIds.length }} 项-->
<!--        </el-checkbox>-->
<!--        -->
<!--        <div class="batch-buttons">-->
<!--          <el-button-->
<!--            type="success"-->
<!--            size="small"-->
<!--            @click="batchMarkCompleted"-->
<!--          >-->
<!--            <el-icon><Check /></el-icon>-->
<!--            标记完成-->
<!--          </el-button>-->
<!--          -->
<!--          <el-button-->
<!--            type="danger"-->
<!--            size="small"-->
<!--            @click="batchDelete"-->
<!--          >-->
<!--            <el-icon><Delete /></el-icon>-->
<!--            批量删除-->
<!--          </el-button>-->
<!--        </div>-->
<!--      </div>-->
<!--      -->
<!--      &lt;!&ndash; 任务列表 - 面试考点：使用任务卡片组件 &ndash;&gt;-->
<!--      <div class="task-list" v-loading="taskStore.loading">-->
<!--        <TaskCard-->
<!--          v-for="task in taskStore.tasks"-->
<!--          :key="task.id"-->
<!--          :task="task"-->
<!--          :selected="taskStore.selectedTaskIds.includes(task.id)"-->
<!--          @select="handleTaskSelect"-->
<!--          @edit="handleTaskEdit"-->
<!--          @delete="handleTaskDelete"-->
<!--          @complete="handleTaskComplete"-->
<!--        />-->
<!--        -->
<!--        &lt;!&ndash; 空状态 - 面试考点：友好的空状态提示 &ndash;&gt;-->
<!--        <el-empty-->
<!--          v-if="taskStore.tasks.length === 0 && !taskStore.loading"-->
<!--          description="暂无任务"-->
<!--        >-->
<!--          <el-button type="primary" @click="createTask">创建第一个任务</el-button>-->
<!--        </el-empty>-->
<!--      </div>-->
<!--      -->
<!--      &lt;!&ndash; 分页 - 面试考点：分页功能 &ndash;&gt;-->
<!--      <div class="pagination" v-if="taskStore.total > 0">-->
<!--        <el-pagination-->
<!--          v-model:current-page="taskStore.currentPage"-->
<!--          v-model:page-size="taskStore.pageSize"-->
<!--          :page-sizes="[10, 20, 50, 100]"-->
<!--          :total="taskStore.total"-->
<!--          layout="total, sizes, prev, pager, next, jumper"-->
<!--          @current-change="handlePageChange"-->
<!--          @size-change="handleSizeChange"-->
<!--        />-->
<!--      </div>-->
<!--    </el-card>-->
<!--    -->
<!--    &lt;!&ndash; 任务编辑对话框 &ndash;&gt;-->
<!--    <TaskEditDialog-->
<!--      v-model="editDialogVisible"-->
<!--      :task="currentEditTask"-->
<!--      @success="handleEditSuccess"-->
<!--    />-->
<!--  </div>-->
<!--</template>-->

<!--<script setup>-->
<!--import { ref, computed, onMounted, watch } from 'vue'-->
<!--import { useRouter } from 'vue-router'-->
<!--import { ElMessage, ElMessageBox } from 'element-plus'-->
<!--import { Search, Check, Delete } from '@element-plus/icons-vue'-->
<!--import { useTaskStore } from '@/pinia/taskStore'-->
<!--import { useCategoryStore } from '@/pinia/categoryStore'-->
<!--import { tagApi } from '@/api/tag'-->
<!--import TaskCard from '@/components/TaskCard.vue'-->
<!--import TaskEditDialog from '@/components/TaskEditDialog.vue'-->

<!--const router = useRouter()-->
<!--const taskStore = useTaskStore()-->
<!--const categoryStore = useCategoryStore()-->

<!--const editDialogVisible = ref(false)-->
<!--const currentEditTask = ref(null)-->
<!--const dueDateRange = ref([])-->
<!--const tags = ref([])-->

<!--const isAllSelected = computed({-->
<!--  get: () => taskStore.isAllSelected(),-->
<!--  set: (value) => {-->
<!--    if (value) {-->
<!--      taskStore.selectAllTasks()-->
<!--    } else {-->
<!--      taskStore.deselectAllTasks()-->
<!--    }-->
<!--  }-->
<!--})-->

<!--// 组件挂载时加载数据 - 面试考点：初始化数据-->
<!--onMounted(async () => {-->
<!--  await categoryStore.loadCategories()-->
<!--  await loadTags()-->
<!--  await taskStore.loadTasks()-->
<!--})-->

<!--const loadTags = async () => {-->
<!--  try {-->
<!--    tags.value = await tagApi.getTags()-->
<!--  } catch (error) {-->
<!--    ElMessage.error('加载标签失败')-->
<!--  }-->
<!--}-->

<!--// 监听筛选条件变化 - 面试考点：筛选条件联动-->
<!--watch(() => taskStore.filters, () => {-->
<!--  taskStore.loadTasks()-->
<!--}, { deep: true })-->

<!--// 监听分页变化-->
<!--watch(() => taskStore.currentPage, () => {-->
<!--  taskStore.loadTasks()-->
<!--})-->

<!--watch(() => taskStore.pageSize, () => {-->
<!--  taskStore.loadTasks()-->
<!--})-->

<!--const createTask = () => {-->
<!--  currentEditTask.value = null-->
<!--  editDialogVisible.value = true-->
<!--}-->

<!--const handleSearch = () => {-->
<!--  taskStore.setCurrentPage(1)-->
<!--  taskStore.loadTasks()-->
<!--}-->

<!--const handleFilterChange = () => {-->
<!--  taskStore.setCurrentPage(1)-->
<!--  taskStore.loadTasks()-->
<!--}-->

<!--const handleDateRangeChange = (value) => {-->
<!--  if (value && value.length === 2) {-->
<!--    taskStore.setFilters({-->
<!--      due_date_start: value[0],-->
<!--      due_date_end: value[1]-->
<!--    })-->
<!--  } else {-->
<!--    taskStore.setFilters({-->
<!--      due_date_start: null,-->
<!--      due_date_end: null-->
<!--    })-->
<!--  }-->
<!--}-->

<!--const resetFilters = () => {-->
<!--  taskStore.resetFilters()-->
<!--  dueDateRange.value = []-->
<!--}-->

<!--const handlePageChange = (page) => {-->
<!--  taskStore.setCurrentPage(page)-->
<!--}-->

<!--const handleSizeChange = (size) => {-->
<!--  taskStore.setPageSize(size)-->
<!--}-->

<!--const handleTaskSelect = (taskId) => {-->
<!--  taskStore.toggleTaskSelection(taskId)-->
<!--}-->

<!--const handleSelectAll = () => {-->
<!--  if (isAllSelected.value) {-->
<!--    taskStore.deselectAllTasks()-->
<!--  } else {-->
<!--    taskStore.selectAllTasks()-->
<!--  }-->
<!--}-->

<!--const handleTaskEdit = (task) => {-->
<!--  currentEditTask.value = task-->
<!--  editDialogVisible.value = true-->
<!--}-->

<!--const handleTaskDelete = async (taskId) => {-->
<!--  try {-->
<!--    await ElMessageBox.confirm('确定要删除这个任务吗？', '提示', {-->
<!--      confirmButtonText: '确定',-->
<!--      cancelButtonText: '取消',-->
<!--      type: 'warning'-->
<!--    })-->
<!--    await taskStore.deleteTask(taskId)-->
<!--  } catch {-->
<!--    // 用户取消删除-->
<!--  }-->
<!--}-->

<!--const handleTaskComplete = async (taskId) => {-->
<!--  await taskStore.updateTaskStatus(taskId, 'completed')-->
<!--}-->

<!--const batchMarkCompleted = async () => {-->
<!--  try {-->
<!--    await ElMessageBox.confirm(-->
<!--      `确定要将选中的 ${taskStore.selectedTaskIds.length} 个任务标记为已完成吗？`,-->
<!--      '提示',-->
<!--      {-->
<!--        confirmButtonText: '确定',-->
<!--        cancelButtonText: '取消',-->
<!--        type: 'success'-->
<!--      }-->
<!--    )-->
<!--    await taskStore.batchUpdateTasks({-->
<!--      task_ids: taskStore.selectedTaskIds,-->
<!--      status: 'completed'-->
<!--    })-->
<!--  } catch {-->
<!--    // 用户取消操作-->
<!--  }-->
<!--}-->

<!--const batchDelete = async () => {-->
<!--  try {-->
<!--    await ElMessageBox.confirm(-->
<!--      `确定要删除选中的 ${taskStore.selectedTaskIds.length} 个任务吗？`,-->
<!--      '提示',-->
<!--      {-->
<!--        confirmButtonText: '确定',-->
<!--        cancelButtonText: '取消',-->
<!--        type: 'warning'-->
<!--      }-->
<!--    )-->
<!--    await taskStore.batchDeleteTasks(taskStore.selectedTaskIds)-->
<!--  } catch {-->
<!--    // 用户取消操作-->
<!--  }-->
<!--}-->

<!--const handleEditSuccess = () => {-->
<!--  editDialogVisible.value = false-->
<!--  taskStore.loadTasks()-->
<!--}-->
<!--</script>-->

<!--<style scoped>-->
<!--.task-list-container {-->
<!--  padding: 20px;-->
<!--}-->

<!--.card-header {-->
<!--  display: flex;-->
<!--  justify-content: space-between;-->
<!--  align-items: center;-->
<!--}-->

<!--.filter-section {-->
<!--  margin-bottom: 20px;-->
<!--  padding-bottom: 20px;-->
<!--  border-bottom: 1px solid #EBEEF5;-->
<!--}-->

<!--.batch-actions {-->
<!--  display: flex;-->
<!--  justify-content: space-between;-->
<!--  align-items: center;-->
<!--  margin-bottom: 20px;-->
<!--  padding: 12px;-->
<!--  background: #F5F7FA;-->
<!--  border-radius: 4px;-->
<!--}-->

<!--.batch-buttons {-->
<!--  display: flex;-->
<!--  gap: 8px;-->
<!--}-->

<!--.task-list {-->
<!--  min-height: 400px;-->
<!--  margin-bottom: 20px;-->
<!--}-->

<!--.pagination {-->
<!--  display: flex;-->
<!--  justify-content: center;-->
<!--  padding: 20px 0;-->
<!--}-->

<!--.filter-actions {-->
<!--  display: flex;-->
<!--  justify-content: flex-end;-->
<!--  align-items: center;-->
<!--  height: 100%;-->
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
  <div class="task-wrapper">
    <el-card class="task-card">
      <template #header>
        <div class="card-header">
          <div class="header-left">
            <h2>任务管理</h2>
            <el-tag v-if="workspaceStore.currentWorkspaceId" type="warning" effect="plain" size="small">
              {{ currentWorkspaceName }}
            </el-tag>
          </div>
          <el-button type="primary" @click="createTask">+ 新建任务</el-button>
        </div>
      </template>

      <!-- 直观版筛选栏 -->
      <div class="filter-container">
        <el-row :gutter="12" align="middle">
          <el-col :span="5">
            <el-input
              v-model="taskStore.filters.keyword"
              placeholder="搜索标题/描述"
              clearable
              @input="handleSearch"
              size="default"
              prefix-icon="Search"
              class="filter-input"
            />
          </el-col>

          <el-col :span="3">
            <el-select
              v-model="taskStore.filters.status"
              placeholder="状态"
              clearable
              @change="handleFilterChange"
              size="default"
            >
              <el-option label="全部" :value="null" />
              <el-option label="待办" value="pending" />
              <el-option label="进行中" value="in_progress" />
              <el-option label="已完成" value="completed" />
              <el-option label="已取消" value="cancelled" />
            </el-select>
          </el-col>

          <el-col :span="3">
            <el-select
              v-model="taskStore.filters.priority"
              placeholder="优先级"
              clearable
              @change="handleFilterChange"
              size="default"
            >
              <el-option label="全部" :value="null" />
              <el-option label="低" value="low" />
              <el-option label="中" value="medium" />
              <el-option label="高" value="high" />
              <el-option label="紧急" value="urgent" />
            </el-select>
          </el-col>

          <el-col :span="3">
            <el-select
              v-model="taskStore.filters.category_id"
              placeholder="分类"
              clearable
              @change="handleFilterChange"
              size="default"
            >
              <el-option label="全部分类" :value="null" />
              <el-option
                v-for="category in categoryStore.categories"
                :key="category.id"
                :label="category.name"
                :value="category.id"
              />
            </el-select>
          </el-col>

          <el-col :span="3">
            <el-select
              v-model="taskStore.filters.tag_id"
              placeholder="标签"
              clearable
              @change="handleFilterChange"
              size="default"
            >
              <el-option label="全部标签" :value="null" />
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
          </el-col>

          <el-col :span="5">
            <el-date-picker
              v-model="dueDateRange"
              type="daterange"
              range-separator="至"
              start-placeholder="开始日期"
              end-placeholder="结束日期"
              @change="handleDateRangeChange"
              size="default"
              style="width:100%"
            />
          </el-col>

          <el-col :span="2">
            <el-button
              type="primary"
              plain
              @click="resetFilters"
              size="default"
              style="width:100%"
            >
              重置
            </el-button>
          </el-col>
        </el-row>

        <el-row :gutter="12" align="middle" style="margin-top: 10px" v-if="workspaceStore.currentWorkspaceId">
          <el-col :span="5">
            <el-select
              v-model="taskStore.filters.assignee_id"
              placeholder="指派人"
              clearable
              @change="handleFilterChange"
              size="default"
              style="width:100%"
            >
              <el-option label="全部" :value="null" />
              <el-option
                v-for="m in filterMembers"
                :key="m.user_id"
                :label="m.nickname || m.email"
                :value="m.user_id"
              />
            </el-select>
          </el-col>
        </el-row>
      </div>

      <!-- 批量操作 -->
      <div class="batch-bar" v-if="taskStore.selectedTaskIds.length > 0">
        <el-checkbox
          :indeterminate="taskStore.isIndeterminate()"
          v-model="isAllSelected"
          @change="handleSelectAll"
        >
          已选择 {{ taskStore.selectedTaskIds.length }} 项
        </el-checkbox>
        <div class="batch-btns">
          <el-button type="success" @click="batchMarkCompleted">
            <el-icon><Check /></el-icon>标记完成
          </el-button>
          <el-button type="danger" @click="batchDelete">
            <el-icon><Delete /></el-icon>批量删除
          </el-button>
        </div>
      </div>

      <!-- 任务列表 -->
      <div class="task-list" v-loading="taskStore.loading">
        <TaskCard
          v-for="task in taskStore.tasks"
          :key="task.id"
          :task="task"
          :selected="taskStore.selectedTaskIds.includes(task.id)"
          @select="handleTaskSelect"
          @edit="handleTaskEdit"
          @delete="handleTaskDelete"
          @complete="handleTaskComplete"
        />

        <el-empty
          v-if="taskStore.tasks.length === 0 && !taskStore.loading"
          description="暂无任务"
          class="empty-box"
        >
          <el-button type="primary" @click="createTask">创建第一个任务</el-button>
        </el-empty>
      </div>

      <!-- 分页 -->
      <div class="page-box" v-if="taskStore.total > 0">
        <el-pagination
          v-model:current-page="taskStore.currentPage"
          v-model:page-size="taskStore.pageSize"
          :page-sizes="[10,20,50]"
          :total="taskStore.total"
          layout="total, sizes, prev, pager, next, jumper"
          @current-change="handlePageChange"
          @size-change="handleSizeChange"
        />
      </div>
    </el-card>

    <TaskEditDialog
      v-model="editDialogVisible"
      :task="currentEditTask"
      @success="handleEditSuccess"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Check, Delete } from '@element-plus/icons-vue'
import { useTaskStore } from '@/pinia/taskStore'
import { useCategoryStore } from '@/pinia/categoryStore'
import { useWorkspaceStore } from '@/pinia/workspaceStore'
import { tagApi } from '@/api/tag'
import { workspaceApi } from '@/api/workspace'
import TaskCard from '@/components/TaskCard.vue'
import TaskEditDialog from '@/components/TaskEditDialog.vue'

const router = useRouter()
const route = useRoute()
const taskStore = useTaskStore()
const categoryStore = useCategoryStore()
const workspaceStore = useWorkspaceStore()

const editDialogVisible = ref(false)
const currentEditTask = ref(null)
const dueDateRange = ref([])
const tags = ref([])
const filterMembers = ref([])

const currentWorkspaceName = computed(() => {
  if (!workspaceStore.currentWorkspaceId) return ''
  const ws = workspaceStore.workspaces.find(w => w.id === workspaceStore.currentWorkspaceId)
  return ws ? ws.name : ''
})

const isAllSelected = computed({
  get: () => taskStore.isAllSelected(),
  set: (value) => {
    if (value) {
      taskStore.selectAllTasks()
    } else {
      taskStore.deselectAllTasks()
    }
  }
})

onMounted(async () => {
  // 检查URL参数中是否有status参数
  const urlParams = new URLSearchParams(window.location.search)
  const statusParam = urlParams.get('status')
  if (statusParam) {
    taskStore.setFilters({ status: statusParam })
  }

  await categoryStore.loadCategories()
  await loadTags()
  await loadFilterMembers()
  await taskStore.loadTasks()
})

// 切换工作空间时重新加载
watch(() => workspaceStore.currentWorkspaceId, async () => {
  await categoryStore.loadCategories()
  await loadTags()
  await loadFilterMembers()
  await taskStore.loadTasks()
})

const loadTags = async () => {
  try {
    const params = workspaceStore.currentWorkspaceId ? { workspace_id: workspaceStore.currentWorkspaceId } : {}
    tags.value = await tagApi.getTags(params)
  } catch (error) {
    ElMessage.error('加载标签失败')
  }
}

const loadFilterMembers = async () => {
  if (!workspaceStore.currentWorkspaceId) {
    filterMembers.value = []
    return
  }
  try {
    filterMembers.value = await workspaceApi.getMembers(workspaceStore.currentWorkspaceId)
  } catch (error) {
    console.error('加载成员列表失败:', error)
  }
}

watch(() => taskStore.filters, () => {
  taskStore.loadTasks()
}, { deep: true })

watch(() => taskStore.currentPage, () => {
  taskStore.loadTasks()
})

watch(() => taskStore.pageSize, () => {
  taskStore.loadTasks()
})

// 监听路由变化，更新筛选条件
watch(() => route.query, (newQuery) => {
  const statusParam = newQuery.status
  if (statusParam) {
    taskStore.setFilters({ status: statusParam })
  } else {
    // 如果没有status参数，重置status筛选条件
    taskStore.setFilters({ status: null })
  }
}, { immediate: true })

const createTask = () => {
  currentEditTask.value = null
  editDialogVisible.value = true
}

const handleSearch = () => {
  taskStore.setCurrentPage(1)
  taskStore.loadTasks()
}

const handleFilterChange = () => {
  taskStore.setCurrentPage(1)
  taskStore.loadTasks()
}

const handleDateRangeChange = (value) => {
  if (value && value.length === 2) {
    taskStore.setFilters({
      due_date_start: value[0],
      due_date_end: value[1]
    })
  } else {
    taskStore.setFilters({
      due_date_start: null,
      due_date_end: null
    })
  }
}

const resetFilters = () => {
  taskStore.resetFilters()
  dueDateRange.value = []
}

const handlePageChange = (page) => {
  taskStore.setCurrentPage(page)
}

const handleSizeChange = (size) => {
  taskStore.setPageSize(size)
}

const handleTaskSelect = (taskId) => {
  taskStore.toggleTaskSelection(taskId)
}

const handleSelectAll = () => {
  if (isAllSelected.value) {
    taskStore.deselectAllTasks()
  } else {
    taskStore.selectAllTasks()
  }
}

const handleTaskEdit = (task) => {
  currentEditTask.value = task
  editDialogVisible.value = true
}

const handleTaskDelete = async (taskId) => {
  try {
    await ElMessageBox.confirm('确定要删除这个任务吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    await taskStore.deleteTask(taskId)
  } catch {}
}

const handleTaskComplete = async (taskId) => {
  await taskStore.updateTaskStatus(taskId, 'completed')
}

const batchMarkCompleted = async () => {
  try {
    await ElMessageBox.confirm(
      `确定要将选中的 ${taskStore.selectedTaskIds.length} 个任务标记为已完成吗？`,
      '提示',
      { type: 'success' }
    )
    await taskStore.batchUpdateTasks({
      task_ids: taskStore.selectedTaskIds,
      status: 'completed'
    })
  } catch {}
}

const batchDelete = async () => {
  try {
    await ElMessageBox.confirm(
      `确定要删除选中的 ${taskStore.selectedTaskIds.length} 个任务吗？`,
      '提示',
      { type: 'warning' }
    )
    await taskStore.batchDeleteTasks(taskStore.selectedTaskIds)
  } catch {}
}

const handleEditSuccess = () => {
  editDialogVisible.value = false
  taskStore.loadTasks()
}
</script>

<style scoped>
.task-wrapper {
  padding: 28px;
  background: var(--bg-secondary);
  min-height: calc(100vh - 65px);
}

.task-card {
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

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.card-header h2 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
}

/* 筛选栏直观优化 */
.filter-container {
  background: var(--bg-secondary);
  padding: 16px;
  border-radius: 12px;
  margin-bottom: 20px;
}

.filter-input,
.filter-select {
  width: 100%;
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

/* 批量操作 */
.batch-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 16px;
  background: var(--bg-secondary);
  border-radius: 12px;
  margin-bottom: 20px;
}

.batch-btns {
  display: flex;
  gap: 10px;
}

/* 任务列表 */
.task-list {
  min-height: 460px;
  margin-bottom: 24px;
}

.empty-box {
  padding: 60px 0;
}

/* 分页 */
.page-box {
  display: flex;
  justify-content: center;
}
</style>