<script setup lang="ts">
import { Delete, Star } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { computed, onMounted, ref } from 'vue'

import { getBrands, getCategories } from '../../api/catalog'
import { getFavorites, removeFavorite } from '../../api/trade'
import ProductCard from '../../components/ProductCard.vue'
import StatePanel from '../../components/StatePanel.vue'
import type { Brand, Category, ProductSummary } from '../../types/catalog'

const products = ref<ProductSummary[]>([])
const categories = ref<Category[]>([])
const brands = ref<Brand[]>([])
const total = ref(0)
const loading = ref(true)
const removingId = ref<number | null>(null)
const error = ref('')

const categoryNames = computed(() => new Map(categories.value.map((item) => [item.id, item.name])))
const brandNames = computed(() => new Map(brands.value.map((item) => [item.id, item.name])))

async function loadFavorites() {
  loading.value = true
  error.value = ''
  try {
    const [favoriteData, categoryData, brandData] = await Promise.all([
      getFavorites(1, 50),
      getCategories(),
      getBrands(),
    ])
    products.value = favoriteData.items
    total.value = favoriteData.total
    categories.value = categoryData
    brands.value = brandData
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : '收藏加载失败'
  } finally {
    loading.value = false
  }
}

async function remove(product: ProductSummary) {
  removingId.value = product.id
  try {
    await removeFavorite(product.id)
    products.value = products.value.filter((item) => item.id !== product.id)
    total.value = Math.max(0, total.value - 1)
    ElMessage.success('已取消收藏')
  } catch {
    ElMessage.error('暂时无法取消收藏，请稍后再试')
  } finally {
    removingId.value = null
  }
}

onMounted(loadFavorites)
</script>

<template>
  <div class="page-shell favorites-page">
    <header class="favorites-header">
      <div>
        <div class="title-line"><el-icon><Star /></el-icon><h1>我的收藏</h1></div>
        <p>把感兴趣的商品放在一起，比较后再决定。</p>
      </div>
      <span v-if="!loading" class="tabular">{{ total }} 件商品</span>
    </header>

    <div v-if="loading" class="favorites-grid" aria-label="收藏加载中">
      <el-skeleton v-for="item in 4" :key="item" animated>
        <template #template>
          <el-skeleton-item variant="image" class="skeleton-image" />
          <el-skeleton-item variant="h3" style="width: 70%; margin-top: 14px" />
          <el-skeleton-item variant="text" style="width: 88%; margin-top: 10px" />
        </template>
      </el-skeleton>
    </div>
    <StatePanel
      v-else-if="error"
      title="暂时无法读取收藏"
      description="请稍后再试。"
      action-label="重新加载"
      @action="loadFavorites"
    />
    <StatePanel
      v-else-if="!products.length"
      title="还没有收藏商品"
      description="浏览商品详情时，可以把喜欢的商品加入收藏。"
      action-label="去逛商品"
      @action="$router.push('/products')"
    />
    <div v-else class="favorites-grid">
      <article v-for="product in products" :key="product.id" class="favorite-item">
        <ProductCard
          :product="product"
          :category-name="categoryNames.get(product.category_id)"
          :brand-name="product.brand_id ? brandNames.get(product.brand_id) : undefined"
        />
        <el-button
          text
          :icon="Delete"
          :loading="removingId === product.id"
          @click="remove(product)"
        >
          取消收藏
        </el-button>
      </article>
    </div>
  </div>
</template>

<style scoped>
.favorites-page {
  min-height: 70vh;
  padding-top: 42px;
}

.favorites-header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 24px;
  margin-bottom: 28px;
}

.title-line {
  display: flex;
  align-items: center;
  gap: 10px;
}

.title-line .el-icon {
  color: var(--color-brand-600);
  font-size: 24px;
}

.favorites-header h1,
.favorites-header p {
  margin: 0;
}

.favorites-header h1 {
  font-size: clamp(1.9rem, 3vw, 2.7rem);
  letter-spacing: -0.04em;
}

.favorites-header p {
  margin-top: 9px;
  color: var(--color-ink-500);
}

.favorites-header > span {
  color: var(--color-ink-500);
  font-size: 13px;
}

.favorites-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 22px 18px;
}

.favorite-item {
  display: grid;
  align-content: start;
  gap: 4px;
}

.favorite-item .el-button {
  justify-self: end;
  color: var(--color-ink-500);
}

.skeleton-image {
  width: 100%;
  height: auto;
  aspect-ratio: 1.34;
  border-radius: var(--radius-container);
}

@media (max-width: 1023px) {
  .favorites-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

@media (max-width: 767px) {
  .favorites-page {
    padding-top: 28px;
  }

  .favorites-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 16px 12px;
  }
}
</style>
