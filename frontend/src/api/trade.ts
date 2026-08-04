import type { PageData } from '../types/api'
import type { ProductSummary } from '../types/catalog'
import type {
  Address,
  AddressPayload,
  AdminOrderDetail,
  AdminOrderSummary,
  AdminReview,
  CartSummary,
  OrderDetail,
  OrderSummary,
  PaymentResult,
  Review,
  OrderStatus,
  Wallet,
  WalletTransaction,
} from '../types/trade'
import { http } from './http'

export async function getFavorites(page = 1, pageSize = 20) {
  return (
    await http.get('/favorites', { params: { page, page_size: pageSize } })
  ).data.data as PageData<ProductSummary>
}

export async function getFavoriteStatus(productId: number) {
  return (await http.get(`/favorites/${productId}/status`)).data.data as boolean
}

export async function addFavorite(productId: number) {
  return (await http.post(`/favorites/${productId}`)).data.data as ProductSummary
}

export async function removeFavorite(productId: number) {
  await http.delete(`/favorites/${productId}`)
}

export async function getAddresses() {
  return (await http.get('/addresses')).data.data as Address[]
}

export async function createAddress(payload: AddressPayload) {
  return (await http.post('/addresses', payload)).data.data as Address
}

export async function updateAddress(id: number, payload: Partial<AddressPayload>) {
  return (await http.patch(`/addresses/${id}`, payload)).data.data as Address
}

export async function deleteAddress(id: number) {
  await http.delete(`/addresses/${id}`)
}

export async function getCart() {
  return (await http.get('/cart')).data.data as CartSummary
}

export async function addCartItem(skuId: number, quantity: number) {
  return (await http.post('/cart/items', { sku_id: skuId, quantity })).data.data as CartSummary
}

export async function updateCartItem(
  itemId: number,
  payload: { quantity?: number; selected?: boolean },
) {
  return (await http.patch(`/cart/items/${itemId}`, payload)).data.data as CartSummary
}

export async function selectAllCartItems(selected: boolean) {
  return (await http.put('/cart/selection', { selected })).data.data as CartSummary
}

export async function deleteCartItem(itemId: number) {
  return (await http.delete(`/cart/items/${itemId}`)).data.data as CartSummary
}

export async function getWallet() {
  return (await http.get('/wallet')).data.data as Wallet
}

export async function rechargeWallet(amount: number) {
  return (await http.post('/wallet/recharge', { amount })).data.data as Wallet
}

export async function getWalletTransactions(page = 1, pageSize = 20) {
  return (
    await http.get('/wallet/transactions', { params: { page, page_size: pageSize } })
  ).data.data as PageData<WalletTransaction>
}

export async function createOrder(addressId: number, buyerRemark?: string) {
  return (
    await http.post('/orders', { address_id: addressId, buyer_remark: buyerRemark || null })
  ).data.data as OrderDetail
}

export async function getOrders(page = 1, pageSize = 20) {
  return (await http.get('/orders', { params: { page, page_size: pageSize } })).data
    .data as PageData<OrderSummary>
}

export async function getOrder(id: number) {
  return (await http.get(`/orders/${id}`)).data.data as OrderDetail
}

export async function payOrder(id: number) {
  return (await http.post(`/orders/${id}/pay`)).data.data as PaymentResult
}

export async function cancelOrder(id: number) {
  return (await http.post(`/orders/${id}/cancel`)).data.data as OrderDetail
}

export async function completeOrder(id: number) {
  return (await http.post(`/orders/${id}/complete`)).data.data as OrderDetail
}

export async function createReview(payload: {
  order_item_id: number
  rating: number
  content: string
  anonymous: boolean
  image_urls?: string[]
}) {
  return (await http.post('/reviews', payload)).data.data as Review
}

export async function getProductReviews(productId: number, page = 1, pageSize = 20) {
  return (
    await http.get(`/catalog/products/${productId}/reviews`, {
      params: { page, page_size: pageSize },
    })
  ).data.data as PageData<Review>
}

export async function getAdminOrders(
  page = 1,
  pageSize = 20,
  orderStatus?: OrderStatus,
) {
  return (
    await http.get('/admin/orders', {
      params: { page, page_size: pageSize, order_status: orderStatus },
    })
  ).data.data as PageData<AdminOrderSummary>
}

export async function getAdminOrder(id: number) {
  return (await http.get(`/admin/orders/${id}`)).data.data as AdminOrderDetail
}

export async function shipAdminOrder(id: number) {
  return (await http.post(`/admin/orders/${id}/ship`)).data.data as AdminOrderDetail
}

export async function completeAdminOrder(id: number) {
  return (await http.post(`/admin/orders/${id}/complete`)).data.data as AdminOrderDetail
}

export async function getAdminReviews(page = 1, pageSize = 20) {
  return (
    await http.get('/admin/reviews', { params: { page, page_size: pageSize } })
  ).data.data as PageData<AdminReview>
}

export async function updateReviewVisibility(id: number, visible: boolean) {
  return (await http.patch(`/admin/reviews/${id}`, { visible })).data.data as AdminReview
}
