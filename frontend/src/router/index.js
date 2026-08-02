import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from '@/pinia/userStore'
import routes from './routes'

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach(async (to, from, next) => {
  const userStore = useUserStore()

  // 每次路由跳转时，如果存在 token，主动校验其有效性
  // 这样可以在 access_token 过期但 refresh_token 仍有效时，提前刷新，避免
  // 页面组件发起 API 请求后才触发 401 拦截器去刷新，减少一次失败的请求
  if (userStore.token) {
    await userStore.initAuth()
  }

  const requiresAuth = to.meta.requiresAuth
  const isAuthenticated = userStore.isLoggedIn

  if (requiresAuth && !isAuthenticated) {
    next('/auth/login')
  } else if ((to.path === '/auth/login' || to.path === '/auth/register') && isAuthenticated) {
    next('/')
  } else {
    next()
  }
})

export default router
