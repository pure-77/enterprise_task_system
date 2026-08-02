<!--<template>-->
<!--  <div class="register-container">-->
<!--    <el-card class="register-card">-->
<!--      <template #header>-->
<!--        <h2>用户注册</h2>-->
<!--      </template>-->
<!--      -->
<!--      <el-form-->
<!--        ref="registerForm"-->
<!--        :model="formData"-->
<!--        :rules="rules"-->
<!--        label-width="80px"-->
<!--        @submit.prevent="handleRegister"-->
<!--      >-->
<!--        <el-form-item label="邮箱" prop="email">-->
<!--          <el-input-->
<!--            v-model="formData.email"-->
<!--            placeholder="请输入邮箱"-->
<!--            clearable-->
<!--          />-->
<!--        </el-form-item>-->
<!--        -->
<!--        <el-form-item label="验证码" prop="verify_code">-->
<!--          <div class="verify-code-wrapper">-->
<!--            <el-input-->
<!--              v-model="formData.verify_code"-->
<!--              placeholder="请输入验证码"-->
<!--              maxlength="6"-->
<!--              clearable-->
<!--            />-->
<!--            <el-button-->
<!--              :disabled="isSending || countdown > 0"-->
<!--              :loading="isSending"-->
<!--              @click="handleSendVerifyCode"-->
<!--            >-->
<!--              {{ countdown > 0 ? `${countdown}秒后重发` : '发送验证码' }}-->
<!--            </el-button>-->
<!--          </div>-->
<!--        </el-form-item>-->
<!--        -->
<!--        <el-form-item label="密码" prop="password">-->
<!--          <el-input-->
<!--            v-model="formData.password"-->
<!--            type="password"-->
<!--            placeholder="请输入密码（至少6位）"-->
<!--            show-password-->
<!--            clearable-->
<!--          />-->
<!--        </el-form-item>-->
<!--        -->
<!--        <el-form-item label="昵称" prop="nickname">-->
<!--          <el-input-->
<!--            v-model="formData.nickname"-->
<!--            placeholder="请输入昵称"-->
<!--            clearable-->
<!--          />-->
<!--        </el-form-item>-->
<!--        -->
<!--        <el-form-item>-->
<!--          <el-button-->
<!--            type="primary"-->
<!--            :loading="isRegistering"-->
<!--            @click="handleRegister"-->
<!--            style="width: 100%"-->
<!--          >-->
<!--            注册-->
<!--          </el-button>-->
<!--        </el-form-item>-->
<!--        -->
<!--        <el-form-item>-->
<!--          <div class="login-link">-->
<!--            已有账号？<router-link to="/auth/login">立即登录</router-link>-->
<!--          </div>-->
<!--        </el-form-item>-->
<!--      </el-form>-->
<!--    </el-card>-->
<!--  </div>-->
<!--</template>-->

<!--<script setup>-->
<!--import { ref, reactive } from 'vue'-->
<!--import { useRouter } from 'vue-router'-->
<!--import { ElMessage } from 'element-plus'-->
<!--import { useUserStore } from '@/pinia/userStore'-->
<!--import { validate } from '@/utils/validate'-->

<!--const router = useRouter()-->
<!--const userStore = useUserStore()-->

<!--const registerForm = ref(null)-->
<!--const isSending = ref(false)-->
<!--const isRegistering = ref(false)-->
<!--const countdown = ref(0)-->
<!--let countdownTimer = null-->

<!--const formData = reactive({-->
<!--  email: '',-->
<!--  verify_code: '',-->
<!--  password: '',-->
<!--  nickname: ''-->
<!--})-->

<!--const rules = {-->
<!--  email: [-->
<!--    { required: true, message: '请输入邮箱', trigger: 'blur' },-->
<!--    {-->
<!--      validator: (rule, value, callback) => {-->
<!--        if (!validate.email(value)) {-->
<!--          callback(new Error('邮箱格式不正确'))-->
<!--        } else {-->
<!--          callback()-->
<!--        }-->
<!--      },-->
<!--      trigger: 'blur'-->
<!--    }-->
<!--  ],-->
<!--  verify_code: [-->
<!--    { required: true, message: '请输入验证码', trigger: 'blur' },-->
<!--    {-->
<!--      validator: (rule, value, callback) => {-->
<!--        if (!validate.verifyCode(value)) {-->
<!--          callback(new Error('验证码格式不正确'))-->
<!--        } else {-->
<!--          callback()-->
<!--        }-->
<!--      },-->
<!--      trigger: 'blur'-->
<!--    }-->
<!--  ],-->
<!--  password: [-->
<!--    { required: true, message: '请输入密码', trigger: 'blur' },-->
<!--    {-->
<!--      validator: (rule, value, callback) => {-->
<!--        if (!validate.password(value)) {-->
<!--          callback(new Error('密码长度不能少于6位'))-->
<!--        } else {-->
<!--          callback()-->
<!--        }-->
<!--      },-->
<!--      trigger: 'blur'-->
<!--    }-->
<!--  ],-->
<!--  nickname: [-->
<!--    { required: true, message: '请输入昵称', trigger: 'blur' },-->
<!--    {-->
<!--      validator: (rule, value, callback) => {-->
<!--        if (!validate.nickname(value)) {-->
<!--          callback(new Error('昵称长度为2-50位'))-->
<!--        } else {-->
<!--          callback()-->
<!--        }-->
<!--      },-->
<!--      trigger: 'blur'-->
<!--    }-->
<!--  ]-->
<!--}-->

