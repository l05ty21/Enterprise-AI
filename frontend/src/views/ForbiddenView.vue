<script setup lang="ts">
import { useRouter } from 'vue-router'

const router = useRouter()
</script>

<template>
  <div class="status-page">
    <el-result icon="warning" title="403" sub-title="抱歉，当前账号没有访问该页面的权限">
      <template #extra>
        <el-button type="primary" @click="router.push('/dashboard')">返回工作台</el-button>
        <el-button @click="router.back()">返回上一页</el-button>
      </template>
    </el-result>
  </div>
</template>

<style scoped>
.status-page {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
}
</style>
