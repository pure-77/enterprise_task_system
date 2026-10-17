import axios from 'axios'
import { ElMessage } from 'element-plus'
import { auth } from '@/utils/auth'
import { authApi } from './auth'
import { useUserStore } from '@/pinia/userStore'

const request = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL,
  timeout: 10000
})

// 标记是否正在刷新令牌
let isRefreshing = false
// 存储需要重试的请求（{ resolve, reject, config }）
let requests = []

request.interceptors.request.use(
  config => {
    // 刷新令牌请求跳过 Authorization header，避免过期 token 干扰
    if (!config._skipAuth) {
      const token = auth.getToken()
      if (token) {
        config.headers.Authorization = `Bearer ${token}`
      }
    }
    return config
  },
  error => {
    return Promise.reject(error)
  }
)

request.interceptors.response.use(
  response => {
    // 统一解包: {code:0, data:...} → 直接返回 data 内容
    const body = response.data
    if (body && typeof body === 'object' && 'code' in body) {
      if (body.code === 0) {
        return body.data
      }
      // 业务错误
      ElMessage.error(body.message || '请求失败')
      return Promise.reject(new Error(body.message || '请求失败'))
    }
    return body
  },
  async error => {
    if (error.response) {
      const { status, data, config } = error.response
      // 后端 AppCodeException 响应体为 {code, message, data, detail?}
      // 业务消息优先取 message，兼容旧版 HTTPException 的 detail
      const errMsg = data?.message || data?.detail

      switch (status) {
        case 400:
          ElMessage.error(errMsg || '请求参数错误')
          break
        case 401:
          // 检查当前是否在登录页面
          const isLoginPage = window.location.pathname === '/auth/login'
          
          // 如果不是登录页面，尝试刷新令牌
          if (!isLoginPage) {
            const refreshToken = auth.getRefreshToken()
            
            if (refreshToken && !isRefreshing) {
              isRefreshing = true
              
              try {
                // 调用刷新令牌接口
                const response = await authApi.refreshToken()
                
                // 更新令牌
                auth.setToken(response.access_token)
                auth.setRefreshToken(response.refresh_token)
                
                // 更新Pinia状态
                const userStore = useUserStore()
                userStore.token = response.access_token
                userStore.refreshToken = response.refresh_token
                
                // 重新发起之前失败的请求
                requests.forEach(({ resolve, config }) => {
                  config.headers.Authorization = `Bearer ${response.access_token}`
                  resolve(request(config))
                })
                requests = []
                
                // 重新发起当前请求
                config.headers.Authorization = `Bearer ${response.access_token}`
                return request(config)
              } catch (refreshError) {
                // 多标签页竞态：另一个标签页可能刚刷新过令牌，localStorage 里已是新 token
                const latestRefresh = auth.getRefreshToken()
                if (refreshError.response?.status === 401 && latestRefresh && latestRefresh !== refreshToken) {
                  try {
                    const retry = await authApi.refreshToken()
                    auth.setToken(retry.access_token)
                    auth.setRefreshToken(retry.refresh_token)
                    const userStore2 = useUserStore()
                    userStore2.token = retry.access_token
                    userStore2.refreshToken = retry.refresh_token
                    requests.forEach(({ resolve, config }) => {
                      config.headers.Authorization = `Bearer ${retry.access_token}`
                      resolve(request(config))
                    })
                    requests = []
                    config.headers.Authorization = `Bearer ${retry.access_token}`
                    return request(config)
                  } catch { /* 重试仍失败，走下方踢登录逻辑 */ }
                }

                // 刷新失败，拒绝所有排队请求
                requests.forEach(({ reject }) => reject(refreshError))
                requests = []

                // 区分网络错误和认证失败
                if (refreshError.response && refreshError.response.status === 401) {
                  // 刷新令牌本身无效，清除所有状态
                  auth.removeToken()
                  const userStore = useUserStore()
                  userStore.token = null
                  userStore.refreshToken = null
                  userStore.userInfo = null
                  userStore.isLoggedIn = false
                  localStorage.removeItem('userInfo')
                  ElMessage.error('登录已过期，请重新登录')
                  window.location.href = '/auth/login'
                } else {
                  // 网络错误或服务器错误，保留令牌让用户重试
                  ElMessage.error('网络异常，请刷新页面重试')
                }
              } finally {
                isRefreshing = false
              }
            } else if (refreshToken && isRefreshing) {
              // 如果正在刷新令牌，将请求加入队列
              return new Promise((resolve, reject) => {
                requests.push({ resolve, reject, config })
              })
            } else {
              // 没有刷新令牌，跳转到登录页面
              auth.removeToken()
              // 同步Pinia状态
              const userStore = useUserStore()
              userStore.token = null
              userStore.refreshToken = null
              userStore.userInfo = null
              userStore.isLoggedIn = false
              localStorage.removeItem('userInfo')
              ElMessage.error(data.detail || '未授权，请重新登录')
              window.location.href = '/auth/login'
            }
          } else {
            // 登录页面的401错误，强制刷新页面
            auth.removeToken()
            // 同步Pinia状态
            const userStore = useUserStore()
            userStore.token = null
            userStore.refreshToken = null
            userStore.userInfo = null
            userStore.isLoggedIn = false
            localStorage.removeItem('userInfo')
            window.location.reload()
          }
          break
        case 403:
          ElMessage.error(errMsg || '没有权限访问')
          break
        case 404:
          ElMessage.error(errMsg || '请求的资源不存在')
          break
        case 409:
          ElMessage.error(errMsg || '数据冲突')
          break
        case 422:
          ElMessage.error(errMsg || '参数验证失败')
          break
        case 429:
          ElMessage.error(errMsg || '请求过于频繁')
          break
        case 500:
          ElMessage.error(errMsg || '服务器错误')
          break
        default:
          ElMessage.error('网络错误')
      }
    } else {
      ElMessage.error('网络连接失败')
    }
    
    return Promise.reject(error)
  }
)

export default request
