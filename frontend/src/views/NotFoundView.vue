<script setup lang="ts">
import { useRouter } from 'vue-router'

const router = useRouter()
</script>

<template>
  <div class="status-page">
    <el-result icon="info" title="404" sub-title="页面不存在或已被移除">
      <template #extra>
        <el-button type="primary" @click="router.push('/dashboard')">返回工作台</el-button>
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
