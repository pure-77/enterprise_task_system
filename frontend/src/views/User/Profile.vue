<!--<template>-->
<!--  <div class="profile-container">-->
<!--    <el-card>-->
<!--      <template #header>-->
<!--        <span>个人中心</span>-->
<!--      </template>-->
<!--      -->
<!--      <el-tabs v-model="activeTab">-->
<!--        &lt;!&ndash; 基本信息 &ndash;&gt;-->
<!--        <el-tab-pane label="基本信息" name="basic">-->
<!--          <el-form :model="userForm" :rules="rules" label-width="100px" style="max-width: 600px;">-->
<!--            <el-form-item label="头像">-->
<!--              <el-upload-->
<!--                class="avatar-uploader"-->
<!--                :action="uploadUrl"-->
<!--                :show-file-list="false"-->
<!--                :on-success="handleAvatarSuccess"-->
<!--                :before-upload="beforeAvatarUpload"-->
<!--              >-->
<!--                <img v-if="userForm.avatar" :src="userForm.avatar" class="avatar" />-->
<!--                <el-icon v-else class="avatar-uploader-icon"><Plus /></el-icon>-->
<!--              </el-upload>-->
<!--            </el-form-item>-->
<!--            -->
<!--            <el-form-item label="昵称" prop="nickname">-->
<!--              <el-input v-model="userForm.nickname" />-->
<!--            </el-form-item>-->
<!--            -->
<!--            <el-form-item label="邮箱" prop="email">-->
<!--              <el-input v-model="userForm.email" disabled />-->
<!--            </el-form-item>-->
<!--            -->
<!--            <el-form-item>-->
<!--              <el-button type="primary" @click="updateNickname">保存昵称</el-button>-->
<!--            </el-form-item>-->
<!--          </el-form>-->
<!--        </el-tab-pane>-->
<!--        -->
<!--        &lt;!&ndash; 修改密码 &ndash;&gt;-->
<!--        <el-tab-pane label="修改密码" name="password">-->
<!--          <el-form :model="passwordForm" :rules="passwordRules" label-width="100px" style="max-width: 600px;">-->
<!--            <el-form-item label="旧密码" prop="old_password">-->
<!--              <el-input v-model="passwordForm.old_password" type="password" show-password />-->
<!--            </el-form-item>-->
<!--            -->
<!--            <el-form-item label="新密码" prop="new_password">-->
<!--              <el-input v-model="passwordForm.new_password" type="password" show-password />-->
<!--            </el-form-item>-->
<!--            -->
<!--            <el-form-item label="确认密码" prop="confirm_password">-->
<!--              <el-input v-model="passwordForm.confirm_password" type="password" show-password />-->
<!--            </el-form-item>-->
<!--            -->
<!--            <el-form-item>-->
<!--              <el-button type="primary" @click="updatePassword">修改密码</el-button>-->
<!--            </el-form-item>-->
<!--          </el-form>-->
<!--        </el-tab-pane>-->
<!--        -->
<!--        &lt;!&ndash; 修改邮箱 &ndash;&gt;-->
<!--        <el-tab-pane label="修改邮箱" name="email">-->
<!--          <el-form :model="emailForm" :rules="emailRules" label-width="100px" style="max-width: 600px;">-->
<!--            <el-form-item label="当前密码" prop="password">-->
<!--              <el-input v-model="emailForm.password" type="password" show-password />-->
<!--            </el-form-item>-->
<!--            -->
<!--            <el-form-item label="新邮箱" prop="new_email">-->
<!--              <el-input v-model="emailForm.new_email" />-->
<!--            </el-form-item>-->
<!--            -->
<!--            <el-form-item>-->
<!--              <el-button type="primary" @click="requestEmailChange">发送验证码</el-button>-->
<!--            </el-form-item>-->
<!--            -->
<!--            <el-form-item v-if="emailChangeStep === 'verify'">-->
<!--              <el-input v-model="emailForm.verification_code" placeholder="请输入验证码" />-->
<!--            </el-form-item>-->
<!--            -->
<!--            <el-form-item v-if="emailChangeStep === 'verify'">-->
<!--              <el-button type="primary" @click="verifyEmailChange">验证邮箱</el-button>-->
<!--            </el-form-item>-->
<!--          </el-form>-->
<!--        </el-tab-pane>-->
<!--      </el-tabs>-->
<!--    </el-card>-->
<!--  </div>-->
<!--</template>-->

