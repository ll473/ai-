<script setup lang="ts">
import { Picture } from '@element-plus/icons-vue'

import type { ProductSummary } from '../types/catalog'

defineProps<{
  product: ProductSummary
  categoryName?: string
  brandName?: string
}>()

const formatPrice = (value: string) => Number(value).toLocaleString('zh-CN', {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
})
</script>

<template>
  <RouterLink :to="`/products/${product.id}`" class="product-card focus-ring">
    <div class="product-card__media">
      <img
        v-if="product.main_image_url"
        :src="product.main_image_url"
        :alt="product.name"
        loading="lazy"
      />
      <div v-else class="product-card__empty-image">
        <el-icon :size="30"><Picture /></el-icon>
        <span>暂无商品图片</span>
      </div>
    </div>
    <div class="product-card__body">
      <div v-if="product.sales_count > 0 || categoryName" class="product-card__tags">
        <span v-if="product.sales_count > 0" class="recommend-tag">推荐</span>
        <span v-if="categoryName">{{ categoryName }}</span>
      </div>
      <h3>{{ product.name }}</h3>
      <p>{{ product.subtitle || '查看商品规格与详细信息' }}</p>
      <div class="product-card__footer">
        <div>
          <span v-if="brandName" class="brand-name">{{ brandName }}</span>
          <div class="product-card__price">
            <strong class="tabular"><small>¥</small>{{ formatPrice(product.min_price) }}</strong>
            <span v-if="product.min_price !== product.max_price">起</span>
          </div>
        </div>
        <div class="product-card__meta">
          <span v-if="Number(product.rating) > 0"><strong>{{ product.rating }}</strong> 分</span>
          <span>{{ product.sales_count }} 人买过</span>
        </div>
      </div>
    </div>
  </RouterLink>
</template>

<style scoped>
.product-card {
  display: flex;
  min-width: 0;
  min-height: 100%;
  overflow: hidden;
  flex-direction: column;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-container);
  background: var(--color-surface);
  transition: transform 180ms ease, border-color 180ms ease, box-shadow 180ms ease;
}

.product-card:hover {
  border-color: color-mix(in srgb, var(--color-brand-600) 38%, var(--color-line));
  box-shadow: var(--shadow-card);
  transform: translateY(-3px);
}

.product-card__media {
  aspect-ratio: 1.34;
  overflow: hidden;
  border-bottom: 1px solid var(--color-line);
  background: var(--color-surface-soft);
}

.product-card__media img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 360ms cubic-bezier(0.16, 1, 0.3, 1);
}

.product-card:hover .product-card__media img {
  transform: scale(1.025);
}

.product-card__empty-image {
  display: grid;
  height: 100%;
  place-items: center;
  align-content: center;
  gap: 10px;
  color: var(--color-ink-400);
  font-size: 13px;
}

.product-card__body {
  display: flex;
  min-height: 210px;
  flex: 1;
  flex-direction: column;
  padding: 14px 15px 15px;
}

.product-card__tags {
  display: flex;
  min-height: 24px;
  align-items: center;
  gap: 6px;
}

.product-card__tags span {
  padding: 3px 7px;
  border-radius: 5px;
  background: var(--color-surface-soft);
  color: var(--color-ink-500);
  font-size: 11px;
  line-height: 1.4;
}

.product-card__tags .recommend-tag {
  background: color-mix(in srgb, var(--color-success) 12%, var(--color-surface));
  color: var(--color-success);
}

h3,
p {
  margin: 0;
}

h3 {
  display: -webkit-box;
  overflow: hidden;
  min-height: 48px;
  margin-top: 8px;
  color: var(--color-ink-950);
  font-size: 15px;
  font-weight: 700;
  line-height: 1.55;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

p {
  display: -webkit-box;
  overflow: hidden;
  min-height: 40px;
  margin-top: 7px;
  color: var(--color-ink-500);
  font-size: 12px;
  line-height: 1.65;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.product-card__footer {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 10px;
  margin-top: auto;
  padding-top: 14px;
}

.brand-name {
  color: var(--color-ink-500);
  font-size: 11px;
}

.product-card__price {
  display: flex;
  align-items: baseline;
  gap: 4px;
  margin-top: 3px;
}

.product-card__price strong {
  color: var(--color-danger);
  font-size: 20px;
  letter-spacing: -0.025em;
}

.product-card__price small {
  margin-right: 2px;
  font-size: 12px;
}

.product-card__price > span,
.product-card__meta span {
  color: var(--color-ink-500);
  font-size: 10px;
}

.product-card__meta {
  display: grid;
  flex: 0 0 auto;
  gap: 4px;
  justify-items: end;
  padding-bottom: 2px;
}

.product-card__meta strong {
  color: var(--color-warning);
}

@media (max-width: 767px) {
  .product-card__body {
    min-height: 170px;
    padding: 10px;
  }

  .product-card__tags {
    overflow: hidden;
    white-space: nowrap;
  }

  h3 {
    min-height: 42px;
    margin-top: 6px;
    font-size: 13px;
  }

  p,
  .brand-name,
  .product-card__meta {
    display: none;
  }

  .product-card__footer {
    padding-top: 10px;
  }

  .product-card__price strong {
    font-size: 17px;
  }
}
</style>
