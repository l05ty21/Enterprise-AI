<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { Lock, OfficeBuilding, User } from '@element-plus/icons-vue'

import { resolveErrorMessage } from '@/api/client'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const auth = useAuthStore()

const formRef = ref<FormInstance>()
const loading = ref(false)

const form = reactive({
  organization_name: '',
  organization_code: '',
  username: '',
  real_name: '',
  email: '',
  password: '',
  confirm_password: '',
})

const rules: FormRules = {
  organization_name: [
    { required: true, message: '请输入企业名称', trigger: 'blur' },
    { min: 2, max: 100, message: '长度在 2 到 100 个字符', trigger: 'blur' },
  ],
  organization_code: [
    { required: true, message: '请输入企业编码', trigger: 'blur' },
    {
      pattern: /^[a-z][a-z0-9_-]{1,31}$/,
      message: '小写字母开头，只能含小写字母、数字、下划线、连字符',
      trigger: 'blur',
    },
  ],
  username: [
    { required: true, message: '请输入管理员用户名', trigger: 'blur' },
    {
      pattern: /^[A-Za-z0-9_]{2,64}$/,
      message: '2-64 位字母、数字或下划线',
      trigger: 'blur',
    },
  ],
  email: [{ type: 'email', message: '邮箱格式不正确', trigger: 'blur' }],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 8, message: '密码至少 8 位', trigger: 'blur' },
    {
      validator: (_rule, value: string, callback) => {
        if (!value) return callback()
        const hasLetter = /[A-Za-z]/.test(value)
        const hasDigit = /\d/.test(value)
        if (!hasLetter || !hasDigit) {
          return callback(new Error('密码必须同时包含字母和数字'))
        }
        callback()
      },
      trigger: 'blur',
    },
  ],
  confirm_password: [
    { required: true, message: '请再次输入密码', trigger: 'blur' },
    {
      validator: (_rule, value: string, callback) => {
        if (value !== form.password) {
          return callback(new Error('两次输入的密码不一致'))
        }
        callback()
      },
      trigger: 'blur',
    },
  ],
}

async function handleSubmit(): Promise<void> {
  if (!formRef.value) return
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  loading.value = true
  try {
    await auth.register({
      organization_name: form.organization_name.trim(),
      organization_code: form.organization_code.trim().toLowerCase(),
      username: form.username.trim(),
      password: form.password,
      real_name: form.real_name.trim() || null,
      email: form.email.trim() || null,
    })
    ElMessage.success('注册成功，已为你自动登录')
    await router.replace('/dashboard')
  } catch (error) {
    ElMessage.error(resolveErrorMessage(error, '注册失败，请稍后重试'))
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="register-page">
    <section class="register-brand">
      <div class="brand-inner">
        <div class="brand-logo">智</div>
        <h1>开通你的企业空间</h1>
        <p class="brand-subtitle">30 秒完成注册，立即使用 AI 助手</p>
        <ul class="brand-points">
          <li>独立企业数据空间，租户之间完全隔离</li>
          <li>内置四种角色，开箱即用的权限体系</li>
          <li>注册即获得企业管理员身份与全部功能</li>
        </ul>
      </div>
    </section>

    <section class="register-panel">
      <div class="register-card">
        <h2>企业注册</h2>
        <p class="register-tip">注册后你将成为该企业的管理员</p>

        <el-form
          ref="formRef"
          :model="form"
          :rules="rules"
          size="large"
          label-position="top"
          @submit.prevent="handleSubmit"
        >
          <el-form-item label="企业名称" prop="organization_name">
            <el-input
              v-model="form.organization_name"
              placeholder="例如 星河科技有限公司"
              :prefix-icon="OfficeBuilding"
              clearable
            />
          </el-form-item>

          <el-form-item label="企业编码" prop="organization_code">
            <el-input
              v-model="form.organization_code"
              placeholder="小写字母开头，例如 xinghe"
              clearable
            />
            <div class="field-hint">登录时需要填写这个编码，注册后不可修改</div>
          </el-form-item>

          <el-form-item label="管理员用户名" prop="username">
            <el-input
              v-model="form.username"
              placeholder="用于登录，例如 boss"
              :prefix-icon="User"
              clearable
            />
          </el-form-item>

          <el-form-item label="姓名（可选）">
            <el-input v-model="form.real_name" placeholder="显示在系统里" clearable />
          </el-form-item>

          <el-form-item label="邮箱（可选）" prop="email">
            <el-input v-model="form.email" placeholder="用于接收通知" clearable />
          </el-form-item>

          <el-form-item label="密码" prop="password">
            <el-input
              v-model="form.password"
              type="password"
              placeholder="至少 8 位，需含字母和数字"
              :prefix-icon="Lock"
              show-password
            />
          </el-form-item>

          <el-form-item label="确认密码" prop="confirm_password">
            <el-input
              v-model="form.confirm_password"
              type="password"
              placeholder="再输入一次"
              :prefix-icon="Lock"
              show-password
              @keyup.enter="handleSubmit"
            />
          </el-form-item>

          <el-button
            type="primary"
            class="register-button"
            :loading="loading"
            native-type="submit"
            @click="handleSubmit"
          >
            注册并进入
          </el-button>
        </el-form>

        <div class="switch-line">
          已经有账号了？
          <router-link to="/login" class="switch-link">去登录</router-link>
        </div>
      </div>
    </section>
  </div>
</template>

<style scoped>
.register-page {
  display: flex;
  min-height: 100vh;
}

.register-brand {
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
  font-size: 30px;
  letter-spacing: 1px;
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

.register-panel {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px;
  background: #fff;
  overflow-y: auto;
}

.register-card {
  width: 100%;
  max-width: 420px;
}

.register-card h2 {
  margin: 0 0 8px;
  font-size: 26px;
}

.register-tip {
  margin: 0 0 24px;
  color: #909399;
  font-size: 14px;
}

.field-hint {
  margin-top: 4px;
  font-size: 12px;
  line-height: 1.4;
  color: #a8abb2;
}

.register-button {
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
  .register-brand {
    display: none;
  }
}
</style>
