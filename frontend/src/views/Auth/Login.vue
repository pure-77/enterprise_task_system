

<template>
  <div class="login-wrapper">
    <div class="login-bg-shapes">
      <div class="shape shape-1"></div>
      <div class="shape shape-2"></div>
    </div>
    <div class="login-box">
      <div class="login-card">
        <!-- 顶部标题区域 -->
        <div class="login-header">
          <h1>欢迎回来</h1>
          <p>登录到任务管理系统</p>
        </div>

        <!-- 表单 -->
        <el-form
          ref="loginForm"
          :model="formData"
          :rules="rules"
          @submit.prevent="handleLogin"
          class="login-form"
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

          <el-form-item prop="password">
            <el-input
              v-model="formData.password"
              type="password"
              placeholder="请输入密码"
              show-password
              size="large"
              prefix-icon="Lock"
              clearable
            />
          </el-form-item>

          <!-- 登录按钮 -->
          <el-form-item>
            <el-button
              type="primary"
              native-type="submit"
              :loading="userStore.loading"
              class="login-btn"
              size="large"
            >
              安全登录
            </el-button>
          </el-form-item>

          <!-- 注册链接和忘记密码 -->
          <div class="login-footer">
            <div class="footer-links">
              <router-link to="/auth/forgot-password" class="forgot-text">忘记密码？</router-link>
              <span class="footer-divider">|</span>
              <span>还没有账号？</span>
              <router-link to="/auth/register" class="register-text">立即注册</router-link>
            </div>
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
const loginForm = ref(null)

const formData = reactive({
  email: '',
  password: ''
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
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' }
  ]
}

const handleLogin = async () => {
  try {
    await loginForm.value.validate()
  } catch (error) {
    return
  }

  try {
    await userStore.login(formData)
    ElMessage.success('登录成功')
    router.push('/')
  } catch (error) {
    console.error('登录失败:', error)
    ElMessage.error(error.response?.data?.detail || '登录失败，请检查后端服务是否启动')
  }
}
</script>

<style scoped>
/* 外层全屏背景 — 紫粉渐变 */
.login-wrapper {
  width: 100vw; min-height: 100vh;
  background: linear-gradient(135deg, #7C3AED 0%, #A855F7 30%, #EC4899 80%, #F472B6 100%);
  display: flex; align-items: center; justify-content: center;
  padding: 20px; box-sizing: border-box;
  position: relative; overflow: hidden;
}
/* 装饰性背景图形 */
.login-bg-shapes { position: absolute; inset: 0; pointer-events: none; }
.shape {
  position: absolute; border-radius: 50%;
  background: rgba(255,255,255,0.06);
}
.shape-1 { width: 600px; height: 600px; top: -200px; right: -150px; }
.shape-2 { width: 400px; height: 400px; bottom: -100px; left: -100px; }

/* 卡片容器 */
.login-box {
  width: 100%;
  max-width: 440px;
}

/* 登录卡片 */
.login-card {
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
.login-header {
  text-align: center;
  margin-bottom: 36px;
}

.login-header h1 {
  font-size: 28px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 8px 0;
  line-height: 1.2;
}

.login-header p {
  font-size: 15px;
  color: var(--text-secondary);
  margin: 0;
}

/* 表单间距 */
.login-form {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

/* 登录按钮 */
.login-btn {
  width: 100%;
  height: 48px;
  border-radius: 10px;
  font-size: 16px;
  font-weight: 500;
  margin-top: 8px;
}

/* 底部注册链接 */
.login-footer {
  text-align: center;
  font-size: 14px;
  color: var(--text-secondary);
}

.register-text {
  color: var(--primary-color);
  font-weight: 500;
  text-decoration: none;
  margin-left: 4px;
}

.register-text:hover {
  text-decoration: underline;
}

.forgot-text {
  color: var(--primary-color);
  font-weight: 500;
  text-decoration: none;
}

.forgot-text:hover {
  text-decoration: underline;
}

.footer-links {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
}

.footer-divider {
  color: var(--text-light);
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