<!--<script setup>-->
<!--import { ref, onMounted } from 'vue'-->
<!--import { ElMessage } from 'element-plus'-->
<!--import { Plus } from '@element-plus/icons-vue'-->
<!--import { useUserStore } from '@/pinia/userStore'-->
<!--import { profileApi } from '@/api/profile'-->

<!--const userStore = useUserStore()-->

<!--const activeTab = ref('basic')-->
<!--const uploadUrl = ref(`${import.meta.env.VITE_API_BASE_URL}/profile/avatar`)-->

<!--const userForm = ref({-->
<!--  nickname: '',-->
<!--  email: '',-->
<!--  avatar: ''-->
<!--})-->

<!--const passwordForm = ref({-->
<!--  old_password: '',-->
<!--  new_password: '',-->
<!--  confirm_password: ''-->
<!--})-->

<!--const emailForm = ref({-->
<!--  password: '',-->
<!--  new_email: '',-->
<!--  verification_code: ''-->
<!--})-->

<!--const emailChangeStep = ref('request')-->

<!--const rules = {-->
<!--  nickname: [-->
<!--    { required: true, message: '请输入昵称', trigger: 'blur' }-->
<!--  ]-->
<!--}-->

<!--const passwordRules = {-->
<!--  old_password: [-->
<!--    { required: true, message: '请输入旧密码', trigger: 'blur' }-->
<!--  ],-->
<!--  new_password: [-->
<!--    { required: true, message: '请输入新密码', trigger: 'blur' },-->
<!--    { min: 6, message: '密码长度不能少于6位', trigger: 'blur' }-->
<!--  ],-->
<!--  confirm_password: [-->
<!--    { required: true, message: '请确认密码', trigger: 'blur' },-->
<!--    {-->
<!--      validator: (rule, value, callback) => {-->
<!--        if (value !== passwordForm.value.new_password) {-->
<!--          callback(new Error('两次输入的密码不一致'))-->
<!--        } else {-->
<!--          callback()-->
<!--        }-->
<!--      },-->
<!--      trigger: 'blur'-->
<!--    }-->
<!--  ]-->
<!--}-->

<!--const emailRules = {-->
<!--  password: [-->
<!--    { required: true, message: '请输入当前密码', trigger: 'blur' }-->
<!--  ],-->
<!--  new_email: [-->
<!--    { required: true, message: '请输入新邮箱', trigger: 'blur' },-->
<!--    { type: 'email', message: '请输入正确的邮箱地址', trigger: 'blur' }-->
<!--  ]-->
<!--}-->

<!--const loadUserInfo = () => {-->
<!--  userForm.value.nickname = userStore.getNickname || ''-->
<!--  userForm.value.email = userStore.getEmail || ''-->
<!--  userForm.value.avatar = userStore.getAvatar || ''-->
<!--}-->

<!--const beforeAvatarUpload = (file) => {-->
<!--  const isImage = file.type.startsWith('image/')-->
<!--  const isLt2M = file.size / 1024 / 1024 < 2-->
<!--  -->
<!--  if (!isImage) {-->
<!--    ElMessage.error('只能上传图片文件!')-->
<!--    return false-->
<!--  }-->
<!--  if (!isLt2M) {-->
<!--    ElMessage.error('图片大小不能超过 2MB!')-->
<!--    return false-->
<!--  }-->
<!--  return true-->
<!--}-->

<!--const handleAvatarSuccess = (response) => {-->
<!--  userForm.value.avatar = response.avatar_url-->
<!--  ElMessage.success('头像上传成功')-->
<!--  userStore.updateAvatar(response.avatar_url)-->
<!--}-->

<!--const updateNickname = async () => {-->
<!--  try {-->
<!--    await profileApi.updateNickname({ nickname: userForm.value.nickname })-->
<!--    ElMessage.success('昵称修改成功')-->
<!--    userStore.updateNickname(userForm.value.nickname)-->
<!--  } catch (error) {-->
<!--    ElMessage.error('昵称修改失败')-->
<!--  }-->
<!--}-->

