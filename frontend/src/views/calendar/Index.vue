<template>
  <div class="page">
    <div class="page-head">
      <h2>日程日历</h2>
      <div class="head-actions">
        <el-radio-group v-model="viewMode" size="small">
          <el-radio-button label="calendar">月历</el-radio-button>
          <el-radio-button label="list">列表</el-radio-button>
        </el-radio-group>
        <el-button type="primary" @click="openCreate">+ 新建</el-button>
      </div>
    </div>

    <div class="cal-nav">
      <el-button @click="prevMonth"><el-icon><ArrowLeft /></el-icon></el-button>
      <span class="month-label">{{ year }}年{{ month }}月</span>
      <el-button @click="nextMonth"><el-icon><ArrowRight /></el-icon></el-button>
      <el-button @click="goToday">今天</el-button>
      <span class="count-tip">共 {{ events.length }} 个日程</span>
    </div>

    <!-- ============ 月历视图 ============ -->
    <el-card v-if="viewMode === 'calendar'" class="cal-card">
      <div class="cal-grid">
        <div class="cal-header" v-for="d in dayNames" :key="d">{{ d }}</div>
        <div v-for="(day, i) in calendarDays" :key="i"
             :class="['cal-day', { dim: !day.current, today: day.isToday }]"
             @click="onDayClick(day)">
          <span class="day-num">{{ day.date }}</span>
          <div class="day-events">
            <div v-for="ev in day.events" :key="ev.id"
                 class="event-chip" :style="{ background: ev.color || 'var(--primary-color)' }"
                 @click.stop="editEvent(ev)">{{ ev.title }}</div>
            <div v-if="day.events.length > 3" class="more-tip">+{{ day.events.length - 3 }}个</div>
          </div>
        </div>
      </div>
      <el-empty v-if="!events.length" description="本月暂无日程" />
    </el-card>

    <!-- ============ 列表视图 ============ -->
    <el-card v-else class="list-card">
      <div v-if="!events.length" class="empty-wrap"><el-empty description="暂无日程" /></div>
      <div v-else class="ev-list">
        <div v-for="ev in sortedEvents" :key="ev.id" class="ev-row" @click="editEvent(ev)">
          <div class="ev-bar" :style="{ background: ev.color || 'var(--primary-color)' }"></div>
          <div class="ev-main">
            <div class="ev-title">{{ ev.title }}</div>
            <div class="ev-sub">
              <span class="ev-time"><el-icon><Clock /></el-icon> {{ formatEventTime(ev) }}</span>
              <span v-if="ev.location" class="ev-loc"><el-icon><Location /></el-icon> {{ ev.location }}</span>
              <span v-if="ev.creator_name" class="ev-creator">发起人: {{ ev.creator_name }}</span>
            </div>
            <div v-if="ev.description" class="ev-desc">{{ ev.description }}</div>
          </div>
        </div>
      </div>
    </el-card>

    <!-- ============ 近期日程面板（两视图都显示） ============ -->
    <el-card v-if="upcomingEvents.length" class="upcoming-card">
      <template #header>
        <div class="card-head"><span>近期日程（未来 7 天）</span></div>
      </template>
      <div class="upcoming-list">
        <div v-for="ev in upcomingEvents" :key="ev.id" class="upcoming-item" @click="editEvent(ev)">
          <div class="upcoming-date">
            <span class="d-day">{{ getDayNum(ev.start_time) }}</span>
            <span class="d-mon">{{ getMonthLabel(ev.start_time) }}</span>
          </div>
          <div class="upcoming-body">
            <div class="upcoming-title">{{ ev.title }}</div>
            <div class="upcoming-time">{{ formatEventTime(ev) }}</div>
          </div>
          <div class="upcoming-dot" :style="{ background: ev.color || 'var(--primary-color)' }"></div>
        </div>
      </div>
    </el-card>

    <!-- ============ 新建/编辑弹窗 ============ -->
    <el-dialog v-model="dialogVisible" :title="editingEvent ? '编辑日程' : '新建日程'" width="500px">
      <el-form label-width="80px">
        <el-form-item label="标题"><el-input v-model="form.title" placeholder="日程标题" /></el-form-item>
        <el-form-item label="开始时间">
          <el-date-picker v-model="form.start_time" type="datetime" value-format="YYYY-MM-DDTHH:mm:ss" style="width:100%" />
        </el-form-item>
        <el-form-item label="结束时间">
          <el-date-picker v-model="form.end_time" type="datetime" value-format="YYYY-MM-DDTHH:mm:ss" style="width:100%" />
        </el-form-item>
        <el-form-item label="地点"><el-input v-model="form.location" placeholder="可选" /></el-form-item>
        <el-form-item label="描述"><el-input v-model="form.description" type="textarea" :rows="2" /></el-form-item>
        <el-form-item label="颜色"><el-color-picker v-model="form.color" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button v-if="editingEvent" type="danger" @click="doDelete">删除</el-button>
        <el-button type="primary" @click="doSave" :loading="saving">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { ArrowLeft, ArrowRight, Clock, Location } from '@element-plus/icons-vue'
