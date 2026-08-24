<script setup lang="ts">
import { computed, shallowRef, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { getProductComparison } from '../../api/catalog'
import ProductComparisonAiPanel from '../../components/catalog/ProductComparisonAiPanel.vue'
import { useCompareStore } from '../../stores/compare'
import type { ProductComparisonItem } from '../../types/catalog'

interface ComparisonRow {
  key: string
  label: string
  values: string[]
  different: boolean
}

const route = useRoute()
const router = useRouter()
const compare = useCompareStore()

const products = shallowRef<ProductComparisonItem[]>([])
const loading = shallowRef(false)
const loadError = shallowRef('')
const unavailableIds = shallowRef<number[]>([])
const differencesOnly = shallowRef(false)
let requestSequence = 0
let internalCanonicalIds: string | null = null

function normalizeProductIds(value: unknown): number[] {
  const parts = Array.isArray(value) ? value : [value]
  const ids: number[] = []
  for (const part of parts) {
    if (typeof part !== 'string') continue
    for (const token of part.split(',')) {
      if (!/^[1-9]\d*$/.test(token) || ids.length === 4) continue
      const productId = Number(token)
      if (!Number.isSafeInteger(productId) || ids.includes(productId)) continue
      ids.push(productId)
    }
  }
  return ids
}

function formatParameter(value: unknown): string {
  if (value === null || value === undefined || value === '') return '未提供'
  if (typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean')
    return String(value)
  return JSON.stringify(value)
}

function formatPriceRange(product: ProductComparisonItem): string {
  const min = `¥${Number(product.min_price).toLocaleString('zh-CN', { minimumFractionDigits: 2 })}`
  const max = `¥${Number(product.max_price).toLocaleString('zh-CN', { minimumFractionDigits: 2 })}`
  return product.min_price === product.max_price ? min : `${min} – ${max}`
}

function buildRows(
  keys: string[],
  valuesForProduct: (product: ProductComparisonItem, key: string) => string,
  keyPrefix = '',
): ComparisonRow[] {
  return keys.map((key) => {
    const values = products.value.map(product => valuesForProduct(product, key))
    return { key: `${keyPrefix}${key}`, label: key, values, different: new Set(values).size > 1 }
  })
}

const parameterRows = computed(() => buildRows(
  [...new Set(products.value.flatMap(product => Object.keys(product.parameters || {})))],
  (product, key) => formatParameter(product.parameters?.[key]),
))

const skuAttributeRows = computed(() => buildRows(
  [...new Set(products.value.flatMap(product => product.skus.flatMap(sku => Object.keys(sku.attributes || {}))))],
  (product, key) => {
    const values = product.skus
      .map(sku => formatParameter(sku.attributes?.[key]))
      .filter(value => value !== '未提供')
    return [...new Set(values)].join(' / ') || '未提供'
  },
  'sku:',
))

const fixedRows = computed<ComparisonRow[]>(() => [
  { key: 'brand', label: '品牌', values: products.value.map(product => product.brand_name || '未提供'), different: false },
  { key: 'price', label: '价格区间', values: products.value.map(formatPriceRange), different: false },
  { key: 'rating', label: '评分', values: products.value.map(product => `${Number(product.rating).toFixed(1)} 分`), different: false },
  { key: 'review_count', label: '评价数', values: products.value.map(product => `${product.review_count} 条`), different: false },
  { key: 'sales_count', label: '销量', values: products.value.map(product => `${product.sales_count} 件`), different: false },
  { key: 'total_available_stock', label: '总可售库存', values: products.value.map(product => `${product.total_available_stock} 件`), different: false },
].map(row => ({ ...row, different: new Set(row.values).size > 1 })))

const visibleRows = computed(() => {
  const rows = [...fixedRows.value, ...parameterRows.value, ...skuAttributeRows.value]
  return differencesOnly.value ? rows.filter(row => row.different) : rows
})

const hasEnoughProducts = computed(() => products.value.length >= 2)
const hasDetailedParameters = computed(() => parameterRows.value.length > 0 || skuAttributeRows.value.length > 0)

function isCanonicalRouteValue(value: unknown, ids: number[]) {
  const canonicalIds = ids.join(',')
  if (!canonicalIds) return value === undefined
  return typeof value === 'string' && value === canonicalIds
}

async function replaceWithResolvedIds(ids: number[]) {
  if (isCanonicalRouteValue(route.query.ids, ids)) return
  const resolvedIds = ids.join(',')
  internalCanonicalIds = resolvedIds
  await router.replace({
    path: '/compare',
    query: resolvedIds ? { ids: resolvedIds } : {},
  })
}

async function loadComparison(value: unknown) {
  const requestedIds = normalizeProductIds(value)
  const requestedIdsText = requestedIds.join(',')
  const isInternalCanonicalReload = internalCanonicalIds === requestedIdsText
    && isCanonicalRouteValue(value, requestedIds)
  if (isInternalCanonicalReload) {
    internalCanonicalIds = null
    return
  }
  const sequence = ++requestSequence
  loadError.value = ''
  unavailableIds.value = []

  if (requestedIds.length < 2) {
    if (!requestedIds.length) {
      products.value = []
      compare.clear()
    }
    loading.value = false
    return
  }

  loading.value = true
  try {
    const result = await getProductComparison(requestedIds)
    if (sequence !== requestSequence) return
    products.value = result.items
    unavailableIds.value = result.unavailable_ids
    compare.replaceFromProducts(result.items)
    await replaceWithResolvedIds(result.items.map(product => product.id))
  } catch (cause) {
    if (sequence !== requestSequence) return
    products.value = []
    loadError.value = cause instanceof Error ? cause.message : '商品对比加载失败，请稍后重试'
  } finally {
    if (sequence === requestSequence) loading.value = false
  }
}

function retryComparison() {
  void loadComparison(route.query.ids)
}

async function removeProduct(productId: number) {
  products.value = products.value.filter(product => product.id !== productId)
  unavailableIds.value = unavailableIds.value.filter(id => id !== productId)
  compare.remove(productId)
  internalCanonicalIds = compare.ids.join(',')
  await router.replace({
    path: '/compare',
    query: compare.ids.length ? { ids: compare.ids.join(',') } : {},
  })
}

watch(() => route.query.ids, value => void loadComparison(value), { immediate: true })
</script>

<template>
  <main class="page-shell product-comparison-page">
    <header class="comparison-header">
      <div>
        <p class="comparison-eyebrow">商品对比中心</p>
        <h1 class="comparison-title">清楚比较，再做选择</h1>
        <p class="comparison-description">价格、库存和规格均来自当前在售商品数据。</p>
      </div>
      <label class="differences-toggle">
        <input v-model="differencesOnly" aria-label="仅看差异" type="checkbox">
        <span>仅看差异</span>
      </label>
    </header>

    <p v-if="unavailableIds.length" class="comparison-notice" role="status">
      部分商品已失效，已从对比中移除
    </p>

    <section v-if="loading" class="comparison-state" aria-live="polite">正在加载对比商品…</section>
    <section v-else-if="loadError" class="comparison-state comparison-state--error" role="alert">
      <p>{{ loadError }}</p>
      <button type="button" aria-label="重新加载商品对比" @click="retryComparison">重新加载</button>
    </section>
    <section v-else-if="!hasEnoughProducts" class="comparison-state">
      <h2>请选择至少两件同分类商品</h2>
      <p>从商品列表或详情页加入对比，即可在这里查看差异。</p>
      <p v-if="products.length">当前保留：{{ products.map(product => product.name).join('、') }}</p>
      <RouterLink class="browse-link" to="/products">返回商品列表</RouterLink>
    </section>
    <section v-else class="comparison-table-wrap" aria-label="商品对比表">
      <table class="comparison-table">
        <thead>
          <tr>
            <th class="comparison-table__label" scope="col">对比项目</th>
            <th v-for="product in products" :key="product.id" class="comparison-table__product" scope="col">
              <div class="product-heading">
                <img v-if="product.main_image_url" :src="product.main_image_url" :alt="product.name">
                <div>
                  <p>{{ product.name }}</p>
                  <span>{{ product.category_name }}</span>
                </div>
              </div>
              <div class="product-actions">
                <RouterLink :to="{ name: 'product-detail', params: { id: product.id } }">查看详情</RouterLink>
                <button type="button" :aria-label="`移除商品 ${product.id}`" @click="removeProduct(product.id)">移除</button>
              </div>
            </th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in visibleRows" :key="row.key" :data-parameter="row.label">
            <th class="comparison-table__label" scope="row">{{ row.label }}</th>
            <td v-for="(value, index) in row.values" :key="products[index]?.id" :class="{ 'price-value': row.key === 'price' }">{{ value }}</td>
          </tr>
          <tr v-if="!hasDetailedParameters && !differencesOnly" data-parameter-notice>
            <th class="comparison-table__label" scope="row">详细参数</th>
            <td :colspan="products.length">商家暂未提供详细参数</td>
          </tr>
        </tbody>
      </table>
    </section>
    <ProductComparisonAiPanel v-if="products.length >= 2" :products="products" />
  </main>
</template>

<style scoped>
.product-comparison-page {
  min-height: 70vh;
  padding-top: 34px;
}

.comparison-header {
  display: flex;
  align-items: end;
  justify-content: space-between;
  gap: 24px;
  margin-bottom: 24px;
}

.comparison-eyebrow {
  margin: 0 0 8px;
  color: var(--color-brand-600);
  font-size: 13px;
  font-weight: 720;
}

.comparison-title {
  margin: 0;
  color: var(--color-ink-950);
  font-size: clamp(28px, 4vw, 42px);
  letter-spacing: -0.045em;
}

.comparison-description {
  margin: 10px 0 0;
  color: var(--color-ink-500);
}

.differences-toggle {
  display: inline-flex;
  flex: 0 0 auto;
  align-items: center;
  gap: 8px;
  min-height: 40px;
  padding: 0 12px;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-control);
  background: var(--color-surface);
  color: var(--color-ink-700);
  cursor: pointer;
  font-size: 13px;
  font-weight: 650;
}

.differences-toggle input {
  accent-color: var(--color-brand-600);
}

.comparison-notice {
  margin: 0 0 16px;
  padding: 12px 14px;
  border: 1px solid #f1d49e;
  border-radius: var(--radius-control);
  background: #fff9ed;
  color: #8a5800;
  font-size: 13px;
}

.comparison-state {
  padding: 48px 24px;
  border: 1px dashed var(--color-line-strong);
  border-radius: var(--radius-container);
  background: var(--color-surface-soft);
  color: var(--color-ink-600);
  text-align: center;
}

.comparison-state h2 {
  margin: 0;
  color: var(--color-ink-900);
  font-size: 20px;
}

.comparison-state p {
  margin: 10px 0 20px;
}

.comparison-state--error {
  border-color: #efb5b5;
  background: #fff7f7;
  color: var(--color-danger);
}

.comparison-state--error p {
  margin: 0 0 16px;
}

.comparison-state--error button {
  min-height: 36px;
  padding: 0 14px;
  border: 1px solid var(--color-danger);
  border-radius: var(--radius-control);
  background: var(--color-surface);
  color: var(--color-danger);
  cursor: pointer;
  font-weight: 650;
}

.browse-link,
.product-actions a {
  color: var(--color-brand-700);
  font-size: 13px;
  font-weight: 650;
}

.comparison-table-wrap {
  overflow-x: auto;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-container);
  background: var(--color-surface);
}