<!--const updatePassword = async () => {-->
<!--  try {-->
<!--    await profileApi.updatePassword({-->
<!--      old_password: passwordForm.value.old_password,-->
<!--      new_password: passwordForm.value.new_password-->
<!--    })-->
<!--    ElMessage.success('密码修改成功')-->
<!--    passwordForm.value = {-->
<!--      old_password: '',-->
<!--      new_password: '',-->
<!--      confirm_password: ''-->
<!--    }-->
<!--  } catch (error) {-->
<!--    ElMessage.error('密码修改失败')-->
<!--  }-->
<!--}-->

<!--const requestEmailChange = async () => {-->
<!--  try {-->
<!--    await profileApi.updateEmail({-->
<!--      email: emailForm.value.new_email,-->
<!--      password: emailForm.value.password-->
<!--    })-->
<!--    emailChangeStep.value = 'verify'-->
<!--    ElMessage.success('验证码已发送到新邮箱')-->
<!--  } catch (error) {-->
<!--    ElMessage.error('发送验证码失败')-->
<!--  }-->
<!--}-->

<!--const verifyEmailChange = async () => {-->
<!--  try {-->
<!--    await profileApi.verifyEmailChange({-->
<!--      email: emailForm.value.new_email,-->
<!--      code: emailForm.value.verification_code-->
<!--    })-->
<!--    ElMessage.success('邮箱修改成功')-->
<!--    userForm.value.email = emailForm.value.new_email-->
<!--    emailChangeStep.value = 'request'-->
<!--    emailForm.value = {-->
<!--      password: '',-->
<!--      new_email: '',-->
<!--      verification_code: ''-->
<!--    }-->
<!--  } catch (error) {-->
<!--    ElMessage.error('邮箱验证失败')-->
<!--  }-->
<!--}-->

<!--onMounted(() => {-->
<!--  loadUserInfo()-->
<!--})-->
<!--</script>-->

<!--<style scoped>-->
<!--.profile-container {-->
<!--  padding: 20px;-->
<!--}-->

<!--.avatar-uploader {-->
<!--  text-align: center;-->
<!--}-->

<!--.avatar {-->
<!--  width: 100px;-->
<!--  height: 100px;-->
<!--  border-radius: 50%;-->
<!--  object-fit: cover;-->
<!--}-->

<!--.avatar-uploader-icon {-->
<!--  font-size: 28px;-->
<!--  color: #8c939d;-->
<!--  width: 100px;-->
<!--  height: 100px;-->
<!--  line-height: 100px;-->

<!--  text-align: center;-->
<!--  border: 1px dashed #d9d9d9;-->
<!--  border-radius: 50%;-->
<!--}-->
<!--</style>-->


<template>
  <div class="profile-wrapper">
    <el-card class="profile-card">
      <template #header>
        <h2>个人中心</h2>
      </template>

      <el-tabs v-model="activeTab" class="profile-tabs">
        <!-- 基本信息 -->
        <el-tab-pane label="基本信息" name="basic">
          <el-form :model="userForm" :rules="rules" label-width="100px" class="profile-form">
            <el-form-item label="头像">
              <!-- 自定义上传头像 -->
              <el-upload
                class="avatar-uploader"
                :show-file-list="false"
                :before-upload="beforeAvatarUpload"
                :http-request="customUploadAvatar"
              >
                <img v-if="userForm.avatar" :src="appendToken(userForm.avatar)" class="avatar" />
                <el-icon v-else class="avatar-uploader-icon"><Plus /></el-icon>
              </el-upload>
            </el-form-item>

            <el-form-item label="昵称" prop="nickname">
              <el-input v-model="userForm.nickname" placeholder="请输入昵称" clearable />
            </el-form-item>

            <el-form-item label="邮箱" prop="email">
              <el-input v-model="userForm.email" disabled />
            </el-form-item>

            <el-form-item>
              <el-button type="primary" @click="updateNickname">保存昵称</el-button>
            </el-form-item>
          </el-form>
        </el-tab-pane>

        <!-- 修改密码 -->
        <el-tab-pane label="修改密码" name="password">
          <el-form :model="passwordForm" :rules="passwordRules" label-width="100px" class="profile-form">
            <el-form-item label="旧密码" prop="old_password">
              <el-input v-model="passwordForm.old_password" type="password" show-password />
            </el-form-item>

            <el-form-item label="新密码" prop="new_password">
              <el-input v-model="passwordForm.new_password" type="password" show-password />
            </el-form-item>

            <el-form-item label="确认密码" prop="confirm_password">
              <el-input v-model="passwordForm.confirm_password" type="password" show-password />
            </el-form-item>

            <el-form-item>
              <el-button type="primary" @click="updatePassword">修改密码</el-button>
            </el-form-item>
          </el-form>
        </el-tab-pane>

        <!-- 修改邮箱 -->
        <el-tab-pane label="修改邮箱" name="email">
          <el-form :model="emailForm" :rules="emailRules" label-width="100px" class="profile-form">
            <el-form-item label="当前密码" prop="password">
              <el-input v-model="emailForm.password" type="password" show-password />
            </el-form-item>

            <el-form-item label="新邮箱" prop="new_email">
              <el-input v-model="emailForm.new_email" placeholder="请输入新邮箱" />
            </el-form-item>

            <el-form-item>
              <el-button type="primary" @click="requestEmailChange">发送验证码</el-button>
            </el-form-item>

            <el-form-item v-if="emailChangeStep === 'verify'">
              <el-input v-model="emailForm.verification_code" placeholder="请输入验证码" />
            </el-form-item>

            <el-form-item v-if="emailChangeStep === 'verify'">
              <el-button type="primary" @click="verifyEmailChange">验证邮箱</el-button>
            </el-form-item>
          </el-form>
        </el-tab-pane>
      </el-tabs>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { useUserStore } from '@/pinia/userStore'