import { calendarApi } from '@/api/calendar'
import { useWorkspaceStore } from '@/pinia/workspaceStore'
const wsStore = useWorkspaceStore()

const dayNames = ['日','一','二','三','四','五','六']
const now = new Date()
const year = ref(now.getFullYear())
const month = ref(now.getMonth() + 1)
const events = ref([])
const viewMode = ref('calendar')
const dialogVisible = ref(false)
const editingEvent = ref(null)
const saving = ref(false)
const form = ref({ title: '', start_time: null, end_time: null, description: '', location: '', color: '#7C3AED' })

const todayStr = `${now.getFullYear()}-${String(now.getMonth()+1).padStart(2,'0')}-${String(now.getDate()).padStart(2,'0')}`

const calendarDays = computed(() => {
  const first = new Date(year.value, month.value - 1, 1)
  const last = new Date(year.value, month.value, 0)
  const startPad = first.getDay()
  const days = []
  for (let i = 0; i < startPad; i++) days.push({ date: '', current: false, isToday: false, events: [] })
  for (let d = 1; d <= last.getDate(); d++) {
    const ds = `${year.value}-${String(month.value).padStart(2,'0')}-${String(d).padStart(2,'0')}`
    days.push({
      date: d, current: true, isToday: ds === todayStr,
      events: events.value.filter(e => e.start_time?.startsWith(ds))
    })
  }
  return days
})

// 列表视图：按开始时间升序
const sortedEvents = computed(() => [...events.value].sort((a,b) => (a.start_time||'').localeCompare(b.start_time||'')))

// 近期日程：未来 7 天（基于今天）
const upcomingEvents = computed(() => {
  const today = new Date()
  today.setHours(0,0,0,0)
  const sevenLater = new Date(today)
  sevenLater.setDate(sevenLater.getDate() + 7)
  return events.value
    .filter(e => {
      const t = new Date(e.start_time)
      return t >= today && t <= sevenLater
    })
    .sort((a,b) => (a.start_time||'').localeCompare(b.start_time||''))
    .slice(0, 6)
})

function prevMonth() { if (month.value === 1) { year.value--; month.value = 12 } else month.value--; loadEvents() }
function nextMonth() { if (month.value === 12) { year.value++; month.value = 1 } else month.value++; loadEvents() }
function goToday() { year.value = now.getFullYear(); month.value = now.getMonth() + 1; loadEvents() }

async function loadEvents() {
  // 修复：end 使用下个月 1 号，避免月末事件被排除
  const startY = year.value
  const startM = month.value
  const start = `${startY}-${String(startM).padStart(2,'0')}-01`
  const nextM = startM === 12 ? 1 : startM + 1
  const nextY = startM === 12 ? startY + 1 : startY
  const end = `${nextY}-${String(nextM).padStart(2,'0')}-01`
  try {
    const r = await calendarApi.getEvents(wsStore.currentWorkspaceId, { start, end })
    events.value = r || []
  } catch { events.value = [] }
}

function formatEventTime(ev) {
  if (!ev.start_time) return ''
  const s = ev.start_time.replace('T', ' ').slice(0, 16)
  if (ev.end_time) {
    const e = ev.end_time.replace('T', ' ').slice(0, 16)
    return `${s} ~ ${e}`
  }
  return s
}

function getDayNum(t) { return t ? t.slice(8, 10) : '' }
function getMonthLabel(t) {
  if (!t) return ''
  const m = parseInt(t.slice(5, 7), 10)
  return `${m}月`
}

function onDayClick(day) {
  if (!day.current) return
  // 点击空白日期快速新建
  const ds = `${year.value}-${String(month.value).padStart(2,'0')}-${String(day.date).padStart(2,'0')}`
  openCreate(ds)
}

function openCreate(dateStr) {
  editingEvent.value = null
  const base = dateStr ? `${dateStr}T09:00:00` : null
  const end = dateStr ? `${dateStr}T10:00:00` : null
  form.value = { title: '', start_time: base, end_time: end, description: '', location: '', color: '#7C3AED' }
  dialogVisible.value = true
}

function editEvent(ev) {
  editingEvent.value = ev
  form.value = {
    title: ev.title,
    start_time: ev.start_time,
    end_time: ev.end_time,
    description: ev.description || '',
    location: ev.location || '',
    color: ev.color || '#7C3AED'
  }
  dialogVisible.value = true
}

