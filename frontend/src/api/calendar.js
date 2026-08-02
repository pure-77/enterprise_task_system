import request from './request'

export const calendarApi = {
  getEvents: (workspaceId, params) => request.get('/calendar/events', { params: { workspace_id: workspaceId, ...params } }),
  createEvent: (data) => request.post('/calendar/events', data),
  updateEvent: (id, data) => request.put(`/calendar/events/${id}`, data),
  deleteEvent: (id) => request.delete(`/calendar/events/${id}`),
  updateAttendee: (eventId, data) => request.put(`/calendar/events/${eventId}/attendees`, data),
}