import { profileApi } from '@/api/profile'
import { appendToken } from '@/utils/auth'
import request from '@/api/request'

// 状态管理
const userStore = useUserStore()
const activeTab = ref('basic')

// 表单数据
const userForm = ref({
  nickname: '',
  email: '',
  avatar: ''
})

const passwordForm = ref({
  old_password: '',
  new_password: '',
  confirm_password: ''
})

const emailForm = ref({
  password: '',
  new_email: '',
  verification_code: ''
})

const emailChangeStep = ref('request')

// 表单校验规则
const rules = {
  nickname: [{ required: true, message: '请输入昵称', trigger: 'blur' }]
}

const passwordRules = {
  old_password: [{ required: true, message: '请输入旧密码', trigger: 'blur' }],
  new_password: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 6, message: '密码长度不能少于6位', trigger: 'blur' }
  ],
  confirm_password: [
    { required: true, message: '请确认密码', trigger: 'blur' },
    {
      validator: (rule, value) => {
        if (value !== passwordForm.value.new_password) {
          return new Error('两次输入的密码不一致')
        }
        return true
      },
      trigger: 'blur'
    }
  ]
}

const emailRules = {
  password: [{ required: true, message: '请输入当前密码', trigger: 'blur' }],
  new_email: [
    { required: true, message: '请输入新邮箱', trigger: 'blur' },
    { type: 'email', message: '请输入正确的邮箱地址', trigger: 'blur' }
  ]
}

// 加载用户信息
const loadUserInfo = () => {
  userForm.value.nickname = userStore.getNickname || ''
  userForm.value.email = userStore.getEmail || ''
  
  // 确保头像URL是完整的绝对路径
  let avatar = userStore.getAvatar || ''
  if (avatar && avatar.startsWith('/')) {
    // 静态文件服务直接挂载在根路径下，不需要API路径
    const baseUrl = import.meta.env.VITE_API_BASE_URL.replace('/api/v1', '')
    avatar = baseUrl + avatar
  }
  userForm.value.avatar = avatar
}

// 头像上传前校验（和后端规则一致）
const beforeAvatarUpload = (file) => {
  const isImage = file.type.startsWith('image/')
  const isLt2M = file.size / 1024 / 1024 < 2

  if (!isImage) {
    ElMessage.error('只能上传图片文件!')
    return false
  }
  if (!isLt2M) {
    ElMessage.error('图片大小不能超过 2MB!')
    return false
  }
  return true
}

