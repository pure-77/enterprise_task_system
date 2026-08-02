<template>
  <div class="backup-wrapper">
    <el-card class="backup-card">
      <template #header>
        <h2>数据备份</h2>
      </template>

      <el-row :gutter="24">
        <!-- 导出数据 -->
        <el-col :span="12">
          <div class="backup-item">
            <div class="backup-title">
              <h3>导出数据</h3>
              <p class="desc">将您的任务数据导出为 JSON 或 Excel 格式</p>
            </div>

            <div class="btn-group">
              <el-button
                type="primary"
                size="default"
                @click="exportJson"
                :loading="exportingJson"
                class="btn-long"
              >
                <el-icon><Download /></el-icon>
                导出为 JSON
              </el-button>

              <el-button
                type="success"
                size="default"
                @click="exportExcel"
                :loading="exportingExcel"
                class="btn-long"
              >
                <el-icon><Download /></el-icon>
                导出为 Excel
              </el-button>
            </div>

            <div v-if="excelTaskId" class="task-status">
              <el-alert
                :title="excelStatusText"
                :type="excelStatusType"
                :closable="false"
                show-icon
              />
            </div>
          </div>
        </el-col>

        <!-- 导入数据 -->
        <el-col :span="12">
          <div class="backup-item">
            <div class="backup-title">
              <h3>导入数据</h3>
              <p class="desc">从 JSON 文件导入任务数据</p>
            </div>

            <el-upload
              class="upload-box"
              drag
              :http-request="handleUpload"
              :before-upload="beforeUpload"
              :show-file-list="false"
              accept=".json"
            >
              <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
              <div class="el-upload__text">
                将文件拖到此处，或<em>点击上传</em>
              </div>
              <template #tip>
                <div class="el-upload__tip">
                  仅支持 JSON 格式的备份文件
                </div>
              </template>
            </el-upload>

            <div v-if="importTaskId" class="task-status">
              <el-alert
                :title="importStatusText"
                :type="importStatusType"
                :closable="false"
                show-icon
              />
            </div>
          </div>
        </el-col>
      </el-row>

      <el-divider />

      <!-- 备份说明 -->
      <div class="info-box">
        <h3>备份说明</h3>
        <ul class="info-list">
          <li>导出的数据包含任务、分类和标签信息</li>
          <li>JSON 格式适合长期保存和跨平台使用</li>
          <li>Excel 格式方便查看和编辑（通过后台异步生成）</li>
          <li>导入时会自动合并重复的分类和标签</li>
          <li>建议定期备份重要数据</li>
        </ul>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Download, UploadFilled } from '@element-plus/icons-vue'
import { backupApi } from '@/api/backup'

const exportingJson = ref(false)
const exportingExcel = ref(false)
const excelTaskId = ref(null)
const excelStatusText = ref('')
const excelStatusType = ref('info')
const importTaskId = ref(null)
const importStatusText = ref('')
const importStatusType = ref('info')

let excelPollTimer = null
let importPollTimer = null

