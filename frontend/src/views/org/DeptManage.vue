<template>
  <div class="page">
    <div class="page-head">
      <h2>部门管理</h2>
      <div class="head-actions">
        <el-button type="primary" @click="openAdd(null)">+ 根部门</el-button>
      </div>
    </div>

    <el-row :gutter="16">
      <!-- 左侧：部门树 -->
      <el-col :span="14">
        <el-card class="tree-card">
          <template #header>
            <div class="card-head">
              <span>部门架构</span>
              <span class="tip">点击部门查看成员</span>
            </div>
          </template>
          <el-tree
            :data="tree"
            :props="{children:'children',label:'name'}"
            node-key="id"
            default-expand-all
            highlight-current
            @node-click="onDeptClick"
          >
            <template #default="{data}">
              <span class="node">
                <span class="dept-name">{{ data.name }}</span>
                <span class="count">{{ data.member_count }}人</span>
                <span class="actions">
                  <el-button link type="primary" size="small" @click.stop="openAdd(data)">+子部门</el-button>
                  <el-button link size="small" @click.stop="openEdit(data)">编辑</el-button>
                  <el-button link type="danger" size="small" @click.stop="doDelete(data)">删除</el-button>
                </span>
              </span>
            </template>
          </el-tree>
        </el-card>
      </el-col>

      <!-- 右侧：部门成员 -->
      <el-col :span="10">
        <el-card class="member-card">
          <template #header>
            <div class="card-head">
              <span>{{ currentDept ? `「${currentDept.name}」成员` : '部门成员' }}</span>
              <el-button
                v-if="currentDept"
                type="primary"
                size="small"
                @click="showAddMember = true"
              >+ 添加成员</el-button>
            </div>
          </template>

          <div v-if="!currentDept" class="empty-tip">
            <el-empty description="点击左侧部门查看成员" :image-size="80" />
          </div>

          <div v-else v-loading="memberLoading">
            <div v-if="deptMembers.length === 0" class="empty-tip">
              <el-empty description="该部门暂无成员" :image-size="60" />
            </div>
            <div v-else class="member-list">
              <div v-for="m in deptMembers" :key="m.id" class="member-row">
                <el-avatar :size="36" :src="appendToken(m.avatar)">{{ (m.nickname || m.real_name || '?')[0] }}</el-avatar>
                <div class="member-info">
                  <div class="member-name">{{ m.nickname || m.real_name || '未命名' }}</div>
                  <div class="member-sub">
                    {{ m.position_name || '未设置职位' }}
                    <span v-if="m.role" class="role-tag">{{ roleLabel(m.role) }}</span>
                  </div>
                </div>
                <el-dropdown trigger="click" @command="(cmd) => onMemberAction(cmd, m)">
                  <el-button link :icon="More" />
                  <template #dropdown>
                    <el-dropdown-menu>
                      <el-dropdown-item command="move">调整部门</el-dropdown-item>
                      <el-dropdown-item command="remove" divided>移出部门</el-dropdown-item>
                    </el-dropdown-menu>
                  </template>
                </el-dropdown>
              </div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 创建/编辑部门弹窗 -->
    <el-dialog v-model="dialog" :title="editingDept ? '编辑部门' : '创建部门'" width="420px">
      <el-form label-width="80px">
        <el-form-item label="名称"><el-input v-model="form.name" placeholder="请输入部门名称" /></el-form-item>
        <el-form-item label="负责人">
          <el-select v-model="form.leader_id" placeholder="选择负责人" filterable clearable style="width:100%">
            <el-option
              v-for="m in allMembers"
              :key="m.id"
              :label="m.nickname || m.real_name || '未命名'"
              :value="m.user_id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="排序"><el-input-number v-model="form.sort_order" :min="0" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialog=false">取消</el-button>
        <el-button type="primary" @click="doSave" :loading="saving">保存</el-button>
      </template>
    </el-dialog>

    <!-- 添加成员到部门弹窗 -->
    <el-dialog v-model="showAddMember" :title="`添加成员到「${currentDept?.name}」`" width="480px">
      <el-input v-model="memberSearch" placeholder="搜索成员姓名" :prefix-icon="Search" clearable style="margin-bottom:12px" />
      <div class="all-member-list">
        <div
          v-for="m in filteredAllMembers"
          :key="m.id"
          class="member-row"
          @click="addMemberToDept(m)"
        >
          <el-avatar :size="32" :src="appendToken(m.avatar)">{{ (m.nickname || m.real_name || '?')[0] }}</el-avatar>
          <div class="member-info">
            <div class="member-name">{{ m.nickname || m.real_name || '未命名' }}</div>
            <div class="member-sub">
              {{ m.department_name ? '当前: ' + m.department_name : '未分配部门' }}
            </div>
          </div>
          <el-icon class="add-icon"><Plus /></el-icon>
        </div>
        <el-empty v-if="filteredAllMembers.length === 0" description="暂无可选成员" :image-size="60" />
      </div>
    </el-dialog>

    <!-- 调整部门弹窗 -->
    <el-dialog v-model="showMoveMember" title="调整部门" width="420px">
      <el-form label-width="80px">
        <el-form-item label="成员">
          <span class="member-name">{{ moveMember?.nickname || moveMember?.real_name }}</span>
        </el-form-item>
        <el-form-item label="新部门">
          <el-select v-model="moveTargetDept" placeholder="选择新部门" filterable style="width:100%">
            <el-option
              v-for="d in flatDepts"
              :key="d.id"
              :label="d.fullPath"
              :value="d.id"
            />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showMoveMember = false">取消</el-button>
        <el-button type="primary" @click="doMoveMember" :loading="moving">确认调整</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { More, Plus, Search } from '@element-plus/icons-vue'
