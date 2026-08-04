<script setup lang="ts">
import { Filter, Search } from '@element-plus/icons-vue'
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { getBrands, getCategories, getProducts } from '../../api/catalog'
import ProductCard from '../../components/ProductCard.vue'
import StatePanel from '../../components/StatePanel.vue'
import type { Brand, Category, ProductSummary } from '../../types/catalog'

const route = useRoute()
const router = useRouter()
const products = ref<ProductSummary[]>([])
const categories = ref<Category[]>([])
const brands = ref<Brand[]>([])
const total = ref(0)
const loading = ref(true)
const error = ref('')
const categoryNames = computed(() => new Map(categories.value.map((item) => [item.id, item.name])))
const brandNames = computed(() => new Map(brands.value.map((item) => [item.id, item.name])))
const filters = reactive({
  keyword: typeof route.query.keyword === 'string' ? route.query.keyword : '',
  category_id: Number(route.query.category_id) || undefined,
  brand_id: Number(route.query.brand_id) || undefined,
  page: Number(route.query.page) || 1,
  page_size: 12,
})

async function loadFilters() {
  const [categoryData, brandData] = await Promise.all([getCategories(), getBrands()])
  categories.value = categoryData
  brands.value = brandData
}

async function loadProducts() {
  loading.value = true
  error.value = ''
  try {
    const data = await getProducts({
      page: filters.page,
      page_size: filters.page_size,
      keyword: filters.keyword || undefined,
      category_id: filters.category_id,
      brand_id: filters.brand_id,
    })
    products.value = data.items
    total.value = data.total
    await router.replace({
      query: {
        ...(filters.keyword ? { keyword: filters.keyword } : {}),
        ...(filters.category_id ? { category_id: filters.category_id } : {}),
        ...(filters.brand_id ? { brand_id: filters.brand_id } : {}),
        ...(filters.page > 1 ? { page: filters.page } : {}),
      },
    })
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : '商品加载失败'
  } finally {
    loading.value = false
  }
}

function applyFilters() {
  filters.page = 1
  loadProducts()
}

function changePage(page: number) {
  filters.page = page
  loadProducts()
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

onMounted(async () => {
  try {
    await loadFilters()
  } catch {
    // Product loading still provides a useful page when taxonomy is temporarily unavailable.
  }
  await loadProducts()
})
</script>

<template>
  <div class="page-shell product-list-page">
    <header class="list-header">
      <div>
        <h1 class="page-heading">全部商品</h1>
        <p>从日常好物中，找到更适合你的那一件。</p>
      </div>
      <span class="result-count tabular">{{ total }} 件商品</span>
    </header>

    <section class="filter-bar" aria-label="商品筛选">
      <div class="filter-title"><el-icon><Filter /></el-icon><strong>筛选</strong></div>
      <el-input
        v-model="filters.keyword"
        clearable
        placeholder="输入商品关键词"
        aria-label="商品关键词"
        @keyup.enter="applyFilters"
      >
        <template #prefix><el-icon><Search /></el-icon></template>
      </el-input>
      <el-select v-model="filters.category_id" clearable placeholder="全部分类" aria-label="商品分类">
        <el-option v-for="item in categories" :key="item.id" :label="item.name" :value="item.id" />
      </el-select>
      <el-select v-model="filters.brand_id" clearable placeholder="全部品牌" aria-label="商品品牌">
        <el-option v-for="item in brands" :key="item.id" :label="item.name" :value="item.id" />
      </el-select>
      <el-button type="primary" @click="applyFilters">查看结果</el-button>
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
      description="调整关键词、分类或品牌后重新查询。"
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

.list-header {
  display: flex;
  align-items: end;
  justify-content: space-between;
  gap: 24px;
}

.list-header p {
  margin: 10px 0 0;
  color: var(--color-ink-500);
  line-height: 1.65;
}

.result-count {
  color: var(--color-ink-500);
  font-size: 14px;
}

.filter-bar {
  display: grid;
  grid-template-columns: auto minmax(220px, 1fr) minmax(150px, 220px) minmax(150px, 220px) auto;
  gap: 12px;
  margin: 26px 0 34px;
  padding: 14px;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-container);
  background: var(--color-surface);
  box-shadow: 0 8px 24px rgb(38 55 82 / 5%);
}

.filter-title {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 0 8px;
  color: var(--color-ink-700);
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

  .filter-title {
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

  .filter-bar {
    grid-template-columns: 1fr;
  }

  .filter-title {
    grid-column: auto;
  }

  .product-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 24px 12px;
  }
}
</style>
