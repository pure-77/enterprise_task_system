import { defineStore } from 'pinia'
import { workspaceApi } from '@/api/workspace'
import { ElMessage } from 'element-plus'

export const useWorkspaceStore = defineStore('workspace', {
  state: () => ({
    workspaces: [],
    currentWorkspaceId: null,
    currentWorkspace: null,
    loading: false
  }),

  getters: {
    getWorkspaces: (state) => state.workspaces,
    isPersonalMode: (state) => state.currentWorkspaceId === null,
    currentRole: (state) => {
      if (!state.currentWorkspaceId || !state.workspaces.length) return null
      const ws = state.workspaces.find(w => w.id === state.currentWorkspaceId)
      return ws ? ws.role : null
    }
  },

  actions: {
    async loadWorkspaces() {
      this.loading = true
      try {
        const data = await workspaceApi.getWorkspaces()
        this.workspaces = data
        return data
      } catch (error) {
        console.error('加载空间列表失败:', error)
        return []
      } finally {
        this.loading = false
      }
    },

    async createWorkspace(data) {
      try {
        const ws = await workspaceApi.createWorkspace(data)
        this.workspaces.unshift(ws)
        ElMessage.success('空间创建成功')
        return ws
      } catch (error) {
        ElMessage.error('空间创建失败')
        throw error
      }
    },

    async updateWorkspace(id, data) {
      try {
        await workspaceApi.updateWorkspace(id, data)
        const index = this.workspaces.findIndex(w => w.id === id)
        if (index !== -1) {
          this.workspaces[index] = { ...this.workspaces[index], ...data }
        }
        ElMessage.success('空间更新成功')
      } catch (error) {
        ElMessage.error('空间更新失败')
        throw error
      }
    },

    async deleteWorkspace(id) {
      try {
        await workspaceApi.deleteWorkspace(id)
        this.workspaces = this.workspaces.filter(w => w.id !== id)
        if (this.currentWorkspaceId === id) {
          this.switchToPersonal()
        }
        ElMessage.success('空间已解散')
      } catch (error) {
        ElMessage.error('解散空间失败')
        throw error
      }
    },

    switchWorkspace(workspaceId) {
      this.currentWorkspaceId = workspaceId
      localStorage.setItem('currentWorkspaceId', workspaceId || '')
    },

    switchToPersonal() {
      this.currentWorkspaceId = null
      localStorage.removeItem('currentWorkspaceId')
    },

    restoreWorkspaceContext() {
      const saved = localStorage.getItem('currentWorkspaceId')
      if (saved === '' || saved === null || saved === undefined) {
        // 自动选择第一个可用工作空间，避免 null 导致新模块 API 报错
        this.currentWorkspaceId = this.workspaces.length > 0 ? this.workspaces[0].id : null
      } else {
        this.currentWorkspaceId = parseInt(saved)
      }
    }
  }
})