import { useWorkspaceStore } from '@/pinia/workspaceStore'
import { useUserStore } from '@/pinia/userStore'
import { appendToken } from '@/utils/auth'
import request from '@/api/request'

const wsStore = useWorkspaceStore()
const userStore = useUserStore()

// ====== 部门树 ======
const tree = ref([])
const dialog = ref(false)
const editingDept = ref(null)
const parentDept = ref(null)
const saving = ref(false)
const form = ref({ name: '', leader_id: null, sort_order: 0 })

const currentDept = ref(null)
const deptMembers = ref([])
const memberLoading = ref(false)

// 所有成员（用于负责人选择和添加成员）
const allMembers = ref([])
const showAddMember = ref(false)
const memberSearch = ref('')

// 调整部门
const showMoveMember = ref(false)
const moveMember = ref(null)
const moveTargetDept = ref(null)
const moving = ref(false)

// 权限：只有 OWNER 或 ADMIN 可以编辑
const canManage = ref(false)

const filteredAllMembers = computed(() => {
  const k = memberSearch.value.trim().toLowerCase()
  if (!k) return allMembers.value
  return allMembers.value.filter(m =>
    (m.nickname || '').toLowerCase().includes(k) ||
    (m.real_name || '').toLowerCase().includes(k)
  )
})

// 扁平化部门树（用于调整部门选择）
const flatDepts = computed(() => {
  const result = []
  const walk = (nodes, parentPath = '') => {
    for (const n of nodes) {
      const fullPath = parentPath ? `${parentPath} / ${n.name}` : n.name
      result.push({ id: n.id, name: n.name, fullPath })
      if (n.children && n.children.length) walk(n.children, fullPath)
    }
  }
  walk(tree.value)
  return result
})

const roleLabel = (role) => {
  const map = { owner: '拥有者', admin: '管理员', member: '成员' }
  return map[role] || role
}

async function loadTree() {
  try {
    const r = await request.get('/org/departments', { params: { workspace_id: wsStore.currentWorkspaceId } })
    tree.value = r || []
  } catch (e) {
    console.error('加载部门树失败', e)
  }
}

async function loadAllMembers() {
  try {
    const r = await request.get('/org/members', {
      params: { workspace_id: wsStore.currentWorkspaceId, page: 1, page_size: 100 }
    })
    allMembers.value = r.items || []
  } catch (e) {
    console.error('加载成员失败', e)
  }
}

async function loadDeptMembers(deptId) {
  if (!deptId) return
  memberLoading.value = true
  try {
    const r = await request.get('/org/members', {
      params: { workspace_id: wsStore.currentWorkspaceId, department_id: deptId, page: 1, page_size: 100 }
    })
    deptMembers.value = r.items || []
  } catch (e) {
    console.error('加载部门成员失败', e)
  } finally { memberLoading.value = false }
}

function onDeptClick(data) {
  currentDept.value = data
  loadDeptMembers(data.id)
}

// ====== 部门 CRUD ======
function openAdd(parent) {
  if (!canManage.value) return ElMessage.warning('需要管理员权限')
  editingDept.value = null
  parentDept.value = parent
  form.value = { name: '', leader_id: null, sort_order: 0 }
  dialog.value = true
}

function openEdit(d) {
  if (!canManage.value) return ElMessage.warning('需要管理员权限')
  editingDept.value = d
  parentDept.value = null
  form.value = { name: d.name, leader_id: d.leader_id, sort_order: d.sort_order }
  dialog.value = true
}

async function doSave() {
  if (!form.value.name.trim()) return ElMessage.warning('请输入部门名称')
  saving.value = true
  try {
    const data = {
      ...form.value,
      workspace_id: wsStore.currentWorkspaceId,
      parent_id: parentDept.value?.id || null
    }
    if (editingDept.value) {
      await request.put(`/org/departments/${editingDept.value.id}`, data)
    } else {
      await request.post('/org/departments', data)
    }
    ElMessage.success('已保存')
    dialog.value = false
    await loadTree()
  } catch { /* 拦截器已提示错误 */ } finally { saving.value = false }
}

