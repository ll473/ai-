<script setup lang="ts">
import { ElMessage } from 'element-plus'
import { onMounted, ref } from 'vue'

import { getAdminReviews, updateReviewVisibility } from '../../api/trade'
import type { AdminReview } from '../../types/trade'

const reviews = ref<AdminReview[]>([])
const total = ref(0)
const loading = ref(true)
const updatingId = ref<number | null>(null)
const formatDate = (value: string) => new Date(value).toLocaleString('zh-CN')

async function load() {
  loading.value = true
  try { const data = await getAdminReviews(); reviews.value = data.items; total.value = data.total }
  catch (error) { ElMessage.error(error instanceof Error ? error.message : '评价加载失败') }
  finally { loading.value = false }
}

async function changeVisibility(review: AdminReview, visible: boolean) {
  updatingId.value = review.id
  try { Object.assign(review, await updateReviewVisibility(review.id, visible)); ElMessage.success(visible ? '评价已显示' : '评价已隐藏') }
  catch (error) { ElMessage.error(error instanceof Error ? error.message : '状态更新失败'); await load() }
  finally { updatingId.value = null }
}

onMounted(load)
</script>

<template>
  <div>
    <header class="admin-page-header"><div><h1 class="page-heading">评价管理</h1><p>审核用户真实订单评价；隐藏后会同步重算商品评分和评价数量。</p></div><span>{{ total }} 条评价</span></header>
    <el-table v-loading="loading" :data="reviews" empty-text="暂无评价" row-key="id">
      <el-table-column label="商品" min-width="190"><template #default="{ row }"><div class="primary-cell"><strong>{{ row.product_name }}</strong><span>商品 ID {{ row.product_id }}</span></div></template></el-table-column>
      <el-table-column label="用户" width="140"><template #default="{ row }"><div class="primary-cell"><strong>{{ row.anonymous ? '匿名展示' : row.display_name }}</strong><span>@{{ row.username }}</span></div></template></el-table-column>
      <el-table-column label="评分" width="150"><template #default="{ row }"><el-rate :model-value="row.rating" disabled /></template></el-table-column>
      <el-table-column prop="content" label="评价内容" min-width="280" show-overflow-tooltip />
      <el-table-column label="提交时间" width="170"><template #default="{ row }">{{ formatDate(row.created_at) }}</template></el-table-column>
      <el-table-column label="前台显示" width="110" align="center"><template #default="{ row }"><el-switch :model-value="row.visible" :loading="updatingId === row.id" @change="changeVisibility(row, Boolean($event))" /></template></el-table-column>
    </el-table>
  </div>
</template>

<style scoped>
.admin-page-header { display: flex; align-items: end; justify-content: space-between; gap: 20px; margin-bottom: 24px; }.admin-page-header p { margin: 8px 0 0; color: var(--color-ink-500); }.admin-page-header > span { color: var(--color-ink-500); font-size: 13px; }.primary-cell { display: grid; gap: 5px; }.primary-cell span { color: var(--color-ink-500); font-size: 12px; }
@media (max-width: 767px) { .admin-page-header { align-items: start; flex-direction: column; } }
</style>
