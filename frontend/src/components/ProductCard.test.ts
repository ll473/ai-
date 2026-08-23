import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import ProductCard from './ProductCard.vue'
import { useCompareStore } from '../stores/compare'
import type { ProductSummary } from '../types/catalog'

const routerPush = vi.fn()

const product: ProductSummary = {
  id: 42,
  category_id: 7,
  brand_id: null,
  name: '人体工学椅',
  subtitle: '适合长时间办公',
  product_no: 'CHAIR-42',
  main_image_url: null,
  min_price: '1299.00',
  max_price: '1299.00',
  rating: '5.00',
  review_count: 0,
  sales_count: 10,
  status: 'ON_SALE',
  created_at: '2026-01-01T00:00:00Z',
}

describe('ProductCard product comparison entry', () => {
  beforeEach(() => {
    localStorage.clear()
    setActivePinia(createPinia())
    routerPush.mockReset()
  })

  it('adds a product to comparison without triggering product navigation', async () => {
    const compare = useCompareStore()
    const wrapper = mount(ProductCard, {
      props: { product },
      global: {
        stubs: {
          RouterLink: {
            emits: ['click'],
            template: '<a class="product-link" @click="routerPush"><slot /></a>',
            methods: { routerPush },
          },
          ElIcon: { template: '<span><slot /></span>' },
        },
      },
    })

    await wrapper.get('button[aria-label="加入商品对比"]').trigger('click')

    expect(compare.ids).toEqual([42])
    expect(routerPush).not.toHaveBeenCalled()
    expect(wrapper.get('button').text()).toContain('已加入对比')
  })
})
