import { defineStore } from 'pinia'
import { categoryApi } from '@/api/category'
import { useWorkspaceStore } from './workspaceStore'
import { ElMessage } from 'element-plus'

export const useCategoryStore = defineStore('category', {
  state: () => ({
    categories: [],
    loading: false
  }),

  getters: {
    getCategories: (state) => state.categories,
    getCategoryById: (state) => (id) => {
      return state.categories.find(category => category.id === id)
    }
  },

  actions: {
    _getWorkspaceParam() {
      const workspaceStore = useWorkspaceStore()
      if (workspaceStore.currentWorkspaceId) {
        return { workspace_id: workspaceStore.currentWorkspaceId }
      }
      return {}
    },

    async loadCategories() {
      this.loading = true
      try {
        const params = { ...this._getWorkspaceParam() }
        const data = await categoryApi.getCategories(params)
        this.categories = data
        return data
      } catch (error) {
        ElMessage.error('获取分类列表失败')
        console.error('加载分类列表失败:', error)
        return []
      } finally {
        this.loading = false
      }
    },

    async createCategory(data) {
      try {
        const category = await categoryApi.createCategory({
          ...data,
          ...this._getWorkspaceParam()
        })
        this.categories.push(category)
        ElMessage.success('分类创建成功')
        return category
      } catch (error) {
        ElMessage.error('分类创建失败')
        console.error('创建分类失败:', error)
        throw error
      }
    },

    async updateCategory(id, data) {
      try {
        const updatedCategory = await categoryApi.updateCategory(id, data)
        const index = this.categories.findIndex(c => c.id === id)
        if (index !== -1) this.categories[index] = updatedCategory
        ElMessage.success('分类更新成功')
        return updatedCategory
      } catch (error) {
        ElMessage.error('分类更新失败')
        console.error('更新分类失败:', error)
        throw error
      }
    },

    async deleteCategory(id, moveToCategoryId) {
      try {
        await categoryApi.deleteCategory(id, moveToCategoryId)
        this.categories = this.categories.filter(c => c.id !== id)
        ElMessage.success('分类删除成功')
        return true
      } catch (error) {
        ElMessage.error('分类删除失败')
        console.error('删除分类失败:', error)
        throw error
      }
    }
  }
})
