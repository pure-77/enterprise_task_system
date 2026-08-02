import request from './request'

export const notificationApi = {
  getList: (params) => request.get('/notification/notifications', { params }),
  getUnreadCount: () => request.get('/notification/notifications/unread-count'),
  markRead: (data) => request.post('/notification/notifications/read', data),
  markAllRead: () => request.post('/notification/notifications/read-all'),
  getSettings: () => request.get('/notification/settings'),
  updateSetting: (type, data) => request.put(`/notification/settings/${type}`, data),
}
