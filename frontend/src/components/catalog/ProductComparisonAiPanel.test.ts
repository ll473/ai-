import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import ProductComparisonAiPanel from './ProductComparisonAiPanel.vue'
import type { ProductComparisonAiResult } from '../../types/ai'
import type { ProductComparisonItem } from '../../types/catalog'

const mocks = vi.hoisted(() => ({
  compareProductsWithAi: vi.fn(),
  routerPush: vi.fn(),
  auth: { isAuthenticated: false, user: null as { id: number } | null },
  demo: { enabled: false },
}))

vi.mock('../../api/ai', () => ({
  compareProductsWithAi: mocks.compareProductsWithAi,
}))

vi.mock('../../stores/auth', () => ({
  useAuthStore: () => mocks.auth,
}))

vi.mock('../../demo/config', () => ({
  get demoMode() {
    return mocks.demo.enabled
  },
}))

vi.mock('vue-router', () => ({
  useRouter: () => ({ push: mocks.routerPush }),
}))

function product(id: number): ProductComparisonItem {
  return {
    id,
    category_id: 2,
    category_name: '数码影音',
    brand_id: id,
    brand_name: 'EchoArc',
    name: id === 2 ? 'EchoArc H1' : `商品 ${id}`,
    subtitle: null,
    product_no: `P-${id}`,
    main_image_url: null,
    min_price: '899.00',
    max_price: '899.00',
    rating: '4.80',
    review_count: 20,
    sales_count: 30,
    status: 'ON_SALE',
    created_at: '2026-01-01T00:00:00Z',
    parameters: {},
    skus: [],
    total_available_stock: 10,
  }
}

const result: ProductComparisonAiResult = {
  recommended_product_id: 2,
  summary: '更适合需要兼顾续航与降噪的办公场景。',
  items: [
    { product_id: 2, strengths: ['续航更长'], weaknesses: ['价格更高'], suitable_for: ['办公室'] },
    { product_id: 3, strengths: ['更轻便'], weaknesses: ['降噪较弱'], suitable_for: ['通勤'] },
  ],
  considerations: ['建议实际试听佩戴感。'],
}

function deferred<T>() {
  let resolve!: (value: T) => void
  const promise = new Promise<T>((done) => { resolve = done })
  return { promise, resolve }
}

function mountPanel(products = [product(2), product(3)]) {
  return mount(ProductComparisonAiPanel, { props: { products } })
}

