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

export interface Promotion {
  id: number
  name: string
  product_id: number | null
  promotion_type: 'PERCENT' | 'FIXED'
  value: string
  minimum_amount: string
  starts_at: string
  ends_at: string
  priority: number
  enabled: boolean
  created_at: string
  updated_at: string
}

export interface PromotionPayload {
  name: string
  product_id: number | null
  promotion_type: Promotion['promotion_type']
  value: number
  minimum_amount: number
  starts_at: string
  ends_at: string
  priority: number
  enabled: boolean
}
