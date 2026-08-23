<script setup lang="ts">
import { ElMessage } from 'element-plus'

import { useCompareStore } from '../../stores/compare'
import type { ProductSummary } from '../../types/catalog'

const props = withDefaults(defineProps<{
  product: ProductSummary
  compact?: boolean
}>(), {
  compact: false,
})

const compare = useCompareStore()

function toggle() {
  if (compare.contains(props.product.id)) {
    compare.remove(props.product.id)
    return
  }

  const result = compare.add(props.product)
  if (!result.ok) {
    ElMessage.warning(result.reason === 'category_mismatch'
      ? '只能对比同一分类商品，请先清空当前对比'
      : '最多只能同时对比 4 件商品')
  }
}
</script>

<template>
  <button
    class="compare-toggle-button focus-ring"
    :class="{ 'compare-toggle-button--compact': compact, 'is-selected': compare.contains(product.id) }"
    type="button"
    :aria-label="compare.contains(product.id) ? '移除商品对比' : '加入商品对比'"
    @click="toggle"
  >
    {{ compare.contains(product.id) ? '已加入对比' : (compact ? '对比' : '加入对比') }}
  </button>
</template>

<style scoped>
.compare-toggle-button {
  min-height: 36px;
  padding: 0 12px;
  border: 1px solid var(--color-brand-200);
  border-radius: var(--radius-control);
  background: var(--color-surface);
  color: var(--color-brand-700);
  cursor: pointer;
  font-size: 13px;
  font-weight: 650;
  transition: border-color 160ms ease, background-color 160ms ease, color 160ms ease;
}

.compare-toggle-button:hover,
.compare-toggle-button.is-selected {
  border-color: var(--color-brand-600);
  background: var(--color-brand-50);
  color: var(--color-brand-700);
}

.compare-toggle-button--compact {
  min-height: 32px;
  padding: 0 10px;
  font-size: 12px;
}
</style>
