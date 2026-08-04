<script setup lang="ts">
import { ArrowLeft } from '@element-plus/icons-vue'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { computed, nextTick, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { useAuthStore } from '../stores/auth'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()
const mode = ref<'login' | 'register'>('login')
const loginFormRef = ref<FormInstance>()
const registerFormRef = ref<FormInstance>()
const loginForm = reactive({ account: '', password: '' })
const registerForm = reactive({
  username: '',
  nickname: '',
  email: '',
  phone: '',
  password: '',
  confirmPassword: '',
})

const loginRules: FormRules = {
  account: [{ required: true, message: '请输入用户名、邮箱或手机号', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
}

const registerRules: FormRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 50, message: '用户名需要 3–50 个字符', trigger: 'blur' },
    { pattern: /^[A-Za-z0-9_]+$/, message: '只能使用字母、数字和下划线', trigger: 'blur' },
  ],
  nickname: [{ max: 80, message: '昵称不能超过 80 个字符', trigger: 'blur' }],
  email: [{ type: 'email', message: '请输入正确的邮箱地址', trigger: 'blur' }],
  password: [
    { required: true, message: '请设置登录密码', trigger: 'blur' },
    { min: 8, max: 128, message: '密码至少需要 8 个字符', trigger: 'blur' },
  ],
  confirmPassword: [
    { required: true, message: '请再次输入密码', trigger: 'blur' },
    {
      validator: (_rule, value, callback) => {
        if (value !== registerForm.password) callback(new Error('两次输入的密码不一致'))
        else callback()
      },
      trigger: ['blur', 'change'],
    },
  ],
}

const visualTitle = computed(() => mode.value === 'login'
  ? '登录后，\n继续轻松选购'
  : '创建账号，\n开始安心选购')
const visualDescription = computed(() => mode.value === 'login'
  ? '查看订单、管理地址，也可以让购物助手帮你挑选。'
  : '注册后即可收藏商品、管理购物车，并使用 AI 智能导购。')

function switchMode(nextMode: 'login' | 'register') {
  mode.value = nextMode
  nextTick(() => {
    loginFormRef.value?.clearValidate()
    registerFormRef.value?.clearValidate()
  })
}

async function finishLogin(user: { role: 'ADMIN' | 'USER' }) {
  const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : null
  await router.push(redirect || (user.role === 'ADMIN' ? '/admin' : '/'))
}

async function submitLogin() {
  const valid = await loginFormRef.value?.validate().catch(() => false)
  if (!valid) return
  try {
    const user = await auth.login(loginForm.account, loginForm.password)
    ElMessage.success('登录成功')
    await finishLogin(user)
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '账号或密码不正确，请重新输入')
  }
}

async function submitRegister() {
  const valid = await registerFormRef.value?.validate().catch(() => false)
  if (!valid) return
  try {
    const user = await auth.register({
      username: registerForm.username.trim(),
      password: registerForm.password,
      nickname: registerForm.nickname.trim() || null,
      email: registerForm.email.trim() || null,
      phone: registerForm.phone.trim() || null,
    })
    ElMessage.success('注册成功，已为你自动登录')
    await finishLogin(user)
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '注册失败，请稍后重试')
  }
}
</script>