async function doDelete(d) {
  if (!canManage.value) return ElMessage.warning('需要管理员权限')
  try {
    await ElMessageBox.confirm(`删除「${d.name}」及其子部门？`, '提示', { type: 'warning' })
    await request.delete(`/org/departments/${d.id}`)
    ElMessage.success('已删除')
    if (currentDept.value?.id === d.id) {
      currentDept.value = null
      deptMembers.value = []
    }
    await loadTree()
  } catch {}
}

// ====== 成员调整部门 ======
async function addMemberToDept(m) {
  if (!currentDept.value) return
  try {
    await request.put(`/org/members/${m.id}`, { department_id: currentDept.value.id })
    ElMessage.success(`已将「${m.nickname || m.real_name}」加入「${currentDept.value.name}」`)
    await Promise.all([loadDeptMembers(currentDept.value.id), loadTree(), loadAllMembers()])
    showAddMember.value = false
  } catch { /* 拦截器已提示错误 */ }
}

function onMemberAction(cmd, m) {
  if (cmd === 'move') {
    moveMember.value = m
    moveTargetDept.value = null
    showMoveMember.value = true
  } else if (cmd === 'remove') {
    doRemoveMember(m)
  }
}

async function doMoveMember() {
  if (!moveTargetDept.value) return ElMessage.warning('请选择新部门')
  moving.value = true
  try {
    await request.put(`/org/members/${moveMember.value.id}`, { department_id: moveTargetDept.value })
    ElMessage.success('部门已调整')
    showMoveMember.value = false
    await Promise.all([loadDeptMembers(currentDept.value.id), loadTree(), loadAllMembers()])
  } catch { /* 拦截器已提示错误 */ } finally { moving.value = false }
}

async function doRemoveMember(m) {
  try {
    await ElMessageBox.confirm(`确定将「${m.nickname || m.real_name}」移出「${currentDept.value.name}」？`, '提示', { type: 'warning' })
    await request.put(`/org/members/${m.id}`, { department_id: null })
    ElMessage.success('已移出部门')
    await Promise.all([loadDeptMembers(currentDept.value.id), loadTree(), loadAllMembers()])
  } catch {}
}

// ====== 权限检查 ======
async function checkPermission() {
  try {
    const ws = await request.get(`/workspaces/${wsStore.currentWorkspaceId}`)
    canManage.value = ws.owner_id === userStore.userInfo?.id
    if (!canManage.value) {
      // 检查是否为 ADMIN
      const members = await request.get(`/workspaces/${wsStore.currentWorkspaceId}/members`)
      const me = (members.items || members || []).find(m => m.user_id === userStore.userInfo?.id)
      canManage.value = me?.role === 'admin' || me?.role === 'owner'
    }
  } catch (e) {
    canManage.value = false
  }
}

onMounted(async () => {
  await checkPermission()
  await Promise.all([loadTree(), loadAllMembers()])
})

// 切换工作空间时重新加载
watch(() => wsStore.currentWorkspaceId, async () => {
  await checkPermission()
  await Promise.all([loadTree(), loadAllMembers()])
})
</script>

<style scoped>
.page { padding: 0; }
.page-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.page-head h2 { font-size: 22px; font-weight: 700; margin: 0; }

.card-head { display: flex; justify-content: space-between; align-items: center; }
.card-head .tip { font-size: 12px; color: var(--text-light); font-weight: normal; }

.tree-card, .member-card { border-radius: var(--radius-lg); }

.node { display: flex; align-items: center; gap: 8px; flex: 1; }
.dept-name { font-weight: 500; }
.count { color: var(--text-light); font-size: 12px; background: var(--bg-tertiary); padding: 1px 8px; border-radius: 10px; }
.actions { margin-left: auto; }

.empty-tip { padding: 20px 0; }

.member-list { display: flex; flex-direction: column; gap: 4px; }
.member-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 10px;
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: background 0.2s;
}
.member-row:hover { background: var(--bg-secondary); }
.member-info { flex: 1; min-width: 0; }
.member-name { font-size: 14px; font-weight: 500; color: var(--text-primary); }
.member-sub { font-size: 12px; color: var(--text-light); margin-top: 2px; }
.role-tag {
  display: inline-block;
  padding: 0 6px;
  margin-left: 4px;
  border-radius: 4px;
  background: var(--bg-tertiary);
  font-size: 11px;
}

.all-member-list { max-height: 360px; overflow-y: auto; }
.add-icon { color: var(--primary-color); }
</style>
