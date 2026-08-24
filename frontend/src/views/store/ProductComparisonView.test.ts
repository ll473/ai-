import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia, type Pinia } from 'pinia'
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
let pinia: Pinia

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
      name: '标准款',
      attributes: id === 2 ? { 配色: '黑色' } : { 配色: '蓝色' },
      price: '499.00',
      available_stock: 10,
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
  let reject!: (reason: unknown) => void
  const promise = new Promise<T>((done, fail) => { resolve = done; reject = fail })
  return { promise, resolve, reject }
}

function mountView() {
  const wrapper = mount(ProductComparisonView, {
    global: {
      plugins: [pinia],
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
    pinia = createPinia()
    setActivePinia(pinia)
    route.query = { ids: '2,3' }
    mocks.getProductComparison.mockReset()
    mocks.replace.mockReset()
    mocks.replace.mockImplementation(async (location: { query?: Record<string, unknown> }) => {
      route.query = location.query || {}
    })
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

  it('does not let an old request error clear a newer successful comparison', async () => {
    const oldRequest = deferred<ProductComparisonResult>()
    const nextRequest = deferred<ProductComparisonResult>()
    mocks.getProductComparison
      .mockReturnValueOnce(oldRequest.promise)
      .mockReturnValueOnce(nextRequest.promise)

    const wrapper = mountView()
    route.query = { ids: '4,5' }
    await flushPromises()
    nextRequest.resolve(comparison([product(4), product(5)]))
    await flushPromises()
    oldRequest.reject(new Error('旧请求失败'))
    await flushPromises()

    expect(wrapper.text()).toContain('商品 4')
    expect(wrapper.find('[role="alert"]').exists()).toBe(false)
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

  it('rewrites trailing invalid IDs in a shared link to its canonical form', async () => {
    route.query = { ids: '2,3,bad' }
    mocks.getProductComparison.mockResolvedValue(comparison([product(2), product(3)]))

    mountView()
    await flushPromises()

    expect(route.query).toEqual({ ids: '2,3' })
    expect(mocks.replace).toHaveBeenCalledWith({ path: '/compare', query: { ids: '2,3' } })
  })

  it('rewrites repeated query parameters to one canonical shared IDs parameter', async () => {
    route.query = { ids: ['2', '3'] }
    mocks.getProductComparison.mockResolvedValue(comparison([product(2), product(3)]))

    mountView()
    await flushPromises()

    expect(route.query).toEqual({ ids: '2,3' })
    expect(mocks.replace).toHaveBeenCalledWith({ path: '/compare', query: { ids: '2,3' } })
  })

  it('keeps the unavailable product notice after an internal URL rewrite reloads the route', async () => {
    route.query = { ids: '2,3,9' }
    mocks.getProductComparison.mockResolvedValueOnce(comparison([product(2), product(3)], [9]))

    const wrapper = mountView()
    await flushPromises()

    expect(route.query).toEqual({ ids: '2,3' })
    expect(wrapper.text()).toContain('部分商品已失效，已从对比中移除')
    expect(mocks.getProductComparison).toHaveBeenCalledTimes(1)
  })

  it('leaves the loading state when a late request is superseded by fewer than two products', async () => {
    const pending = deferred<ProductComparisonResult>()
    mocks.getProductComparison.mockReturnValue(pending.promise)

    const wrapper = mountView()
    route.query = { ids: '2' }
    await flushPromises()

    expect(wrapper.text()).toContain('请选择至少两件同分类商品')
    expect(wrapper.text()).not.toContain('正在加载对比商品')

    pending.resolve(comparison([product(2), product(3)]))
    await flushPromises()
  })

  it('keeps saved selections on a comparison request error and offers a retry', async () => {
    const compare = useCompareStore()
    compare.replaceFromProducts([product(2), product(3)])
    mocks.getProductComparison
      .mockRejectedValueOnce(new Error('网络暂时不可用'))
      .mockResolvedValueOnce(comparison([product(2), product(3)]))

    const wrapper = mountView()
    await flushPromises()

    expect(compare.ids).toEqual([2, 3])
    await wrapper.get('button[aria-label="重新加载商品对比"]').trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('商品 2')
  })

  it('removing one of two products keeps the remaining product without another comparison request', async () => {
    mocks.getProductComparison.mockResolvedValue(comparison([product(2), product(3)]))
    const wrapper = mountView()
    await flushPromises()

    await wrapper.get('[aria-label="移除商品 2"]').trigger('click')
    await flushPromises()

    expect(mocks.getProductComparison).toHaveBeenCalledTimes(1)
    expect(useCompareStore().ids).toEqual([3])
    expect(wrapper.text()).toContain('商品 3')
    expect(wrapper.text()).toContain('请选择至少两件同分类商品')
  })

  it('keeps a single valid product when the comparison response expires the other candidate', async () => {
    mocks.getProductComparison.mockResolvedValue(comparison([product(2)], [3]))
    const wrapper = mountView()
    await flushPromises()

    expect(useCompareStore().ids).toEqual([2])
    expect(wrapper.text()).toContain('商品 2')
    expect(wrapper.text()).toContain('部分商品已失效，已从对比中移除')
    expect(wrapper.text()).toContain('请选择至少两件同分类商品')
  })

  it('hides shared fixed facts and SKU attributes together with shared parameters', async () => {
    const sameFacts = product(3, { 续航: '40 小时' })
    sameFacts.brand_name = 'KeyNest'
    sameFacts.min_price = '499.00'
    sameFacts.max_price = '529.00'
    sameFacts.skus[0].attributes = { 配色: '黑色' }
    mocks.getProductComparison.mockResolvedValue(comparison([
      product(2, { 续航: '40 小时' }),
      sameFacts,
    ]))
    const wrapper = mountView()
    await flushPromises()

    await wrapper.get('[aria-label="仅看差异"]').setValue(true)

    expect(wrapper.text()).not.toContain('品牌')
    expect(wrapper.text()).not.toContain('价格区间')
    expect(wrapper.text()).not.toContain('评分')
    expect(wrapper.text()).not.toContain('续航')
    expect(wrapper.find('[data-parameter="配色"]').exists()).toBe(false)
  })

  it('keeps a fixed fact row when that fact differs', async () => {
    mocks.getProductComparison.mockResolvedValue(comparison([product(2), product(3)]))
    const wrapper = mountView()
    await flushPromises()

    await wrapper.get('[aria-label="仅看差异"]').setValue(true)

    expect(wrapper.get('[data-parameter="价格区间"]').text()).toContain('¥499.00')
  })

  it('explains when no product offers parameters or SKU attributes', async () => {
    const first = product(2)
    const second = product(3)
    first.skus = []
    second.skus = []
    mocks.getProductComparison.mockResolvedValue(comparison([first, second]))
    const wrapper = mountView()
    await flushPromises()

    expect(wrapper.text()).toContain('商家暂未提供详细参数')
  })
})
