<!--<template>-->
<!--  <div class="task-card" :class="{ 'completed': task.status === 'completed', 'cancelled': task.status === 'cancelled' }">-->
<!--    <div class="task-header">-->
<!--      <div class="task-info">-->
<!--        <el-checkbox-->
<!--          :model-value="selected"-->
<!--          @change="handleSelect"-->
<!--          class="task-checkbox"-->
<!--        />-->
<!--        <div class="task-priority" :class="`priority-${task.priority}`">-->
<!--          {{ priorityText }}-->
<!--        </div>-->
<!--        <div class="task-status" :class="`status-${task.status}`">-->
<!--          {{ statusText }}-->
<!--        </div>-->
<!--      </div>-->
<!--      <div class="task-actions">-->
<!--        <el-button type="text" size="small" @click="handleEdit">-->
<!--          <el-icon><Edit /></el-icon>-->
<!--        </el-button>-->
<!--        <el-button type="text" size="small" @click="handleDelete">-->
<!--          <el-icon><Delete /></el-icon>-->
<!--        </el-button>-->
<!--      </div>-->
<!--    </div>-->
<!--    -->
<!--    <div class="task-content">-->
<!--      <h3 class="task-title">{{ task.title }}</h3>-->
<!--      <p class="task-description" v-if="task.description">{{ task.description }}</p>-->
<!--      <div class="task-tags" v-if="task.tags && task.tags.length > 0">-->
<!--        <el-tag-->
<!--          v-for="tag in task.tags"-->
<!--          :key="tag.id"-->
<!--          :color="tag.color"-->
<!--          size="small"-->
<!--          effect="plain"-->
<!--        >-->
<!--          {{ tag.name }}-->
<!--        </el-tag>-->
<!--      </div>-->
<!--    </div>-->
<!--    -->
<!--    <div class="task-footer">-->
<!--      <div class="task-meta">-->
<!--        <span class="task-category">{{ categoryText }}</span>-->
<!--        <span class="task-due-date" v-if="task.due_date">-->
<!--          <el-icon><Clock /></el-icon>-->
<!--          {{ formatDate(task.due_date) }}-->
<!--        </span>-->
<!--      </div>-->
<!--      <div class="task-quick-actions">-->
<!--        <el-button-->
<!--          v-if="task.status !== 'completed'"-->
<!--          type="primary"-->
<!--          size="small"-->
<!--          @click="handleComplete"-->
<!--        >-->
<!--          <el-icon><Check /></el-icon>-->
<!--          完成-->
<!--        </el-button>-->
<!--      </div>-->
<!--    </div>-->
<!--  </div>-->
<!--</template>-->

<!--<script setup>-->
<!--import { computed } from 'vue'-->
<!--import { Edit, Delete, Clock, Check } from '@element-plus/icons-vue'-->
<!--import { useCategoryStore } from '@/pinia/categoryStore'-->

<!--const props = defineProps({-->
<!--  task: {-->
<!--    type: Object,-->
<!--    required: true-->
<!--  },-->
<!--  selected: {-->
<!--    type: Boolean,-->
<!--    default: false-->
<!--  }-->
<!--})-->

<!--const emit = defineEmits(['select', 'edit', 'delete', 'complete'])-->

<!--const categoryStore = useCategoryStore()-->

<!--const priorityText = computed(() => {-->
<!--  const priorityMap = {-->
<!--    'low': '低',-->
<!--    'medium': '中',-->
<!--    'high': '高',-->
<!--    'urgent': '紧急'-->
<!--  }-->
<!--  return priorityMap[props.task.priority] || '中'-->
<!--})-->

<!--const statusText = computed(() => {-->
<!--  const statusMap = {-->
<!--    'pending': '待办',-->
<!--    'in_progress': '进行中',-->
<!--    'completed': '已完成',-->
<!--    'cancelled': '已取消'-->
<!--  }-->
<!--  return statusMap[props.task.status] || '待办'-->
<!--})-->

<!--const categoryText = computed(() => {-->
<!--  const category = categoryStore.getCategoryById(props.task.category_id)-->
<!--  return category ? category.name : '未分类'-->
<!--})-->

<!--const formatDate = (date) => {-->
<!--  if (!date) return ''-->
<!--  const d = new Date(date)-->
<!--  return d.toLocaleDateString('zh-CN', {-->
<!--    month: '2-digit',-->
<!--    day: '2-digit',-->
<!--    hour: '2-digit',-->
<!--    minute: '2-digit'-->
<!--  })-->
<!--}-->

<!--const handleSelect = () => {-->
<!--  emit('select', props.task.id)-->
<!--}-->

<!--const handleEdit = () => {-->
<!--  emit('edit', props.task)-->
<!--}-->

<!--const handleDelete = () => {-->
<!--  emit('delete', props.task.id)-->
<!--}-->

<!--const handleComplete = () => {-->
<!--  emit('complete', props.task.id)-->
<!--}-->
<!--</script>-->

