<template>
  <div class="page">
    <div class="page-head"><h2>企业公告</h2><el-button v-if="isAdmin" type="primary" @click="openCreate">发布公告</el-button></div>
    <el-table :data="list" v-loading="loading" stripe @row-click="row => $router.push(`/announcements/${row.id}`)" style="cursor:pointer">
      <el-table-column prop="title" label="标题" min-width="200">
        <template #default="{row}"><el-tag v-if="row.is_pinned" type="danger" size="small" style="margin-right:8px">置顶</el-tag>{{ row.title }}</template>
      </el-table-column>
      <el-table-column prop="type" label="类型" width="80" />
      <el-table-column prop="creator_name" label="发布者" width="100" />
      <el-table-column prop="created_at" label="时间" width="160" />
    </el-table>

    <el-dialog v-model="showCreate" title="发布公告" width="560px">
      <el-form label-width="80px">
        <el-form-item label="标题"><el-input v-model="f.title" /></el-form-item>
        <el-form-item label="类型">
          <el-select v-model="f.type"><el-option v-for="o in ['notice','news','policy','urgent']" :key="o" :label="o" :value="o" /></el-select>
        </el-form-item>
        <el-form-item label="内容"><el-input v-model="f.content" type="textarea" :rows="6" /></el-form-item>
        <el-form-item label="置顶"><el-switch v-model="f.is_pinned" /></el-form-item>
        <el-form-item label="必读"><el-switch v-model="f.is_must_read" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreate = false">取消</el-button>
        <el-button type="primary" @click="doCreate" :loading="creating">发布</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { announcementApi } from '@/api/announcement'
import { useWorkspaceStore } from '@/pinia/workspaceStore'
const wsStore = useWorkspaceStore()
const isAdmin = ref(true) // TODO
const list = ref([]); const loading = ref(false)
const showCreate = ref(false); const creating = ref(false)
const f = ref({ title: '', content: '', type: 'notice', is_pinned: false, is_must_read: false })

async function load() {
  loading.value = true
  try { const r = await announcementApi.getList(wsStore.currentWorkspaceId); list.value = r?.items || [] }
  finally { loading.value = false }
}

async function doCreate() {
  creating.value = true
  try { await announcementApi.create({ ...f.value, workspace_id: wsStore.currentWorkspaceId }); ElMessage.success('已发布'); showCreate.value = false; load() }
  catch { ElMessage.error('发布失败') }
  finally { creating.value = false }
}

function openCreate() { f.value = { title: '', content: '', type: 'notice', is_pinned: false, is_must_read: false }; showCreate.value = true }
onMounted(() => load())
</script>
<style scoped>
.page { padding: 0; } .page-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; } .page-head h2 { font-size: 22px; font-weight: 700; }
</style>
