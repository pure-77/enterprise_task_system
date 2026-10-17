import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from '@/pinia/userStore'
import routes from './routes'

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 认证已在 main.js 中初始化完成，路由守卫只做权限检查
router.beforeEach((to, from, next) => {
  const userStore = useUserStore()

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
