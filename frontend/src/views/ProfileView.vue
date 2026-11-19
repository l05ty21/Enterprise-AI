<script setup lang="ts">
import { reactive, ref } from 'vue'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'

import { resolveErrorMessage } from '@/api/client'
import { authApi } from '@/api/auth'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()

const profileRef = ref<FormInstance>()
const passwordRef = ref<FormInstance>()
const savingProfile = ref(false)
const savingPassword = ref(false)

const profileForm = reactive({
  real_name: auth.user?.real_name ?? '',
  email: auth.user?.email ?? '',
  phone: auth.user?.phone ?? '',
})

const passwordForm = reactive({
  old_password: '',
  new_password: '',
  confirm_password: '',
})

const profileRules: FormRules = {
  email: [{ type: 'email', message: '邮箱格式不正确', trigger: 'blur' }],
}

const passwordRules: FormRules = {
  old_password: [{ required: true, message: '请输入原密码', trigger: 'blur' }],
  new_password: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    {
      validator: (_rule, value: string, callback) => {
        if (!value || value.length < 8 || !/[A-Za-z]/.test(value) || !/\d/.test(value)) {
          callback(new Error('至少 8 位，且同时包含字母和数字'))
          return
        }
        callback()
      },
      trigger: 'blur',
    },
  ],
  confirm_password: [
    { required: true, message: '请再次输入新密码', trigger: 'blur' },
    {
      validator: (_rule, value: string, callback) => {
        if (value !== passwordForm.new_password) {
          callback(new Error('两次输入的密码不一致'))
          return
        }
        callback()
      },
      trigger: 'blur',
    },
  ],
}

async function saveProfile(): Promise<void> {
  if (!profileRef.value) {
    return
  }
  const valid = await profileRef.value.validate().catch(() => false)
  if (!valid) {
    return
  }
  savingProfile.value = true
  try {
    const { data } = await authApi.updateProfile({
      real_name: profileForm.real_name || null,
      email: profileForm.email || null,
      phone: profileForm.phone || null,
    })
    auth.user = data
    ElMessage.success('资料已更新')
  } catch (error) {
    ElMessage.error(resolveErrorMessage(error, '更新失败'))
  } finally {
    savingProfile.value = false
  }
}

async function changePassword(): Promise<void> {
  if (!passwordRef.value) {
    return
  }
  const valid = await passwordRef.value.validate().catch(() => false)
  if (!valid) {
    return
  }
  savingPassword.value = true
  try {
    await authApi.changePassword({
      old_password: passwordForm.old_password,
      new_password: passwordForm.new_password,
    })
    ElMessage.success('密码已修改，请使用新密码重新登录')
    passwordForm.old_password = ''
    passwordForm.new_password = ''
    passwordForm.confirm_password = ''
    await auth.logout()
    window.location.assign('/login')
  } catch (error) {
    ElMessage.error(resolveErrorMessage(error, '修改密码失败'))
  } finally {
    savingPassword.value = false
  }
}
</script>

<template>
  <div class="page-container">
    <el-row :gutter="16">
      <el-col :xs="24" :md="10">
        <el-card shadow="never" header="账号信息">
          <el-descriptions :column="1" border>
            <el-descriptions-item label="用户名">
              {{ auth.user?.username }}
            </el-descriptions-item>
            <el-descriptions-item label="姓名">
              {{ auth.user?.real_name || '—' }}
            </el-descriptions-item>
            <el-descriptions-item label="企业">
              {{ auth.user?.organization_name || '—' }}
            </el-descriptions-item>
            <el-descriptions-item label="部门">
              {{ auth.user?.department_name || '未分配' }}
            </el-descriptions-item>
            <el-descriptions-item label="角色">
              <el-tag
                v-for="role in auth.roles"
                :key="role.id"
                size="small"
                effect="plain"
                style="margin-right: 6px"
              >
                {{ role.name }}
              </el-tag>
              <span v-if="!auth.roles.length">—</span>
            </el-descriptions-item>
            <el-descriptions-item label="权限点">
              {{ auth.user?.permissions.length ?? 0 }} 项
            </el-descriptions-item>
          </el-descriptions>
        </el-card>
      </el-col>

      <el-col :xs="24" :md="14">
        <el-card shadow="never" header="基本资料">
          <el-form ref="profileRef" :model="profileForm" :rules="profileRules" label-width="80px">
            <el-form-item label="姓名">
              <el-input v-model="profileForm.real_name" placeholder="真实姓名" />
            </el-form-item>
            <el-form-item label="邮箱" prop="email">
              <el-input v-model="profileForm.email" placeholder="name@example.com" />
            </el-form-item>
            <el-form-item label="手机号">
              <el-input v-model="profileForm.phone" placeholder="可选" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :loading="savingProfile" @click="saveProfile">
                保存资料
              </el-button>
            </el-form-item>
          </el-form>
        </el-card>

        <el-card shadow="never" header="修改密码" style="margin-top: 16px">
          <el-form
            ref="passwordRef"
            :model="passwordForm"
            :rules="passwordRules"
            label-width="80px"
          >
            <el-form-item label="原密码" prop="old_password">
              <el-input v-model="passwordForm.old_password" type="password" show-password />
            </el-form-item>
            <el-form-item label="新密码" prop="new_password">
              <el-input v-model="passwordForm.new_password" type="password" show-password />
            </el-form-item>
            <el-form-item label="确认密码" prop="confirm_password">
              <el-input v-model="passwordForm.confirm_password" type="password" show-password />
            </el-form-item>
            <el-form-item>
              <el-button type="danger" :loading="savingPassword" @click="changePassword">
                修改密码
              </el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>
