<script setup lang="ts">
import { Box, ChatDotSquare, Picture, Wallet } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { cancelOrder, completeOrder, createReview, getOrder, getOrders, payOrder } from '../../api/trade'
import StatePanel from '../../components/StatePanel.vue'
import type { OrderDetail, OrderItem, OrderStatus, OrderSummary } from '../../types/trade'

const route = useRoute()
const router = useRouter()
const orders = ref<OrderSummary[]>([])
const loading = ref(true)
const detailLoading = ref(false)
const acting = ref(false)
const drawerOpen = ref(false)
const detail = ref<OrderDetail | null>(null)
const reviewOpen = ref(false)
const reviewItem = ref<OrderItem | null>(null)
const reviewForm = reactive({ rating: 5, content: '', anonymous: false })
const money = (value: string) => Number(value).toLocaleString('zh-CN', { minimumFractionDigits: 2 })
const formatDate = (value: string) => new Date(value).toLocaleString('zh-CN')
const statusMap: Record<OrderStatus, { text: string; type: 'warning' | 'success' | 'primary' | 'info' | 'danger' }> = {
  PENDING_PAYMENT: { text: '待支付', type: 'warning' }, PAID: { text: '待发货', type: 'primary' },
  SHIPPED: { text: '已发货', type: 'primary' }, COMPLETED: { text: '已完成', type: 'success' },
  CANCELLED: { text: '已取消', type: 'info' }, REFUNDED: { text: '已退款', type: 'danger' },
}

async function load() {
  loading.value = true
  try {
    orders.value = (await getOrders()).items
    const target = Number(route.query.order)
    if (target) await openDetail(target)
  } catch (error) { ElMessage.error(error instanceof Error ? error.message : '订单加载失败') }
  finally { loading.value = false }
}

async function openDetail(id: number) {
  drawerOpen.value = true
  detailLoading.value = true
  try { detail.value = await getOrder(id) }
  catch (error) { ElMessage.error(error instanceof Error ? error.message : '订单详情加载失败') }
  finally { detailLoading.value = false }
}

async function pay(id: number) {
  acting.value = true
  try {
    const result = await payOrder(id)
    detail.value = result.order
    ElMessage.success(`支付成功，钱包余额 ¥${money(result.wallet_balance)}`)
    orders.value = (await getOrders()).items
  } catch (error) {
    const message = error instanceof Error ? error.message : '支付失败'
    ElMessage.error(message)
    if (message.includes('余额不足')) await router.push('/wallet')
  } finally { acting.value = false }
}

async function cancel(id: number) {
  await ElMessageBox.confirm('订单取消后无法恢复，确定继续吗？', '取消订单', { type: 'warning' })
  acting.value = true
  try {
    detail.value = await cancelOrder(id)
    ElMessage.success('订单已取消')
    orders.value = (await getOrders()).items
  } catch (error) { ElMessage.error(error instanceof Error ? error.message : '取消失败') }
  finally { acting.value = false }
}

async function confirmReceipt(id: number) {
  await ElMessageBox.confirm('请确认已经收到商品。确认后订单将完成，并可提交评价。', '确认收货', { type: 'warning' })
  acting.value = true
  try {
    detail.value = await completeOrder(id)
    ElMessage.success('已确认收货')
    orders.value = (await getOrders()).items
  } catch (error) { ElMessage.error(error instanceof Error ? error.message : '确认收货失败') }
  finally { acting.value = false }
}

function openReview(item: OrderItem) {
  reviewItem.value = item
  Object.assign(reviewForm, { rating: 5, content: '', anonymous: false })
  reviewOpen.value = true
}

async function submitReview() {
  if (!reviewItem.value || !reviewForm.content.trim()) { ElMessage.warning('请填写评价内容'); return }
  acting.value = true
  try {
    await createReview({ order_item_id: reviewItem.value.id, rating: reviewForm.rating, content: reviewForm.content.trim(), anonymous: reviewForm.anonymous })
    ElMessage.success('评价发布成功')
    reviewOpen.value = false
    if (detail.value) detail.value = await getOrder(detail.value.id)
  } catch (error) { ElMessage.error(error instanceof Error ? error.message : '评价提交失败') }
  finally { acting.value = false }
}

