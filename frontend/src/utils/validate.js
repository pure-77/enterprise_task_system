// 验证工具函数
export const validate = {
  // 邮箱验证
  email: (value) => {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
    return emailRegex.test(value)
  },
  
  // 验证码验证
  verifyCode: (value) => {
    const codeRegex = /^\d{6}$/
    return codeRegex.test(value)
  },
  
  // 密码验证
  password: (value) => {
    return value.length >= 6
  },
  
  // 昵称验证
  nickname: (value) => {
    return value.length >= 2 && value.length <= 50
  }
}
