<template>
  <div class="page">
    <div class="page-head"><h2>成员花名册</h2></div>
    <div class="filter-bar">
      <el-select v-model="filters.department_id" placeholder="部门" clearable style="width:160px">
        <el-option v-for="d in depts" :key="d.id" :label="d.name" :value="d.id" />
      </el-select>
      <el-input v-model="filters.keyword" placeholder="搜索姓名/工号" clearable style="width:200px" />
      <el-select v-model="filters.status" placeholder="状态" clearable style="width:100px">
        <el-option label="在职" value="active" /><el-option label="离职" value="leave" />
      </el-select>
      <el-button type="primary" @click="load">查询</el-button>
    </div>
    <el-table :data="list" v-loading="loading" stripe>
      <el-table-column prop="real_name" label="姓名" width="100" />
      <el-table-column prop="nickname" label="昵称" width="100" />
      <el-table-column prop="email" label="邮箱" min-width="180" />
      <el-table-column prop="employee_no" label="工号" width="100" />
      <el-table-column prop="department_name" label="部门" width="100" />
      <el-table-column prop="position_name" label="职位" width="100" />
      <el-table-column prop="status" label="状态" width="80">
        <template #default="{row}"><el-tag :type="row.status==='active'?'success':'info'" size="small">{{ row.status==='active'?'在职':'离职' }}</el-tag></template>
      </el-table-column>
    </el-table>
    <el-pagination v-model:current-page="p" :total="total" layout="prev,next,total" @current-change="load" style="margin-top:16px" />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useWorkspaceStore } from '@/pinia/workspaceStore'
import request from '@/api/request'
const wsStore = useWorkspaceStore()
const depts = ref([]); const list = ref([]); const loading = ref(false)
const p = ref(1); const total = ref(0)
const filters = ref({ department_id: null, keyword: '', status: 'active' })

async function load() {
  loading.value = true
  try {
    const r = await request.get('/org/members', { params: { workspace_id: wsStore.currentWorkspaceId, ...filters.value, page: p.value, page_size: 20 } })
    const d = r
    list.value = d.items || d || []; total.value = d.total || 0
  } finally { loading.value = false }
}

onMounted(async () => {
  try { const r = await request.get('/org/departments', { params: { workspace_id: wsStore.currentWorkspaceId } }); depts.value = flattenTree(r || []) }
  catch {}
  load()
})

function flattenTree(nodes) {
  let result = []
  for (const n of nodes) { result.push({ id: n.id, name: n.name }); if (n.children) result = result.concat(flattenTree(n.children)) }
  return result
}
</script>
<style scoped>
.page { padding: 0; } .page-head h2 { font-size: 22px; font-weight: 700; margin-bottom: 16px; }
.filter-bar { display: flex; gap: 12px; margin-bottom: 16px; }
</style>
