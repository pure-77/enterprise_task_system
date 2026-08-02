import request from './request'

/**
 * 分类API - 面试考点：前后端API交互
 */
export const categoryApi = {
  /**
   * 创建分类
   * @param {Object} data - 分类数据
   * @param {string} data.name - 分类名称
   * @param {string} data.color - 分类颜色
   * @returns {Promise} - 返回创建的分类
   */
  createCategory: (data) => {
    return request({
      url: '/categories',
      method: 'post',
      data
    })
  },

  /**
   * 获取分类列表
   * @returns {Promise} - 返回分类列表
   */
  getCategories: (params) => {
    return request({
      url: '/categories',
      method: 'get',
      params
    })
  },

  /**
   * 获取单个分类
   * @param {number} id - 分类ID
   * @returns {Promise} - 返回分类详情
   */
  getCategory: (id) => {
    return request({
      url: `/categories/${id}`,
      method: 'get'
    })
  },

  /**
   * 更新分类
   * @param {number} id - 分类ID
   * @param {Object} data - 分类数据
   * @param {string} [data.name] - 分类名称
   * @param {string} [data.color] - 分类颜色
   * @returns {Promise} - 返回更新后的分类
   */
  updateCategory: (id, data) => {
    return request({
      url: `/categories/${id}`,
      method: 'put',
      data
    })
  },

  /**
   * 删除分类
   * @param {number} id - 分类ID
   * @param {number} [moveToCategoryId] - 迁移任务到的分类ID
   * @returns {Promise} - 返回删除结果
   */
  deleteCategory: (id, moveToCategoryId) => {
    return request({
      url: `/categories/${id}`,
      method: 'delete',
      params: { move_to_category_id: moveToCategoryId }
    })
  }
}