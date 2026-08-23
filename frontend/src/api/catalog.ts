import { http } from './http'
import { demoBrands, demoCategories, getDemoProduct, getDemoProducts } from '../demo/catalog'
import { demoMode } from '../demo/config'
import type { ApiResponse, PageData } from '../types/api'
import type {
  Brand,
  CatalogSearchResult,
  Category,
  ProductDetail,
  ProductQuery,
  ProductSearchQuery,
  ProductSummary,
  SearchSuggestion,
} from '../types/catalog'

export async function getCategories(admin = false) {
  if (demoMode && !admin) return demoCategories
  const path = admin ? '/admin/catalog/categories' : '/catalog/categories'
  const response = await http.get<ApiResponse<Category[]>>(path)
  return response.data.data
}

export async function getBrands(admin = false) {
  if (demoMode && !admin) return demoBrands
  const path = admin ? '/admin/catalog/brands' : '/catalog/brands'
  const response = await http.get<ApiResponse<Brand[]>>(path)
  return response.data.data
}

export async function getProducts(query: ProductQuery = {}, admin = false) {
  if (demoMode && !admin) return getDemoProducts(query)
  const path = admin ? '/admin/catalog/products' : '/catalog/products'
  const response = await http.get<ApiResponse<PageData<ProductSummary>>>(path, { params: query })
  return response.data.data
}

export async function getSearchSuggestions(query: string, limit = 8) {
  if (demoMode) {
    const data = getDemoProducts({ keyword: query, page: 1, page_size: limit })
    return data.items.map<SearchSuggestion>((item) => ({
      kind: 'product',
      label: item.name,
      value: item.name,
      product_id: item.id,
    }))
  }
  const response = await http.get<ApiResponse<SearchSuggestion[]>>(
    '/catalog/search/suggestions',
    { params: { q: query, limit } },
  )
  return response.data.data
}

export async function searchCatalog(query: ProductSearchQuery = {}) {
  if (demoMode) {
    const data = getDemoProducts(query)
    return {
      ...data,
      facets: {
        categories: [],
        brands: [],
        min_price: null,
        max_price: null,
        in_stock_count: data.total,
      },
      search_mode: 'catalog',
    } satisfies CatalogSearchResult
  }
  const response = await http.get<ApiResponse<CatalogSearchResult>>('/catalog/search', {
    params: query,
  })
  return response.data.data
}

export async function recordSearchEvent(payload: {
  event_type: 'search' | 'click'
  query?: string
  product_id?: number
  result_count?: number
  filters?: Record<string, unknown>
}) {
  if (demoMode) return
  let sessionKey = sessionStorage.getItem('commerce_session')
  if (!sessionKey) {
    sessionKey = crypto.randomUUID()
    sessionStorage.setItem('commerce_session', sessionKey)
  }
  await http.post('/catalog/search-events', { ...payload, session_key: sessionKey })
}

export async function getProduct(productId: number, admin = false) {
  if (demoMode && !admin) {
    const product = getDemoProduct(productId)
    if (!product) throw new Error('没有找到这个展示商品')
    return product
  }
  const path = admin
    ? `/admin/catalog/products/${productId}`
    : `/catalog/products/${productId}`
  const response = await http.get<ApiResponse<ProductDetail>>(path)
  return response.data.data
}

export async function recordProductView(productId: number, source = 'DETAIL') {
  let sessionKey = sessionStorage.getItem('commerce_session')
  if (!sessionKey) {
    sessionKey = crypto.randomUUID()
    sessionStorage.setItem('commerce_session', sessionKey)
  }
  await http.post(`/catalog/products/${productId}/view`, {
    session_key: sessionKey,
    source,
  })
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