<template>
  <main class="login-page">
    <section class="login-visual">
      <RouterLink to="/" class="back-link focus-ring">
        <el-icon><ArrowLeft /></el-icon><span>返回商城</span>
      </RouterLink>
      <div class="visual-copy">
        <span>AI 智能商城</span>
        <h1>{{ visualTitle }}</h1>
        <p>{{ visualDescription }}</p>
      </div>
    </section>

    <section class="login-form-panel">
      <div class="login-form-wrap">
        <div class="login-heading">
          <span class="brand-mark">A</span>
          <div>
            <h2>{{ mode === 'login' ? '欢迎回来' : '创建商城账号' }}</h2>
            <p>{{ mode === 'login' ? '登录你的商城账号' : '填写基础信息即可开始购物' }}</p>
          </div>
        </div>

        <div class="auth-switch" role="tablist" aria-label="登录或注册">
          <button type="button" role="tab" :aria-selected="mode === 'login'" :class="{ active: mode === 'login' }" @click="switchMode('login')">登录</button>
          <button type="button" role="tab" :aria-selected="mode === 'register'" :class="{ active: mode === 'register' }" @click="switchMode('register')">注册</button>
        </div>

        <el-form
          v-if="mode === 'login'"
          ref="loginFormRef"
          :model="loginForm"
          :rules="loginRules"
          label-position="top"
          @submit.prevent="submitLogin"
        >
          <el-form-item label="账号" prop="account">
            <el-input v-model="loginForm.account" size="large" autocomplete="username" placeholder="用户名、邮箱或手机号" />
          </el-form-item>
          <el-form-item label="密码" prop="password">
            <el-input v-model="loginForm.password" size="large" type="password" show-password autocomplete="current-password" placeholder="请输入密码" @keyup.enter="submitLogin" />
          </el-form-item>
          <el-button type="primary" size="large" :loading="auth.loading" class="submit-button" @click="submitLogin">登录</el-button>
        </el-form>

        <el-form
          v-else
          ref="registerFormRef"
          :model="registerForm"
          :rules="registerRules"
          label-position="top"
          @submit.prevent="submitRegister"
        >
          <div class="register-grid">
            <el-form-item label="用户名" prop="username">
              <el-input v-model="registerForm.username" size="large" autocomplete="username" placeholder="字母、数字或下划线" />
            </el-form-item>
            <el-form-item label="昵称（选填）" prop="nickname">
              <el-input v-model="registerForm.nickname" size="large" autocomplete="nickname" placeholder="怎么称呼你" />
            </el-form-item>
          </div>
          <div class="register-grid">
            <el-form-item label="邮箱（选填）" prop="email">
              <el-input v-model="registerForm.email" size="large" autocomplete="email" placeholder="用于账号联系" />
            </el-form-item>
            <el-form-item label="手机号（选填）" prop="phone">
              <el-input v-model="registerForm.phone" size="large" autocomplete="tel" placeholder="请输入手机号" />
            </el-form-item>
          </div>
          <el-form-item label="设置密码" prop="password">
            <el-input v-model="registerForm.password" size="large" type="password" show-password autocomplete="new-password" placeholder="至少 8 个字符" />
          </el-form-item>
          <el-form-item label="确认密码" prop="confirmPassword">
            <el-input v-model="registerForm.confirmPassword" size="large" type="password" show-password autocomplete="new-password" placeholder="再次输入密码" @keyup.enter="submitRegister" />
          </el-form-item>
          <el-button type="primary" size="large" :loading="auth.loading" class="submit-button" @click="submitRegister">注册并登录</el-button>
        </el-form>

        <p class="form-note">{{ mode === 'login' ? '还没有账号？切换到“注册”即可自行创建。' : '注册后将自动登录，你可以随时在个人中心完善资料。' }}</p>
      </div>
    </section>
  </main>
</template>

<style scoped>
.login-page { display: grid; min-height: 100dvh; grid-template-columns: minmax(380px, 1.05fr) minmax(500px, .95fr); background: var(--color-surface); }
.login-visual { position: relative; display: flex; isolation: isolate; overflow: hidden; flex-direction: column; justify-content: space-between; padding: 38px clamp(32px, 6vw, 86px) 68px; background: linear-gradient(180deg, rgb(8 22 46 / 24%), rgb(8 22 46 / 86%)), url('/uploads/demo-products/noise-cancelling-headphones.png') center / cover; color: #f5f8ff; }
.back-link { display: inline-flex; width: fit-content; align-items: center; gap: 8px; color: #e7efff; font-size: 14px; font-weight: 620; }
.visual-copy > span { font-size: 13px; font-weight: 700; letter-spacing: .06em; }
h1 { max-width: 10ch; margin: 16px 0 20px; font-size: clamp(3rem, 5.6vw, 5.8rem); font-weight: 760; letter-spacing: -.065em; line-height: 1.02; white-space: pre-line; }
.visual-copy p { max-width: 32ch; margin: 0; color: #d5e1f5; font-size: 16px; line-height: 1.8; }
.login-form-panel { display: grid; place-items: center; padding: 42px 48px; background: var(--color-surface); }
.login-form-wrap { width: min(100%, 460px); }
.login-heading { display: flex; align-items: center; gap: 14px; margin-bottom: 24px; }
.brand-mark { display: grid; width: 44px; height: 44px; place-items: center; border-radius: 12px; background: var(--color-brand-600); color: #f8fbff; font-size: 20px; font-weight: 760; box-shadow: 0 10px 24px rgb(23 100 215 / 22%); }
h2, .login-heading p, .form-note { margin: 0; } h2 { font-size: 26px; letter-spacing: -.035em; }.login-heading p, .form-note { margin-top: 6px; color: var(--color-ink-500); font-size: 13px; }
.auth-switch { display: grid; width: 100%; grid-template-columns: 1fr 1fr; gap: 4px; margin-bottom: 24px; padding: 4px; border-radius: 10px; background: var(--color-ground); }
.auth-switch button { min-height: 38px; border: 0; border-radius: 7px; background: transparent; color: var(--color-ink-500); cursor: pointer; font-weight: 700; }.auth-switch button.active { background: white; color: var(--color-brand-700); box-shadow: 0 2px 8px rgb(20 42 80 / 8%); }
.register-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }.submit-button { width: 100%; margin-top: 8px; }.form-note { margin-top: 20px; line-height: 1.7; }
@media (max-width: 820px) { .login-page { display: block; }.login-visual { min-height: 260px; padding: 28px 24px 36px; }.visual-copy { margin-top: 46px; }h1 { margin: 10px 0; font-size: 2.8rem; }.visual-copy p { font-size: 14px; }.login-form-panel { padding: 36px 24px 64px; }.register-grid { grid-template-columns: 1fr; gap: 0; } }
</style>
