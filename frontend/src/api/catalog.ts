import { http } from './http'
import type { ApiResponse, PageData } from '../types/api'
import type {
  Brand,
  Category,
  ProductDetail,
  ProductQuery,
  ProductSummary,
} from '../types/catalog'

export async function getCategories(admin = false) {
  const path = admin ? '/admin/catalog/categories' : '/catalog/categories'
  const response = await http.get<ApiResponse<Category[]>>(path)
  return response.data.data
}

export async function getBrands(admin = false) {
  const path = admin ? '/admin/catalog/brands' : '/catalog/brands'
  const response = await http.get<ApiResponse<Brand[]>>(path)
  return response.data.data
}

export async function getProducts(query: ProductQuery = {}, admin = false) {
  const path = admin ? '/admin/catalog/products' : '/catalog/products'
  const response = await http.get<ApiResponse<PageData<ProductSummary>>>(path, { params: query })
  return response.data.data
}

export async function getProduct(productId: number, admin = false) {
  const path = admin
    ? `/admin/catalog/products/${productId}`
    : `/catalog/products/${productId}`
  const response = await http.get<ApiResponse<ProductDetail>>(path)
  return response.data.data
}

export async function createCategory(payload: Omit<Category, 'id' | 'created_at'>) {
  const response = await http.post<ApiResponse<Category>>('/admin/catalog/categories', payload)
  return response.data.data
}

export async function updateCategory(categoryId: number, payload: Partial<Category>) {
  const response = await http.put<ApiResponse<Category>>(
    `/admin/catalog/categories/${categoryId}`,
    payload,
  )
  return response.data.data
}

export async function createBrand(payload: Omit<Brand, 'id' | 'created_at'>) {
  const response = await http.post<ApiResponse<Brand>>('/admin/catalog/brands', payload)
  return response.data.data
}

export async function updateBrand(brandId: number, payload: Partial<Brand>) {
  const response = await http.put<ApiResponse<Brand>>(`/admin/catalog/brands/${brandId}`, payload)
  return response.data.data
}

export interface ProductPayload {
  category_id: number
  brand_id: number | null
  name: string
  subtitle: string | null
  product_no: string
  main_image_url: string | null
  detail_markdown: string | null
  parameters: Record<string, unknown> | null
  status: ProductStatus
}

import type { ProductStatus } from '../types/catalog'

export async function createProduct(payload: ProductPayload) {
  const response = await http.post<ApiResponse<ProductSummary>>('/admin/catalog/products', payload)
  return response.data.data
}

export async function updateProduct(productId: number, payload: Partial<ProductPayload>) {
  const response = await http.put<ApiResponse<ProductSummary>>(
    `/admin/catalog/products/${productId}`,
    payload,
  )
  return response.data.data
}

export async function updateProductSku(skuId: number, payload: {
  sku_no?: string
  name?: string
  attributes?: Record<string, unknown> | null
  price?: number
  market_price?: number | null
  stock?: number
  enabled?: boolean
}) {
  const response = await http.put<ApiResponse<import('../types/catalog').ProductSku>>(
    `/admin/catalog/skus/${skuId}`,
    payload,
  )
  return response.data.data
}
