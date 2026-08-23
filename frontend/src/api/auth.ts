import { http } from './http'
import type { ApiResponse, LoginResult, User } from '../types/api'

export async function login(account: string, password: string) {
  const response = await http.post<ApiResponse<LoginResult>>('/auth/login', { account, password })
  return response.data.data
}

export interface RegisterPayload {
  username: string
  password: string
  email?: string | null
  phone?: string | null
  nickname?: string | null
}

export async function register(payload: RegisterPayload) {
  const response = await http.post<ApiResponse<User>>('/auth/register', payload)
  return response.data.data
}

export async function getCurrentUser() {
  const response = await http.get<ApiResponse<User>>('/auth/me')
  return response.data.data
}

export async function updateProfile(payload: {
  nickname?: string | null
  email?: string | null
  phone?: string | null
  avatar_url?: string | null
}) {
  const response = await http.patch<ApiResponse<User>>('/auth/me', payload)
  return response.data.data
}

export async function changePassword(currentPassword: string, newPassword: string) {
  await http.post('/auth/change-password', {
    current_password: currentPassword,
    new_password: newPassword,
  })
}