onMounted(load)
</script>

<template>
  <div class="page-shell orders-page">
    <div class="page-heading"><div><h1>我的订单</h1><p>查看订单状态、商品明细和收货信息。</p></div></div>
    <el-skeleton v-if="loading" :rows="7" animated />
    <StatePanel v-else-if="!orders.length" title="还没有订单" description="结算购物车后，订单会显示在这里。" action-label="去选商品" @action="router.push('/products')" />
    <div v-else class="order-list">
      <article v-for="order in orders" :key="order.id" class="order-row">
        <div class="order-icon"><el-icon><Box /></el-icon></div>
        <div class="order-main"><span>{{ formatDate(order.created_at) }}</span><strong>{{ order.order_no }}</strong></div>
        <el-tag :type="statusMap[order.status].type" effect="light">{{ statusMap[order.status].text }}</el-tag>
        <div class="order-amount"><span>应付金额</span><strong class="tabular">¥{{ money(order.payable_amount) }}</strong></div>
        <div class="order-actions"><el-button @click="openDetail(order.id)">查看详情</el-button><el-button v-if="order.status === 'PENDING_PAYMENT'" type="primary" :loading="acting" @click="pay(order.id)">余额支付</el-button><el-button v-if="order.status === 'SHIPPED'" type="primary" :loading="acting" @click="confirmReceipt(order.id)">确认收货</el-button></div>
      </article>
    </div>

    <el-drawer v-model="drawerOpen" title="订单详情" size="min(620px, 94vw)">
      <el-skeleton v-if="detailLoading" :rows="8" animated />
      <div v-else-if="detail" class="order-detail">
        <div class="detail-status"><el-tag :type="statusMap[detail.status].type" size="large">{{ statusMap[detail.status].text }}</el-tag><span>订单号 {{ detail.order_no }}</span></div>
        <section><h3>商品明细</h3><article v-for="item in detail.items" :key="item.id" class="detail-item"><div class="detail-image"><img v-if="item.image_url" :src="item.image_url" :alt="item.product_name" /><el-icon v-else><Picture /></el-icon></div><div><strong>{{ item.product_name }}</strong><span>{{ item.sku_name }} · × {{ item.quantity }}</span><el-button v-if="detail.status === 'COMPLETED' && !item.reviewed" link type="primary" :icon="ChatDotSquare" @click="openReview(item)">评价商品</el-button><small v-else-if="item.reviewed">已评价</small></div><strong class="tabular">¥{{ money(item.total_amount) }}</strong></article></section>
        <section><h3>收货信息</h3><p>{{ detail.address_snapshot.receiver_name }} · {{ detail.address_snapshot.receiver_phone }}</p><p>{{ detail.address_snapshot.province }} {{ detail.address_snapshot.city }} {{ detail.address_snapshot.district }} {{ detail.address_snapshot.detail }}</p></section>
        <section class="amount-detail"><div><span>商品金额</span><strong>¥{{ money(detail.product_amount) }}</strong></div><div><span>运费</span><strong>¥{{ money(detail.shipping_amount) }}</strong></div><div class="payable"><span>应付金额</span><strong>¥{{ money(detail.payable_amount) }}</strong></div></section>
        <div v-if="detail.status === 'PENDING_PAYMENT'" class="drawer-actions"><el-button :loading="acting" @click="cancel(detail.id)">取消订单</el-button><el-button type="primary" :icon="Wallet" :loading="acting" @click="pay(detail.id)">余额支付</el-button></div>
        <div v-else-if="detail.status === 'SHIPPED'" class="drawer-actions"><el-button type="primary" :loading="acting" @click="confirmReceipt(detail.id)">确认收货</el-button></div>
      </div>
    </el-drawer>

    <el-dialog v-model="reviewOpen" title="评价商品" width="min(520px, 92vw)">
      <div v-if="reviewItem" class="review-form">
        <strong>{{ reviewItem.product_name }} · {{ reviewItem.sku_name }}</strong>
        <div><span>商品评分</span><el-rate v-model="reviewForm.rating" /></div>
        <el-input v-model="reviewForm.content" type="textarea" :rows="5" maxlength="2000" show-word-limit placeholder="说说商品体验、优点或需要改进的地方" />
        <el-checkbox v-model="reviewForm.anonymous">匿名发布</el-checkbox>
      </div>
      <template #footer><el-button @click="reviewOpen = false">取消</el-button><el-button type="primary" :loading="acting" @click="submitReview">发布评价</el-button></template>
    </el-dialog>
  </div>
