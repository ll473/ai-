import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { reactive } from 'vue'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import ProductCompareTray from './ProductCompareTray.vue'
import { useCompareStore } from '../../stores/compare'
import type { ProductSummary } from '../../types/catalog'

const routerPush = vi.fn()
const route = reactive({ name: 'products' })

vi.mock('vue-router', () => ({
  useRoute: () => route,
  useRouter: () => ({ push: routerPush }),
}))

function product(id: number): ProductSummary {
  return {
    id,
    category_id: 7,
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

function mountTray() {
  return mount(ProductCompareTray, {
    global: {
      stubs: {
        ElIcon: { template: '<span><slot /></span>' },
      },
    },
  })
}

describe('ProductCompareTray', () => {
  beforeEach(() => {
    localStorage.clear()
    setActivePinia(createPinia())
    route.name = 'products'
    routerPush.mockReset()
  })

  it('shows after one item and only opens comparison after a second item', async () => {
    const compare = useCompareStore()
    compare.add(product(1))
    const wrapper = mountTray()

    expect(wrapper.text()).toContain('已选 1 件商品')
    expect(wrapper.get('button[aria-label="开始商品对比"]').attributes('disabled')).toBeDefined()

    compare.add(product(2))
    await wrapper.vm.$nextTick()
    await wrapper.get('button[aria-label="开始商品对比"]').trigger('click')

    expect(routerPush).toHaveBeenCalledWith({ path: '/compare', query: { ids: '1,2' } })
  })

  it('removes and clears selections, and hides on the comparison page', async () => {
    const compare = useCompareStore()
    compare.add(product(1))
    compare.add(product(2))
    const wrapper = mountTray()

    await wrapper.get('button[aria-label="移除商品 1"]').trigger('click')
    expect(compare.ids).toEqual([2])

    await wrapper.get('button[aria-label="清空商品对比"]').trigger('click')
    expect(compare.ids).toEqual([])

    compare.add(product(3))
    route.name = 'product-comparison'
    await wrapper.vm.$nextTick()
    expect(wrapper.find('[data-testid="product-compare-tray"]').exists()).toBe(false)
  })
})
