import { defineStore } from 'pinia'
import { auth } from '@/utils/auth'
import { authApi } from '@/api/auth'
import { profileApi } from '@/api/profile'

export const useUserStore = defineStore('user', {
  state: () => ({
    token: auth.getToken(),
    refreshToken: auth.getRefreshToken(),
    userInfo: JSON.parse(localStorage.getItem('userInfo') || 'null'),
    isLoggedIn: !!auth.getToken(),
    loading: false
  }),
  
  getters: {
    getUserId: (state) => state.userInfo?.id,
    getEmail: (state) => state.userInfo?.email,
    getNickname: (state) => state.userInfo?.nickname,
    getAvatar: (state) => state.userInfo?.avatar
  },
  
  actions: {
    setToken(token) {
      this.token = token
      auth.setToken(token)
    },
    
    setRefreshToken(token) {
      this.refreshToken = token
      auth.setRefreshToken(token)
    },
    
    setUserInfo(userInfo) {
      this.userInfo = userInfo
      this.isLoggedIn = true
      // 持久化存储用户信息
      localStorage.setItem('userInfo', JSON.stringify(userInfo))
    },
    
    updateNickname(nickname) {
      if (this.userInfo) {
        this.userInfo.nickname = nickname
      }
    },
    
    updateAvatar(avatar) {
      if (this.userInfo) {
        this.userInfo.avatar = avatar
      }
    },
    
    async sendVerifyCode(email) {
      try {
        const response = await authApi.sendVerifyCode(email)
        return response
      } catch (error) {
        throw error
      }
    },
    
    async register(userData) {
      try {
        const response = await authApi.register(userData)
        return response
      } catch (error) {
        throw error
      }
    },
    
    async loadUserInfo() {
    try {
      const userInfo = await profileApi.getUserInfo()
      // 确保头像URL是完整的绝对路径
      if (userInfo.avatar && userInfo.avatar.startsWith('/')) {
        // 静态文件服务直接挂载在根路径下，不需要API路径
        const baseUrl = import.meta.env.VITE_API_BASE_URL.replace('/api/v1', '')
        userInfo.avatar = baseUrl + userInfo.avatar
      }
      this.setUserInfo(userInfo)
      return userInfo
    } catch (error) {
      console.error('获取用户信息失败:', error)
      return null
    }
  },

  async login(credentials) {
    this.loading = true
    try {
      const response = await authApi.login(credentials)
      this.setToken(response.access_token)
      this.setRefreshToken(response.refresh_token)
      // 登录成功后获取用户信息
      await this.loadUserInfo()
      return response
    } catch (error) {
      this.isLoggedIn = false
      this.token = null
      this.refreshToken = null
      auth.removeToken()
      throw error
    } finally {
      this.loading = false
    }
  },
    
    async logout() {
      this.loading = true
      try {
        await authApi.logout()
      } catch (error) {
        console.error('Logout error:', error)
      } finally {
        this.token = null
        this.refreshToken = null
        this.userInfo = null
        this.isLoggedIn = false
        auth.removeToken()
        // 清除本地存储的用户信息
        localStorage.removeItem('userInfo')
        this.loading = false
        
        // 强制导航到登录页
        window.location.href = '/auth/login'
      }
    },
    
    async checkAuth() {
      if (!this.token) return false
      // 本地解码JWT检查是否过期
      if (auth.isAccessTokenExpired()) {
        // access_token已过期，尝试用refresh_token刷新
        if (this.refreshToken && !auth.isRefreshTokenExpired()) {
          try {
            const response = await authApi.refreshToken()
            this.setToken(response.access_token)
            this.setRefreshToken(response.refresh_token)
            return true
          } catch {
            // 刷新失败，token无效
            return false
          }
        }
        return false
      }
      return true
    },

    async initAuth() {
      if (this.token) {
        const isValid = await this.checkAuth()
        this.isLoggedIn = isValid
        if (!isValid) {
          auth.removeToken()
          this.token = null
          this.refreshToken = null
          this.userInfo = null
          localStorage.removeItem('userInfo')
        }
      } else {
        this.isLoggedIn = false
      }
    }
  }
})
