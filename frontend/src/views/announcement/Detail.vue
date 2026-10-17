<template>
  <div class="page" v-loading="loading">
    <div class="page-head"><el-button link @click="$router.back()"><el-icon><ArrowLeft /></el-icon>返回</el-button></div>
    <el-card v-if="detail" class="detail-card">
      <el-tag v-if="detail.is_pinned" type="danger" size="small">置顶</el-tag>
      <el-tag v-if="detail.is_must_read" type="warning" size="small" style="margin-left:8px">必读</el-tag>
      <h2 style="margin:16px 0 8px">{{ detail.title }}</h2>
      <div class="meta">{{ detail.creator_name }} · {{ formatTime(detail.created_at) }} · {{ detail.type }}</div>
      <el-divider />
      <div class="content" v-html="detail.content"></div>

      <el-divider />
      <h4>已读情况 ({{ readStatus.read_count }})</h4>
      <div class="read-list">
        <el-tag v-for="u in readStatus.read_users" :key="u.user_id" size="small" style="margin:4px">{{ u.name }}</el-tag>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ArrowLeft } from '@element-plus/icons-vue'
import { announcementApi } from '@/api/announcement'
import { formatTime } from '@/utils/format'
const route = useRoute()
const detail = ref(null); const readStatus = ref({ read_count: 0, read_users: [] }); const loading = ref(false)

onMounted(async () => {
  loading.value = true
  try {
    const [d, r] = await Promise.all([
      announcementApi.getDetail(route.params.id),
      announcementApi.getReadStatus(route.params.id)
    ])
    detail.value = d
    readStatus.value = r
  } finally { loading.value = false }
})
</script>
<style scoped>
.page { padding: 0; } .page-head { margin-bottom: 16px; }
.detail-card { border-radius: var(--radius-lg); }
.meta { color: var(--text-secondary); font-size: 13px; }
.content { line-height: 1.8; min-height: 100px; }
.read-list { display: flex; flex-wrap: wrap; gap: 4px; }
</style>
