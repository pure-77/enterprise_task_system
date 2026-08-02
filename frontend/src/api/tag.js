import request from './request'

export const tagApi = {
  getTags(params) {
    return request({
      url: '/tags',
      method: 'get',
      params
    })
  },

  getTag(id) {
    return request({
      url: `/tags/${id}`,
      method: 'get'
    })
  },

  createTag(data) {
    return request({
      url: '/tags',
      method: 'post',
      data
    })
  },

  updateTag(id, data) {
    return request({
      url: `/tags/${id}`,
      method: 'put',
      data
    })
  },

  deleteTag(id) {
    return request({
      url: `/tags/${id}`,
      method: 'delete'
    })
  }
}