<!--<style scoped>-->
<!--.task-card {-->
<!--  background: white;-->
<!--  border-radius: 8px;-->
<!--  padding: 16px;-->
<!--  margin-bottom: 12px;-->
<!--  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);-->
<!--  transition: all 0.3s;-->
<!--  border-left: 4px solid #409EFF;-->
<!--}-->

<!--.task-card:hover {-->
<!--  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.15);-->
<!--  transform: translateY(-2px);-->
<!--}-->

<!--.task-card.completed {-->
<!--  opacity: 0.6;-->
<!--  border-left-color: #67C23A;-->
<!--}-->

<!--.task-card.cancelled {-->
<!--  opacity: 0.4;-->
<!--  border-left-color: #F56C6C;-->
<!--}-->

<!--.task-header {-->
<!--  display: flex;-->
<!--  justify-content: space-between;-->
<!--  align-items: center;-->
<!--  margin-bottom: 12px;-->
<!--}-->

<!--.task-info {-->
<!--  display: flex;-->
<!--  align-items: center;-->
<!--  gap: 12px;-->
<!--}-->

<!--.task-checkbox {-->
<!--  margin-right: 8px;-->
<!--}-->

<!--.task-priority {-->
<!--  padding: 4px 8px;-->
<!--  border-radius: 4px;-->
<!--  font-size: 12px;-->
<!--  font-weight: 500;-->
<!--}-->

<!--.priority-low {-->
<!--  background: #E8F5E9;-->
<!--  color: #67C23A;-->
<!--}-->

<!--.priority-medium {-->
<!--  background: #E6F7FF;-->
<!--  color: #409EFF;-->
<!--}-->

<!--.priority-high {-->
<!--  background: #FEF0F0;-->
<!--  color: #F56C6C;-->
<!--}-->

<!--.priority-urgent {-->
<!--  background: #FEF0F0;-->
<!--  color: #F56C6C;-->
<!--  font-weight: bold;-->
<!--}-->

<!--.task-status {-->
<!--  padding: 4px 8px;-->
<!--  border-radius: 4px;-->
<!--  font-size: 12px;-->
<!--  font-weight: 500;-->
<!--}-->

<!--.status-pending {-->
<!--  background: #F4F4F5;-->
<!--  color: #909399;-->
<!--}-->

<!--.status-in_progress {-->
<!--  background: #E6F7FF;-->
<!--  color: #409EFF;-->
<!--}-->

<!--.status-completed {-->
<!--  background: #E8F5E9;-->
<!--  color: #67C23A;-->
<!--}-->

<!--.status-cancelled {-->
<!--  background: #FEF0F0;-->
<!--  color: #F56C6C;-->
<!--}-->

<!--.task-actions {-->
<!--  display: flex;-->
<!--  gap: 8px;-->
<!--}-->

<!--.task-content {-->
<!--  margin-bottom: 12px;-->
<!--}-->

<!--.task-title {-->
<!--  margin: 0 0 8px 0;-->
<!--  font-size: 16px;-->
<!--  font-weight: 500;-->
<!--  color: #303133;-->
<!--}-->

<!--.task-description {-->
<!--  margin: 0;-->
<!--  font-size: 14px;-->
<!--  color: #606266;-->
<!--  line-height: 1.5;-->
<!--}-->

<!--.task-tags {-->
<!--  display: flex;-->
<!--  gap: 8px;-->
<!--  flex-wrap: wrap;-->
<!--  margin-top: 8px;-->
<!--}-->

<!--.task-tags .el-tag {-->
<!--  border: none;-->
<!--}-->

<!--.task-footer {-->
<!--  display: flex;-->
<!--  justify-content: space-between;-->
<!--  align-items: center;-->
<!--}-->

<!--.task-meta {-->
<!--  display: flex;-->
<!--  gap: 16px;-->
<!--  font-size: 12px;-->
<!--  color: #909399;-->
<!--}-->

<!--.task-category {-->
<!--  display: flex;-->
<!--  align-items: center;-->
<!--  gap: 4px;-->
<!--}-->

<!--.task-due-date {-->
<!--  display: flex;-->
<!--  align-items: center;-->
<!--  gap: 4px;-->
<!--}-->

<!--.task-due-date.overdue {-->
<!--  color: #F56C6C;-->
<!--}-->

<!--.task-quick-actions {-->
<!--  display: flex;-->
<!--  gap: 8px;-->
<!--}-->
<!--</style>-->

