import request from './request'

/**
 * 任务API - 面试考点：前后端API交互
 */
export const taskApi = {
  /**
   * 创建任务
   * @param {Object} data - 任务数据
   * @param {string} data.title - 任务标题
   * @param {string} [data.description] - 任务描述
   * @param {string} [data.due_date] - 截止日期
   * @param {string} [data.priority] - 任务优先级
   * @param {number} data.category_id - 分类ID
   * @returns {Promise} - 返回创建的任务
   */
  createTask: (data) => {
    return request({
      url: '/tasks',
      method: 'post',
      data
    })
  },

  /**
   * 获取任务列表
   * @param {Object} params - 查询参数
   * @param {string} [params.status] - 任务状态
   * @param {string} [params.priority] - 任务优先级
   * @param {number} [params.category_id] - 分类ID
   * @param {string} [params.keyword] - 关键词搜索
   * @param {string} [params.due_date_start] - 截止日期开始
   * @param {string} [params.due_date_end] - 截止日期结束
   * @param {number} [params.page] - 页码
   * @param {number} [params.page_size] - 每页数量
   * @returns {Promise} - 返回任务列表
   */
  getTasks: (params) => {
    return request({
      url: '/tasks',
      method: 'get',
      params
    })
  },

  /**
   * 获取单个任务
   * @param {number} id - 任务ID
   * @returns {Promise} - 返回任务详情
   */
  getTask: (id) => {
    return request({
      url: `/tasks/${id}`,
      method: 'get'
    })
  },

  /**
   * 更新任务
   * @param {number} id - 任务ID
   * @param {Object} data - 任务数据
   * @param {string} [data.title] - 任务标题
   * @param {string} [data.description] - 任务描述
   * @param {string} [data.due_date] - 截止日期
   * @param {string} [data.status] - 任务状态
   * @param {string} [data.priority] - 任务优先级
   * @param {number} [data.category_id] - 分类ID
   * @returns {Promise} - 返回更新后的任务
   */
  updateTask: (id, data) => {
    return request({
      url: `/tasks/${id}`,
      method: 'put',
      data
    })
  },

  /**
   * 删除任务
   * @param {number} id - 任务ID
   * @returns {Promise} - 返回删除结果
   */
  deleteTask: (id) => {
    return request({
      url: `/tasks/${id}`,
      method: 'delete'
    })
  },

  /**
   * 更新任务状态
   * @param {number} id - 任务ID
   * @param {string} status - 任务状态
   * @returns {Promise} - 返回更新后的任务
   */
  updateTaskStatus: (id, status) => {
    return request({
      url: `/tasks/${id}/status`,
      method: 'patch',
      data: { status }
    })
  },

  /**
   * 批量更新任务
   * @param {Object} data - 批量更新数据
   * @param {number[]} data.task_ids - 任务ID列表
   * @param {string} [data.status] - 任务状态
   * @param {string} [data.priority] - 任务优先级
   * @param {number} [data.category_id] - 分类ID
   * @returns {Promise} - 返回更新结果
   */
  batchUpdateTasks: (data) => {
    return request({
      url: '/tasks/batch/update',
      method: 'post',
      data
    })
  },

  /**
   * 批量删除任务
   * @param {number[]} taskIds - 任务ID列表
   * @returns {Promise} - 返回删除结果
   */
  batchDeleteTasks: (taskIds, workspaceId) => {
    return request({
      url: '/tasks/batch/delete',
      method: 'post',
      data: taskIds,
      params: workspaceId ? { workspace_id: workspaceId } : {}
    })
  },

  // 成员标记自己完成团队公开任务
  completeTeamTask(taskId) {
    return request({
      url: `/tasks/${taskId}/complete`,
      method: 'post'
    })
  }
}