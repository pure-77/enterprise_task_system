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
        <el-table-column label="文件名" min-width="200">
          <template #default="{row}">
            <div class="file-name-cell" @click="handleFileClick(row)">
              <el-icon class="file-type-icon"><component :is="getFileIcon(row)" /></el-icon>
              <span class="file-name-text">{{ row.name }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="size" label="大小" width="100">
          <template #default="{row}">{{ formatSize(row.size) }}</template>
        </el-table-column>
        <el-table-column prop="uploader_name" label="上传者" width="100" />
        <el-table-column prop="created_at" label="上传时间" width="160">
          <template #default="{row}">{{ formatTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="160">
          <template #default="{row}">
            <el-button link type="primary" size="small" @click="previewFile(row)">预览</el-button>
            <el-button link type="primary" size="small" @click="downloadFile(row)">下载</el-button>
            <el-button link type="danger" size="small" @click="delFile(row.id)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="showCreateFolder" title="新建文件夹" width="360px">
      <el-input v-model="folderName" placeholder="文件夹名称" />
      <template #footer><el-button @click="showCreateFolder = false">取消</el-button><el-button type="primary" @click="doCreateFolder">创建</el-button></template>
    </el-dialog>

    <!-- ============ 文件预览 ============ -->
    <el-dialog v-model="showPreview" :title="previewFileData?.name" width="80%" top="5vh" destroy-on-close>
      <div class="preview-container" v-if="previewFileData">
        <!-- 图片预览 -->
        <div v-if="previewType === 'image'" class="preview-image-wrap">
          <img :src="previewUrl" class="preview-img" />
        </div>
        <!-- 视频预览 -->
        <div v-else-if="previewType === 'video'" class="preview-media-wrap">
          <video :src="previewUrl" controls class="preview-media"></video>
        </div>
        <!-- 音频预览 -->
        <div v-else-if="previewType === 'audio'" class="preview-media-wrap">
          <audio :src="previewUrl" controls class="preview-audio"></audio>
        </div>
        <!-- PDF 预览 -->
        <div v-else-if="previewType === 'pdf'" class="preview-iframe-wrap">
          <iframe :src="previewUrl" class="preview-iframe" frameborder="0"></iframe>
        </div>
        <!-- Office 文档：通过第三方文档预览服务 -->
        <div v-else-if="previewType === 'office'" class="preview-iframe-wrap">
          <div v-if="officeLoading" class="preview-loading">
            <el-icon class="is-loading" :size="32"><Loading /></el-icon>
            <span>正在加载文档预览...</span>
          </div>
          <div v-else-if="officeError" class="preview-other">
            <el-icon :size="64" color="var(--text-light)"><Document /></el-icon>
            <p>{{ officeError }}</p>
            <p class="preview-hint">{{ previewFileData?.name }}</p>
            <div class="preview-switcher">
              <el-button size="small" @click="switchOfficeViewer">换个预览源试试</el-button>
              <el-button type="primary" size="small" @click="downloadFile(previewFileData)">直接下载</el-button>
            </div>
          </div>
          <div v-else-if="officeViewerUrl" class="preview-office-wrap">
            <iframe
              :src="officeViewerUrl"
              class="preview-iframe"
              frameborder="0"
            ></iframe>
            <div class="preview-switcher-bar">
              <span class="switcher-label">预览源：{{ officeViewerNames[officeViewerIndex] }}</span>
              <el-button link size="small" @click="switchOfficeViewer">切换来源</el-button>
            </div>
          </div>
        </div>
        <!-- 腾讯云数据万象文档预览 -->
        <div v-else-if="previewType === 'tencent'" class="preview-iframe-wrap">
          <div v-if="officeLoading" class="preview-loading">
            <el-icon class="is-loading" :size="32"><Loading /></el-icon>
            <span>正在加载腾讯云文档预览...</span>
          </div>
          <div v-else-if="officeError" class="preview-other">
            <el-icon :size="64" color="var(--text-light)"><Document /></el-icon>
            <p>{{ officeError }}</p>
            <el-button type="primary" size="small" @click="downloadFile(previewFileData)">直接下载</el-button>
          </div>
          <iframe
            v-else-if="tencentPreviewUrl"
            :src="tencentPreviewUrl"
            class="preview-iframe"
            frameborder="0"
            allowfullscreen
          ></iframe>
        </div>
        <!-- 文本/代码预览 -->
        <div v-else-if="previewType === 'text'" class="preview-text-wrap">
          <pre class="preview-text">{{ previewContent }}</pre>
        </div>
        <!-- 其他类型 -->
        <div v-else class="preview-other">
          <el-icon :size="64" color="var(--text-light)"><Document /></el-icon>
          <p>该文件类型不支持在线预览</p>
          <el-button type="primary" @click="downloadFile(previewFileData)">点击下载</el-button>
        </div>
      </div>
      <template #footer>
        <el-button @click="showPreview = false">关闭</el-button>
        <el-button type="primary" @click="downloadFile(previewFileData)">下载</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Folder, Document, Picture, VideoCamera, Headset, Reading, Tickets, Loading } from '@element-plus/icons-vue'
