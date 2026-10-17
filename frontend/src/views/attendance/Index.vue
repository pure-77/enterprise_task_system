<template>
  <div class="page">
    <div class="page-head">
      <h2>考勤打卡</h2>
      <el-button v-if="isAdmin" type="primary" plain size="small" class="rule-mgr-btn" @click="showRuleMgr = true">
        <el-icon><Setting /></el-icon> 规则管理
      </el-button>
    </div>

    <!-- 规则选择 -->
    <div class="rule-bar" v-if="rules.length > 0">
      <span class="label">考勤规则：</span>
      <el-select v-model="activeRule" @change="loadAll" style="width:240px">
        <el-option v-for="r in rules" :key="r.id" :label="r.name" :value="r.id" />
      </el-select>
      <span v-if="currentRuleObj" class="rule-tip">
        上班 {{ currentRuleObj.work_start?.slice(0,5) }} / 下班 {{ currentRuleObj.work_end?.slice(0,5) }}
        / 弹性 {{ currentRuleObj.flexible_minutes }}分钟 / 工作日 {{ workDayLabel(currentRuleObj.work_days) }}
      </span>
    </div>

    <!-- 无规则空状态 -->
    <el-card v-else class="empty-card">
      <el-empty :description="isAdmin ? '暂无考勤规则，请先创建规则后成员才能打卡' : '暂无考勤规则，请联系管理员配置'">
        <el-button v-if="isAdmin" type="primary" @click="openCreateRule">立即创建考勤规则</el-button>
      </el-empty>
    </el-card>

    <!-- 今日打卡卡片 -->
    <el-card v-if="activeRule" class="today-card">
      <div class="today-top">
        <div class="today-date">
          <span class="td-day">{{ todayDate.day }}</span>
          <span class="td-mon">{{ todayDate.month }}月 · 周{{ todayDate.week }}</span>
        </div>
        <div class="today-status">
          <div class="status-item">
            <div class="status-label">签到</div>
            <div :class="['status-badge', today.checked_in ? 'done' : '']">
              {{ today.checked_in ? formatTimeShort(today.check_in_time) : '未签到' }}
            </div>
            <div v-if="today.check_in_type" class="status-judge">
              <el-tag :type="today.check_in_type === 'normal' ? 'success' : 'danger'" size="small">
                {{ today.check_in_type === 'normal' ? '正常' : '迟到' }}
              </el-tag>
            </div>
          </div>
          <div class="status-divider"></div>
          <div class="status-item">
            <div class="status-label">签退</div>
            <div :class="['status-badge', today.checked_out ? 'done' : '']">
              {{ today.checked_out ? formatTimeShort(today.check_out_time) : '未签退' }}
            </div>
            <div v-if="today.check_out_type" class="status-judge">
              <el-tag :type="today.check_out_type === 'normal' ? 'success' : 'warning'" size="small">
                {{ today.check_out_type === 'normal' ? '正常' : '早退' }}
              </el-tag>
            </div>
          </div>
        </div>
      </div>
      <div class="today-actions">
        <el-button type="primary" size="large" round @click="checkIn" :disabled="today.checked_in" :loading="acting">
          <el-icon><Clock /></el-icon> 签到
        </el-button>
        <el-button type="success" size="large" round @click="checkOut" :disabled="!today.checked_in || today.checked_out" :loading="acting">
          <el-icon><CircleCheck /></el-icon> 签退
        </el-button>
      </div>
    </el-card>

    <!-- 本月统计 -->
    <el-card v-if="activeRule" class="stats-card">
      <h4>本月统计</h4>
      <el-row :gutter="20">
        <el-col :span="6"><div class="stat-item"><span class="num">{{ stats.actual_days }}</span><span class="txt">出勤天</span></div></el-col>
        <el-col :span="6"><div class="stat-item"><span class="num warn">{{ stats.late_count }}</span><span class="txt">迟到</span></div></el-col>
        <el-col :span="6"><div class="stat-item"><span class="num warn">{{ stats.early_count }}</span><span class="txt">早退</span></div></el-col>
        <el-col :span="6"><div class="stat-item"><span class="num">{{ stats.overtime_hours }}</span><span class="txt">加班h</span></div></el-col>
      </el-row>
    </el-card>

    <!-- 打卡记录 -->
    <el-card v-if="activeRule" style="margin-top:20px">
      <h4 style="margin-bottom:12px">打卡记录</h4>
      <el-table :data="records" stripe size="small">
        <el-table-column prop="date" label="日期" width="120" :formatter="(r) => formatDateOnly(r.date)" />
        <el-table-column label="签到" width="100">
          <template #default="{row}">{{ formatTimeShort(row.check_in_time) }}</template>
        </el-table-column>
        <el-table-column label="签退" width="100">
          <template #default="{row}">{{ formatTimeShort(row.check_out_time) }}</template>
        </el-table-column>
        <el-table-column label="签到判定" width="90">
          <template #default="{row}">
            <el-tag v-if="row.check_in_type" :type="row.check_in_type==='normal'?'success':'danger'" size="small">
              {{ row.check_in_type === 'normal' ? '正常' : '迟到' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="签退判定" width="90">
          <template #default="{row}">
            <el-tag v-if="row.check_out_type" :type="row.check_out_type==='normal'?'success':'warning'" size="small">
              {{ row.check_out_type === 'normal' ? '正常' : '早退' }}
            </el-tag>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- ============ 规则管理弹窗（管理员） ============ -->
    <el-dialog v-model="showRuleMgr" title="考勤规则管理" width="640px">
      <div class="rule-mgr-bar">
        <el-button type="primary" size="small" @click="openCreateRule">+ 新建规则</el-button>
      </div>
      <div v-if="!rules.length" class="rule-empty">暂无规则</div>
      <div v-else class="rule-list">
        <div v-for="r in rules" :key="r.id" class="rule-row">
          <div class="rule-info">
            <div class="rule-name">{{ r.name }}</div>
            <div class="rule-meta">
              上班 {{ r.work_start?.slice(0,5) }} · 下班 {{ r.work_end?.slice(0,5) }}
              · 弹性 {{ r.flexible_minutes }}分钟 · {{ workDayLabel(r.work_days) }}
            </div>
          </div>
          <el-button link type="danger" size="small" @click="deleteRule(r)">删除</el-button>
        </div>
      </div>
    </el-dialog>

    <!-- ============ 创建规则弹窗 ============ -->
    <el-dialog v-model="showCreateRule" title="新建考勤规则" width="480px" :close-on-click-modal="false">
      <el-form label-width="100px">
        <el-form-item label="规则名称" required>
          <el-input v-model="ruleForm.name" placeholder="如：标准考勤 / 弹性工作制" />
        </el-form-item>
        <el-form-item label="上班时间" required>
          <el-time-picker v-model="ruleForm.work_start" value-format="HH:mm:ss" format="HH:mm" style="width:100%" />
        </el-form-item>
        <el-form-item label="下班时间" required>
          <el-time-picker v-model="ruleForm.work_end" value-format="HH:mm:ss" format="HH:mm" style="width:100%" />
        </el-form-item>
        <el-form-item label="弹性分钟">
          <el-input-number v-model="ruleForm.flexible_minutes" :min="0" :max="180" :step="5" controls-position="right" style="width:100%" />
          <span class="form-tip">允许迟到的宽限时间</span>
        </el-form-item>
        <el-form-item label="工作日" required>
          <el-checkbox-group v-model="ruleForm.work_days_arr">
            <el-checkbox v-for="d in dayOptions" :key="d.value" :label="d.value">{{ d.label }}</el-checkbox>
          </el-checkbox-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreateRule = false">取消</el-button>
        <el-button type="primary" @click="createRule" :loading="creating">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Setting, Clock, CircleCheck } from '@element-plus/icons-vue'
import { attendanceApi } from '@/api/attendance'
import { useWorkspaceStore } from '@/pinia/workspaceStore'
import { formatTimeShort, formatDateOnly } from '@/utils/format'
const wsStore = useWorkspaceStore()

const isAdmin = computed(() => ['owner', 'admin'].includes(wsStore.currentRole))

const rules = ref([])
const activeRule = ref(null)
const today = ref({ checked_in: false, checked_out: false })
const stats = ref({ actual_days: 0, late_count: 0, early_count: 0, overtime_hours: 0 })
const records = ref([])
const acting = ref(false)

// 规则管理
const showRuleMgr = ref(false)
const showCreateRule = ref(false)
const creating = ref(false)
const ruleForm = ref({ name: '', work_start: '09:00:00', work_end: '18:00:00', flexible_minutes: 10, work_days_arr: [1,2,3,4,5] })

const dayOptions = [
  { value: 1, label: '周一' }, { value: 2, label: '周二' }, { value: 3, label: '周三' },
  { value: 4, label: '周四' }, { value: 5, label: '周五' }, { value: 6, label: '周六' },
  { value: 7, label: '周日' }
]

const currentRuleObj = computed(() => rules.value.find(r => r.id === activeRule.value))

const todayDate = computed(() => {
  const d = new Date()
  const weekMap = ['日','一','二','三','四','五','六']
  return { day: d.getDate(), month: d.getMonth() + 1, week: weekMap[d.getDay()] }
})

function workDayLabel(daysStr) {
  if (!daysStr) return ''
  const map = { '1':'一','2':'二','3':'三','4':'四','5':'五','6':'六','7':'日' }
  return daysStr.split(',').filter(Boolean).map(d => '周' + (map[d] || d)).join('、')
}

// 判断当前时间是否在工作时间范围内
function checkWorkTimeRange() {
  const rule = currentRuleObj.value
  if (!rule) return { within: true }
  const now = new Date()
  const nowMin = now.getHours() * 60 + now.getMinutes()
  const parseMin = (t) => {
    if (!t) return null
    const [h, m] = t.split(':').map(Number)
    return h * 60 + m
  }
  const startMin = parseMin(rule.work_start)
  const endMin = parseMin(rule.work_end)
  if (startMin === null || endMin === null) return { within: true }
  // 考虑弹性时间：签到允许提前，签退允许延后
  const within = nowMin >= startMin && nowMin <= endMin
  return {
    within,
    workStart: rule.work_start?.slice(0, 5),
    workEnd: rule.work_end?.slice(0, 5)
  }
}

// 非工作时间打卡提醒，返回是否继续
async function confirmIfOutOfRange(action) {
  const { within, workStart, workEnd } = checkWorkTimeRange()
  if (within) return true
  try {
    await ElMessageBox.confirm(
      `当前不在${action}时间范围内（工作时间 ${workStart} - ${workEnd}），是否继续${action}？`,
      '时间提醒',
      { confirmButtonText: `继续${action}`, cancelButtonText: '取消', type: 'warning' }
    )
    return true
  } catch {
    return false
  }
}

async function loadRules() {
  try {
    const r = await attendanceApi.getRules(wsStore.currentWorkspaceId)
    rules.value = r || []
    if (rules.value.length && !rules.value.some(x => x.id === activeRule.value)) {
      activeRule.value = rules.value[0].id
    } else if (!rules.value.length) {
      activeRule.value = null
    }
  } catch { rules.value = [] }
}

async function loadAll() {
  if (!activeRule.value) return
  try {
    const [t, s, r] = await Promise.all([
      attendanceApi.getTodayStatus(activeRule.value),
      attendanceApi.getStats({ rule_id: activeRule.value }),
      attendanceApi.getRecords({ rule_id: activeRule.value, page_size: 31 })
    ])
    today.value = t || {}
    stats.value = s || {}
    records.value = (r?.items || [])
  } catch {}
}

async function checkIn() {
  if (!(await confirmIfOutOfRange('签到'))) return
  acting.value = true
  try { await attendanceApi.checkIn({ rule_id: activeRule.value }); ElMessage.success('签到成功'); loadAll() }
  catch { /* 拦截器已提示错误 */ }
  finally { acting.value = false }
}

async function checkOut() {
  if (!(await confirmIfOutOfRange('签退'))) return
  acting.value = true
  try { await attendanceApi.checkOut({ rule_id: activeRule.value }); ElMessage.success('签退成功'); loadAll() }
  catch { /* 拦截器已提示错误 */ }
  finally { acting.value = false }
}

// ====== 规则管理 ======
function openCreateRule() {
  ruleForm.value = { name: '', work_start: '09:00:00', work_end: '18:00:00', flexible_minutes: 10, work_days_arr: [1,2,3,4,5] }
  showCreateRule.value = true
}

async function createRule() {
  if (!ruleForm.value.name.trim()) return ElMessage.warning('请填写规则名称')
  if (!ruleForm.value.work_start || !ruleForm.value.work_end) return ElMessage.warning('请设置上下班时间')
  if (!ruleForm.value.work_days_arr.length) return ElMessage.warning('请选择工作日')
  creating.value = true
  try {
    await attendanceApi.createRule({
      workspace_id: wsStore.currentWorkspaceId,
      name: ruleForm.value.name.trim(),
      work_start: ruleForm.value.work_start,
      work_end: ruleForm.value.work_end,
      flexible_minutes: ruleForm.value.flexible_minutes,
      work_days: ruleForm.value.work_days_arr.sort().join(',')
    })
    ElMessage.success('规则已创建')
    showCreateRule.value = false
    await loadRules()
    if (rules.value.length === 1) { activeRule.value = rules.value[0].id; loadAll() }
  } catch { /* 拦截器已提示错误 */ }
  finally { creating.value = false }
}

async function deleteRule(r) {
  try {
    await ElMessageBox.confirm(`确定删除规则「${r.name}」吗？历史记录将保留。`, '提示', {
      confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning'
    })
    await attendanceApi.deleteRule(r.id)
    ElMessage.success('已删除')
    await loadRules()
    if (activeRule.value && !rules.value.find(x => x.id === activeRule.value)) {
      activeRule.value = rules.value[0]?.id || null
      if (activeRule.value) loadAll()
    }
  } catch {}
}

onMounted(async () => {
  await loadRules()
  if (activeRule.value) loadAll()
})

// 切换工作空间时重新加载
watch(() => wsStore.currentWorkspaceId, async () => {
  await loadRules()
  if (activeRule.value) loadAll()
})
</script>
<style scoped>
.page { padding: 0; }
.page-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.page-head h2 { font-size: 22px; font-weight: 700; margin: 0; }
.rule-mgr-btn { --el-button-text-color: unset; }
.rule-bar { display: flex; align-items: center; gap: 12px; margin-bottom: 20px; flex-wrap: wrap; }
.rule-tip { font-size: 12px; color: var(--text-secondary); }

.empty-card { border-radius: var(--radius-lg); }

.today-card { border-radius: var(--radius-lg); padding: 8px 0; }
.today-top { display: flex; align-items: center; gap: 32px; margin-bottom: 24px; flex-wrap: wrap; }
.today-date { text-align: center; flex-shrink: 0; }
.td-day { font-size: 40px; font-weight: 700; color: var(--primary-color); display: block; line-height: 1; }
.td-mon { font-size: 12px; color: var(--text-tertiary); }
.today-status { display: flex; gap: 40px; flex: 1; justify-content: center; }
.status-item { text-align: center; }
.status-label { font-size: 13px; color: var(--text-secondary); margin-bottom: 8px; }
.status-badge { font-size: 22px; font-weight: 600; color: var(--text-light); }
.status-badge.done { color: var(--success-color); }
.status-judge { margin-top: 6px; }
.status-divider { width: 1px; background: var(--border-color); }
.today-actions { display: flex; justify-content: center; gap: 24px; }

.stats-card { margin-top: 20px; border-radius: var(--radius-lg); }
.stat-item { text-align: center; }
.stat-item .num { font-size: 28px; font-weight: 700; display: block; }
.stat-item .num.warn { color: var(--warning-color); }
.stat-item .txt { font-size: 13px; color: var(--text-secondary); }

/* 规则管理 */
.rule-mgr-bar { margin-bottom: 16px; }
.rule-empty { padding: 30px; text-align: center; color: var(--text-tertiary); }
.rule-list { display: flex; flex-direction: column; gap: 10px; }
.rule-row { display: flex; justify-content: space-between; align-items: center; padding: 12px; border: 1px solid var(--border-light); border-radius: 8px; }
.rule-name { font-size: 14px; font-weight: 600; }
.rule-meta { font-size: 12px; color: var(--text-secondary); margin-top: 4px; }

.form-tip { font-size: 11px; color: var(--text-tertiary); margin-left: 8px; }
</style>
