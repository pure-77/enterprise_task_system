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

// 初始化认证状态
const userStore = useUserStore()
userStore.initAuth()

// 初始化主题
const themeStore = useThemeStore()
themeStore.initTheme()

app.mount('#app')