import { fileApi } from '@/api/file'
import { auth } from '@/utils/auth'
import { useWorkspaceStore } from '@/pinia/workspaceStore'
import { formatTime } from '@/utils/format'
const wsStore = useWorkspaceStore()
const wsId = () => wsStore.currentWorkspaceId

const currentFolder = ref(null)
const folders = ref([])
const files = ref([])
const showCreateFolder = ref(false)
const folderName = ref('')

// 预览相关
const showPreview = ref(false)
const previewFileData = ref(null)
const previewType = ref('')
const previewUrl = ref('')
const previewContent = ref('')
const officeViewerUrl = ref('')
const officeLoading = ref(false)
const officeError = ref('')
const officeViewerIndex = ref(0)
const tencentPreviewUrl = ref('')
const officeViewerNames = ['腾讯文档', 'Google Docs', 'XDOC']
const officeViewerBuilders = [
  (url) => `https://view.xdocin.com/view?src=${encodeURIComponent(url)}&printable=true`,
  (url) => `https://docs.google.com/gview?url=${encodeURIComponent(url)}&embedded=true`,
  (url) => `https://view.xdocin.com/view?src=${encodeURIComponent(url)}&watermark=false`,
]

const fileTypeMap = {
  image: ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp', 'svg', 'ico'],
  video: ['mp4', 'webm', 'avi', 'mov', 'wmv', 'flv', 'mkv'],
  audio: ['mp3', 'wav', 'ogg', 'flac', 'aac', 'm4a'],
  pdf: ['pdf'],
  office: ['doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx'],
  text: ['txt', 'md', 'json', 'xml', 'yaml', 'yml', 'html', 'css', 'js', 'ts', 'py', 'java', 'cpp', 'c', 'go', 'rs', 'sql', 'csv', 'log', 'ini', 'conf', 'sh', 'bat', 'vue', 'jsx', 'tsx', 'php', 'rb', 'swift', 'kt', 'scala', 'r'],
}

const iconMap = {
  image: Picture,
  video: VideoCamera,
  audio: Headset,
  pdf: Reading,
  office: Document,
  text: Tickets,
  other: Document,
}

function getExt(filename) {
  const parts = (filename || '').split('.')
  return parts.length > 1 ? parts.pop().toLowerCase() : ''
}

function getPreviewType(filename) {
  const ext = getExt(filename)
  for (const [type, exts] of Object.entries(fileTypeMap)) {
    if (exts.includes(ext)) return type
  }
  return 'other'
}

function getFileIcon(row) {
  const type = getPreviewType(row.name)
  return iconMap[type] || iconMap.other
}

function formatSize(b) {
  if (!b) return '0 B'
  if (b < 1024) return b + ' B'
  if (b < 1048576) return (b / 1024).toFixed(1) + ' KB'
  return (b / 1048576).toFixed(1) + ' MB'
}

async function load() {
  try {
    const [fd, fl] = await Promise.all([
      fileApi.getFolders(wsId(), currentFolder.value),
      fileApi.getFiles(wsId(), { folder_id: currentFolder.value, page_size: 100 }),
    ])
    folders.value = fd || []
    files.value = fl?.items || []
  } catch {}
}