// 自定义头像上传（适配后端 file 参数名）
const customUploadAvatar = async (options) => {
  const formData = new FormData()
  // 关键：参数名和后端一致为 file
  formData.append('file', options.file, options.file.name)

  try {
    const res = await request({
      url: 'profile/avatar', // 确保接口路径正确
      method: 'POST',
      data: formData,
      headers: {
        'Content-Type': 'multipart/form-data',
        Authorization: 'Bearer ' + (localStorage.getItem('access_token') || '')
      }
    })

    // 确保头像URL是完整的绝对路径
  // 静态文件服务直接挂载在根路径下，不需要API路径
  const baseUrl = import.meta.env.VITE_API_BASE_URL.replace('/api/v1', '')
  const avatarUrl = res.avatar_url.startsWith('/') ? baseUrl + res.avatar_url : res.avatar_url

    // 更新头像显示和状态管理
    userForm.value.avatar = avatarUrl
    userStore.updateAvatar(avatarUrl)
    ElMessage.success('头像上传成功')
  } catch (error) {
    // 显示后端具体错误信息
    const errMsg = error.response?.data?.detail || '头像上传失败'
    ElMessage.error(errMsg)
    console.error('上传失败详情：', error)
  }
}

// 修改昵称
const updateNickname = async () => {
  try {
    await profileApi.updateNickname({ nickname: userForm.value.nickname })
    ElMessage.success('昵称修改成功')
    userStore.updateNickname(userForm.value.nickname)
  } catch (error) {
    ElMessage.error('昵称修改失败')
    console.error(error)
  }
}

// 修改密码
const updatePassword = async () => {
  try {
    await profileApi.updatePassword({
      old_password: passwordForm.value.old_password,
      new_password: passwordForm.value.new_password
    })
    ElMessage.success('密码修改成功')
    // 重置表单
    passwordForm.value = { old_password: '', new_password: '', confirm_password: '' }
  } catch (error) {
    ElMessage.error('密码修改失败')
    console.error(error)
  }
}

// 申请修改邮箱（发送验证码）
const requestEmailChange = async () => {
  try {
    await profileApi.updateEmail({
      email: emailForm.value.new_email,
      password: emailForm.value.password
    })
    emailChangeStep.value = 'verify'
    ElMessage.success('验证码已发送到新邮箱')
  } catch (error) {
    ElMessage.error('发送验证码失败')
    console.error(error)
  }
}

// 验证邮箱验证码
const verifyEmailChange = async () => {
  try {
    await profileApi.verifyEmailChange({
      email: emailForm.value.new_email,
      code: emailForm.value.verification_code
    })
    ElMessage.success('邮箱修改成功')
    // 更新显示并重置表单
    userForm.value.email = emailForm.value.new_email
    emailChangeStep.value = 'request'
    emailForm.value = { password: '', new_email: '', verification_code: '' }
  } catch (error) {
    ElMessage.error('邮箱验证失败')
    console.error(error)
  }
}

// 初始化加载用户信息
onMounted(() => {
  loadUserInfo()
})
</script>

<style scoped>
.profile-wrapper {
  padding: 28px;
  background: var(--bg-secondary);
  min-height: calc(100vh - 65px);
}

.profile-card {
  max-width: 700px;
  margin: 0 auto;
  border-radius: 16px;
  border: none;
  box-shadow: var(--shadow-md);
  overflow: hidden;
  background: var(--bg-primary);
}

:deep(.el-card__header) {
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
  padding: 20px 24px;
  border-bottom: 1px solid var(--border-light);
}

.profile-tabs {
  padding: 8px 24px;
}

.profile-form {
  max-width: 520px;
  margin: 20px auto 0;
  padding-bottom: 20px;
}

/* 头像上传样式 */
.avatar-uploader {
  text-align: center;
  margin: 12px 0;
}

.avatar {
  width: 110px;
  height: 110px;
  border-radius: 50%;
  object-fit: cover;
  border: 1px solid var(--border-light);
}

.avatar-uploader-icon {
  font-size: 28px;
  color: var(--text-light);
  width: 110px;
  height: 110px;
  line-height: 110px;
  text-align: center;
  border: 1px dashed var(--border-color);
  border-radius: 50%;
  cursor: pointer;
  transition: all 0.3s ease;
}

.avatar-uploader-icon:hover {
  border-color: var(--primary-color);
  color: var(--primary-color);
}

/* 表单样式优化 */
:deep(.el-form-item__label) {
  color: var(--text-primary);
  font-weight: 500;
}

:deep(.el-button--primary) {
  background-color: var(--primary-color);
  border-color: var(--primary-color);
}
</style>