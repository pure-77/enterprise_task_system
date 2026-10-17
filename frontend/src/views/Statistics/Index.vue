<!--<template>-->
<!--  <div class="statistics-container">-->
<!--    <el-card>-->
<!--      <template #header>-->
<!--        <div class="card-header">-->
<!--          <span>任务统计</span>-->
<!--          <el-button type="primary" @click="exportExcel">-->
<!--            <el-icon><Download /></el-icon>-->
<!--            导出Excel-->
<!--          </el-button>-->
<!--        </div>-->
<!--      </template>-->
<!--      -->
<!--      &lt;!&ndash; 概览统计卡片 - 面试考点：数据展示 &ndash;&gt;-->
<!--      <div class="overview-section">-->
<!--        <el-row :gutter="20">-->
<!--          <el-col :span="6">-->
<!--            <el-card class="stat-card">-->
<!--              <div class="stat-content">-->
<!--                <div class="stat-number">{{ overview.today_tasks }}</div>-->
<!--                <div class="stat-label">今日待办</div>-->
<!--              </div>-->
<!--            </el-card>-->
<!--          </el-col>-->
<!--          <el-col :span="6">-->
<!--            <el-card class="stat-card">-->
<!--              <div class="stat-content">-->
<!--                <div class="stat-number">{{ overview.week_completed }}</div>-->
<!--                <div class="stat-label">本周完成</div>-->
<!--              </div>-->
<!--            </el-card>-->
<!--          </el-col>-->
<!--          <el-col :span="6">-->
<!--            <el-card class="stat-card">-->
<!--              <div class="stat-content">-->
<!--                <div class="stat-number">{{ overview.total_tasks }}</div>-->
<!--                <div class="stat-label">总任务数</div>-->
<!--              </div>-->
<!--            </el-card>-->
<!--          </el-col>-->
<!--          <el-col :span="6">-->
<!--            <el-card class="stat-card">-->
<!--              <div class="stat-content">-->
<!--                <div class="stat-number">{{ overview.completion_rate }}%</div>-->
<!--                <div class="stat-label">完成率</div>-->
<!--              </div>-->
<!--            </el-card>-->
<!--          </el-col>-->
<!--        </el-row>-->
<!--      </div>-->
<!--      -->
<!--      &lt;!&ndash; 图表区域 - 面试考点：ECharts图表展示 &ndash;&gt;-->
<!--      <div class="charts-section">-->
<!--        <el-row :gutter="20">-->
<!--          &lt;!&ndash; 分类占比饼图 &ndash;&gt;-->
<!--          <el-col :span="12">-->
<!--            <el-card>-->
<!--              <template #header>-->
<!--                <span>分类任务占比</span>-->
<!--              </template>-->
<!--              <Chart-->
<!--                type="pie"-->
<!--                :data="categoryChartData"-->
<!--                height="300px"-->
<!--              />-->
<!--            </el-card>-->
<!--          </el-col>-->
<!--          -->
<!--          &lt;!&ndash; 状态占比饼图 &ndash;&gt;-->
<!--          <el-col :span="12">-->
<!--            <el-card>-->
<!--              <template #header>-->
<!--                <span>任务状态占比</span>-->
<!--              </template>-->
<!--              <Chart-->
<!--                type="pie"-->
<!--                :data="statusChartData"-->
<!--                height="300px"-->
<!--              />-->
<!--            </el-card>-->
<!--          </el-col>-->
<!--        </el-row>-->
<!--        -->
<!--        &lt;!&ndash; 近7天完成趋势柱状图 &ndash;&gt;-->
<!--        <el-row :gutter="20" style="margin-top: 20px;">-->
<!--          <el-col :span="24">-->
<!--            <el-card>-->
<!--              <template #header>-->
<!--                <span>近7天完成趋势</span>-->
<!--              </template>-->
<!--              <Chart-->
<!--                type="line"-->
<!--                :data="completionTrendData"-->
<!--                height="300px"-->
<!--              />-->
<!--            </el-card>-->
<!--          </el-col>-->
<!--        </el-row>-->
<!--      </div>-->
<!--    </el-card>-->
<!--  </div>-->
<!--</template>-->

<!--<script setup>-->
<!--import { ref, onMounted, computed } from 'vue'-->
<!--import { Download } from '@element-plus/icons-vue'-->
<!--import { ElMessage } from 'element-plus'-->
<!--import { statisticsApi } from '@/api/statistics'-->
<!--import Chart from '@/components/Chart.vue'-->

<!--const overview = ref({-->
<!--  total_tasks: 0,-->
<!--  today_tasks: 0,-->
<!--  week_completed: 0,-->
<!--  completion_rate: 0-->
<!--})-->

<!--const categoryStats = ref([])-->
<!--const statusStats = ref([])-->
<!--const completionTrend = ref([])-->

