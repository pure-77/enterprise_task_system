import request from './request'

export const workspaceApi = {
  getWorkspaces() {
    return request({ url: '/workspaces', method: 'get' })
  },

  getWorkspace(id) {
    return request({ url: `/workspaces/${id}`, method: 'get' })
  },

  createWorkspace(data) {
    return request({ url: '/workspaces', method: 'post', data })
  },

  updateWorkspace(id, data) {
    return request({ url: `/workspaces/${id}`, method: 'put', data })
  },

  deleteWorkspace(id) {
    return request({ url: `/workspaces/${id}`, method: 'delete' })
  },

  getMembers(workspaceId) {
    return request({ url: `/workspaces/${workspaceId}/members`, method: 'get' })
  },

  updateMemberRole(workspaceId, userId, data) {
    return request({ url: `/workspaces/${workspaceId}/members/${userId}/role`, method: 'put', data })
  },

  removeMember(workspaceId, userId) {
    return request({ url: `/workspaces/${workspaceId}/members/${userId}`, method: 'delete' })
  },

  leaveWorkspace(workspaceId) {
    return request({ url: `/workspaces/${workspaceId}/members/leave`, method: 'post' })
  },

  createInvitation(workspaceId, data) {
    return request({ url: `/workspaces/${workspaceId}/invitations`, method: 'post', data })
  },

  getWorkspaceInvitations(workspaceId) {
    return request({ url: `/workspaces/${workspaceId}/invitations`, method: 'get' })
  },

  cancelInvitation(workspaceId, invId) {
    return request({ url: `/workspaces/${workspaceId}/invitations/${invId}`, method: 'delete' })
  },

  getMyInvitations() {
    return request({ url: '/invitations', method: 'get' })
  },

  getPendingCount() {
    return request({ url: '/invitations/pending-count', method: 'get' })
  },

  acceptInvitation(id) {
    return request({ url: `/invitations/${id}/accept`, method: 'post' })
  },

  rejectInvitation(id) {
    return request({ url: `/invitations/${id}/reject`, method: 'post' })
  },

  getActivities(workspaceId, limit = 50) {
    return request({ url: `/workspaces/${workspaceId}/activities`, method: 'get', params: { limit } })
  }
}
