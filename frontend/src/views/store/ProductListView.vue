<script setup lang="ts">
import { Filter } from '@element-plus/icons-vue'
import { computed, onMounted, reactive, shallowRef, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import {
  getBrands,
  getCategories,
  recordSearchEvent,
  searchCatalog,
} from '../../api/catalog'
import CatalogSearchBox from '../../components/catalog/CatalogSearchBox.vue'
import ProductCard from '../../components/ProductCard.vue'
import StatePanel from '../../components/StatePanel.vue'
import type {
  Brand,
  Category,
  ProductSearchSort,
  ProductSummary,
  SearchFacets,
  SearchSuggestion,
} from '../../types/catalog'

const route = useRoute()
const router = useRouter()
const products = shallowRef<ProductSummary[]>([])
const categories = shallowRef<Category[]>([])
const brands = shallowRef<Brand[]>([])
const total = shallowRef(0)
const loading = shallowRef(true)
const error = shallowRef('')
const searchMode = shallowRef<'catalog' | 'hybrid'>('catalog')
const facets = shallowRef<SearchFacets>({
  categories: [],
  brands: [],
  min_price: null,
  max_price: null,
  in_stock_count: 0,
})
let productRequestSequence = 0

const categoryNames = computed(() => new Map(categories.value.map((item) => [item.id, item.name])))
const brandNames = computed(() => new Map(brands.value.map((item) => [item.id, item.name])))
const categoryFacetCounts = computed(
  () => new Map(facets.value.categories.map((item) => [item.id, item.count])),
)
const brandFacetCounts = computed(
  () => new Map(facets.value.brands.map((item) => [item.id, item.count])),
)

function queryNumber(value: unknown) {
  if (typeof value !== 'string' || !value.trim()) return undefined
  const parsed = Number(value)
  return Number.isFinite(parsed) && parsed >= 0 ? parsed : undefined
}

function queryBoolean(value: unknown) {
  return value === 'true' || value === '1'
}

function querySort(value: unknown): ProductSearchSort {
  const allowed: ProductSearchSort[] = [
    'relevance',
    'newest',
    'sales',
    'rating',
    'price_asc',
    'price_desc',
  ]
  return typeof value === 'string' && allowed.includes(value as ProductSearchSort)
    ? value as ProductSearchSort
    : 'relevance'
}

const filters = reactive({
  keyword: typeof route.query.keyword === 'string' ? route.query.keyword : '',
  category_id: queryNumber(route.query.category_id),
  brand_id: queryNumber(route.query.brand_id),
  min_price: queryNumber(route.query.min_price),
  max_price: queryNumber(route.query.max_price),
  in_stock: queryBoolean(route.query.in_stock),
  sort: querySort(route.query.sort),
  page: queryNumber(route.query.page) || 1,
  page_size: 12,
})

async function loadFilters() {
  const [categoryData, brandData] = await Promise.all([getCategories(), getBrands()])
  categories.value = categoryData
  brands.value = brandData
}

async function loadProducts() {
  const sequence = ++productRequestSequence
  const snapshot = {
    keyword: filters.keyword.trim(),
    category_id: filters.category_id,
    brand_id: filters.brand_id,
    min_price: filters.min_price,
    max_price: filters.max_price,
    in_stock: filters.in_stock,
    sort: filters.sort,
    page: filters.page,
    page_size: filters.page_size,
  }
  loading.value = true
  error.value = ''
  try {
    const data = await searchCatalog({
      page: snapshot.page,
      page_size: snapshot.page_size,
      keyword: snapshot.keyword || undefined,
      category_id: snapshot.category_id,
      brand_id: snapshot.brand_id,
      min_price: snapshot.min_price,
      max_price: snapshot.max_price,
      in_stock: snapshot.in_stock,
      sort: snapshot.sort,
      semantic: snapshot.keyword.length >= 6,
    })
    if (sequence !== productRequestSequence) return
    products.value = data.items
    total.value = data.total
    facets.value = data.facets
    searchMode.value = data.search_mode
    await router.replace({
      query: {
        ...(snapshot.keyword ? { keyword: snapshot.keyword } : {}),
        ...(snapshot.category_id ? { category_id: String(snapshot.category_id) } : {}),
        ...(snapshot.brand_id ? { brand_id: String(snapshot.brand_id) } : {}),
        ...(snapshot.min_price !== undefined ? { min_price: String(snapshot.min_price) } : {}),
        ...(snapshot.max_price !== undefined ? { max_price: String(snapshot.max_price) } : {}),
        ...(snapshot.in_stock ? { in_stock: 'true' } : {}),
        ...(snapshot.sort !== 'relevance' ? { sort: snapshot.sort } : {}),
        ...(snapshot.page > 1 ? { page: String(snapshot.page) } : {}),
      },
    })
    if (snapshot.keyword) {
      void recordSearchEvent({
        event_type: 'search',
        query: snapshot.keyword,
        result_count: data.total,
        filters: {
          category_id: snapshot.category_id,
          brand_id: snapshot.brand_id,
          min_price: snapshot.min_price,
          max_price: snapshot.max_price,
          in_stock: snapshot.in_stock,
          sort: snapshot.sort,
          search_mode: data.search_mode,
        },
      }).catch(() => undefined)
    }
  } catch (cause) {
    if (sequence === productRequestSequence)
      error.value = cause instanceof Error ? cause.message : '商品加载失败'
  } finally {
    if (sequence === productRequestSequence) loading.value = false
  }
}

async function handleSuggestionSelect(suggestion: SearchSuggestion) {
  if (suggestion.kind !== 'product' || suggestion.product_id === null) return
  void recordSearchEvent({
    event_type: 'click',
    query: filters.keyword.trim() || suggestion.value,
    product_id: suggestion.product_id,
  }).catch(() => undefined)
  await router.push(`/products/${suggestion.product_id}`)
}

function applyFilters(query?: string) {
  if (typeof query === 'string') filters.keyword = query
  filters.page = 1
  void loadProducts()
}

function resetFilters() {
  Object.assign(filters, {
    keyword: '',
    category_id: undefined,
    brand_id: undefined,
    min_price: undefined,
    max_price: undefined,
    in_stock: false,
    sort: 'relevance' as ProductSearchSort,
    page: 1,
  })
  void loadProducts()
}

function changePage(page: number) {
  filters.page = page
  void loadProducts()
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

onMounted(async () => {
  try {
    await loadFilters()
  } catch {
    // Taxonomy failure does not prevent users from searching the product catalog.
  }
  await loadProducts()
})

watch(
  () => route.query,
  async (query) => {
    const next = {
      keyword: typeof query.keyword === 'string' ? query.keyword : '',
      category_id: queryNumber(query.category_id),
      brand_id: queryNumber(query.brand_id),
      min_price: queryNumber(query.min_price),
      max_price: queryNumber(query.max_price),
      in_stock: queryBoolean(query.in_stock),
      sort: querySort(query.sort),
      page: queryNumber(query.page) || 1,
    }
    if (
      next.keyword === filters.keyword
      && next.category_id === filters.category_id
      && next.brand_id === filters.brand_id
      && next.min_price === filters.min_price
      && next.max_price === filters.max_price
      && next.in_stock === filters.in_stock
      && next.sort === filters.sort
      && next.page === filters.page
    ) return
    Object.assign(filters, next)
    await loadProducts()
  },
)
</script>

<template>
  <div class="page-shell product-list-page">
    <header class="list-header">
      <div>
        <h1 class="page-heading">全部商品</h1>
        <p>支持自然语言、商品分类、品牌和价格组合查找。</p>
      </div>
      <div class="result-meta">
        <span v-if="searchMode === 'hybrid'" class="search-mode">智能混合搜索</span>
        <span class="result-count tabular">{{ total }} 件商品</span>
      </div>
    </header>

    <section class="filter-bar" aria-label="商品筛选">
      <div class="filter-title"><el-icon><Filter /></el-icon><strong>筛选</strong></div>
      <CatalogSearchBox
        v-model="filters.keyword"
        class="keyword-search"
        @search="applyFilters"
        @select="handleSuggestionSelect"
      />

      <el-select v-model="filters.category_id" clearable placeholder="全部分类" aria-label="商品分类">
        <el-option
          v-for="item in categories"
          :key="item.id"
          :label="`${item.name}${categoryFacetCounts.has(item.id) ? ` (${categoryFacetCounts.get(item.id)})` : ''}`"
          :value="item.id"
        />
      </el-select>
      <el-select v-model="filters.brand_id" clearable placeholder="全部品牌" aria-label="商品品牌">
        <el-option
          v-for="item in brands"
          :key="item.id"
          :label="`${item.name}${brandFacetCounts.has(item.id) ? ` (${brandFacetCounts.get(item.id)})` : ''}`"
          :value="item.id"
        />
      </el-select>

      <div class="price-range" aria-label="价格区间">
        <el-input-number v-model="filters.min_price" :min="0" :controls="false" placeholder="最低价" />
        <span>—</span>
        <el-input-number v-model="filters.max_price" :min="0" :controls="false" placeholder="最高价" />
      </div>

      <el-select v-model="filters.sort" aria-label="商品排序">
        <el-option label="综合相关度" value="relevance" />
        <el-option label="最新上架" value="newest" />
        <el-option label="销量优先" value="sales" />
        <el-option label="评分优先" value="rating" />
        <el-option label="价格从低到高" value="price_asc" />
        <el-option label="价格从高到低" value="price_desc" />
      </el-select>

      <el-checkbox v-model="filters.in_stock">仅看有货</el-checkbox>
      <div class="filter-actions">
        <el-button @click="resetFilters">重置</el-button>
        <el-button type="primary" @click="applyFilters()">查看结果</el-button>
      </div>
    </section>

    <div v-if="loading" class="product-grid" aria-label="商品加载中">
      <el-skeleton v-for="item in 8" :key="item" animated>
        <template #template>
          <el-skeleton-item variant="image" class="skeleton-image" />
          <el-skeleton-item variant="h3" style="width: 68%; margin-top: 16px" />
          <el-skeleton-item variant="text" style="width: 88%; margin-top: 12px" />
        </template>
      </el-skeleton>
    </div>
    <StatePanel
      v-else-if="error"
      title="商品读取失败"
      description="商品列表暂时不可用，请稍后再试。"
      action-label="重新加载"
      @action="loadProducts"
    />
    <StatePanel
      v-else-if="!products.length"
      title="没有找到符合条件的商品"
      description="可缩短关键词、取消部分筛选，或使用用途描述重新搜索。"
      action-label="清空筛选并查看全部商品"
      @action="resetFilters"
    />
    <div v-else class="product-grid">
      <ProductCard
        v-for="product in products"
        :key="product.id"
        :product="product"
        :category-name="categoryNames.get(product.category_id)"
        :brand-name="product.brand_id ? brandNames.get(product.brand_id) : undefined"
      />
    </div>

    <el-pagination
      v-if="total > filters.page_size"
      class="pagination"
      background
      layout="prev, pager, next"
      :current-page="filters.page"
      :page-size="filters.page_size"
      :total="total"
      @current-change="changePage"
    />
  </div>
</template>

<style scoped>
.product-list-page {
  min-height: 70vh;
  padding-top: 48px;
}

.list-header,
.result-meta,
.filter-title,
.price-range,
.filter-actions {
  display: flex;
  align-items: center;
}

.list-header {
  justify-content: space-between;
  gap: 24px;
}

.list-header p {
  margin: 10px 0 0;
  color: var(--color-ink-500);
  line-height: 1.65;
}

.result-meta {
  gap: 10px;
}

.result-count {
  color: var(--color-ink-500);
  font-size: 14px;
}

.search-mode {
  border-radius: 999px;
  padding: 5px 9px;
  color: var(--el-color-primary);
  background: rgb(37 99 235 / 9%);
  font-size: 12px;
  font-weight: 700;
}

.filter-bar {
  display: grid;
  grid-template-columns: auto minmax(280px, 1.4fr) minmax(140px, 0.7fr) minmax(140px, 0.7fr);
  gap: 12px;
  margin: 26px 0 34px;
  padding: 16px;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-container);
  background: var(--color-surface);
  box-shadow: 0 8px 24px rgb(38 55 82 / 5%);
}

.filter-title {
  gap: 8px;
  padding: 0 8px;
  color: var(--color-ink-700);
}

.keyword-search {
  min-width: 0;
}

.price-range {
  grid-column: 2 / 3;
  gap: 8px;
}

.price-range :deep(.el-input-number) {
  width: 100%;
}

.filter-actions {
  justify-content: flex-end;
  gap: 8px;
}

.product-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 30px 18px;
}

.skeleton-image {
  width: 100%;
  height: auto;
  aspect-ratio: 1;
  border-radius: 12px;
}

.pagination {
  justify-content: center;
  margin-top: 40px;
}

@media (max-width: 1023px) {
  .filter-bar {
    grid-template-columns: 1fr 1fr;
  }

  .filter-title,
  .keyword-search,
  .price-range {
    grid-column: 1 / -1;
  }

  .product-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

@media (max-width: 767px) {
  .product-list-page {
    padding-top: 32px;
  }

  .list-header {
    align-items: flex-start;
    flex-direction: column;
  }

  .filter-bar {
    grid-template-columns: 1fr;
  }

  .filter-title,
  .keyword-search,
  .price-range {
    grid-column: auto;
  }

  .filter-actions {
    justify-content: stretch;
  }

  .filter-actions :deep(.el-button) {
    flex: 1;
  }

  .product-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 24px 12px;
  }
}
</style>
