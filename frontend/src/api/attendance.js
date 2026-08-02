import request from './request'

export const attendanceApi = {
  getRules: (workspaceId) => request.get('/attendance/rules', { params: { workspace_id: workspaceId } }),
  createRule: (data) => request.post('/attendance/rules', data),
  deleteRule: (id) => request.delete(`/attendance/rules/${id}`),
  checkIn: (data) => request.post('/attendance/check-in', data),
  checkOut: (data) => request.post('/attendance/check-out', data),
  getRecords: (params) => request.get('/attendance/records', { params }),
  getStats: (params) => request.get('/attendance/stats', { params }),
  getTodayStatus: (ruleId) => request.get('/attendance/today', { params: { rule_id: ruleId } }),
}
