import request from './request'

/**
 * 统计API - 支持 workspace_id 参数
 */
export const statisticsApi = {
  getOverview(workspaceId) {
    const params = workspaceId ? { workspace_id: workspaceId } : {}
    return request({ url: '/statistics/overview', method: 'get', params })
  },

  getCategoryStats(workspaceId) {
    const params = workspaceId ? { workspace_id: workspaceId } : {}
    return request({ url: '/statistics/category', method: 'get', params })
  },

  getStatusStats(workspaceId) {
    const params = workspaceId ? { workspace_id: workspaceId } : {}
    return request({ url: '/statistics/status', method: 'get', params })
  },

  getCompletionTrend(days = 7, workspaceId) {
    const params = { days }
    if (workspaceId) params.workspace_id = workspaceId
    return request({ url: '/statistics/completion-trend', method: 'get', params })
  },

  exportTasksExcel(workspaceId) {
    const params = workspaceId ? { workspace_id: workspaceId } : {}
    return request({
      url: '/statistics/export/excel',
      method: 'get',
      params,
      responseType: 'blob'
    })
  }
}