function enterFolder(f) { currentFolder.value = f.id; load() }
function goUp() { currentFolder.value = null; load() }

async function doCreateFolder() {
  try {
    await fileApi.createFolder({ workspace_id: wsId(), name: folderName.value, parent_id: currentFolder.value })
    showCreateFolder.value = false
    ElMessage.success('已创建')
    load()
  } catch { ElMessage.error('创建失败') }
}

async function doUpload(opts) {
  try {
    await fileApi.uploadFile(wsId(), currentFolder.value, opts.file)
    ElMessage.success('已上传')
    load()
  } catch { ElMessage.error('上传失败') }
}

async function delFile(id) {
  try {
    await fileApi.deleteFile(id)
    ElMessage.success('已删除')
    load()
  } catch {}
}

async function delFolder(id) {
  try {
    await fileApi.deleteFolder(id)
    ElMessage.success('已删除')
    load()
  } catch {}
}

async function fetchWithAuth(url) {
  const token = auth.getToken()
  const headers = token ? { Authorization: `Bearer ${token}` } : {}
  const res = await fetch(url, { headers })
  if (!res.ok) throw new Error('请求失败')
  return res
}

function buildOfficeViewerUrl(signedUrl, index) {
  return officeViewerBuilders[index](signedUrl)
}

function loadOfficePreview(row, viewerIdx) {
  officeLoading.value = true
  officeError.value = ''
  officeViewerUrl.value = ''
  officeViewerIndex.value = viewerIdx

  fileApi.getSignedUrl(row.id)
    .then(res => {
      const fullUrl = window.location.origin + res.url
      officeViewerUrl.value = buildOfficeViewerUrl(fullUrl, viewerIdx)
    })
    .catch(() => {
      officeError.value = '获取预览链接失败，请直接下载'
    })
    .finally(() => {
      officeLoading.value = false
    })
}

async function loadOfficeAsPdf(row) {
  officeLoading.value = true
  officeError.value = ''

  try {
    const pdfUrl = fileApi.getPreviewPdfUrl(row.id)
    const response = await fetchWithAuth(pdfUrl)

    if (!response.ok) {
      throw new Error('转换失败')
    }

    const blob = await response.blob()
    previewUrl.value = URL.createObjectURL(blob)
    previewType.value = 'pdf'  // 切换为PDF预览模式
  } catch (error) {
    console.error('Office文档转换失败:', error)
    officeError.value = '文档转换失败，请尝试下载后查看'
    // 回退到第三方预览服务
    loadOfficePreview(row, 0)
  } finally {
    officeLoading.value = false
  }
}

async function loadTencentPreview(row) {
  officeLoading.value = true
  officeError.value = ''
  tencentPreviewUrl.value = ''

  try {
    const res = await fileApi.getTencentPreviewUrl(row.id)
    tencentPreviewUrl.value = res.preview_url
    previewType.value = 'tencent'
  } catch (error) {
    console.error('腾讯云预览失败:', error)
    // 回退到PDF转换预览
    loadOfficeAsPdf(row)
  } finally {
    officeLoading.value = false
  }
}

function switchOfficeViewer() {
  if (!previewFileData.value) return
  const nextIdx = (officeViewerIndex.value + 1) % officeViewerBuilders.length
  loadOfficePreview(previewFileData.value, nextIdx)
}

function previewFile(row) {
  const type = getPreviewType(row.name)
  previewFileData.value = row
  previewType.value = type
  // 重置 Office 预览状态
  officeViewerUrl.value = ''
  officeLoading.value = false
  officeError.value = ''
  tencentPreviewUrl.value = ''

  const downloadUrl = fileApi.getDownloadUrl(row.id, 'inline')

  if (type === 'text') {
    fetchWithAuth(downloadUrl)
      .then(res => res.text())
      .then(text => { previewContent.value = text })
      .catch(() => { previewContent.value = '加载文件内容失败' })
    previewUrl.value = ''
  } else if (type === 'image' || type === 'video' || type === 'audio' || type === 'pdf') {
    fetchWithAuth(downloadUrl)
      .then(res => res.blob())
      .then(blob => { previewUrl.value = URL.createObjectURL(blob) })
      .catch(() => { previewUrl.value = '' })
  } else if (type === 'office') {
    previewUrl.value = ''
    // 优先使用腾讯云预览
    loadTencentPreview(row)
  } else {
    previewUrl.value = downloadUrl
  }

  showPreview.value = true
}

