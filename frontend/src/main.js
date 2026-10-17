import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import '@/assets/css/global.css'
import { useUserStore } from './pinia/userStore'
import { useThemeStore } from './pinia/themeStore'

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)
app.use(router)
app.use(ElementPlus)

// 初始化主题（同步，先执行）
const themeStore = useThemeStore()
themeStore.initTheme()

// 等待认证初始化完成后再挂载，避免首屏白屏/加载中
const userStore = useUserStore()
userStore.initAuth().finally(() => {
  app.mount('#app')
})
