import request from './request'

export const authApi = {
  sendVerifyCode(email) {
    return request.post('/auth/send-verify-code', { email })
  },
  
  register(data) {
    return request.post('/auth/register', data)
  },
  
  login(data) {
    return request.post('/auth/login', data)
  },
  
  logout() {
    return request.post('/auth/logout')
  },
  
  refreshToken() {
    const refreshToken = localStorage.getItem('refresh_token')
    return request.post('/auth/refresh', { refresh_token: refreshToken }, { _skipAuth: true })
  }
}
