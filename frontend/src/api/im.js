import request from './request'

export const imApi = {
  createConversation: (data) => request.post('/im/conversations', data),
  getConversations: (workspaceId) => request.get('/im/conversations', { params: { workspace_id: workspaceId } }),
  getConversation: (id) => request.get(`/im/conversations/${id}`),
  getMessages: (convId, params) => request.get(`/im/conversations/${convId}/messages`, { params }),
  sendMessage: (convId, data) => request.post(`/im/conversations/${convId}/messages`, data),
  markRead: (convId, data) => request.post(`/im/conversations/${convId}/read`, data),
  recallMessage: (msgId) => request.put(`/im/messages/${msgId}/recall`),
  addMember: (convId, data) => request.post(`/im/conversations/${convId}/members`, data),
  removeMember: (convId, userId) => request.delete(`/im/conversations/${convId}/members/${userId}`),
  toggleMute: (convId, data) => request.put(`/im/conversations/${convId}/mute`, data),
  uploadFile: (workspaceId, file) => {
    const fd = new FormData()
    fd.append('file', file)
    return request.post('/im/upload', fd, { params: { workspace_id: workspaceId }, headers: { 'Content-Type': 'multipart/form-data' } })
  },
}