<template>
  <div class="task-card" :class="{ completed: task.status === 'completed', cancelled: task.status === 'cancelled' }">
    <div class="task-header">
      <div class="task-info">
        <el-checkbox :model-value="selected" @change="handleSelect" class="task-checkbox" />
        <div class="task-priority" :class="`priority-${task.priority}`">{{ priorityText }}</div>
        <div class="task-status" :class="`status-${task.status}`">{{ statusText }}</div>
        <div class="task-team-badge" v-if="task.is_team_wide">团队</div>
        <div class="task-assignee" v-if="task.assignee_nickname">
          <el-icon><User /></el-icon>
          {{ task.assignee_nickname }}
        </div>
      </div>
      <div class="task-actions">
        <el-button type="text" size="small" @click="handleEdit">
          <el-icon><Edit /></el-icon>
        </el-button>
        <el-button type="text" size="small" @click="handleDelete">
          <el-icon><Delete /></el-icon>
        </el-button>
      </div>
    </div>

    <div class="task-content">
      <h3 class="task-title">{{ task.title }}</h3>
      <p class="task-desc" v-if="task.description">{{ task.description }}</p>
      <div class="task-tags" v-if="task.tags?.length">
        <el-tag
          v-for="tag in task.tags"
          :key="tag.id"
          size="small"
          class="custom-tag"
          :style="{ backgroundColor: tag.color + '15', borderColor: tag.color, color: tag.color }"
        >
          {{ tag.name }}
        </el-tag>
      </div>
    </div>

    <div class="task-footer">
      <div class="task-meta">
        <span class="task-category">{{ categoryText }}</span>
        <span class="task-due" v-if="task.due_date">
          <el-icon><Clock /></el-icon>
          {{ formatDate(task.due_date) }}
        </span>
      </div>
      <div class="task-quick">
        <el-button
          v-if="task.status !== 'completed'"
          type="primary"
          size="small"
          @click="handleComplete"
        >
          <el-icon><Check /></el-icon>完成
        </el-button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { Edit, Delete, Clock, Check, User } from '@element-plus/icons-vue'
import { useCategoryStore } from '@/pinia/categoryStore'

const props = defineProps({
  task: { type: Object, required: true },
  selected: { type: Boolean, default: false }
})

const emit = defineEmits(['select', 'edit', 'delete', 'complete'])
const categoryStore = useCategoryStore()

const priorityText = computed(() => {
  const map = { low: '低', medium: '中', high: '高', urgent: '紧急' }
  return map[props.task.priority] || '中'
})

const statusText = computed(() => {
  const map = { pending: '待办', in_progress: '进行中', completed: '已完成', cancelled: '已取消', overdue: '已逾期' }
  return map[props.task.status] || '待办'
})

const categoryText = computed(() => {
  const cat = categoryStore.getCategoryById(props.task.category_id)
  return cat ? cat.name : '未分类'
})

const formatDate = (date) => {
  if (!date) return ''
  return new Date(date).toLocaleDateString('zh-CN', {
    month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit'
  })
}

const handleSelect = () => emit('select', props.task.id)
const handleEdit = () => emit('edit', props.task)
const handleDelete = () => emit('delete', props.task.id)
const handleComplete = () => emit('complete', props.task.id)
</script>

<style scoped>
.task-card {
  background: var(--bg-primary);
  border-radius: 14px;
  padding: 18px;
  margin-bottom: 14px;
  box-shadow: var(--shadow-md);
  transition: all 0.28s ease;
  border-left: 5px solid var(--primary-color);
}

.task-card:hover {
  box-shadow: var(--shadow-lg);
  transform: translateY(-3px);
}

.task-card.completed {
  opacity: 0.75;
  border-left-color: #67c23a;
}

.task-card.cancelled {
  opacity: 0.55;
  border-left-color: #f56c6c;
}

/* 头部 */
.task-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 14px;
}

.task-info {
  display: flex;
  align-items: center;
  gap: 10px;
}

.task-priority,
.task-status {
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 500;
}

.priority-low { background: #e8f5e9; color: #67c23a; }
.priority-medium { background: #e6f7ff; color: #409eff; }
.priority-high { background: #fef0f0; color: #f56c6c; }
.priority-urgent { background: #fef0f0; color: #f56c6c; font-weight: 600; }

.status-pending { background: #f4f4f5; color: #909399; }
.status-in_progress { background: #e6f7ff; color: #409eff; }
.status-completed { background: #e8f5e9; color: #67c23a; }
.status-cancelled { background: #fef0f0; color: #f56c6c; }
.status-overdue { background: #fef0f0; color: #f56c6c; }

.task-team-badge {
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
  background: #e6f7ff;
  color: #1890ff;
}

.task-assignee {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: var(--text-secondary);
}

.task-actions {
  display: flex;
  gap: 4px;
}

/* 内容 */
.task-content {
  margin-bottom: 16px;
}

.task-title {
  margin: 0 0 10px;
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
}

.task-desc {
  margin: 0 0 10px;
  font-size: 14px;
  color: var(--text-secondary);
  line-height: 1.55;
}

.task-tags {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.custom-tag {
  border-radius: 6px;
  font-weight: 500;
}

/* 底部 */
.task-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.task-meta {
  display: flex;
  gap: 16px;
  font-size: 12px;
  color: var(--text-secondary);
}

.task-due {
  display: flex;
  align-items: center;
  gap: 4px;
}

.task-quick {
  display: flex;
  gap: 8px;
}
</style>