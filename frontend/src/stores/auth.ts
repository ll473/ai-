import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

import * as authApi from '../api/auth'
import type { User } from '../types/api'

function readStoredUser(): User | null {
  const stored = localStorage.getItem('current_user')
  if (!stored) return null
  try {
    return JSON.parse(stored) as User
  } catch {
    localStorage.removeItem('current_user')
    localStorage.removeItem('access_token')
    return null
  }
}

export const useAuthStore = defineStore('auth', () => {
  const user = ref<User | null>(readStoredUser())
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

  async function updateProfile(payload: Parameters<typeof authApi.updateProfile>[0]) {
    const updated = await authApi.updateProfile(payload)
    user.value = updated
    localStorage.setItem('current_user', JSON.stringify(updated))
    return updated
  }

  return { user, loading, isAuthenticated, isAdmin, login, register, logout, updateProfile }
})
