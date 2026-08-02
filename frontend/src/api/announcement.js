import request from './request'

export const announcementApi = {
  getList: (workspaceId, params) => request.get('/announcements', { params: { workspace_id: workspaceId, ...params } }),
  getDetail: (id) => request.get(`/announcements/${id}`),
  create: (data) => request.post('/announcements', data),
  delete: (id) => request.delete(`/announcements/${id}`),
  getReadStatus: (id) => request.get(`/announcements/${id}/read-status`),
}
