<template>
  <div class="forgot-wrapper">
    <div class="forgot-box">
      <div class="forgot-card">
        <!-- 顶部标题区域 -->
        <div class="forgot-header">
          <h1>忘记密码</h1>
          <p>通过邮箱验证码重置您的密码</p>
        </div>

        <!-- 表单 -->
        <el-form
          ref="forgotForm"
          :model="formData"
          :rules="rules"
          @submit.prevent="handleSubmit"
          class="forgot-form"
        >
          <!-- 邮箱输入 -->
          <el-form-item prop="email">
            <el-input
              v-model="formData.email"
              placeholder="请输入注册邮箱"
              clearable
              size="large"
              prefix-icon="Message"
            />
          </el-form-item>

          <!-- 验证码输入 -->
          <el-form-item prop="code">
            <el-input
              v-model="formData.code"
              placeholder="请输入验证码"
              clearable
              size="large"
              prefix-icon="Key"
            >
              <template #append>
                <el-button
                  :loading="sendingCode"
                  :disabled="countdown > 0"
                  @click="sendVerificationCode"
                  size="small"
                >
                  {{ countdown > 0 ? `${countdown}s后重发` : '发送验证码' }}
                </el-button>
              </template>
            </el-input>
          </el-form-item>

          <!-- 新密码输入 -->
          <el-form-item prop="newPassword">
            <el-input
              v-model="formData.newPassword"
              type="password"
              placeholder="请输入新密码"
              show-password
              size="large"
              prefix-icon="Lock"
              clearable
            />
          </el-form-item>

          <!-- 确认新密码输入 -->
          <el-form-item prop="confirmPassword">
            <el-input
              v-model="formData.confirmPassword"
              type="password"
              placeholder="请确认新密码"
              show-password
              size="large"
              prefix-icon="Check"
              clearable
            />
          </el-form-item>

          <!-- 提交按钮 -->
          <el-form-item>
            <el-button
              type="primary"
              native-type="submit"
              :loading="submitting"
              class="submit-btn"
              size="large"
            >
              重置密码
            </el-button>
          </el-form-item>

          <!-- 登录链接 -->
          <div class="forgot-footer">
            想起密码了？
            <router-link to="/auth/login" class="login-text">立即登录</router-link>
          </div>
        </el-form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { profileApi } from '@/api/profile'
import { validate } from '@/utils/validate'

const router = useRouter()
const forgotForm = ref(null)
const sendingCode = ref(false)
const submitting = ref(false)
const countdown = ref(0)
let countdownTimer = null

const formData = reactive({
  email: '',
  code: '',
  newPassword: '',
  confirmPassword: ''
})

const rules = {
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    {
      validator: (rule, value, callback) => {
        if (!validate.email(value)) {
          callback(new Error('邮箱格式不正确'))
        } else {
          callback()
        }
      },
      trigger: 'blur'
    }
  ],
  code: [
    { required: true, message: '请输入验证码', trigger: 'blur' }
  ],
  newPassword: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 6, message: '密码长度至少6位', trigger: 'blur' }
  ],
  confirmPassword: [
    { required: true, message: '请确认新密码', trigger: 'blur' },
    {
      validator: (rule, value, callback) => {
        if (value !== formData.newPassword) {
          callback(new Error('两次输入的密码不一致'))
        } else {
          callback()
        }
      },
      trigger: 'blur'
    }
  ]
}

// 发送验证码
const sendVerificationCode = async () => {
  try {
    // 验证邮箱
    await forgotForm.value.validateField('email')
    
    sendingCode.value = true
    
    // 调用API发送验证码
    await profileApi.requestPasswordReset({ email: formData.email })
    
    ElMessage.success('验证码已发送到邮箱')
    
    // 开始倒计时
    startCountdown()
  } catch (error) {
    console.error('发送验证码失败:', error)
    ElMessage.error(error.response?.data?.detail || '发送验证码失败')
  } finally {
    sendingCode.value = false
  }
}

// 开始倒计时
const startCountdown = () => {
  countdown.value = 60
  
  if (countdownTimer) {
    clearInterval(countdownTimer)
  }
  
  countdownTimer = setInterval(() => {
    if (countdown.value > 0) {
      countdown.value--
    } else {
      clearInterval(countdownTimer)
    }
  }, 1000)
}

// 提交重置密码
const handleSubmit = async () => {
  try {
    // 验证表单
    await forgotForm.value.validate()
    
    submitting.value = true
    
    // 调用API重置密码
    await profileApi.verifyPasswordReset({
      email: formData.email,
      code: formData.code,
      new_password: formData.newPassword
    })
    
    ElMessage.success('密码重置成功')
    
    // 跳转到登录页面
    router.push('/auth/login')
  } catch (error) {
    console.error('重置密码失败:', error)
    ElMessage.error(error.response?.data?.detail || '重置密码失败')
  } finally {
    submitting.value = false
  }
}

// 组件卸载时清除计时器
onUnmounted(() => {
  if (countdownTimer) {
    clearInterval(countdownTimer)
  }
})
</script>

<style scoped>
/* 外层全屏背景 */
.forgot-wrapper {
  width: 100vw;
  min-height: 100vh;
  background: linear-gradient(135deg, #4158d0 0%, #7a46e0 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  box-sizing: border-box;
}

/* 卡片容器 */
.forgot-box {
  width: 100%;
  max-width: 440px;
}

/* 忘记密码卡片 */
.forgot-card {
  background: var(--bg-primary);
  border-radius: 20px;
  padding: 48px 40px;
  box-shadow: var(--shadow-lg);
  box-sizing: border-box;
  animation: fadeIn 0.4s ease forwards;
}

/* 淡入动画 */
@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* 标题区域 */
.forgot-header {
  text-align: center;
  margin-bottom: 36px;
}

.forgot-header h1 {
  font-size: 28px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 8px 0;
  line-height: 1.2;
}

.forgot-header p {
  font-size: 15px;
  color: var(--text-secondary);
  margin: 0;
}

/* 表单间距 */
.forgot-form {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

/* 提交按钮 */
.submit-btn {
  width: 100%;
  height: 48px;
  border-radius: 10px;
  font-size: 16px;
  font-weight: 500;
  margin-top: 8px;
}

/* 底部登录链接 */
.forgot-footer {
  text-align: center;
  font-size: 14px;
  color: var(--text-secondary);
  margin-top: 8px;
}

.login-text {
  color: var(--primary-color);
  font-weight: 500;
  text-decoration: none;
  margin-left: 4px;
}

.login-text:hover {
  text-decoration: underline;
}

/* 输入框样式增强 */
:deep(.el-input__wrapper) {
  border-radius: 10px;
  height: 48px;
  box-shadow: var(--shadow-sm);
}

:deep(.el-input__inner) {
  font-size: 15px;
}
</style>