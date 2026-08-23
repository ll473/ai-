<script setup lang="ts">
import { ArrowRight, MagicStick, Search } from '@element-plus/icons-vue'
import { computed, onMounted, reactive, ref } from 'vue'

import { getBrands, getCategories, getProducts } from '../../api/catalog'
import ProductCard from '../../components/ProductCard.vue'
import StatePanel from '../../components/StatePanel.vue'
import { demoMode } from '../../demo/config'
import type { Brand, Category, ProductSummary } from '../../types/catalog'

const products = ref<ProductSummary[]>([])
const categories = ref<Category[]>([])
const brands = ref<Brand[]>([])
const total = ref(0)
const loading = ref(true)
const error = ref('')
const filters = reactive({
  keyword: '',
  category_id: undefined as number | undefined,
  brand_id: undefined as number | undefined,
})

const categoryNames = computed(() => new Map(categories.value.map((item) => [item.id, item.name])))
const brandNames = computed(() => new Map(brands.value.map((item) => [item.id, item.name])))
const allProductsQuery = computed(() => ({
  ...(filters.keyword ? { keyword: filters.keyword } : {}),
  ...(filters.category_id ? { category_id: filters.category_id } : {}),
  ...(filters.brand_id ? { brand_id: filters.brand_id } : {}),
}))

async function loadProducts() {
  loading.value = true
  error.value = ''
  try {
    const data = await getProducts({
      page: 1,
      page_size: 12,
      keyword: filters.keyword.trim() || undefined,
      category_id: filters.category_id,
      brand_id: filters.brand_id,
    })
    products.value = data.items
    total.value = data.total
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : '商品加载失败'
  } finally {
    loading.value = false
  }
}

function selectCategory(categoryId?: number) {
  if (filters.category_id === categoryId) return
  filters.category_id = categoryId
  loadProducts()
}

function applyFilters() {
  loadProducts()
}

onMounted(async () => {
  const taxonomy = Promise.all([getCategories(), getBrands()])
    .then(([categoryData, brandData]) => {
      categories.value = categoryData
      brands.value = brandData
    })
    .catch(() => {
      categories.value = []
      brands.value = []
    })

  await Promise.all([taxonomy, loadProducts()])
})
</script>

<template>
  <div class="home-view">
    <div class="page-shell home-shell">
      <section class="campaign-banner" aria-labelledby="campaign-title">
        <div>
          <h1 id="campaign-title">好物精选，安心选购</h1>
          <div class="campaign-benefits" aria-label="购物特点">
            <span>价格清楚</span>
            <span>库存可见</span>
            <span>订单可查</span>
          </div>
        </div>
        <RouterLink v-if="!demoMode" to="/ai-guide" class="campaign-action focus-ring">
          <el-icon><MagicStick /></el-icon>
          <span>不知道怎么选？让购物助手帮你</span>
          <el-icon><ArrowRight /></el-icon>
        </RouterLink>
      </section>

      <section class="category-panel" aria-label="商品分类">
        <button
          type="button"
          :class="{ 'is-active': filters.category_id === undefined }"
          @click="selectCategory()"
        >
          全部商品
        </button>
        <button
          v-for="category in categories"
          :key="category.id"
          type="button"
          :class="{ 'is-active': filters.category_id === category.id }"
          @click="selectCategory(category.id)"
        >
          {{ category.name }}
        </button>
      </section>

      <section class="search-panel" aria-label="搜索与筛选">
        <el-input
          v-model="filters.keyword"
          size="large"
          clearable
          placeholder="搜索商品名称、卖点或标签"
          aria-label="商品关键词"
          @keyup.enter="applyFilters"
        >
          <template #prefix><el-icon><Search /></el-icon></template>
        </el-input>
        <el-select
          v-model="filters.brand_id"
          size="large"
          clearable
          placeholder="全部品牌"
          aria-label="商品品牌"
          @change="applyFilters"
        >
          <el-option v-for="brand in brands" :key="brand.id" :label="brand.name" :value="brand.id" />
        </el-select>
        <el-button type="primary" size="large" @click="applyFilters">搜索</el-button>
      </section>

      <section class="product-section" aria-labelledby="products-title">
        <div class="product-section__header">
          <div>
            <h2 id="products-title">精选商品</h2>
            <span v-if="!loading" class="result-count tabular">找到 {{ total }} 件商品</span>
          </div>
          <RouterLink :to="{ name: 'products', query: allProductsQuery }" class="all-link">
            查看全部 <el-icon><ArrowRight /></el-icon>
          </RouterLink>
        </div>

        <div v-if="loading" class="product-grid" aria-label="商品加载中">
          <el-skeleton v-for="item in 8" :key="item" animated>
            <template #template>
              <el-skeleton-item variant="image" class="skeleton-image" />
              <el-skeleton-item variant="h3" style="width: 72%; margin: 16px 16px 0" />
              <el-skeleton-item variant="text" style="width: 82%; margin: 10px 16px 0" />
            </template>
          </el-skeleton>
        </div>
        <StatePanel
          v-else-if="error"
          title="暂时无法读取商品"
          description="商品列表暂时不可用，请稍后再试。"
          action-label="重新加载"
          @action="loadProducts"
        />
        <StatePanel
          v-else-if="!products.length"
          title="没有找到符合条件的商品"
          description="换个关键词、分类或品牌再试试。"
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
      </section>
    </div>
  </div>
