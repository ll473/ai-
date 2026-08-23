<script setup lang="ts">
import { Plus, Refresh } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { onMounted, reactive, ref } from 'vue'

import { createPromotion, deletePromotion, getPromotions, updatePromotion } from '../../api/admin'
import { getProducts } from '../../api/catalog'
import type { Promotion, PromotionPayload } from '../../types/admin'
import type { ProductSummary } from '../../types/catalog'

const items = ref<Promotion[]>([])
const products = ref<ProductSummary[]>([])
const loading = ref(false)
const saving = ref(false)
const dialogOpen = ref(false)
const editingId = ref<number | null>(null)
const form = reactive<PromotionPayload>({
  name: '', product_id: null, promotion_type: 'PERCENT', value: 10,
  minimum_amount: 0, starts_at: '', ends_at: '', priority: 0, enabled: true,
})
const productName = (id: number | null) => id ? products.value.find((item) => item.id === id)?.name || `商品 ${id}` : '全场商品'

async function load() {
  loading.value = true
  try {
    const [promotionData, productData] = await Promise.all([getPromotions(), getProducts({ page_size: 100 }, true)])
    items.value = promotionData.items
    products.value = productData.items
  } catch (error) { ElMessage.error(error instanceof Error ? error.message : '优惠活动加载失败') }
  finally { loading.value = false }
}

function defaults() {
  const start = new Date(); const end = new Date(start.getTime() + 30 * 86400000)
  Object.assign(form, { name: '', product_id: null, promotion_type: 'PERCENT', value: 10, minimum_amount: 0, starts_at: start.toISOString(), ends_at: end.toISOString(), priority: 0, enabled: true })
}

function openCreate() { editingId.value = null; defaults(); dialogOpen.value = true }
function openEdit(item: Promotion) {
  editingId.value = item.id
  Object.assign(form, { name: item.name, product_id: item.product_id, promotion_type: item.promotion_type, value: Number(item.value), minimum_amount: Number(item.minimum_amount), starts_at: item.starts_at, ends_at: item.ends_at, priority: item.priority, enabled: item.enabled })
  dialogOpen.value = true
}

async function save() {
  if (!form.name.trim() || !form.starts_at || !form.ends_at) { ElMessage.warning('请填写完整活动信息'); return }
  saving.value = true
  try {
    if (editingId.value) await updatePromotion(editingId.value, form)
    else await createPromotion(form)
    ElMessage.success('优惠活动已保存'); dialogOpen.value = false; await load()
  } catch (error) { ElMessage.error(error instanceof Error ? error.message : '保存失败') }
  finally { saving.value = false }
}

async function remove(item: Promotion) {
  try { await ElMessageBox.confirm(`确认删除“${item.name}”？`, '删除优惠活动', { type: 'warning' }); await deletePromotion(item.id); await load() }
  catch (error) { if (error !== 'cancel') ElMessage.error(error instanceof Error ? error.message : '删除失败') }
}

onMounted(load)
</script>

<template>
  <div>
    <header class="admin-page-header"><div><h1 class="page-heading">优惠活动</h1><p>维护真实优惠规则，下单结算和 AI 价格工具都会使用这里的数据。</p></div><el-button type="primary" :icon="Plus" @click="openCreate">新增活动</el-button></header>
    <section class="table-card"><div class="table-actions"><el-button :icon="Refresh" @click="load">刷新</el-button></div><el-table v-loading="loading" :data="items" empty-text="暂无优惠活动"><el-table-column prop="name" label="活动名称" min-width="180"/><el-table-column label="适用商品" min-width="220"><template #default="{row}">{{ productName(row.product_id) }}</template></el-table-column><el-table-column label="优惠" width="140"><template #default="{row}">{{ row.promotion_type === 'PERCENT' ? `${row.value}% 折扣` : `立减 ¥${row.value}` }}</template></el-table-column><el-table-column label="最低金额" width="120"><template #default="{row}">¥{{ row.minimum_amount }}</template></el-table-column><el-table-column prop="starts_at" label="开始时间" width="185"/><el-table-column prop="ends_at" label="结束时间" width="185"/><el-table-column label="状态" width="90"><template #default="{row}"><el-tag :type="row.enabled?'success':'info'">{{ row.enabled?'启用':'停用' }}</el-tag></template></el-table-column><el-table-column label="操作" width="140" align="right"><template #default="{row}"><el-button link type="primary" @click="openEdit(row)">编辑</el-button><el-button link type="danger" @click="remove(row)">删除</el-button></template></el-table-column></el-table></section>
    <el-dialog v-model="dialogOpen" :title="editingId ? '编辑优惠活动' : '新增优惠活动'" width="min(720px,94vw)"><el-form label-position="top"><div class="form-grid"><el-form-item label="活动名称"><el-input v-model="form.name"/></el-form-item><el-form-item label="适用商品"><el-select v-model="form.product_id" clearable filterable placeholder="全场商品" style="width:100%"><el-option v-for="item in products" :key="item.id" :label="item.name" :value="item.id"/></el-select></el-form-item></div><div class="form-grid"><el-form-item label="优惠类型"><el-radio-group v-model="form.promotion_type"><el-radio-button value="PERCENT">百分比折扣</el-radio-button><el-radio-button value="FIXED">固定立减</el-radio-button></el-radio-group></el-form-item><el-form-item :label="form.promotion_type==='PERCENT'?'折扣百分比':'立减金额'"><el-input-number v-model="form.value" :min="0.01" :max="form.promotion_type==='PERCENT'?100:100000" style="width:100%"/></el-form-item></div><div class="form-grid"><el-form-item label="最低消费金额"><el-input-number v-model="form.minimum_amount" :min="0" style="width:100%"/></el-form-item><el-form-item label="优先级"><el-input-number v-model="form.priority" :min="0" style="width:100%"/></el-form-item></div><div class="form-grid"><el-form-item label="开始时间"><el-date-picker v-model="form.starts_at" type="datetime" value-format="YYYY-MM-DDTHH:mm:ssZ" style="width:100%"/></el-form-item><el-form-item label="结束时间"><el-date-picker v-model="form.ends_at" type="datetime" value-format="YYYY-MM-DDTHH:mm:ssZ" style="width:100%"/></el-form-item></div><el-switch v-model="form.enabled" active-text="启用活动"/></el-form><template #footer><el-button @click="dialogOpen=false">取消</el-button><el-button type="primary" :loading="saving" @click="save">保存</el-button></template></el-dialog>
  </div>
</template>

<style scoped>.admin-page-header{display:flex;align-items:end;justify-content:space-between;gap:20px;margin-bottom:20px}.admin-page-header p{margin:7px 0 0;color:var(--color-ink-500)}.table-card{padding:14px;border:1px solid var(--color-line);border-radius:var(--radius-container);background:white}.table-actions{display:flex;justify-content:flex-end;margin-bottom:10px}.form-grid{display:grid;grid-template-columns:1fr 1fr;gap:14px}@media(max-width:767px){.admin-page-header{align-items:start;flex-direction:column}.form-grid{grid-template-columns:1fr}.table-card{overflow:auto}.table-card .el-table{min-width:1200px}}</style>
