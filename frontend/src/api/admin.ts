import type { PageData } from '../types/api'
import type { AdminUser, AfterSaleRule, AfterSaleRulePayload } from '../types/admin'
import { http } from './http'

export async function getAdminUsers(params: {
  page?: number
  page_size?: number
  keyword?: string
  user_status?: string
} = {}) {
  return (await http.get('/admin/users', { params })).data.data as PageData<AdminUser>
}

export async function updateAdminUserStatus(id: number, status: AdminUser['status']) {
  return (await http.patch(`/admin/users/${id}/status`, { status })).data.data as AdminUser
}

export async function getAfterSaleRules(params: {
  page?: number
  page_size?: number
  keyword?: string
  rule_type?: string
} = {}) {
  return (await http.get('/admin/after-sale-rules', { params })).data.data as PageData<AfterSaleRule>
}

export async function createAfterSaleRule(payload: AfterSaleRulePayload) {
  return (await http.post('/admin/after-sale-rules', payload)).data.data as AfterSaleRule
}

export async function updateAfterSaleRule(id: number, payload: Partial<AfterSaleRulePayload>) {
  return (await http.patch(`/admin/after-sale-rules/${id}`, payload)).data.data as AfterSaleRule
}

export async function deleteAfterSaleRule(id: number) {
  await http.delete(`/admin/after-sale-rules/${id}`)
}