describe('ProductComparisonAiPanel', () => {
  beforeEach(() => {
    sessionStorage.clear()
    mocks.auth.isAuthenticated = false
    mocks.auth.user = null
    mocks.demo.enabled = false
    mocks.routerPush.mockReset()
    mocks.compareProductsWithAi.mockReset()
  })

  it('sends unauthenticated shoppers to login with the full shared comparison URL', async () => {
    const wrapper = mountPanel()

    await wrapper.get('button').trigger('click')

    expect(mocks.routerPush).toHaveBeenCalledWith({
      name: 'login',
      query: { redirect: '/compare?ids=2,3' },
    })
    expect(mocks.compareProductsWithAi).not.toHaveBeenCalled()
  })

  it('explains that AI comparison needs a complete deployment in demo mode', () => {
    mocks.demo.enabled = true

    const wrapper = mountPanel()

    expect(wrapper.text()).toContain('完整部署并登录后可使用 AI 对比')
    expect(wrapper.find('button').exists()).toBe(false)
  })

  it('sends a trimmed preference on demand and renders the named recommendation', async () => {
    mocks.auth.isAuthenticated = true
    mocks.auth.user = { id: 7 }
    mocks.compareProductsWithAi.mockResolvedValue(result)
    const wrapper = mountPanel()

    await wrapper.get('textarea').setValue('  办公室使用，重视续航  ')
    await wrapper.get('button').trigger('click')
    await flushPromises()

    expect(mocks.compareProductsWithAi).toHaveBeenCalledWith([2, 3], '办公室使用，重视续航')
    expect(wrapper.text()).toContain('更推荐 EchoArc H1')
  })

  it('restores a valid session result for the exact ordered products and preference', () => {
    mocks.auth.isAuthenticated = true
    mocks.auth.user = { id: 7 }
    sessionStorage.setItem('ai-commerce-product-comparison-v1:7:2,3:', JSON.stringify(result))

    const wrapper = mountPanel()

    expect(mocks.compareProductsWithAi).not.toHaveBeenCalled()
    expect(wrapper.text()).toContain('更推荐 EchoArc H1')
  })

  it('removes a structurally invalid JSON cache entry before analyzing again', async () => {
    mocks.auth.isAuthenticated = true
    mocks.auth.user = { id: 7 }
    mocks.compareProductsWithAi.mockResolvedValue(result)
    const key = 'ai-commerce-product-comparison-v1:7:2,3:'
    sessionStorage.setItem(key, JSON.stringify({
      recommended_product_id: 2,
      summary: '损坏的缓存',
      items: null,
      considerations: [],
    }))

    const wrapper = mountPanel()

    expect(sessionStorage.getItem(key)).toBeNull()
    await wrapper.get('button').trigger('click')
    await flushPromises()
    expect(mocks.compareProductsWithAi).toHaveBeenCalledWith([2, 3], undefined)
  })

  it('does not let a previous product request overwrite the changed comparison', async () => {
    mocks.auth.isAuthenticated = true
    mocks.auth.user = { id: 7 }
    const pending = deferred<ProductComparisonAiResult>()
    mocks.compareProductsWithAi.mockReturnValue(pending.promise)
    const wrapper = mountPanel()

    await wrapper.get('button').trigger('click')
    await wrapper.setProps({ products: [product(4), product(5)] })
    pending.resolve(result)
    await flushPromises()

    expect(wrapper.text()).not.toContain('更推荐 EchoArc H1')
  })

  it('does not save a completed request after the panel unmounts', async () => {
    mocks.auth.isAuthenticated = true
    mocks.auth.user = { id: 7 }
    const pending = deferred<ProductComparisonAiResult>()
    mocks.compareProductsWithAi.mockReturnValue(pending.promise)
    const wrapper = mountPanel()

    await wrapper.get('button').trigger('click')
    wrapper.unmount()
    pending.resolve(result)
    await flushPromises()

    expect(sessionStorage.getItem('ai-commerce-product-comparison-v1:7:2,3:')).toBeNull()
  })

  it('keeps the preference and allows retry after an analysis failure', async () => {
    mocks.auth.isAuthenticated = true
    mocks.auth.user = { id: 7 }
    mocks.compareProductsWithAi
      .mockRejectedValueOnce(new Error('AI 对比分析超时，请稍后重试'))
      .mockResolvedValueOnce(result)
    const wrapper = mountPanel()

    await wrapper.get('textarea').setValue('适合办公室')
    await wrapper.get('button').trigger('click')
    await flushPromises()

    expect((wrapper.get('textarea').element as HTMLTextAreaElement).value).toBe('适合办公室')
    expect(wrapper.text()).toContain('AI 对比分析超时，请稍后重试')
    expect(wrapper.get('button').text()).toContain('重新分析')
    await wrapper.get('button').trigger('click')
    await flushPromises()
    expect(mocks.compareProductsWithAi).toHaveBeenCalledTimes(2)
  })

  it('uses the friendly timeout message for a browser request timeout', async () => {
    mocks.auth.isAuthenticated = true
    mocks.auth.user = { id: 7 }
    mocks.compareProductsWithAi.mockRejectedValue(Object.assign(
      new Error('timeout of 20000ms exceeded'),
      { code: 'ECONNABORTED' },
    ))
    const wrapper = mountPanel()

    await wrapper.get('button').trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('AI 对比分析超时，请稍后重试')
    expect(wrapper.text()).not.toContain('timeout of 20000ms exceeded')
  })

  it('does not read an AI cache before login or after a different user signs in', () => {
    sessionStorage.setItem('ai-commerce-product-comparison-v1:7:2,3:', JSON.stringify(result))

    const guest = mountPanel()
    expect(guest.text()).not.toContain('更推荐 EchoArc H1')
    guest.unmount()

    mocks.auth.isAuthenticated = true
    mocks.auth.user = { id: 8 }
    const otherUser = mountPanel()
    expect(otherUser.text()).not.toContain('更推荐 EchoArc H1')
  })

  it('rejects cache results with an unknown recommendation, missing candidate, or duplicate item', () => {
    mocks.auth.isAuthenticated = true
    mocks.auth.user = { id: 7 }
    const invalidResults = [
      { ...result, recommended_product_id: 99 },
      { ...result, items: [result.items[0]] },
      { ...result, items: [result.items[0], result.items[0]] },
    ]

    for (const invalid of invalidResults) {
      sessionStorage.setItem('ai-commerce-product-comparison-v1:7:2,3:', JSON.stringify(invalid))
      const wrapper = mountPanel()
      expect(wrapper.text()).not.toContain('更推荐 EchoArc H1')
      wrapper.unmount()
    }
    expect(sessionStorage.getItem('ai-commerce-product-comparison-v1:7:2,3:')).toBeNull()
  })

  it('keeps the panel usable and does not cache an invalid network response', async () => {
    mocks.auth.isAuthenticated = true
    mocks.auth.user = { id: 7 }
    mocks.compareProductsWithAi.mockResolvedValue({ ...result, recommended_product_id: 99 })
    const wrapper = mountPanel()

    await wrapper.get('button').trigger('click')
    await flushPromises()

    expect(wrapper.get('textarea').exists()).toBe(true)
    expect(wrapper.text()).toContain('AI 对比分析结果无效，请稍后重试')
    expect(sessionStorage.getItem('ai-commerce-product-comparison-v1:7:2,3:')).toBeNull()
  })
})