<!--// 计算分类图表数据-->
<!--const categoryChartData = computed(() => {-->
<!--  return categoryStats.value.map(item => ({-->
<!--    name: item.category_name,-->
<!--    value: item.task_count-->
<!--  }))-->
<!--})-->

<!--// 计算状态图表数据-->
<!--const statusChartData = computed(() => {-->
<!--  return statusStats.value.map(item => ({-->
<!--    name: item.status_name,-->
<!--    value: item.task_count-->
<!--  }))-->
<!--})-->

<!--// 计算完成趋势图表数据-->
<!--const completionTrendData = computed(() => {-->
<!--  return completionTrend.value.map(item => ({-->
<!--    name: item.date,-->
<!--    value: item.completed_count-->
<!--  }))-->
<!--})-->

<!--// 加载统计数据-->
<!--const loadStatistics = async () => {-->
<!--  try {-->
<!--    // 并行请求所有统计数据 - 面试考点：Promise.all优化性能-->
<!--    const [overviewData, categoryData, statusData, trendData] = await Promise.all([-->
<!--      statisticsApi.getOverview(),-->
<!--      statisticsApi.getCategoryStats(),-->
<!--      statisticsApi.getStatusStats(),-->
<!--      statisticsApi.getCompletionTrend()-->
<!--    ])-->
<!--    -->
<!--    overview.value = overviewData-->
<!--    categoryStats.value = categoryData-->
<!--    statusStats.value = statusData-->
<!--    completionTrend.value = trendData-->
<!--  } catch (error) {-->
<!--    ElMessage.error('加载统计数据失败')-->
<!--    console.error('加载统计数据失败:', error)-->
<!--  }-->
<!--}-->

<!--// 导出Excel-->
<!--const exportExcel = async () => {-->
<!--  try {-->
<!--    const response = await statisticsApi.exportTasksExcel()-->
<!--    -->
<!--    // 创建下载链接 - 面试考点：blob文件下载-->
<!--    const blob = new Blob([response.data], {-->
<!--      type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'-->
<!--    })-->
<!--    -->
<!--    const url = URL.createObjectURL(blob)-->
<!--    const link = document.createElement('a')-->
<!--    link.href = url-->
<!--    link.download = `tasks_${new Date().toISOString().split('T')[0]}.xlsx`-->
<!--    link.click()-->
<!--    URL.revokeObjectURL(url)-->
<!--    -->
<!--    ElMessage.success('导出成功')-->
<!--  } catch (error) {-->
<!--    ElMessage.error('导出失败')-->
<!--    console.error('导出失败:', error)-->
<!--  }-->
<!--}-->

<!--// 组件挂载时加载数据-->
<!--onMounted(() => {-->
<!--  loadStatistics()-->
<!--})-->
<!--</script>-->

<!--<style scoped>-->
<!--.statistics-container {-->
<!--  padding: 20px;-->
<!--}-->

<!--.card-header {-->
<!--  display: flex;-->
<!--  justify-content: space-between;-->
<!--  align-items: center;-->
<!--}-->

<!--.overview-section {-->
<!--  margin-bottom: 20px;-->
<!--}-->

<!--.stat-card {-->
<!--  height: 120px;-->
<!--  display: flex;-->
<!--  align-items: center;-->
<!--  justify-content: center;-->
<!--  transition: all 0.3s;-->
<!--}-->

<!--.stat-card:hover {-->
<!--  transform: translateY(-2px);-->
<!--  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);-->
<!--}-->

<!--.stat-content {-->
<!--  text-align: center;-->
<!--}-->

<!--.stat-number {-->
<!--  font-size: 24px;-->
<!--  font-weight: bold;-->
<!--  color: #409EFF;-->
<!--  margin-bottom: 8px;-->
<!--}-->

<!--.stat-label {-->
<!--  font-size: 14px;-->
<!--  color: #606266;-->
<!--}-->

<!--.charts-section {-->
<!--  margin-top: 20px;-->
<!--}-->
<!--</style>-->

