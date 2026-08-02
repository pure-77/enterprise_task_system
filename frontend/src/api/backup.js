import request from './request'

export const backupApi = {
  exportJson() {
    return request({
      url: '/backup/export/json',
      method: 'get',
      responseType: 'blob'
    })
  },

  exportExcel() {
    return request({
      url: '/backup/export/excel',
      method: 'get'
    })
  },

  getTaskStatus(taskId) {
    return request({
      url: `/backup/task/${taskId}`,
      method: 'get'
    })
  },

  downloadFile(taskId) {
    return request({
      url: `/backup/download/${taskId}`,
      method: 'get',
      responseType: 'blob'
    })
  },

  importData(formData) {
    return request({
      url: '/backup/import',
      method: 'post',
      data: formData,
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    })
  }
}
