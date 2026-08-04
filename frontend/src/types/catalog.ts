export type ProductStatus = 'DRAFT' | 'ON_SALE' | 'OFF_SALE'

export interface Category {
  id: number
  parent_id: number | null
  name: string
  slug: string
  icon_url: string | null
  sort_order: number
  enabled: boolean
  created_at: string
}

export interface Brand {
  id: number
  name: string
  slug: string
  logo_url: string | null
  description: string | null
  enabled: boolean
  created_at: string
}

export interface ProductSummary {
  id: number
  category_id: number
  brand_id: number | null
  name: string
  subtitle: string | null
  product_no: string
  main_image_url: string | null
  min_price: string
  max_price: string
  rating: string
  review_count: number
  sales_count: number
  status: ProductStatus
  created_at: string
}

export interface ProductSku {
  id: number
  product_id: number
  sku_no: string
  name: string
  attributes: Record<string, unknown> | null
  price: string
  market_price: string | null
  stock: number
  locked_stock: number
  available_stock: number
  enabled: boolean
  created_at: string
}

export interface ProductImage {
  id: number
  product_id: number
  image_url: string
  alt_text: string | null
  sort_order: number
}

export interface ProductDetail extends ProductSummary {
  detail_markdown: string | null
  parameters: Record<string, unknown> | null
  images: ProductImage[]
  skus: ProductSku[]
}

export interface ProductQuery {
  page?: number
  page_size?: number
  category_id?: number
  brand_id?: number
  keyword?: string
  min_price?: number
  max_price?: number
}

