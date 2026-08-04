<script setup lang="ts">
import { Delete, Picture, ShoppingCart } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import { createOrder, deleteCartItem, getAddresses, getCart, selectAllCartItems, updateCartItem } from '../../api/trade'
import StatePanel from '../../components/StatePanel.vue'
import type { Address, CartSummary } from '../../types/trade'

const router = useRouter()
const cart = ref<CartSummary | null>(null)
const addresses = ref<Address[]>([])
const loading = ref(true)
const submitting = ref(false)
const checkoutOpen = ref(false)
const addressId = ref<number | null>(null)
const remark = ref('')
const allSelected = computed(() => !!cart.value?.items.length && cart.value.items.every((item) => item.selected))
const money = (value: string) => Number(value).toLocaleString('zh-CN', { minimumFractionDigits: 2 })

async function load() {
  loading.value = true
  try { cart.value = await getCart() }
  catch (error) { ElMessage.error(error instanceof Error ? error.message : '购物车加载失败') }
  finally { loading.value = false }
}

async function changeQuantity(itemId: number, quantity: number | undefined) {
  if (!quantity) return
  try { cart.value = await updateCartItem(itemId, { quantity }) }
  catch (error) { ElMessage.error(error instanceof Error ? error.message : '数量更新失败'); await load() }
}

async function changeSelected(itemId: number, selected: boolean) {
  try { cart.value = await updateCartItem(itemId, { selected }) }
  catch (error) { ElMessage.error(error instanceof Error ? error.message : '选择更新失败') }
}

async function toggleAll(selected: boolean) { cart.value = await selectAllCartItems(selected) }
async function remove(itemId: number) { cart.value = await deleteCartItem(itemId) }

async function openCheckout() {
  if (!cart.value?.selected_count) return
  try {
    addresses.value = await getAddresses()
    addressId.value = addresses.value.find((item) => item.is_default)?.id || addresses.value[0]?.id || null
    checkoutOpen.value = true
  } catch (error) { ElMessage.error(error instanceof Error ? error.message : '地址加载失败') }
}

async function submitOrder() {
  if (!addressId.value) { ElMessage.warning('请先选择收货地址'); return }
  submitting.value = true
  try {
    const order = await createOrder(addressId.value, remark.value)
    ElMessage.success('订单已创建，请完成余额支付')
    checkoutOpen.value = false
    await router.push({ name: 'orders', query: { order: order.id } })
  } catch (error) { ElMessage.error(error instanceof Error ? error.message : '下单失败') }
  finally { submitting.value = false }
}

onMounted(load)
</script>

<template>
  <div class="page-shell cart-page">
    <div class="page-heading"><div><h1>购物车</h1><p>确认商品、规格和数量，然后安心结算。</p></div></div>
    <el-skeleton v-if="loading" :rows="7" animated />
    <StatePanel v-else-if="!cart?.items.length" title="购物车还是空的" description="去看看有没有喜欢的商品。" action-label="去选商品" @action="router.push('/products')" />
    <div v-else class="cart-layout">
      <section class="cart-list">
        <div class="selection-row"><el-checkbox :model-value="allSelected" @change="toggleAll(Boolean($event))">全选</el-checkbox><span>共 {{ cart.total_count }} 件商品</span></div>
        <article v-for="item in cart.items" :key="item.id" class="cart-item" :class="{ unavailable: !item.available }">
          <el-checkbox :model-value="item.selected" :disabled="!item.available" aria-label="选择商品" @change="changeSelected(item.id, Boolean($event))" />
          <RouterLink :to="`/products/${item.product_id}`" class="item-image"><img v-if="item.image_url" :src="item.image_url" :alt="item.product_name" /><el-icon v-else><Picture /></el-icon></RouterLink>
          <div class="item-copy"><RouterLink :to="`/products/${item.product_id}`"><strong>{{ item.product_name }}</strong></RouterLink><span>{{ item.sku_name }}</span><em v-if="!item.available">已下架或库存不足</em></div>
          <strong class="unit-price tabular">¥{{ money(item.unit_price) }}</strong>
          <el-input-number :model-value="item.quantity" :min="1" :max="Math.max(1, item.available_stock)" size="small" :disabled="!item.available" @change="changeQuantity(item.id, $event)" />
          <strong class="subtotal tabular">¥{{ money(item.subtotal) }}</strong>
          <el-button text :icon="Delete" aria-label="删除商品" @click="remove(item.id)" />
        </article>
      </section>
      <aside class="checkout-card">
        <el-icon><ShoppingCart /></el-icon><h2>订单小计</h2>
        <div><span>已选商品</span><strong>{{ cart.selected_count }} 件</strong></div>
        <div class="total"><span>应付金额</span><strong class="tabular">¥{{ money(cart.selected_amount) }}</strong></div>
        <el-button type="primary" size="large" :disabled="!cart.selected_count" @click="openCheckout">去结算</el-button>
        <p>提交订单前，你还可以确认收货地址和订单备注。</p>
      </aside>
    </div>

    <el-dialog v-model="checkoutOpen" title="确认订单" width="min(620px, 94vw)">
      <template v-if="addresses.length">
        <el-radio-group v-model="addressId" class="address-options">
          <el-radio v-for="address in addresses" :key="address.id" :value="address.id" border>
            <strong>{{ address.receiver_name }} · {{ address.receiver_phone }}</strong>
            <span>{{ address.province }} {{ address.city }} {{ address.district }} {{ address.detail }}</span>
          </el-radio>
        </el-radio-group>
        <el-form-item label="订单备注（选填）"><el-input v-model="remark" type="textarea" maxlength="500" show-word-limit /></el-form-item>
      </template>
      <StatePanel v-else title="还没有收货地址" description="请先创建收货地址，再回来提交订单。" action-label="去新增地址" @action="router.push('/addresses')" />
      <template #footer><el-button @click="checkoutOpen = false">取消</el-button><el-button type="primary" :loading="submitting" :disabled="!addressId" @click="submitOrder">提交订单</el-button></template>
    </el-dialog>
  </div>
