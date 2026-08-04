export interface Address {
  id: number
  receiver_name: string
  receiver_phone: string
  province: string
  city: string
  district: string
  detail: string
  postal_code: string | null
  is_default: boolean
  created_at: string
}

export type AddressPayload = Omit<Address, 'id' | 'created_at'>

export interface CartItem {
  id: number
  product_id: number
  sku_id: number
  product_name: string
  sku_name: string
  sku_attributes: Record<string, unknown> | null
  image_url: string | null
  unit_price: string
  quantity: number
  selected: boolean
  available_stock: number
  available: boolean
  subtotal: string
}

export interface CartSummary {
  items: CartItem[]
  total_count: number
  selected_count: number
  selected_amount: string
}

export interface Wallet {
  balance: string
}

export interface WalletTransaction {
  id: number
  transaction_no: string
  transaction_type: 'RECHARGE' | 'PAYMENT' | 'REFUND' | 'ADJUSTMENT'
  amount: string
  balance_before: string
  balance_after: string
  reference_type: string | null
  reference_id: string | null
  remark: string | null
  created_at: string
}

export type OrderStatus =
  | 'PENDING_PAYMENT'
  | 'PAID'
  | 'SHIPPED'
  | 'COMPLETED'
  | 'CANCELLED'
  | 'REFUNDED'

export interface OrderSummary {
  id: number
  order_no: string
  status: OrderStatus
  product_amount: string
  discount_amount: string
  shipping_amount: string
  payable_amount: string
  paid_amount: string
  created_at: string
  paid_at: string | null
}

export interface OrderItem {
  id: number
  product_id: number
  sku_id: number
  product_name: string
  sku_name: string
  sku_attributes: Record<string, unknown> | null
  image_url: string | null
  unit_price: string
  quantity: number
  total_amount: string
  reviewed: boolean
}

export interface OrderDetail extends OrderSummary {
  address_snapshot: Record<string, string | null>
  buyer_remark: string | null
  shipped_at: string | null
  completed_at: string | null
  cancelled_at: string | null
  items: OrderItem[]
}

export interface PaymentResult {
  payment_no: string
  status: 'PENDING' | 'SUCCESS' | 'FAILED' | 'REFUNDED'
  paid_amount: string
  wallet_balance: string
  order: OrderDetail
}

export interface AdminOrderSummary extends OrderSummary {
  user_id: number
}

export interface AdminOrderDetail extends OrderDetail {
  user_id: number
}

export interface Review {
  id: number
  product_id: number
  rating: number
  content: string
  image_urls: string[] | null
  anonymous: boolean
  display_name: string
  created_at: string
}

export interface AdminReview extends Review {
  order_item_id: number
  username: string
  product_name: string
  visible: boolean
}