</template>

<style scoped>
.orders-page { min-height: 68vh; padding-top: 46px; }.page-heading { margin-bottom: 34px; }.page-heading h1 { margin: 0 0 8px; font-size: clamp(2rem, 4vw, 3.2rem); letter-spacing: -.045em; }.page-heading p { margin: 0; color: var(--color-ink-500); }
.order-list { display: grid; gap: 12px; }.order-row { display: grid; grid-template-columns: auto minmax(230px, 1fr) auto 140px auto; gap: 20px; align-items: center; padding: 20px; border: 1px solid var(--color-line); border-radius: var(--radius-container); background: var(--color-surface); transition: border-color 160ms ease, transform 160ms ease; }
.order-row:hover { border-color: color-mix(in srgb, var(--color-brand-600) 36%, var(--color-line)); transform: translateY(-1px); }
.order-icon { display: grid; width: 44px; height: 44px; place-items: center; border-radius: 9px; background: var(--color-brand-50); color: var(--color-brand-600); }.order-main, .order-amount { display: grid; gap: 6px; }.order-main span, .order-amount span { color: var(--color-ink-500); font-size: 12px; }.order-amount { text-align: right; }.order-actions { display: flex; justify-content: end; }
.detail-status { display: flex; align-items: center; justify-content: space-between; gap: 16px; padding-bottom: 20px; border-bottom: 1px solid var(--color-line); color: var(--color-ink-500); font-size: 12px; }.order-detail section { margin-top: 30px; }.order-detail h3 { margin: 0 0 16px; }.order-detail p { color: var(--color-ink-500); line-height: 1.7; }
.detail-item { display: grid; grid-template-columns: 64px 1fr auto; gap: 14px; align-items: center; padding: 12px 0; border-top: 1px solid var(--color-line); }.detail-image { display: grid; overflow: hidden; width: 64px; height: 64px; place-items: center; border-radius: 7px; background: #f1f3f6; }.detail-image img { width: 100%; height: 100%; object-fit: cover; }.detail-item > div:nth-child(2) { display: grid; justify-items: start; gap: 6px; }.detail-item span, .detail-item small { color: var(--color-ink-500); font-size: 12px; }
.amount-detail div { display: flex; justify-content: space-between; padding: 9px 0; }.amount-detail span { color: var(--color-ink-500); }.amount-detail .payable { margin-top: 6px; padding-top: 16px; border-top: 1px solid var(--color-line); }.amount-detail .payable strong { color: var(--color-danger); font-size: 22px; }.drawer-actions { position: sticky; bottom: 0; display: flex; justify-content: end; margin-top: 32px; padding: 18px 0; background: white; }
.review-form { display: grid; gap: 20px; }.review-form > div { display: flex; align-items: center; justify-content: space-between; color: var(--color-ink-500); }
@media (max-width: 900px) { .order-row { grid-template-columns: auto 1fr auto; }.order-amount { grid-column: 2; text-align: left; }.order-actions { grid-column: 2 / 4; justify-content: start; } }
@media (max-width: 767px) { .orders-page { padding-top: 30px; }.order-row { gap: 12px; } }
</style>