.comparison-table {
  width: 100%;
  min-width: 720px;
  border-collapse: separate;
  border-spacing: 0;
  table-layout: fixed;
}

.comparison-table th,
.comparison-table td {
  min-width: 240px;
  padding: 16px 18px;
  border-right: 1px solid var(--color-line);
  border-bottom: 1px solid var(--color-line);
  color: var(--color-ink-700);
  font-size: 14px;
  line-height: 1.55;
  text-align: left;
  vertical-align: top;
  word-break: break-word;
}

.comparison-table tr:last-child th,
.comparison-table tr:last-child td {
  border-bottom: 0;
}

.comparison-table th:last-child,
.comparison-table td:last-child {
  border-right: 0;
}

.comparison-table__label {
  position: sticky;
  z-index: 2;
  left: 0;
  min-width: 146px !important;
  width: 146px;
  background: var(--color-surface-soft);
  color: var(--color-ink-600) !important;
  font-size: 13px !important;
  font-weight: 670;
}

.comparison-table thead .comparison-table__label {
  z-index: 3;
  background: var(--color-surface);
}

.comparison-table__product {
  background: var(--color-surface);
}

.product-heading {
  display: flex;
  align-items: center;
  gap: 10px;
}

.product-heading img {
  width: 42px;
  height: 42px;
  border-radius: 8px;
  object-fit: cover;
}

.product-heading p {
  margin: 0;
  color: var(--color-ink-950);
  font-size: 14px;
}

.product-heading span {
  color: var(--color-ink-500);
  font-size: 12px;
  font-weight: 500;
}

.product-actions {
  display: flex;
  gap: 12px;
  margin-top: 12px;
}

.product-actions button {
  padding: 0;
  border: 0;
  background: transparent;
  color: var(--color-ink-500);
  cursor: pointer;
  font-size: 13px;
}

.product-actions button:hover {
  color: var(--color-danger);
}

.price-value {
  color: var(--color-danger) !important;
  font-weight: 700;
}

@media (max-width: 720px) {
  .product-comparison-page {
    padding-top: 22px;
  }

  .comparison-header {
    align-items: start;
    flex-direction: column;
  }

  .comparison-title {
    font-size: 30px;
  }

  .comparison-table th,
  .comparison-table td {
    min-width: 220px;
    padding: 14px;
  }

  .comparison-table__label {
    min-width: 118px !important;
    width: 118px;
  }
}
</style>
