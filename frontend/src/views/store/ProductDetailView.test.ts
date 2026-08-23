import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia, type Pinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import ProductDetailView from './ProductDetailView.vue'
import { useCompareStore } from '../../stores/compare'

const mocks = vi.hoisted(() => ({
  errorMessage: vi.fn(),
  getProduct: vi.fn(),
  getProductReviews: vi.fn(),
  push: vi.fn(),
  successMessage: vi.fn(),
  writeText: vi.fn(),
}))

vi.mock('../../api/ai', () => ({ askProductQuestion: vi.fn() }))
vi.mock('../../api/catalog', () => ({
  getProduct: mocks.getProduct,
  recordProductView: vi.fn(),
}))
vi.mock('../../api/trade', () => ({
  addCartItem: vi.fn(),
  addFavorite: vi.fn(),
  getFavoriteStatus: vi.fn(),
  getProductReviews: mocks.getProductReviews,
  removeFavorite: vi.fn(),
}))
vi.mock('../../stores/auth', () => ({
  useAuthStore: () => ({ isAuthenticated: false }),
}))
vi.mock('vue-router', () => ({
  useRoute: () => ({ params: { id: '42' }, fullPath: '/products/42' }),
  useRouter: () => ({ push: mocks.push }),
}))
vi.mock('element-plus', () => ({
  ElMessage: {
    error: mocks.errorMessage,
    success: mocks.successMessage,
    warning: vi.fn(),
  },
}))

const product = {
  id: 42,
  category_id: 1,
  brand_id: null,
  name: 'EonFlex 人体工学椅',
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
  detail_markdown: null,
  parameters: null,
  images: [],
  skus: [{
    id: 1,
    product_id: 42,
    sku_no: 'CHAIR-42-BLACK',
    name: '黑色',
    attributes: null,
    price: '1299.00',
    market_price: null,
    stock: 10,
    locked_stock: 0,
    available_stock: 10,
    enabled: true,
    created_at: '2026-01-01T00:00:00Z',
  }],
}

let pinia: Pinia

function mountView() {
  return mount(ProductDetailView, {
    global: {
      plugins: [pinia],
      stubs: {
        ElButton: {
          emits: ['click'],
          template: '<button v-bind="$attrs" @click="$emit(\'click\')"><slot /></button>',
        },
        ElIcon: { template: '<span><slot /></span>' },
        ElInput: { template: '<textarea />' },
        ElInputNumber: { template: '<input type="number">' },
        ElRate: { template: '<span />' },
        ElSkeleton: { template: '<div><slot /></div>' },
        RouterLink: { template: '<a><slot /></a>' },
        StatePanel: { template: '<section />' },
      },
    },
  })
}

describe('ProductDetailView sharing', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
    pinia = createPinia()
    setActivePinia(pinia)
    mocks.getProduct.mockResolvedValue(product)
    mocks.getProductReviews.mockResolvedValue({
      items: [],
      page: 1,
      page_size: 20,
      total: 0,
    })
    Object.defineProperty(navigator, 'clipboard', {
      configurable: true,
      value: { writeText: mocks.writeText },
    })
  })

  it('copies the current product URL and confirms success', async () => {
    mocks.writeText.mockResolvedValue(undefined)
    const wrapper = mountView()
    await flushPromises()

    await wrapper.get('button[aria-label="复制商品链接"]').trigger('click')
    await flushPromises()

    expect(mocks.writeText).toHaveBeenCalledWith(window.location.href)
    expect(mocks.successMessage).toHaveBeenCalledWith('商品链接已复制')
  })

  it('shows a manual-copy hint when clipboard access fails', async () => {
    mocks.writeText.mockRejectedValue(new Error('clipboard denied'))
    const wrapper = mountView()
    await flushPromises()

    await wrapper.get('button[aria-label="复制商品链接"]').trigger('click')
    await flushPromises()

    expect(mocks.errorMessage).toHaveBeenCalledWith('复制失败，请手动复制地址栏链接')
  })

  it('adds the loaded product to comparison from the detail page', async () => {
    const wrapper = mountView()
    await flushPromises()

    await wrapper.get('button[aria-label="加入商品对比"]').trigger('click')

    expect(useCompareStore().ids).toEqual([42])
    expect(wrapper.get('button[aria-label="移除商品对比"]').text()).toContain('已加入对比')
    expect(mocks.push).not.toHaveBeenCalled()
  })
})
