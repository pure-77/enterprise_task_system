import request from './request'

export const approvalApi = {
  getTemplates: (workspaceId) => request.get('/approval/templates', { params: { workspace_id: workspaceId } }),
  createTemplate: (data) => request.post('/approval/templates', data),
  submit: (data) => request.post('/approval/instances', data),
  getPending: (workspaceId, params) => request.get('/approval/instances/pending', { params: { workspace_id: workspaceId, ...params } }),
  getMyApplications: (workspaceId, params) => request.get('/approval/instances/my', { params: { workspace_id: workspaceId, ...params } }),
  getProcessed: (workspaceId, params) => request.get('/approval/instances/processed', { params: { workspace_id: workspaceId, ...params } }),
  getDetail: (id) => request.get(`/approval/instances/${id}`),
  approve: (id, data) => request.post(`/approval/instances/${id}/approve`, data),
  reject: (id, data) => request.post(`/approval/instances/${id}/reject`, data),
  transfer: (id, data) => request.post(`/approval/instances/${id}/transfer`, data),
  recall: (id) => request.post(`/approval/instances/${id}/recall`),
  cancel: (id) => request.post(`/approval/instances/${id}/cancel`),
}
