<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { Lock, User } from '@element-plus/icons-vue'

import { resolveErrorMessage } from '@/api/client'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()

const formRef = ref<FormInstance>()
const loading = ref(false)

const form = reactive({
  organization_code: '',
  username: '',
  password: '',
})

const rules: FormRules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
}

async function handleSubmit(): Promise<void> {
  if (!formRef.value) {
    return
  }
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) {
    return
  }

  loading.value = true
  try {
    await auth.login({
      username: form.username.trim(),
      password: form.password,
      organization_code: form.organization_code.trim() || undefined,
    })
    ElMessage.success('登录成功')
    const redirect = (route.query.redirect as string) || '/dashboard'
    await router.replace(redirect)
  } catch (error) {
    ElMessage.error(resolveErrorMessage(error, '登录失败，请检查账号密码'))
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="login-page">
    <section class="login-brand">
      <div class="brand-inner">
        <div class="brand-logo">智</div>
        <h1>智企协同</h1>
        <p class="brand-subtitle">Enterprise AI · 企业级 AI SaaS 平台</p>
        <ul class="brand-points">
          <li>统一身份与 RBAC 权限，多企业数据隔离</li>
          <li>云端 + 本地模型自由切换的 AI 网关</li>
          <li>知识库 RAG、工单、审批一体化协同</li>
        </ul>
        <p class="brand-footer">已上线：权限体系 · AI 模型网关 · 流式对话</p>
      </div>
    </section>

    <section class="login-panel">
      <div class="login-card">
        <h2>欢迎回来</h2>
        <p class="login-tip">请使用企业账号登录管理后台</p>

        <el-form
          ref="formRef"
          :model="form"
          :rules="rules"
          size="large"
          label-position="top"
          @submit.prevent="handleSubmit"
        >
          <el-form-item label="企业编码" prop="organization_code">
            <el-input v-model="form.organization_code" placeholder="例如 demo" clearable />
          </el-form-item>

          <el-form-item label="用户名" prop="username">
            <el-input v-model="form.username" placeholder="请输入用户名" :prefix-icon="User" clearable />
          </el-form-item>

          <el-form-item label="密码" prop="password">
            <el-input
              v-model="form.password"
              type="password"
              placeholder="请输入密码"
              :prefix-icon="Lock"
              show-password
              @keyup.enter="handleSubmit"
            />
          </el-form-item>

          <el-button
            type="primary"
            class="login-button"
            :loading="loading"
            native-type="submit"
            @click="handleSubmit"
          >
            登录
          </el-button>
        </el-form>

        <div class="switch-line">
          还没有账号？
          <router-link to="/register" class="switch-link">立即注册</router-link>
        </div>
      </div>
    </section>
  </div>
</template>

<style scoped>
.login-page {
  display: flex;
  min-height: 100vh;
}

.login-brand {
  flex: 1.1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 48px;
  color: #fff;
  background: linear-gradient(135deg, #1f2d3d 0%, #2b3a55 45%, #4a3f7a 100%);
}

.brand-inner {
  max-width: 420px;
}

.brand-logo {
  width: 52px;
  height: 52px;
  border-radius: 14px;
  background: linear-gradient(135deg, #409eff, #6f42c1);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  font-weight: 700;
  margin-bottom: 24px;
}

.brand-inner h1 {
  margin: 0 0 8px;
  font-size: 34px;
  letter-spacing: 2px;
}

.brand-subtitle {
  margin: 0 0 32px;
  color: #b1b3b8;
}

.brand-points {
  margin: 0;
  padding-left: 20px;
  line-height: 2;
  color: #dcdfe6;
}

.brand-footer {
  margin-top: 40px;
  font-size: 13px;
  color: #8d9095;
}

.login-panel {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px;
  background: #fff;
}

.login-card {
  width: 100%;
  max-width: 380px;
}

.login-card h2 {
  margin: 0 0 8px;
  font-size: 26px;
}

.login-tip {
  margin: 0 0 28px;
  color: #909399;
  font-size: 14px;
}

.login-button {
  width: 100%;
  margin-top: 8px;
}

.switch-line {
  margin-top: 20px;
  font-size: 14px;
  color: #909399;
  text-align: center;
}

.switch-link {
  color: #409eff;
  text-decoration: none;
}

.switch-link:hover {
  text-decoration: underline;
}

@media (max-width: 900px) {
  .login-brand {
    display: none;
  }
}
</style>