<template>
  <div class="statistics-wrapper">
    <el-card class="stat-card-main">
      <template #header>
        <div class="card-header">
          <h2>任务统计</h2>
          <el-button type="primary" @click="exportExcel">
            <el-icon><Download /></el-icon>
            导出Excel
          </el-button>
        </div>
      </template>

      <div class="overview-section">
        <el-row :gutter="20">
          <el-col :span="6">
            <el-card class="stat-item today-card">
              <div class="stat-inner">
                <div class="stat-value">{{ overview.today_tasks }}</div>
                <div class="stat-desc">今日待办</div>
              </div>
            </el-card>
          </el-col>

          <el-col :span="6">
            <el-card class="stat-item week-card">
              <div class="stat-inner">
                <div class="stat-value">{{ overview.week_completed }}</div>
                <div class="stat-desc">本周完成</div>
              </div>
            </el-card>
          </el-col>

          <el-col :span="6">
            <el-card class="stat-item total-card">
              <div class="stat-inner">
                <div class="stat-value">{{ overview.total_tasks }}</div>
                <div class="stat-desc">总任务数</div>
              </div>
            </el-card>
          </el-col>

          <el-col :span="6">
            <el-card class="stat-item rate-card">
              <div class="stat-inner">
                <div class="stat-value">{{ overview.completion_rate }}%</div>
                <div class="stat-desc">完成率</div>
              </div>
            </el-card>
          </el-col>
        </el-row>
      </div>

      <div class="charts-section">
        <el-row :gutter="20">
          <el-col :span="12">
            <el-card class="chart-card">
              <template #header>
                <div class="chart-title">分类任务占比</div>
              </template>
              <Chart type="pie" :data="categoryChartData" height="300px" />
            </el-card>
          </el-col>

          <el-col :span="12">
            <el-card class="chart-card">
              <template #header>
                <div class="chart-title">任务状态占比</div>
              </template>
              <Chart type="pie" :data="statusChartData" height="300px" />
            </el-card>
          </el-col>
        </el-row>

        <el-row :gutter="20" style="margin-top: 20px">
          <el-col :span="24">
            <el-card class="chart-card">
              <template #header>
                <div class="chart-title">近7天完成趋势</div>
              </template>
              <Chart type="line" :data="completionTrendData" height="300px" />
            </el-card>
          </el-col>
        </el-row>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted, computed, watch } from 'vue'
import { Download } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { statisticsApi } from '@/api/statistics'
import { useWorkspaceStore } from '@/pinia/workspaceStore'
import Chart from '@/components/Chart.vue'

const workspaceStore = useWorkspaceStore()

const overview = ref({
  total_tasks: 0,
  today_tasks: 0,
  week_completed: 0,
  completion_rate: 0
})

const categoryStats = ref([])
const statusStats = ref([])
const completionTrend = ref([])

const categoryChartData = computed(() => {
  return categoryStats.value.map(item => ({
    name: item.category_name,
    value: item.task_count
  }))
})

const statusChartData = computed(() => {
  return statusStats.value.map(item => ({
    name: item.status_name,
    value: item.task_count
  }))
})

const completionTrendData = computed(() => {
  return completionTrend.value.map(item => ({
    name: item.date,
    value: item.completed_count
  }))
})

const loadStatistics = async () => {
  try {
    const wsId = workspaceStore.currentWorkspaceId
    const [overviewData, categoryData, statusData, trendData] = await Promise.all([
      statisticsApi.getOverview(wsId),
      statisticsApi.getCategoryStats(wsId),
      statisticsApi.getStatusStats(wsId),
      statisticsApi.getCompletionTrend(7, wsId)
    ])
    overview.value = overviewData
    categoryStats.value = categoryData
    statusStats.value = statusData
    completionTrend.value = trendData
  } catch (error) {
    ElMessage.error('加载统计数据失败')
  }
}

// ✅ 修复后的导出Excel（关键！）
const exportExcel = async () => {
  try {
    const response = await statisticsApi.exportTasksExcel({
      responseType: 'blob'  // 必须加这个！
    })

    const blob = new Blob([response], {
      type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    })

    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `任务报表_${new Date().toLocaleDateString()}.xlsx`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)

    ElMessage.success('Excel 导出成功！')
  } catch (error) {
    ElMessage.error('导出失败')
    console.error(error)
  }
}

onMounted(() => {
  loadStatistics()
})

// 切换工作空间时重新加载
watch(() => workspaceStore.currentWorkspaceId, () => {
  loadStatistics()
})
</script>

<style scoped>
.statistics-wrapper {
  padding: 28px;
  background: var(--bg-secondary);
  min-height: calc(100vh - 65px);
}

.stat-card-main {
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

.overview-section {
  margin-bottom: 28px;
}

.stat-item {
  border-radius: 14px;
  border: none;
  transition: all 0.3s ease;
  overflow: hidden;
  background: var(--bg-primary);
}

.stat-item:hover {
  transform: translateY(-4px);
  box-shadow: var(--shadow-lg);
}

.stat-inner {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 12px 0;
}

.stat-value {
  font-size: 28px;
  font-weight: 700;
  color: var(--primary-color);
  margin-bottom: 6px;
}

.stat-desc {
  font-size: 14px;
  color: var(--text-secondary);
}

.today-card .stat-value { color: #409eff; }
.week-card .stat-value { color: #26c66f; }
.total-card .stat-value { color: #722ed1; }
.rate-card .stat-value { color: #fa8c16; }

.charts-section {
  margin-top: 12px;
}

.chart-card {
  border-radius: 14px;
  border: none;
  box-shadow: var(--shadow-sm);
  background: var(--bg-primary);
}

.chart-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
}
</style>