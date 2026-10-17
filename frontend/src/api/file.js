import request from './request'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || ''

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
  getDownloadUrl: (id, mode = 'inline') => `${API_BASE_URL}/files/${id}/download?mode=${mode}`,
  getSignedUrl: (id) => request.get(`/files/${id}/signed-url`),
  getPreviewPdfUrl: (id) => `${API_BASE_URL}/files/${id}/preview-pdf`,
  getTencentPreviewUrl: (id) => request.get(`/files/${id}/preview-tencent`),
}
