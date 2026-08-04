import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

import * as authApi from '../api/auth'
import type { User } from '../types/api'

const storedUser = localStorage.getItem('current_user')

export const useAuthStore = defineStore('auth', () => {
  const user = ref<User | null>(storedUser ? JSON.parse(storedUser) : null)
  const loading = ref(false)
  const isAuthenticated = computed(() => Boolean(user.value && localStorage.getItem('access_token')))
  const isAdmin = computed(() => user.value?.role === 'ADMIN')

  async function login(account: string, password: string) {
    loading.value = true
    try {
      const result = await authApi.login(account, password)
      localStorage.setItem('access_token', result.access_token)
      localStorage.setItem('current_user', JSON.stringify(result.user))
      user.value = result.user
      return result.user
    } finally {
      loading.value = false
    }
  }

  async function register(payload: authApi.RegisterPayload) {
    loading.value = true
    try {
      await authApi.register(payload)
      const result = await authApi.login(payload.username, payload.password)
      localStorage.setItem('access_token', result.access_token)
      localStorage.setItem('current_user', JSON.stringify(result.user))
      user.value = result.user
      return result.user
    } finally {
      loading.value = false
    }
  }

  function logout() {
    localStorage.removeItem('access_token')
    localStorage.removeItem('current_user')
    user.value = null
  }

  return { user, loading, isAuthenticated, isAdmin, login, register, logout }
})
