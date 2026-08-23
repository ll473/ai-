import { beforeEach, describe, expect, it } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

import { useCompareStore } from './compare'
import type { ProductSummary } from '../types/catalog'

function summary(id: number, categoryId: number): ProductSummary {
  return {
    id,
    category_id: categoryId,
    brand_id: null,
    name: `商品 ${id}`,
    subtitle: null,
    product_no: `P-${id}`,
    main_image_url: null,
    min_price: '1.00',
    max_price: '1.00',
    rating: '0.00',
    review_count: 0,
    sales_count: 0,
    status: 'ON_SALE',
    created_at: '2026-01-01T00:00:00Z',
  }
}

describe('useCompareStore', () => {
  beforeEach(() => {
    localStorage.clear()
    setActivePinia(createPinia())
  })

  it('keeps at most four unique products from one category', () => {
    const store = useCompareStore()

    expect(store.add(summary(1, 10))).toEqual({ ok: true })
    expect(store.add(summary(1, 10))).toEqual({ ok: true })
    expect(store.add(summary(2, 11))).toEqual({ ok: false, reason: 'category_mismatch' })
    store.add(summary(3, 10))
    store.add(summary(4, 10))
    store.add(summary(5, 10))
    expect(store.add(summary(6, 10))).toEqual({ ok: false, reason: 'limit_reached' })
    expect(store.ids).toEqual([1, 3, 4, 5])
  })

  it('recovers from malformed persisted state', () => {
    localStorage.setItem('ai-commerce-product-compare-v1', '{broken')

    const store = useCompareStore()

    expect(store.items).toEqual([])
    expect(localStorage.getItem('ai-commerce-product-compare-v1')).toBeNull()
  })
})
