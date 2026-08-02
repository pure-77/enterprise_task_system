<template>
  <div class="blank-layout">
    <router-view />
  </div>
</template>

<script setup>
// 空白布局 - 用于登录/注册页面
</script>

<style scoped>
.blank-layout {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}
</style>