// 导出 JSON
const exportJson = async () => {
  try {
    exportingJson.value = true
    const response = await backupApi.exportJson()
    const blob = new Blob([response], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `tasks_backup_${new Date().toISOString().slice(0, 10)}.json`
    link.click()
    URL.revokeObjectURL(url)
    ElMessage.success('JSON 导出成功')
  } catch (error) {
    ElMessage.error('JSON 导出失败')
  } finally {
    exportingJson.value = false
  }
}

// 导出 Excel (异步)
const exportExcel = async () => {
  try {
    exportingExcel.value = true
    const { task_id } = await backupApi.exportExcel()
    excelTaskId.value = task_id
    excelStatusText.value = 'Excel 导出任务已提交，正在生成文件...'
    excelStatusType.value = 'info'
    pollExcelTask(task_id)
  } catch (error) {
    ElMessage.error('Excel 导出请求失败')
    exportingExcel.value = false
  }
}

const pollExcelTask = async (taskId) => {
  const poll = async () => {
    try {
      const result = await backupApi.getTaskStatus(taskId)
      if (result.status === 'success') {
        excelStatusText.value = '文件生成完成，正在下载...'
        excelStatusType.value = 'success'
        clearPollTimer('excel')
        await downloadExcelFile(taskId)
        excelTaskId.value = null
        exportingExcel.value = false
        ElMessage.success('Excel 导出成功')
      } else if (result.status === 'failure') {
        excelStatusText.value = result.error || '导出失败'
        excelStatusType.value = 'error'
        clearPollTimer('excel')
        exportingExcel.value = false
      } else {
        excelStatusText.value = result.message || '正在处理中...'
        excelPollTimer = setTimeout(poll, 2000)
      }
    } catch {
      excelPollTimer = setTimeout(poll, 3000)
    }
  }
  poll()
}

const downloadExcelFile = async (taskId) => {
  const blob = await backupApi.downloadFile(taskId)
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `tasks_backup_${new Date().toISOString().slice(0, 10)}.xlsx`
  link.click()
  URL.revokeObjectURL(url)
}

// 上传前校验
const beforeUpload = (file) => {
  const isJson = file.name.endsWith('.json')
  if (!isJson) {
    ElMessage.error('只能上传 JSON 格式的备份文件！')
    return false
  }
  return true
}

// 处理文件上传
const handleUpload = async (options) => {
  try {
    const formData = new FormData()
    formData.append('file', options.file)

    const { task_id } = await backupApi.importData(formData)
    importTaskId.value = task_id
    importStatusText.value = '数据导入任务已提交，正在处理...'
    importStatusType.value = 'info'
    pollImportTask(task_id)
  } catch (error) {
    ElMessage.error('数据导入请求失败')
    options.onError(error)
  }
}

const pollImportTask = async (taskId) => {
  const poll = async () => {
    try {
      const result = await backupApi.getTaskStatus(taskId)
      if (result.status === 'success') {
        const imported = result.result?.imported_tasks || 0
        importStatusText.value = `导入完成`
        importStatusType.value = 'success'
        clearPollTimer('import')
        importTaskId.value = null
        ElMessage.success(`数据导入成功，共导入 ${imported} 条任务`)
      } else if (result.status === 'failure') {
        importStatusText.value = result.error || '导入失败'
        importStatusType.value = 'error'
        clearPollTimer('import')
        ElMessage.error('数据导入失败')
      } else {
        importStatusText.value = result.message || '正在处理中...'
        importPollTimer = setTimeout(poll, 2000)
      }
    } catch {
      importPollTimer = setTimeout(poll, 3000)
    }
  }
  poll()
}

const clearPollTimer = (type) => {
  if (type === 'excel' && excelPollTimer) {
    clearTimeout(excelPollTimer)
    excelPollTimer = null
  }
  if (type === 'import' && importPollTimer) {
    clearTimeout(importPollTimer)
    importPollTimer = null
  }
}
</script>

<style scoped>
.backup-wrapper {
  padding: 28px;
  background: var(--bg-secondary);
  min-height: calc(100vh - 65px);
}

.backup-card {
  border-radius: 16px;
  border: none;
  box-shadow: var(--shadow-md);
  overflow: hidden;
  background: var(--bg-primary);
}

:deep(.el-card__header) {
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
}

/* 卡片模块 */
.backup-item {
  padding: 24px;
  background: var(--bg-secondary);
  border-radius: 14px;
  text-align: center;
}

.backup-title h3 {
  margin: 0 0 8px;
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
}

.desc {
  margin: 0 0 24px;
  color: var(--text-secondary);
  font-size: 14px;
}

/* 按钮组 */
.btn-group {
  display: flex;
  justify-content: center;
  gap: 14px;
}

.btn-long {
  min-width: 140px;
}

/* 任务状态提示 */
.task-status {
  margin-top: 16px;
}

/* 上传区域 */
.upload-box {
  margin-top: 8px;
}

:deep(.el-upload-dragger) {
  border-radius: 10px;
  border-color: var(--border-light);
  background: var(--bg-primary);
}

:deep(.el-upload-dragger:hover) {
  border-color: var(--primary-color);
}

/* 说明区域 */
.info-box {
  padding: 20px 24px;
  background: var(--bg-secondary);
  border-radius: 12px;
}

.info-box h3 {
  margin: 0 0 14px;
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
}

.info-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.info-list li {
  padding: 6px 0 6px 18px;
  color: var(--text-secondary);
  font-size: 14px;
  position: relative;
}

.info-list li::before {
  content: '•';
  position: absolute;
  left: 0;
  color: var(--primary-color);
  font-weight: bold;
}
</style>
