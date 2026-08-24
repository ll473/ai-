import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { reactive } from 'vue'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import ProductComparisonView from './ProductComparisonView.vue'
import { useCompareStore } from '../../stores/compare'
import type { ProductComparisonItem, ProductComparisonResult } from '../../types/catalog'

const mocks = vi.hoisted(() => ({
  getProductComparison: vi.fn(),
  replace: vi.fn(),
}))

const route = reactive({ query: { ids: '2,3' } as Record<string, unknown> })
const mountedWrappers: ReturnType<typeof mount>[] = []

vi.mock('../../api/catalog', () => ({
  getProductComparison: mocks.getProductComparison,
}))

vi.mock('vue-router', () => ({
  useRoute: () => route,
  useRouter: () => ({ replace: mocks.replace }),
}))

function product(id: number, parameters: Record<string, unknown> = {}): ProductComparisonItem {
  return {
    id,
    category_id: 2,
    category_name: '数码影音',
    brand_id: id === 2 ? 2 : 3,
    brand_name: id === 2 ? 'KeyNest' : 'EchoArc',
    name: `商品 ${id}`,
    subtitle: null,
    product_no: `P-${id}`,
    main_image_url: null,
    min_price: id === 2 ? '499.00' : '899.00',
    max_price: id === 2 ? '529.00' : '899.00',
    rating: '4.80',
    review_count: 20,
    sales_count: 30,
    status: 'ON_SALE',
    created_at: '2026-01-01T00:00:00Z',
    parameters,
    skus: [{
      id: id * 10,
      product_id: id,
      sku_no: `SKU-${id}`,
      name: '标准款',
      attributes: id === 2 ? { 配色: '黑色' } : { 配色: '蓝色' },
      price: '499.00',
      market_price: null,
      stock: 10,
      locked_stock: 0,
      available_stock: 10,
      enabled: true,
      created_at: '2026-01-01T00:00:00Z',
    }],
    total_available_stock: 10,
  }
}

function comparison(items: ProductComparisonItem[], unavailableIds: number[] = []): ProductComparisonResult {
  return {
    items,
    unavailable_ids: unavailableIds,
    category_id: items[0]?.category_id || null,
    category_name: items[0]?.category_name || null,
  }
}

function deferred<T>() {
  let resolve!: (value: T) => void
  const promise = new Promise<T>((done) => { resolve = done })
  return { promise, resolve }
}

function mountView() {
  const wrapper = mount(ProductComparisonView, {
    global: {
      plugins: [createPinia()],
      stubs: {
        RouterLink: { template: '<a><slot /></a>' },
      },
    },
  })
  mountedWrappers.push(wrapper)
  return wrapper
}

describe('ProductComparisonView', () => {
  beforeEach(() => {
    localStorage.clear()
    setActivePinia(createPinia())
    route.query = { ids: '2,3' }
    mocks.getProductComparison.mockReset()
    mocks.replace.mockReset()
  })

  afterEach(() => {
    mountedWrappers.splice(0).forEach(wrapper => wrapper.unmount())
  })

  it('restores valid shared IDs and removes unavailable products from the store and URL', async () => {
    route.query = { ids: '2,bad,2,3,9,10,11' }
    mocks.getProductComparison.mockResolvedValue(comparison([product(2), product(3)], [9, 10]))

    const wrapper = mountView()
    await flushPromises()

    expect(mocks.getProductComparison).toHaveBeenCalledWith([2, 3, 9, 10])
    expect(mocks.replace).toHaveBeenLastCalledWith({
      path: '/compare',
      query: { ids: '2,3' },
    })
    expect(useCompareStore().ids).toEqual([2, 3])
    expect(wrapper.text()).toContain('部分商品已失效，已从对比中移除')
  })

  it('ignores a late response after the shared comparison IDs change', async () => {
    const oldRequest = deferred<ProductComparisonResult>()
    const nextRequest = deferred<ProductComparisonResult>()
    mocks.getProductComparison
      .mockReturnValueOnce(oldRequest.promise)
      .mockReturnValueOnce(nextRequest.promise)

    const wrapper = mountView()
    route.query = { ids: '4,5' }
    await flushPromises()
    expect(mocks.getProductComparison).toHaveBeenCalledTimes(2)
    nextRequest.resolve(comparison([product(4), product(5)]))
    await flushPromises()
    oldRequest.resolve(comparison([product(2), product(3)]))
    await flushPromises()

    expect(wrapper.text()).toContain('商品 4')
    expect(wrapper.text()).not.toContain('商品 2')
    expect(useCompareStore().ids).toEqual([4, 5])
  })

  it('shows the parameter union and hides only shared dynamic rows', async () => {
    mocks.getProductComparison.mockResolvedValue(comparison([
      product(2, { 续航: '40 小时', 重量: '250 g', 降噪: '支持' }),
      product(3, { 续航: '40 小时', 重量: '230 g' }),
    ]))

    const wrapper = mountView()
    await flushPromises()

    expect(wrapper.get('[data-parameter="续航"]').text()).toContain('40 小时')
    expect(wrapper.get('[data-parameter="降噪"]').text()).toContain('未提供')
    await wrapper.get('[aria-label="仅看差异"]').setValue(true)

    expect(wrapper.find('[data-parameter="续航"]').exists()).toBe(false)
    expect(wrapper.get('[data-parameter="重量"]').text()).toContain('250 g')
    expect(wrapper.get('[data-parameter="降噪"]').text()).toContain('未提供')
  })
})
