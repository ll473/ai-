<script setup lang="ts">
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'

import { changePassword } from '../../api/auth'
import { useAuthStore } from '../../stores/auth'

const auth = useAuthStore()
const router = useRouter()
const profileSaving = ref(false)
const passwordSaving = ref(false)
const passwordFormRef = ref<FormInstance>()

const profile = reactive({
  nickname: auth.user?.nickname || '',
  email: auth.user?.email || '',
  phone: auth.user?.phone || '',
  avatar_url: auth.user?.avatar_url || '',
})
const password = reactive({ current: '', next: '', confirm: '' })
const passwordRules: FormRules = {
  current: [{ required: true, message: '请输入当前密码', trigger: 'blur' }],
  next: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 8, message: '密码至少 8 位', trigger: 'blur' },
    { pattern: /^(?=.*[A-Za-z])(?=.*\d).+$/, message: '必须同时包含字母和数字', trigger: 'blur' },
  ],
  confirm: [{
    validator: (_rule, value, callback) => value === password.next
      ? callback()
      : callback(new Error('两次输入的密码不一致')),
    trigger: 'blur',
  }],
}

async function saveProfile() {
  profileSaving.value = true
  try {
    await auth.updateProfile({
      nickname: profile.nickname || null,
      email: profile.email || null,
      phone: profile.phone || null,
      avatar_url: profile.avatar_url || null,
    })
    ElMessage.success('个人资料已保存')
  } finally {
    profileSaving.value = false
  }
}

async function savePassword() {
  if (!await passwordFormRef.value?.validate().catch(() => false)) return
  passwordSaving.value = true
  try {
    await changePassword(password.current, password.next)
    ElMessage.success('密码已修改，请重新登录')
    auth.logout()
    router.replace({ name: 'login' })
  } finally {
    passwordSaving.value = false
  }
}
</script>

<template>
  <div class="page-shell account-page">
    <header><span>账号设置</span><h1>个人资料与安全</h1><p>维护联系方式，并定期更新登录密码。</p></header>
    <div class="settings-grid">
      <section>
        <div class="section-heading"><h2>个人资料</h2><p>用户名 {{ auth.user?.username }} 不可修改。</p></div>
        <el-form label-position="top" @submit.prevent="saveProfile">
          <el-form-item label="昵称"><el-input v-model="profile.nickname" maxlength="80" /></el-form-item>
          <el-form-item label="邮箱"><el-input v-model="profile.email" maxlength="255" /></el-form-item>
          <el-form-item label="手机号"><el-input v-model="profile.phone" maxlength="30" /></el-form-item>
          <el-form-item label="头像地址"><el-input v-model="profile.avatar_url" maxlength="500" /></el-form-item>
          <el-button type="primary" :loading="profileSaving" native-type="submit">保存资料</el-button>
        </el-form>
      </section>
      <section>
        <div class="section-heading"><h2>修改密码</h2><p>新密码至少 8 位，并同时包含字母和数字。</p></div>
        <el-form ref="passwordFormRef" :model="password" :rules="passwordRules" label-position="top" @submit.prevent="savePassword">
          <el-form-item label="当前密码" prop="current"><el-input v-model="password.current" type="password" show-password /></el-form-item>
          <el-form-item label="新密码" prop="next"><el-input v-model="password.next" type="password" show-password /></el-form-item>
          <el-form-item label="确认新密码" prop="confirm"><el-input v-model="password.confirm" type="password" show-password /></el-form-item>
          <el-button type="primary" :loading="passwordSaving" native-type="submit">修改密码</el-button>
        </el-form>
      </section>
    </div>
  </div>
</template>

<style scoped>
.account-page { min-height: 70vh; padding-top: 48px; }
header span { color: var(--color-brand-600); font-size: 12px; font-weight: 700; }
header h1 { margin: 6px 0 4px; font-size: clamp(2rem, 4vw, 3.4rem); letter-spacing: -.05em; }
header p, .section-heading p { margin: 0; color: var(--color-ink-500); }
.settings-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 20px; margin-top: 34px; }
section { padding: 28px; border: 1px solid var(--color-line); border-radius: var(--radius-container); background: var(--color-surface); }
.section-heading { margin-bottom: 24px; }
.section-heading h2 { margin: 0 0 5px; font-size: 20px; }
.section-heading p { font-size: 12px; }
.el-button { width: 100%; }
@media (max-width: 767px) { .settings-grid { grid-template-columns: 1fr; } }
</style>
