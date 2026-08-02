import { defineStore } from 'pinia'
import { taskApi } from '@/api/task'
import { useWorkspaceStore } from './workspaceStore'
import { ElMessage } from 'element-plus'

export const useTaskStore = defineStore('task', {
  state: () => ({
    tasks: [],
    total: 0,
    currentPage: 1,
    pageSize: 10,
    loading: false,
    selectedTaskIds: [],
    filters: {
      status: null,
      priority: null,
      category_id: null,
      tag_id: null,
      keyword: null,
      due_date_start: null,
      due_date_end: null,
      assignee_id: null
    }
  }),

  getters: {
    getTasks: (state) => state.tasks,
    getSelectedTasks: (state) => {
      return state.tasks.filter(task => state.selectedTaskIds.includes(task.id))
    },
    getSelectedCount: (state) => state.selectedTaskIds.length,
    getTaskById: (state) => (id) => {
      return state.tasks.find(task => task.id === id)
    }
  },

  actions: {
    _getWorkspaceContext() {
      const workspaceStore = useWorkspaceStore()
      if (workspaceStore.currentWorkspaceId) {
        return { workspace_id: workspaceStore.currentWorkspaceId }
      }
      return {}
    },

    async loadTasks() {
      this.loading = true
      try {
        const params = {
          page: this.currentPage,
          page_size: this.pageSize,
          ...this.filters,
          ...this._getWorkspaceContext()
        }
        Object.keys(params).forEach(key => {
          if (params[key] === null || params[key] === undefined || params[key] === '') {
            delete params[key]
          }
        })
        const data = await taskApi.getTasks(params)
        this.tasks = data.tasks
        this.total = data.total
        return data
      } catch (error) {
        ElMessage.error('获取任务列表失败')
        console.error('加载任务列表失败:', error)
        return []
      } finally {
        this.loading = false
      }
    },

    async createTask(data) {
      try {
        const task = await taskApi.createTask({ ...data, ...this._getWorkspaceContext() })
        this.tasks.unshift(task)
        this.total += 1
        ElMessage.success('任务创建成功')
        return task
      } catch (error) {
        ElMessage.error('任务创建失败')
        console.error('创建任务失败:', error)
        throw error
      }
    },

    async updateTask(id, data) {
      try {
        const updatedTask = await taskApi.updateTask(id, { ...data, ...this._getWorkspaceContext() })
        const index = this.tasks.findIndex(task => task.id === id)
        if (index !== -1) {
          this.tasks[index] = updatedTask
        }
        ElMessage.success('任务更新成功')
        return updatedTask
      } catch (error) {
        ElMessage.error('任务更新失败')
        console.error('更新任务失败:', error)
        throw error
      }
    },

    async deleteTask(id) {
      try {
        await taskApi.deleteTask(id)
        this.tasks = this.tasks.filter(task => task.id !== id)
        this.selectedTaskIds = this.selectedTaskIds.filter(taskId => taskId !== id)
        this.total -= 1
        ElMessage.success('任务删除成功')
        return true
      } catch (error) {
        ElMessage.error('任务删除失败')
        console.error('删除任务失败:', error)
        throw error
      }
    },

    async updateTaskStatus(id, status) {
      try {
        const updatedTask = await taskApi.updateTaskStatus(id, status)
        const index = this.tasks.findIndex(task => task.id === id)
        if (index !== -1) {
          this.tasks[index] = updatedTask
        }
        ElMessage.success('任务状态更新成功')
        return updatedTask
      } catch (error) {
        ElMessage.error('任务状态更新失败')
        console.error('更新任务状态失败:', error)
        throw error
      }
    },

    async batchUpdateTasks(data) {
      try {
        const result = await taskApi.batchUpdateTasks(
          { ...data, ...this._getWorkspaceContext() }
        )
        await this.loadTasks()
        this.selectedTaskIds = []
        ElMessage.success(result.message)
        return result
      } catch (error) {
        ElMessage.error('批量更新失败')
        console.error('批量更新失败:', error)
        throw error
      }
    },

    async batchDeleteTasks(taskIds) {
      try {
        const result = await taskApi.batchDeleteTasks(
          taskIds,
          this._getWorkspaceContext().workspace_id
        )
        await this.loadTasks()
        this.selectedTaskIds = []
        ElMessage.success(result.message)
        return result
      } catch (error) {
        ElMessage.error('批量删除失败')
        console.error('批量删除失败:', error)
        throw error
      }
    },

    setFilters(filters) {
      this.filters = { ...this.filters, ...filters }
      this.currentPage = 1
    },

    resetFilters() {
      this.filters = {
        status: null, priority: null, category_id: null, tag_id: null,
        keyword: null, due_date_start: null, due_date_end: null,
        assignee_id: null
      }
      this.currentPage = 1
    },

    setCurrentPage(page) { this.currentPage = page },
    setPageSize(size) { this.pageSize = size; this.currentPage = 1 },

    selectTask(taskId) {
      if (!this.selectedTaskIds.includes(taskId)) this.selectedTaskIds.push(taskId)
    },
    deselectTask(taskId) {
      this.selectedTaskIds = this.selectedTaskIds.filter(id => id !== taskId)
    },
    toggleTaskSelection(taskId) {
      if (this.selectedTaskIds.includes(taskId)) this.deselectTask(taskId)
      else this.selectTask(taskId)
    },
    selectAllTasks() { this.selectedTaskIds = this.tasks.map(task => task.id) },
    deselectAllTasks() { this.selectedTaskIds = [] },
    isAllSelected() { return this.tasks.length > 0 && this.selectedTaskIds.length === this.tasks.length },
    isIndeterminate() { return this.selectedTaskIds.length > 0 && this.selectedTaskIds.length < this.tasks.length }
  }
})
