import { defineStore } from 'pinia'

export const useThemeStore = defineStore('theme', {
  state: () => ({
    isDark: localStorage.getItem('theme') === 'dark'
  }),
  
  getters: {
    currentTheme: (state) => state.isDark ? 'dark' : 'light'
  },
  
  actions: {
    toggleTheme() {
      this.isDark = !this.isDark
      this.saveTheme()
      this.applyTheme()
    },
    
    setTheme(isDark) {
      this.isDark = isDark
      this.saveTheme()
      this.applyTheme()
    },
    
    saveTheme() {
      localStorage.setItem('theme', this.isDark ? 'dark' : 'light')
    },
    
    applyTheme() {
      if (this.isDark) {
        document.documentElement.classList.add('dark-theme')
      } else {
        document.documentElement.classList.remove('dark-theme')
      }
    },
    
    initTheme() {
      this.applyTheme()
    }
  }
})
