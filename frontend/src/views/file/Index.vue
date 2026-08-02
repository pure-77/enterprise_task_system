<template>
  <div class="page">
    <div class="page-head"><h2>文件管理</h2></div>
    <div class="toolbar">
      <el-button @click="goUp" :disabled="!currentFolder">上级</el-button>
      <el-button type="primary" @click="showCreateFolder = true">+ 文件夹</el-button>
      <el-upload :http-request="doUpload" :show-file-list="false">
        <el-button type="success">上传文件</el-button>
      </el-upload>
    </div>
    <el-card class="file-card">
      <div v-if="folders.length" class="section"><h4>文件夹</h4>
        <div class="grid">
          <div v-for="f in folders" :key="f.id" class="grid-item" @click="enterFolder(f)" @dblclick="enterFolder(f)">
            <el-icon :size="36" color="var(--warning-color)"><Folder /></el-icon>
            <span>{{ f.name }}</span>
            <el-button link type="danger" size="small" @click.stop="delFolder(f.id)">删除</el-button>
          </div>
        </div>
      </div>
      <el-table :data="files" stripe>
        <el-table-column prop="name" label="文件名" min-width="200" />
        <el-table-column prop="size" label="大小" width="100">
          <template #default="{row}">{{ formatSize(row.size) }}</template>
        </el-table-column>
        <el-table-column prop="uploader_name" label="上传者" width="100" />
        <el-table-column label="操作" width="120">
          <template #default="{row}">
            <el-button link type="primary" size="small" @click="window.open(row.url)">下载</el-button>
            <el-button link type="danger" size="small" @click="delFile(row.id)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="showCreateFolder" title="新建文件夹" width="360px">
      <el-input v-model="folderName" placeholder="文件夹名称" />
      <template #footer><el-button @click="showCreateFolder = false">取消</el-button><el-button type="primary" @click="doCreateFolder">创建</el-button></template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Folder } from '@element-plus/icons-vue'
import { fileApi } from '@/api/file'
import { useWorkspaceStore } from '@/pinia/workspaceStore'
const wsStore = useWorkspaceStore()
const wsId = () => wsStore.currentWorkspaceId

const currentFolder = ref(null)
const folders = ref([])
const files = ref([])
const showCreateFolder = ref(false)
const folderName = ref('')

function formatSize(b) { if (!b) return '0 B'; if (b < 1024) return b + ' B'; if (b < 1048576) return (b/1024).toFixed(1) + ' KB'; return (b/1048576).toFixed(1) + ' MB' }

async function load() {
  try {
    const [fd, fl] = await Promise.all([
      fileApi.getFolders(wsId(), currentFolder.value),
      fileApi.getFiles(wsId(), { folder_id: currentFolder.value, page_size: 100 })
    ])
    folders.value = fd || []
    files.value = fl?.items || []
  } catch {}
}

function enterFolder(f) { currentFolder.value = f.id; load() }
function goUp() { currentFolder.value = null; load() }
async function doCreateFolder() {
  try { await fileApi.createFolder({ workspace_id: wsId(), name: folderName.value, parent_id: currentFolder.value }); showCreateFolder.value = false; ElMessage.success('已创建'); load() }
  catch { ElMessage.error('创建失败') }
}
async function doUpload(opts) {
  try { await fileApi.uploadFile(wsId(), currentFolder.value, opts.file); ElMessage.success('已上传'); load() }
  catch { ElMessage.error('上传失败') }
}
async function delFile(id) { try { await fileApi.deleteFile(id); ElMessage.success('已删除'); load() } catch {} }
async function delFolder(id) { try { await fileApi.deleteFolder(id); ElMessage.success('已删除'); load() } catch {} }

onMounted(() => load())
</script>
<style scoped>
.page { padding: 0; } .page-head h2 { font-size: 22px; font-weight: 700; margin-bottom: 16px; }
.toolbar { display: flex; gap: 12px; margin-bottom: 16px; }
.file-card { border-radius: var(--radius-lg); }
.section { margin-bottom: 12px; } .section h4 { margin: 0 0 8px; }
.grid { display: flex; gap: 16px; flex-wrap: wrap; }
.grid-item { display: flex; flex-direction: column; align-items: center; gap: 4px; cursor: pointer; padding: 12px; border-radius: 8px; transition: background 0.2s; }
.grid-item:hover { background: var(--bg-secondary); }
</style>
