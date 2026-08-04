export interface AdminUser {
  id: number
  username: string
  email: string | null
  phone: string | null
  nickname: string | null
  avatar_url: string | null
  role: 'USER' | 'ADMIN'
  status: 'ACTIVE' | 'DISABLED'
  created_at: string
}

export interface AfterSaleRule {
  id: number
  name: string
  category_id: number | null
  rule_type: string
  keywords: string[] | null
  content: string
  priority: number
  enabled: boolean
  created_at: string
  updated_at: string
}

export type AfterSaleRulePayload = Omit<AfterSaleRule, 'id' | 'created_at' | 'updated_at'>