</template>

<style scoped>
.home-view {
  min-height: 70vh;
  padding: 26px 0 0;
}

.home-shell {
  display: grid;
  gap: 16px;
}

.campaign-banner {
  display: flex;
  min-height: 154px;
  align-items: center;
  justify-content: space-between;
  gap: 36px;
  padding: 30px 38px;
  overflow: hidden;
  border: 1px solid rgb(218 89 67 / 32%);
  border-radius: var(--radius-container);
  background: linear-gradient(105deg, #ee6558 0%, #ef8464 100%);
  color: #fffaf7;
  box-shadow: 0 12px 30px rgb(183 76 55 / 12%);
}

.campaign-banner h1 {
  margin: 0;
  font-size: clamp(1.8rem, 3vw, 2.55rem);
  font-weight: 760;
  letter-spacing: -0.04em;
  line-height: 1.18;
}

.campaign-benefits {
  display: flex;
  align-items: center;
  margin-top: 14px;
  color: rgb(255 250 247 / 88%);
  font-size: 14px;
}

.campaign-benefits span {
  display: inline-flex;
  align-items: center;
}

.campaign-benefits span + span::before {
  width: 1px;
  height: 13px;
  margin: 0 12px;
  background: rgb(255 250 247 / 42%);
  content: '';
}

.campaign-action {
  display: inline-flex;
  min-height: 44px;
  flex: 0 0 auto;
  align-items: center;
  gap: 8px;
  padding: 0 17px;
  border: 1px solid rgb(255 250 247 / 68%);
  border-radius: var(--radius-control);
  background: #fffaf7;
  color: #b54239;
  font-size: 14px;
  font-weight: 700;
  white-space: nowrap;
  transition: transform 160ms ease, box-shadow 160ms ease;
}

.campaign-action:hover {
  transform: translateY(-2px);
  box-shadow: 0 10px 24px rgb(112 46 37 / 20%);
}

.category-panel {
  display: flex;
  flex-wrap: wrap;
  gap: 9px 14px;
  padding: 14px 16px;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-container);
  background: var(--color-surface);
}

.category-panel button {
  min-height: 34px;
  padding: 0 15px;
  border: 1px solid transparent;
  border-radius: var(--radius-control);
  background: transparent;
  color: var(--color-ink-700);
  cursor: pointer;
  font-size: 13px;
  font-weight: 600;
  transition: color 150ms ease, background-color 150ms ease, border-color 150ms ease;
}

.category-panel button:hover {
  color: var(--color-brand-700);
  background: var(--color-brand-50);
}

.category-panel button.is-active {
  border-color: var(--color-brand-600);
  background: var(--color-brand-600);
  color: #f8fbff;
}

.search-panel {
  display: grid;
  grid-template-columns: minmax(260px, 1fr) minmax(150px, 220px) auto;
  gap: 12px;
  padding: 14px 16px;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-container);
  background: var(--color-surface);
  box-shadow: 0 8px 24px rgb(38 55 82 / 4%);
}

.search-panel .el-button {
  min-width: 88px;
}

.product-section {
  padding-top: 16px;
}

.product-section__header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 24px;
  margin-bottom: 18px;
}

.product-section__header > div {
  display: flex;
  align-items: baseline;
  gap: 12px;
}

.product-section h2 {
  margin: 0;
  font-size: clamp(1.45rem, 2.3vw, 2rem);
  letter-spacing: -0.035em;
}

.result-count {
  color: var(--color-ink-500);
  font-size: 13px;
}

.all-link {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  color: var(--color-brand-600);
  font-size: 14px;
  font-weight: 680;
}

.all-link .el-icon {
  transition: transform 160ms ease;
}

.all-link:hover .el-icon {
  transform: translateX(3px);
}

.product-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 18px;
}

.skeleton-image {
  width: 100%;
  height: auto;
  aspect-ratio: 1.34;
  border-radius: var(--radius-container) var(--radius-container) 0 0;
}

@media (prefers-color-scheme: dark) {
  .campaign-banner {
    border-color: rgb(239 132 100 / 38%);
    background: linear-gradient(105deg, #743f3b 0%, #795042 100%);
    box-shadow: none;
  }

  .campaign-action {
    border-color: rgb(255 246 240 / 72%);
    background: #f8eee9;
    color: #71312d;
  }
}

@media (max-width: 1023px) {
  .product-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

@media (max-width: 767px) {
  .home-view {
    padding-top: 14px;
  }

  .home-shell {
    gap: 12px;
  }

  .campaign-banner {
    min-height: auto;
    align-items: flex-start;
    flex-direction: column;
    gap: 22px;
    padding: 24px 20px;
  }

  .campaign-banner h1 {
    font-size: 1.75rem;
  }

  .campaign-action {
    width: 100%;
    justify-content: center;
    white-space: normal;
  }

  .category-panel {
    overflow-x: auto;
    flex-wrap: nowrap;
    padding: 10px;
  }

  .category-panel button {
    flex: 0 0 auto;
  }

  .search-panel {
    grid-template-columns: minmax(0, 1fr) auto;
    padding: 10px;
  }

  .search-panel .el-select {
    grid-column: 1 / -1;
    grid-row: 2;
  }

  .product-section {
    padding-top: 10px;
  }

  .product-section__header > div {
    display: grid;
    gap: 4px;
  }

  .product-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 12px;
  }
}
</style>
