import request from './request'

export const fileApi = {
  getFolders: (workspaceId, parentId) => request.get('/files/folders', { params: { workspace_id: workspaceId, parent_id: parentId } }),
  createFolder: (data) => request.post('/files/folders', data),
  deleteFolder: (id) => request.delete(`/files/folders/${id}`),
  getFiles: (workspaceId, params) => request.get('/files', { params: { workspace_id: workspaceId, ...params } }),
  uploadFile: (workspaceId, folderId, file) => {
    const fd = new FormData()
    fd.append('file', file)
    return request.post('/files/upload', fd, { params: { workspace_id: workspaceId, folder_id: folderId }, headers: { 'Content-Type': 'multipart/form-data' } })
  },
  deleteFile: (id) => request.delete(`/files/${id}`),
  moveFile: (id, data) => request.put(`/files/${id}/move`, data),
}