<!--const handleSendVerifyCode = async () => {-->
<!--  if (!validate.email(formData.email)) {-->
<!--    ElMessage.warning('请先输入正确的邮箱')-->
<!--    return-->
<!--  }-->
<!--  -->
<!--  isSending.value = true-->
<!--  try {-->
<!--    const response = await userStore.sendVerifyCode(formData.email)-->
<!--    ElMessage.success(response.message || '验证码已发送')-->
<!--    -->
<!--    countdown.value = response.remaining_time || 60-->
<!--    startCountdown()-->
<!--  } catch (error) {-->
<!--    console.error('发送验证码失败:', error)-->
<!--    ElMessage.error('发送验证码失败，请检查后端服务是否启动')-->
<!--  } finally {-->
<!--    isSending.value = false-->
<!--  }-->
<!--}-->

<!--const startCountdown = () => {-->
<!--  countdownTimer = setInterval(() => {-->
<!--    countdown.value&#45;&#45;-->
<!--    if (countdown.value <= 0) {-->
<!--      clearInterval(countdownTimer)-->
<!--      countdownTimer = null-->
<!--    }-->
<!--  }, 1000)-->
<!--}-->

<!--const handleRegister = async () => {-->
<!--  try {-->
<!--    await registerForm.value.validate()-->
<!--  } catch (error) {-->
<!--    return-->
<!--  }-->
<!--  -->
<!--  isRegistering.value = true-->
<!--  try {-->
<!--    await userStore.register(formData)-->
<!--    ElMessage.success('注册成功，请登录')-->
<!--    router.push('/auth/login')-->
<!--  } catch (error) {-->
<!--    console.error('注册失败:', error)-->
<!--    ElMessage.error(error.response?.data?.detail || '注册失败，请检查后端服务是否启动')-->
<!--  } finally {-->
<!--    isRegistering.value = false-->
<!--  }-->
<!--}-->
<!--</script>-->

<!--<style scoped>-->
<!--.register-container {-->
<!--  display: flex;-->
<!--  justify-content: center;-->
<!--  align-items: center;-->
<!--  min-height: 100vh;-->
<!--  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);-->
<!--}-->

<!--.register-card {-->
<!--  width: 450px;-->
<!--  border-radius: 8px;-->
<!--  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);-->
<!--}-->

<!--.register-card :deep(.el-card__header) {-->
<!--  text-align: center;-->
<!--  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);-->
<!--  color: white;-->
<!--}-->

<!--.register-card h2 {-->
<!--  margin: 0;-->
<!--  color: white;-->
<!--}-->

<!--.verify-code-wrapper {-->
<!--  display: flex;-->
<!--  gap: 10px;-->
<!--}-->

<!--.verify-code-wrapper .el-input {-->
<!--  flex: 1;-->
<!--}-->

<!--.verify-code-wrapper .el-button {-->
<!--  white-space: nowrap;-->
<!--}-->

<!--.login-link {-->
<!--  text-align: center;-->
<!--  width: 100%;-->
<!--}-->

<!--.login-link a {-->
<!--  color: #409EFF;-->
<!--  text-decoration: none;-->
<!--}-->

<!--.login-link a:hover {-->
<!--  text-decoration: underline;-->
<!--}-->
<!--</style>-->


