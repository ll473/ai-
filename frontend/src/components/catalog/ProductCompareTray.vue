<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { useCompareStore } from '../../stores/compare'

const route = useRoute()
const router = useRouter()
const compare = useCompareStore()

const canCompare = computed(() => compare.ids.length >= 2)
const isVisible = computed(() => compare.items.length > 0 && route.name !== 'product-comparison')

function openComparison() {
  if (!canCompare.value) return
  void router.push({ path: '/compare', query: { ids: compare.ids.join(',') } })
}
</script>

<template>
  <section v-if="isVisible" data-testid="product-compare-tray" class="product-compare-tray" aria-label="商品对比清单">
    <div class="product-compare-tray__inner">
      <div class="product-compare-tray__summary">
        <strong>商品对比</strong>
        <span>已选 {{ compare.items.length }} 件商品</span>
      </div>

      <div class="product-compare-tray__items" aria-label="已选商品">
        <div v-for="item in compare.items" :key="item.id" class="product-compare-tray__item">
          <img v-if="item.main_image_url" :src="item.main_image_url" :alt="item.name" />
          <span>{{ item.name }}</span>
          <button type="button" :aria-label="`移除商品 ${item.id}`" @click="compare.remove(item.id)">移除</button>
        </div>
      </div>

      <div class="product-compare-tray__actions">
        <button type="button" aria-label="清空商品对比" class="clear-button" @click="compare.clear">清空</button>
        <button
          type="button"
          aria-label="开始商品对比"
          class="start-button focus-ring"
          :disabled="!canCompare"
          @click="openComparison"
        >
          开始对比
        </button>
      </div>
    </div>
  </section>
</template>

<style scoped>
.product-compare-tray {
  position: fixed;
  z-index: 40;
  right: 16px;
  bottom: max(16px, env(safe-area-inset-bottom));
  left: 16px;
  pointer-events: none;
}

.product-compare-tray__inner {
  display: flex;
  width: min(100%, 1120px);
  min-height: 72px;
  align-items: center;
  gap: 18px;
  margin: 0 auto;
  padding: 12px 14px;
  border: 1px solid color-mix(in srgb, var(--color-brand-600) 25%, var(--color-line));
  border-radius: var(--radius-container);
  background: color-mix(in srgb, var(--color-surface) 96%, transparent);
  box-shadow: 0 16px 44px rgb(18 45 88 / 18%);
  backdrop-filter: blur(14px);
  pointer-events: auto;
}

.product-compare-tray__summary {
  display: grid;
  flex: 0 0 auto;
  gap: 3px;
}

.product-compare-tray__summary strong {
  color: var(--color-ink-950);
  font-size: 14px;
}

.product-compare-tray__summary span {
  color: var(--color-ink-500);
  font-size: 12px;
}

.product-compare-tray__items {
  display: flex;
  min-width: 0;
  flex: 1;
  gap: 8px;
  overflow-x: auto;
  padding-bottom: 1px;
}

.product-compare-tray__item {
  display: flex;
  min-width: 150px;
  max-width: 210px;
  align-items: center;
  gap: 7px;
  padding: 7px 8px;
  border-radius: 8px;
  background: var(--color-surface-soft);
}

.product-compare-tray__item img {
  width: 28px;
  height: 28px;
  flex: 0 0 auto;
  border-radius: 5px;
  object-fit: cover;
}

.product-compare-tray__item span {
  overflow: hidden;
  flex: 1;
  color: var(--color-ink-700);
  font-size: 12px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.product-compare-tray__item button,
.clear-button {
  border: 0;
  background: transparent;
  color: var(--color-ink-500);
  cursor: pointer;
  font-size: 12px;
  white-space: nowrap;
}

.product-compare-tray__actions {
  display: flex;
  flex: 0 0 auto;
  align-items: center;
  gap: 10px;
}

.start-button {
  min-height: 36px;
  padding: 0 15px;
  border: 1px solid var(--color-brand-600);
  border-radius: var(--radius-control);
  background: var(--color-brand-600);
  color: #fff;
  cursor: pointer;
  font-size: 13px;
  font-weight: 700;
}

.start-button:disabled {
  border-color: var(--color-line);
  background: var(--color-surface-soft);
  color: var(--color-ink-400);
  cursor: not-allowed;
}

@media (max-width: 720px) {
  .product-compare-tray {
    right: 8px;
    bottom: max(8px, env(safe-area-inset-bottom));
    left: 8px;
  }

  .product-compare-tray__inner {
    gap: 10px;
    padding: 10px;
  }

  .product-compare-tray__summary {
    display: none;
  }

  .product-compare-tray__item {
    min-width: 130px;
  }

  .clear-button {
    display: none;
  }
}
</style>
