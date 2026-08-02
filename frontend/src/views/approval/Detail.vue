<template>
  <div class="page" v-loading="loading">
    <div class="page-head"><h2>审批详情</h2></div>
    <el-card v-if="detail" class="detail-card">
      <div class="info-row"><span class="label">标题</span><span>{{ detail.title }}</span></div>
      <div class="info-row"><span class="label">申请人</span><span>{{ detail.applicant_name }}</span></div>
      <div class="info-row"><span class="label">状态</span><el-tag :type="statusType(detail.status)">{{ statusLabel(detail.status) }}</el-tag></div>
      <div class="info-row"><span class="label">提交时间</span><span>{{ detail.submitted_at }}</span></div>

      <h4 style="margin: 24px 0 12px">审批流程</h4>
      <el-timeline>
        <el-timeline-item v-for="n in detail.nodes" :key="n.id"
          :type="n.status === 'approved' ? 'success' : n.status === 'rejected' ? 'danger' : 'warning'"
          :timestamp="n.acted_at">
          {{ n.node_name }} — {{ n.approver_name }}
          <template v-if="n.status === 'pending' && canAct(n)">
            <div style="margin-top:8px">
              <el-input v-model="n._comment" placeholder="审批意见(可选)" size="small" style="width:200px;margin-right:8px" />
              <el-button type="success" size="small" @click="doAction(n, 'approve')">通过</el-button>
              <el-button type="danger" size="small" @click="doAction(n, 'reject')">驳回</el-button>
            </div>
          </template>
          <div v-if="n.comment" style="color:var(--text-secondary);font-size:13px">意见: {{ n.comment }}</div>
        </el-timeline-item>
      </el-timeline>
      <div style="margin-top:16px" v-if="detail.status === 'pending' && detail.applicant_id === currentUserId">
        <el-button type="warning" @click="recall">撤回</el-button>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { approvalApi } from '@/api/approval'
import { useUserStore } from '@/pinia/userStore'

const route = useRoute()
const userStore = useUserStore()
const currentUserId = userStore.userInfo?.id
const detail = ref(null)
const loading = ref(false)

const statusMap = { pending: '审批中', approved: '已通过', rejected: '已驳回', recalled: '已撤回' }
const stMap = { pending: 'warning', approved: 'success', rejected: 'danger', recalled: 'info' }
function statusLabel(s) { return statusMap[s] || s }
function statusType(s) { return stMap[s] || 'info' }
function canAct(n) { return n.status === 'pending' && detail.value?.status === 'pending' }

async function load() {
  loading.value = true
  try {
    const res = await approvalApi.getDetail(route.params.id)
    detail.value = res
    detail.value.nodes.forEach(n => n._comment = '')
  } finally { loading.value = false }
}

async function doAction(node, action) {
  try {
    const data = { node_id: node.id, comment: node._comment || '' }
    if (action === 'approve') await approvalApi.approve(detail.value.id, data)
    else await approvalApi.reject(detail.value.id, data)
    ElMessage.success(action === 'approve' ? '已通过' : '已驳回')
    load()
  } catch (e) { ElMessage.error('操作失败') }
}

async function recall() {
  try {
    await approvalApi.recall(detail.value.id)
    ElMessage.success('已撤回')
    load()
  } catch (e) { ElMessage.error('撤回失败') }
}

onMounted(() => load())
</script>
<style scoped>
.page { padding: 0; }
.page-head h2 { font-size: 22px; font-weight: 700; margin: 0 0 20px; color: var(--text-primary); }
.detail-card { border-radius: var(--radius-lg); }
.info-row { display: flex; gap: 16px; margin-bottom: 12px; align-items: center; }
.label { color: var(--text-secondary); width: 70px; flex-shrink: 0; }
</style>
