<template>
  <router-view />
</template>

<script setup>
import { onMounted } from 'vue'
import { useUserStore } from './pinia/userStore'

const userStore = useUserStore()

onMounted(async () => {
  if (userStore.token && !userStore.userInfo) {
    await userStore.loadUserInfo()
  }
})
</script>

<style>
#app { min-height: 100vh; }
</style>
