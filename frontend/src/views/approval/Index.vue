<template>
  <div class="page">
    <div class="page-head"><h2>OA 审批</h2></div>
    <el-tabs v-model="tab" @tab-change="onTabChange">
      <el-tab-pane label="待我审批" name="pending" />
      <el-tab-pane label="我发起的" name="my" />
      <el-tab-pane label="我已审批" name="processed" />
      <el-tab-pane label="审批模板" name="templates" />
    </el-tabs>

    <!-- 审批列表 -->
    <template v-if="tab !== 'templates'">
      <div class="action-bar">
        <el-button type="primary" @click="openSubmit">+ 发起审批</el-button>
      </div>
      <el-table :data="list" v-loading="loading" stripe>
        <el-table-column prop="title" label="标题" min-width="200">
          <template #default="{ row }">
            <div class="title-cell">
              <el-tag :type="categoryType(row.template_category)" size="small" effect="plain" class="cat-tag">
                {{ categoryLabel(row.template_category) }}
              </el-tag>
              <span>{{ row.title }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="template_name" label="模板" width="120" />
        <el-table-column prop="applicant_name" label="申请人" width="100" />
        <el-table-column label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="statusType(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="100">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="$router.push(`/approval/${row.id}`)">查看</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-pagination v-model:current-page="p" :total="total" layout="prev,next,total" @current-change="load" />
    </template>

    <!-- 模板管理 -->
    <template v-else>
      <div class="tpl-grid" v-loading="loading">
        <el-card v-for="t in templates" :key="t.id" class="tpl-card" shadow="hover" @click="openSubmitFromTemplate(t)">
          <div class="tpl-icon" :style="{ background: categoryColor(t.category) }">
            <el-icon :size="24"><component :is="iconComp(t.icon)" /></el-icon>
          </div>
          <div class="tpl-meta">
            <div class="tpl-name">
              {{ t.name }}
              <el-tag v-if="t.is_builtin" size="small" type="info" effect="plain">内置</el-tag>
            </div>
            <div class="tpl-desc">{{ t.description || '无说明' }}</div>
            <div class="tpl-cat">{{ categoryLabel(t.category) }} · {{ fieldCount(t) }}个字段</div>
          </div>
        </el-card>
        <el-empty v-if="!loading && !templates.length" description="暂无模板" />
      </div>
    </template>

    <!-- 发起审批弹窗：第一步 选模板 -->
    <el-dialog v-model="showSubmit" title="发起审批" width="640px" :close-on-click-modal="false">
      <!-- 步骤一：选择模板 -->
      <div v-if="!selectedTpl" class="tpl-pick">
        <p class="pick-tip">请选择审批类型</p>
        <div class="pick-grid">
          <div v-for="t in templates" :key="t.id" class="pick-item" @click="pickTemplate(t)">
            <div class="pick-icon" :style="{ background: categoryColor(t.category) }">
              <el-icon :size="22"><component :is="iconComp(t.icon)" /></el-icon>
            </div>
            <div class="pick-name">{{ t.name }}</div>
            <div class="pick-desc">{{ t.description || '' }}</div>
          </div>
        </div>
      </div>

      <!-- 步骤二：填写表单 -->
      <div v-else>
        <div class="form-head">
          <el-button link @click="backToPick"><el-icon><ArrowLeft /></el-icon> 重新选择</el-button>
          <h3 class="form-title">
            <el-icon><component :is="iconComp(selectedTpl.icon)" /></el-icon>
            {{ selectedTpl.name }}
          </h3>
        </div>
        <el-form label-width="110px" class="submit-form">
          <el-form-item label="标题">
            <el-input v-model="submitTitle" placeholder="审批标题（默认使用模板名）" />
          </el-form-item>
          <el-form-item
            v-for="f in formFields"
            :key="f.key"
            :label="f.label"
            :required="f.required"
          >
            <el-input
              v-if="f.type === 'input'"
              v-model="formData[f.key]"
              :placeholder="f.placeholder || ''"
            />
            <el-input
              v-else-if="f.type === 'textarea'"
              v-model="formData[f.key]"
              type="textarea"
              :rows="3"
              :placeholder="f.placeholder || ''"
            />
            <el-input-number
              v-else-if="f.type === 'number'"
              v-model="formData[f.key]"
              :min="0"
              :step="f.key === 'days' ? 0.5 : 1"
              controls-position="right"
              style="width:100%"
            />
            <el-input-number
              v-else-if="f.type === 'money'"
              v-model="formData[f.key]"
              :min="0"
              :precision="2"
              :step="100"
              controls-position="right"
              style="width:100%"
            />
            <el-date-picker
              v-else-if="f.type === 'date'"
              v-model="formData[f.key]"
              type="date"
              value-format="YYYY-MM-DD"
              style="width:100%"
            />
            <el-date-picker
              v-else-if="f.type === 'datetime'"
              v-model="formData[f.key]"
              type="datetime"
              value-format="YYYY-MM-DD HH:mm"
              style="width:100%"
            />
            <el-select
              v-else-if="f.type === 'select'"
              v-model="formData[f.key]"
              style="width:100%"
            >
              <el-option v-for="opt in (f.options || [])" :key="opt" :label="opt" :value="opt" />
            </el-select>
            <el-input v-else v-model="formData[f.key]" />
          </el-form-item>
        </el-form>
      </div>

      <template #footer>
        <el-button @click="showSubmit = false">取消</el-button>
        <el-button v-if="selectedTpl" type="primary" @click="doSubmit" :loading="submitting">提交审批</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { ArrowLeft, Calendar, Money, Position, Clock, Document, DocumentChecked, EditPen } from '@element-plus/icons-vue'
import { approvalApi } from '@/api/approval'
import { useWorkspaceStore } from '@/pinia/workspaceStore'
const wsStore = useWorkspaceStore()
const wsId = () => wsStore.currentWorkspaceId

const tab = ref('pending')
const list = ref([])
const templates = ref([])
const loading = ref(false)
const p = ref(1)
const total = ref(0)

// 发起审批状态
const showSubmit = ref(false)
const selectedTpl = ref(null)
const submitTitle = ref('')
const formData = ref({})
const submitting = ref(false)

const statusMap = { pending: '审批中', approved: '已通过', rejected: '已驳回', recalled: '已撤回', cancelled: '已取消' }
const statusTypeMap = { pending: 'warning', approved: 'success', rejected: 'danger', recalled: 'info', cancelled: 'info' }
function statusLabel(s) { return statusMap[s] || s }
function statusType(s) { return statusTypeMap[s] || 'info' }

const categoryMap = { leave: '请假', expense: '报销', travel: '出差', overtime: '加班', custom: '通用' }
const categoryColors = { leave: '#7C3AED', expense: '#F59E0B', travel: '#06B6D4', overtime: '#EF4444', custom: '#64748B' }
function categoryLabel(c) { return categoryMap[c] || '其他' }
function categoryColor(c) { return categoryColors[c] || '#64748B' }
function categoryType(c) {
  return ({ leave: 'warning', expense: 'danger', travel: 'primary', overtime: 'warning', custom: 'info' })[c] || 'info'
}

// 图标组件映射
const iconMap = { Calendar, Money, Position, Clock, Document, DocumentChecked }
function iconComp(name) { return iconMap[name] || Document }

const formFields = computed(() => selectedTpl.value?.form_schema?.fields || [])

function fieldCount(t) { return t?.form_schema?.fields?.length || 0 }

async function load() {
  loading.value = true
  try {
    if (tab.value === 'templates') {
      templates.value = (await approvalApi.getTemplates(wsId())) || []
      return
    }
    let res
    if (tab.value === 'pending') res = await approvalApi.getPending(wsId(), { page: p.value })
    else if (tab.value === 'my') res = await approvalApi.getMyApplications(wsId(), { page: p.value })
    else if (tab.value === 'processed') res = await approvalApi.getProcessed(wsId(), { page: p.value })
    const d = res
    list.value = d.items || d || []
    total.value = d.total || 0
  } finally { loading.value = false }
}

function onTabChange() { p.value = 1; load() }

// ====== 发起审批 ======
async function openSubmit() {
  selectedTpl.value = null
  submitTitle.value = ''
  formData.value = {}
  showSubmit.value = true
  if (!templates.value.length) {
    try { templates.value = (await approvalApi.getTemplates(wsId())) || [] } catch {}
  }
}

function openSubmitFromTemplate(t) {
  selectedTpl.value = null
  pickTemplate(t)
  showSubmit.value = true
}

function pickTemplate(t) {
  selectedTpl.value = t
  submitTitle.value = t.name
  formData.value = {}
  // 初始化默认值
  for (const f of (t.form_schema?.fields || [])) {
    if (f.type === 'select' && f.options?.length) formData.value[f.key] = f.options[0]
    else formData.value[f.key] = f.type === 'number' || f.type === 'money' ? 0 : ''
  }
}

function backToPick() {
  selectedTpl.value = null
  submitTitle.value = ''
  formData.value = {}
}

async function doSubmit() {
  if (!selectedTpl.value) return ElMessage.warning('请选择审批类型')
  if (!submitTitle.value.trim()) return ElMessage.warning('请填写标题')
  // 校验必填
  for (const f of formFields.value) {
    if (f.required) {
      const v = formData.value[f.key]
      if (v === '' || v === null || v === undefined) {
        return ElMessage.warning(`请填写「${f.label}」`)
      }
    }
  }
  submitting.value = true
  try {
    await approvalApi.submit({
      template_id: selectedTpl.value.id,
      title: submitTitle.value.trim(),
      form_data: { ...formData.value }
    })
    ElMessage.success('已提交')
    showSubmit.value = false
    selectedTpl.value = null
    load()
  } catch { /* 拦截器已提示错误 */ }
  finally { submitting.value = false }
}

onMounted(() => load())
</script>
<style scoped>
.page { padding: 0; }
.page-head h2 { font-size: 22px; font-weight: 700; margin: 0 0 16px; color: var(--text-primary); }
.action-bar { margin-bottom: 16px; }

.title-cell { display: flex; align-items: center; gap: 8px; }
.cat-tag { flex-shrink: 0; }

/* 模板网格 */
.tpl-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 16px; }
.tpl-card { cursor: pointer; transition: transform 0.15s; }
.tpl-card:hover { transform: translateY(-2px); }
.tpl-card :deep(.el-card__body) { display: flex; gap: 14px; align-items: flex-start; }
.tpl-icon { width: 48px; height: 48px; border-radius: 10px; display: flex; align-items: center; justify-content: center; color: #fff; flex-shrink: 0; }
.tpl-meta { flex: 1; min-width: 0; }
.tpl-name { font-size: 15px; font-weight: 600; display: flex; align-items: center; gap: 6px; }
.tpl-desc { font-size: 12px; color: var(--text-secondary); margin: 4px 0; }
.tpl-cat { font-size: 11px; color: var(--text-tertiary); }

/* 选择模板 */
.tpl-pick .pick-tip { margin: 0 0 16px; color: var(--text-secondary); font-size: 14px; }
.pick-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 12px; }
.pick-item { border: 1px solid var(--border-color); border-radius: 10px; padding: 16px; cursor: pointer; text-align: center; transition: all 0.15s; }
.pick-item:hover { border-color: var(--primary-color); background: var(--primary-gradient-soft); }
.pick-icon { width: 44px; height: 44px; border-radius: 10px; display: inline-flex; align-items: center; justify-content: center; color: #fff; margin-bottom: 8px; }
.pick-name { font-size: 14px; font-weight: 600; }
.pick-desc { font-size: 11px; color: var(--text-tertiary); margin-top: 4px; min-height: 14px; }

/* 表单 */
.form-head { display: flex; align-items: center; gap: 16px; margin-bottom: 20px; padding-bottom: 12px; border-bottom: 1px solid var(--border-light); }
.form-title { margin: 0; font-size: 16px; font-weight: 600; display: flex; align-items: center; gap: 6px; }
.submit-form { max-height: 50vh; overflow-y: auto; padding-right: 8px; }
</style>
