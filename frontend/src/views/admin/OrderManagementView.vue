<script setup lang="ts">
import { ElMessage, ElMessageBox } from 'element-plus'
import { onMounted, ref } from 'vue'

import { completeAdminOrder, getAdminOrder, getAdminOrders, shipAdminOrder } from '../../api/trade'
import type { AdminOrderDetail, AdminOrderSummary, OrderStatus } from '../../types/trade'

const orders = ref<AdminOrderSummary[]>([])
const total = ref(0)
const loading = ref(true)
const acting = ref(false)
const drawerOpen = ref(false)
const detail = ref<AdminOrderDetail | null>(null)
const statusFilter = ref<OrderStatus>()
const statusMap: Record<OrderStatus, { label: string; type: 'warning' | 'primary' | 'success' | 'info' | 'danger' }> = {
  PENDING_PAYMENT: { label: '待支付', type: 'warning' }, PAID: { label: '待发货', type: 'primary' },
  SHIPPED: { label: '已发货', type: 'primary' }, COMPLETED: { label: '已完成', type: 'success' },
  CANCELLED: { label: '已取消', type: 'info' }, REFUNDED: { label: '已退款', type: 'danger' },
}
const money = (value: string) => `¥${Number(value).toFixed(2)}`
const formatDate = (value: string) => new Date(value).toLocaleString('zh-CN')

async function load() {
  loading.value = true
  try { const data = await getAdminOrders(1, 20, statusFilter.value); orders.value = data.items; total.value = data.total }
  catch (error) { ElMessage.error(error instanceof Error ? error.message : '订单加载失败') }
  finally { loading.value = false }
}

async function openDetail(id: number) {
  drawerOpen.value = true
  try { detail.value = await getAdminOrder(id) }
  catch (error) { ElMessage.error(error instanceof Error ? error.message : '订单详情加载失败') }
}

async function ship(id: number) {
  await ElMessageBox.confirm('确认该订单已经完成出库并发货吗？', '订单发货', { type: 'warning' })
  acting.value = true
  try { detail.value = await shipAdminOrder(id); ElMessage.success('订单已发货'); await load() }
  catch (error) { ElMessage.error(error instanceof Error ? error.message : '发货失败') }
  finally { acting.value = false }
}

async function complete(id: number) {
  await ElMessageBox.confirm('确定由管理员将该订单标记为已完成吗？', '完成订单', { type: 'warning' })
  acting.value = true
  try { detail.value = await completeAdminOrder(id); ElMessage.success('订单已完成'); await load() }
  catch (error) { ElMessage.error(error instanceof Error ? error.message : '操作失败') }
  finally { acting.value = false }
}

onMounted(load)
</script>

<template>
  <div>
    <header class="admin-page-header"><div><h1 class="page-heading">订单管理</h1><p>处理已支付订单的发货与履约状态，金额和地址均读取订单快照。</p></div><span>{{ total }} 笔订单</span></header>
    <section class="toolbar"><el-select v-model="statusFilter" clearable placeholder="全部状态" @change="load"><el-option v-for="(item, key) in statusMap" :key="key" :label="item.label" :value="key" /></el-select><el-button @click="load">刷新</el-button></section>
    <el-table v-loading="loading" :data="orders" empty-text="暂无订单" row-key="id">
      <el-table-column prop="order_no" label="订单号" min-width="235"><template #default="{ row }"><div class="primary-cell"><strong>{{ row.order_no }}</strong><span>{{ formatDate(row.created_at) }}</span></div></template></el-table-column>
      <el-table-column prop="user_id" label="用户 ID" width="100" />
      <el-table-column label="金额" width="130" align="right"><template #default="{ row }"><strong class="tabular">{{ money(row.payable_amount) }}</strong></template></el-table-column>
      <el-table-column label="状态" width="110"><template #default="{ row }"><el-tag :type="statusMap[row.status as OrderStatus].type" effect="plain">{{ statusMap[row.status as OrderStatus].label }}</el-tag></template></el-table-column>
      <el-table-column label="操作" min-width="210" align="right"><template #default="{ row }"><el-button link @click="openDetail(row.id)">详情</el-button><el-button v-if="row.status === 'PAID'" link type="primary" :loading="acting" @click="ship(row.id)">确认发货</el-button><el-button v-if="row.status === 'SHIPPED'" link type="primary" :loading="acting" @click="complete(row.id)">完成订单</el-button></template></el-table-column>
    </el-table>

    <el-drawer v-model="drawerOpen" title="订单履约详情" size="min(620px, 94vw)">
      <div v-if="detail" class="detail-panel">
        <div class="detail-head"><el-tag :type="statusMap[detail.status].type">{{ statusMap[detail.status].label }}</el-tag><span>用户 ID {{ detail.user_id }}</span></div>
        <section><h3>商品明细</h3><article v-for="item in detail.items" :key="item.id"><div><strong>{{ item.product_name }}</strong><span>{{ item.sku_name }} · × {{ item.quantity }}</span></div><strong>{{ money(item.total_amount) }}</strong></article></section>
        <section><h3>收货地址快照</h3><p>{{ detail.address_snapshot.receiver_name }} · {{ detail.address_snapshot.receiver_phone }}</p><p>{{ detail.address_snapshot.province }} {{ detail.address_snapshot.city }} {{ detail.address_snapshot.district }} {{ detail.address_snapshot.detail }}</p></section>
        <section class="amount"><span>实付金额</span><strong>{{ money(detail.paid_amount) }}</strong></section>
        <div class="detail-actions"><el-button v-if="detail.status === 'PAID'" type="primary" :loading="acting" @click="ship(detail.id)">确认发货</el-button><el-button v-if="detail.status === 'SHIPPED'" type="primary" :loading="acting" @click="complete(detail.id)">完成订单</el-button></div>
      </div>
    </el-drawer>
  </div>
</template>

<style scoped>
.admin-page-header { display: flex; align-items: end; justify-content: space-between; gap: 20px; margin-bottom: 24px; }.admin-page-header p { margin: 8px 0 0; color: var(--color-ink-500); }.admin-page-header > span { color: var(--color-ink-500); font-size: 13px; }.toolbar { display: flex; gap: 10px; margin-bottom: 18px; }.toolbar .el-select { width: 200px; }.primary-cell { display: grid; gap: 5px; }.primary-cell span { color: var(--color-ink-500); font-size: 12px; }
.detail-head { display: flex; justify-content: space-between; padding-bottom: 18px; border-bottom: 1px solid var(--color-line); color: var(--color-ink-500); }.detail-panel section { margin-top: 28px; }.detail-panel article { display: flex; justify-content: space-between; gap: 20px; padding: 14px 0; border-top: 1px solid var(--color-line); }.detail-panel article > div { display: grid; gap: 6px; }.detail-panel article span, .detail-panel p { color: var(--color-ink-500); font-size: 13px; line-height: 1.7; }.amount { display: flex; justify-content: space-between; padding-top: 18px; border-top: 1px solid var(--color-line); }.amount strong { color: var(--color-danger); font-size: 22px; }.detail-actions { position: sticky; bottom: 0; display: flex; justify-content: end; padding: 20px 0; background: white; }
@media (max-width: 767px) { .admin-page-header { align-items: start; flex-direction: column; } }
</style>