function downloadFile(row) {
  const url = fileApi.getDownloadUrl(row.id, 'attachment')
  fetchWithAuth(url)
    .then(res => res.blob())
    .then(blob => {
      const link = document.createElement('a')
      link.href = URL.createObjectURL(blob)
      link.download = row.name
      link.click()
      URL.revokeObjectURL(link.href)
    })
    .catch(() => {
      window.open(url, '_blank')
    })
}

function handleFileClick(row) {
  const type = getPreviewType(row.name)
  if (type === 'other') {
    downloadFile(row)
  } else {
    previewFile(row)
  }
}

// 关闭预览时释放 Blob URL
watch(showPreview, (val) => {
  if (!val) {
    if (previewUrl.value && previewUrl.value.startsWith('blob:')) {
      URL.revokeObjectURL(previewUrl.value)
    }
    previewUrl.value = ''
    officeViewerUrl.value = ''
    officeError.value = ''
    tencentPreviewUrl.value = ''
  }
})

onMounted(() => load())

// 切换工作空间时重新加载
watch(() => wsStore.currentWorkspaceId, () => load())
</script>

<style scoped>
.page { padding: 0; }
.page-head h2 { font-size: 22px; font-weight: 700; margin-bottom: 16px; }
.toolbar { display: flex; gap: 12px; margin-bottom: 16px; }
.file-card { border-radius: var(--radius-lg); }
.section { margin-bottom: 12px; }
.section h4 { margin: 0 0 8px; }
.grid { display: flex; gap: 16px; flex-wrap: wrap; }
.grid-item { display: flex; flex-direction: column; align-items: center; gap: 4px; cursor: pointer; padding: 12px; border-radius: 8px; transition: background 0.2s; }
.grid-item:hover { background: var(--bg-secondary); }

.file-name-cell {
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  padding: 2px 4px;
  border-radius: 4px;
  transition: background 0.2s;
}
.file-name-cell:hover { background: var(--bg-secondary); }
.file-type-icon { color: var(--primary-color); }
.file-name-text { color: var(--text-primary); }

/* 预览样式 */
.preview-container {
  min-height: 300px;
  display: flex;
  justify-content: center;
  align-items: center;
}
.preview-image-wrap, .preview-media-wrap, .preview-iframe-wrap, .preview-text-wrap {
  width: 100%;
  display: flex;
  justify-content: center;
  align-items: center;
}
.preview-img {
  max-width: 100%;
  max-height: 70vh;
  border-radius: 8px;
}
.preview-media {
  max-width: 100%;
  max-height: 70vh;
}
.preview-audio {
  width: 100%;
  max-width: 500px;
}
.preview-iframe {
  width: 100%;
  height: 70vh;
  border: none;
  border-radius: 8px;
}
.preview-text-wrap {
  max-height: 70vh;
  overflow: auto;
  background: var(--bg-secondary);
  border-radius: 8px;
  padding: 16px;
}
.preview-text {
  white-space: pre-wrap;
  word-break: break-all;
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 13px;
  line-height: 1.6;
  margin: 0;
}
.preview-other {
  text-align: center;
  padding: 40px;
}
.preview-other p {
  color: var(--text-secondary);
  margin: 16px 0;
}
.preview-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  height: 50vh;
  color: var(--text-light);
}
.preview-office-wrap {
  width: 100%;
  display: flex;
  flex-direction: column;
}
.preview-switcher {
  display: flex;
  gap: 8px;
  justify-content: center;
  margin-top: 8px;
}
.preview-switcher-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  margin-top: 4px;
  background: var(--bg-secondary);
  border-radius: 6px;
  font-size: 12px;
  color: var(--text-light);
}
.switcher-label { font-size: 12px; }
.preview-hint {
  font-size: 13px;
  color: var(--text-light);
  margin: 8px 0 16px !important;
  word-break: break-all;
}
</style>
