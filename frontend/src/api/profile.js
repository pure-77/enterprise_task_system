import request from './request'

export const profileApi = {
  updateNickname(data) {
    return request({
      url: '/profile/nickname',
      method: 'put',
      data
    })
  },

  updatePassword(data) {
    return request({
      url: '/profile/password',
      method: 'put',
      data
    })
  },

  updateEmail(data) {
    return request({
      url: '/profile/email',
      method: 'put',
      data
    })
  },

  verifyEmailChange(data) {
    return request({
      url: '/profile/email/verify',
      method: 'post',
      data
    })
  },

  requestPasswordReset(data) {
    return request({
      url: '/profile/reset-password/request',
      method: 'post',
      data
    })
  },

  verifyPasswordReset(data) {
    return request({
      url: '/profile/reset-password/verify',
      method: 'post',
      data
    })
  },

  getUserInfo() {
    return request({
      url: '/profile/me',
      method: 'get'
    })
  }
}