</template>

<style scoped>
.cart-page { min-height: 68vh; padding-top: 46px; }
.page-heading { margin-bottom: 34px; }
.page-heading h1 { margin: 0 0 8px; font-size: clamp(2rem, 4vw, 3.2rem); letter-spacing: -.045em; }
.page-heading p { margin: 0; color: var(--color-ink-500); }
.cart-layout { display: grid; grid-template-columns: minmax(0, 1fr) 300px; gap: 34px; align-items: start; }
.cart-list { overflow: hidden; border: 1px solid var(--color-line); border-radius: var(--radius-container); background: var(--color-surface); }
.selection-row { display: flex; justify-content: space-between; padding: 16px 20px; border-bottom: 1px solid var(--color-line); color: var(--color-ink-500); font-size: 13px; }
.cart-item { display: grid; grid-template-columns: auto 84px minmax(160px, 1fr) 100px 130px 110px auto; gap: 16px; align-items: center; padding: 20px; border-bottom: 1px solid var(--color-line); }
.cart-item:last-child { border-bottom: 0; }
.cart-item.unavailable { opacity: .65; }
.item-image { display: grid; overflow: hidden; width: 84px; height: 84px; place-items: center; border-radius: var(--radius-control); background: var(--color-surface-soft); color: var(--color-ink-400); }
.item-image img { width: 100%; height: 100%; object-fit: cover; }
.item-copy { display: grid; gap: 7px; }
.item-copy span { color: var(--color-ink-500); font-size: 13px; }
.item-copy em { color: var(--color-danger); font-size: 12px; font-style: normal; }
.subtotal { color: var(--color-danger); }
.checkout-card { position: sticky; top: calc(var(--nav-height) + 24px); padding: 26px; border: 1px solid var(--color-line); border-radius: var(--radius-container); background: var(--color-surface); box-shadow: var(--shadow-card); }
.checkout-card > .el-icon { color: var(--color-brand-600); font-size: 24px; }
.checkout-card h2 { margin: 16px 0 24px; }
.checkout-card > div { display: flex; justify-content: space-between; padding: 12px 0; color: var(--color-ink-500); }
.checkout-card .total { margin-top: 8px; border-top: 1px solid var(--color-line); color: var(--color-ink-700); }
.checkout-card .total strong { color: var(--color-danger); font-size: 22px; }
.checkout-card .el-button { width: 100%; margin-top: 18px; }
.checkout-card p { color: var(--color-ink-500); font-size: 12px; line-height: 1.7; }
.address-options { display: grid; gap: 10px; margin-bottom: 24px; }
.address-options .el-radio { width: 100%; height: auto; margin: 0; padding: 14px; }
.address-options strong, .address-options span { display: block; line-height: 1.7; }
.address-options span { color: var(--color-ink-500); font-size: 12px; }
@media (max-width: 1023px) { .cart-layout { grid-template-columns: 1fr; } .checkout-card { position: static; } .cart-item { grid-template-columns: auto 72px 1fr auto; } .unit-price, .cart-item .el-input-number, .subtotal { grid-column: 3; } }
@media (max-width: 767px) { .cart-page { padding-top: 30px; } .cart-item { gap: 12px; } .item-image { width: 64px; height: 64px; } }
</style>