<template>
  <div class="register-wrapper">
    <div class="register-box">
      <div class="register-card">
        <!-- 顶部标题 -->
        <div class="register-header">
          <h1>创建账号</h1>
          <p>欢迎加入个人任务管理系统</p>
        </div>

        <el-form
          ref="registerForm"
          :model="formData"
          :rules="rules"
          @submit.prevent="handleRegister"
          class="register-form"
        >
          <el-form-item prop="email">
            <el-input
              v-model="formData.email"
              placeholder="请输入邮箱"
              clearable
              size="large"
              prefix-icon="User"
            />
          </el-form-item>

          <!-- 验证码 -->
          <el-form-item prop="verify_code">
            <div class="verify-code-group">
              <el-input
                v-model="formData.verify_code"
                placeholder="请输入6位验证码"
                maxlength="6"
                clearable
                size="large"
              />
              <el-button
                :disabled="isSending || countdown > 0"
                :loading="isSending"
                @click="handleSendVerifyCode"
                size="large"
                type="primary"
                class="code-btn"
              >
                {{ countdown > 0 ? `${countdown}秒` : '获取验证码' }}
              </el-button>
            </div>
          </el-form-item>

          <el-form-item prop="password">
            <el-input
              v-model="formData.password"
              type="password"
              placeholder="请输入密码（至少6位）"
              show-password
              size="large"
              prefix-icon="Lock"
              clearable
            />
          </el-form-item>

          <el-form-item prop="nickname">
            <el-input
              v-model="formData.nickname"
              placeholder="请输入昵称"
              clearable
              size="large"
              prefix-icon="Avatar"
            />
          </el-form-item>

          <!-- 注册按钮 -->
          <el-form-item>
            <el-button
              type="primary"
              native-type="submit"
              :loading="isRegistering"
              class="register-btn"
              size="large"
            >
              完成注册
            </el-button>
          </el-form-item>

          <!-- 登录链接 -->
          <div class="register-footer">
            已有账号？
            <router-link to="/auth/login" class="login-text">立即登录</router-link>
          </div>
        </el-form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useUserStore } from '@/pinia/userStore'
import { validate } from '@/utils/validate'

const router = useRouter()
const userStore = useUserStore()

const registerForm = ref(null)
const isSending = ref(false)
const isRegistering = ref(false)
const countdown = ref(0)
let countdownTimer = null

const formData = reactive({
  email: '',
  verify_code: '',
  password: '',
  nickname: ''
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
  verify_code: [
    { required: true, message: '请输入验证码', trigger: 'blur' },
    {
      validator: (rule, value, callback) => {
        if (!validate.verifyCode(value)) {
          callback(new Error('验证码格式不正确'))
        } else {
          callback()
        }
      },
      trigger: 'blur'
    }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    {
      validator: (rule, value, callback) => {
        if (!validate.password(value)) {
          callback(new Error('密码长度不能少于6位'))
        } else {
          callback()
        }
      },
      trigger: 'blur'
    }
  ],
  nickname: [
    { required: true, message: '请输入昵称', trigger: 'blur' },
    {
      validator: (rule, value, callback) => {
        if (!validate.nickname(value)) {
          callback(new Error('昵称长度为2-50位'))
        } else {
          callback()
        }
      },
      trigger: 'blur'
    }
  ]
}

const handleSendVerifyCode = async () => {
  if (!validate.email(formData.email)) {
    ElMessage.warning('请先输入正确的邮箱')
    return
  }

  isSending.value = true
  try {
    const response = await userStore.sendVerifyCode(formData.email)
    ElMessage.success(response.message || '验证码已发送')

    countdown.value = response.remaining_time || 60
    startCountdown()
  } catch (error) {
    console.error('发送验证码失败:', error)
    ElMessage.error('发送验证码失败，请检查后端服务')
  } finally {
    isSending.value = false
  }
}

const startCountdown = () => {
  countdownTimer = setInterval(() => {
    countdown.value--
    if (countdown.value <= 0) {
      clearInterval(countdownTimer)
      countdownTimer = null
    }
  }, 1000)
}

const handleRegister = async () => {
  try {
    await registerForm.value.validate()
  } catch (error) {
    return
  }

  isRegistering.value = true
  try {
    await userStore.register(formData)
    ElMessage.success('注册成功，请登录')
    router.push('/auth/login')
  } catch (error) {
    console.error('注册失败:', error)
    ElMessage.error(error.response?.data?.detail || '注册失败')
  } finally {
    isRegistering.value = false
  }
}
</script>

<style scoped>
/* 全屏背景 */
.register-wrapper {
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
.register-box {
  width: 100%;
  max-width: 440px;
}

/* 注册卡片 */
.register-card {
  background: var(--bg-primary);
  border-radius: 20px;
  padding: 48px 40px;
  box-shadow: var(--shadow-lg);
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

/* 标题 */
.register-header {
  text-align: center;
  margin-bottom: 36px;
}

.register-header h1 {
  font-size: 28px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 8px 0;
}

.register-header p {
  font-size: 15px;
  color: var(--text-secondary);
  margin: 0;
}

/* 表单间距 */
.register-form {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

/* 验证码组合 */
.verify-code-group {
  display: flex;
  gap: 12px;
  align-items: center;
}

.verify-code-group .el-input {
  flex: 1;
}

.code-btn {
  min-width: 110px;
  border-radius: 10px !important;
}

/* 注册按钮 */
.register-btn {
  width: 100%;
  height: 48px;
  border-radius: 10px;
  font-size: 16px;
  font-weight: 500;
  margin-top: 8px;
}

/* 底部链接 */
.register-footer {
  text-align: center;
  font-size: 14px;
  color: var(--text-secondary);
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

/* 输入框增强 */
:deep(.el-input__wrapper) {
  border-radius: 10px;
  height: 48px;
  box-shadow: var(--shadow-sm);
}

:deep(.el-input__inner) {
  font-size: 15px;
}
</style>