async function doSave() {
  if (!form.value.title?.trim()) return ElMessage.warning('请填写标题')
  if (!form.value.start_time) return ElMessage.warning('请选择开始时间')
  saving.value = true
  try {
    const data = {
      ...form.value,
      workspace_id: wsStore.currentWorkspaceId,
      event_type: 'normal'
    }
    if (editingEvent.value) await calendarApi.updateEvent(editingEvent.value.id, data)
    else await calendarApi.createEvent(data)
    ElMessage.success('已保存')
    dialogVisible.value = false
    loadEvents()
  } catch { /* 拦截器已提示错误 */ }
  finally { saving.value = false }
}

async function doDelete() {
  try {
    await calendarApi.deleteEvent(editingEvent.value.id)
    ElMessage.success('已删除')
    dialogVisible.value = false
    loadEvents()
  } catch { /* 拦截器已提示错误 */ }
}

onMounted(() => loadEvents())

// 切换工作空间时重新加载
watch(() => wsStore.currentWorkspaceId, () => loadEvents())
</script>
<style scoped>
.page { padding: 0; }
.page-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.page-head h2 { font-size: 22px; font-weight: 700; margin: 0; }
.head-actions { display: flex; align-items: center; gap: 12px; }
.cal-nav { display: flex; align-items: center; gap: 12px; margin-bottom: 16px; }
.month-label { font-size: 18px; font-weight: 600; min-width: 110px; text-align: center; }
.count-tip { margin-left: auto; font-size: 13px; color: var(--text-secondary); }

/* 月历 */
.cal-card { border-radius: var(--radius-lg); }
.cal-grid { display: grid; grid-template-columns: repeat(7, 1fr); }
.cal-header { padding: 10px; text-align: center; font-weight: 600; font-size: 13px; color: var(--text-secondary); border-bottom: 1px solid var(--border-light); }
.cal-day { min-height: 92px; padding: 6px; border-bottom: 1px solid var(--border-light); border-right: 1px solid var(--border-light); cursor: pointer; transition: background 0.15s; }
.cal-day:hover { background: var(--primary-gradient-soft); }
.cal-day:nth-child(7n) { border-right: none; }
.cal-day.dim { opacity: 0.3; cursor: default; }
.cal-day.today { background: var(--primary-gradient-soft); }
.day-num { font-size: 13px; font-weight: 500; }
.day-events { display: flex; flex-direction: column; gap: 2px; margin-top: 4px; }
.event-chip { font-size: 11px; color: #fff; padding: 2px 6px; border-radius: 4px; cursor: pointer; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.more-tip { font-size: 10px; color: var(--text-tertiary); padding: 0 4px; }

/* 列表视图 */
.list-card { border-radius: var(--radius-lg); }
.empty-wrap { padding: 40px 0; }
.ev-list { display: flex; flex-direction: column; gap: 12px; }
.ev-row { display: flex; gap: 14px; padding: 14px; border: 1px solid var(--border-light); border-radius: 10px; cursor: pointer; transition: all 0.15s; }
.ev-row:hover { border-color: var(--primary-color); box-shadow: 0 2px 8px rgba(0,0,0,0.06); }
.ev-bar { width: 4px; border-radius: 2px; flex-shrink: 0; }
.ev-main { flex: 1; min-width: 0; }
.ev-title { font-size: 15px; font-weight: 600; margin-bottom: 6px; }
.ev-sub { display: flex; flex-wrap: wrap; gap: 16px; font-size: 12px; color: var(--text-secondary); }
.ev-sub span { display: inline-flex; align-items: center; gap: 4px; }
.ev-desc { font-size: 13px; color: var(--text-tertiary); margin-top: 6px; }

/* 近期日程 */
.upcoming-card { margin-top: 20px; border-radius: var(--radius-lg); }
.card-head { font-weight: 600; }
.upcoming-list { display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 12px; }
.upcoming-item { display: flex; align-items: center; gap: 12px; padding: 12px; border: 1px solid var(--border-light); border-radius: 10px; cursor: pointer; transition: all 0.15s; }
.upcoming-item:hover { border-color: var(--primary-color); }
.upcoming-date { text-align: center; flex-shrink: 0; width: 44px; }
.d-day { font-size: 22px; font-weight: 700; display: block; color: var(--primary-color); line-height: 1; }
.d-mon { font-size: 11px; color: var(--text-tertiary); }
.upcoming-body { flex: 1; min-width: 0; }
.upcoming-title { font-size: 14px; font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.upcoming-time { font-size: 12px; color: var(--text-secondary); margin-top: 2px; }
.upcoming-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
</style>
