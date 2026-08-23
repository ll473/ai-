import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import ProductListView from './ProductListView.vue'

const apiMocks = vi.hoisted(() => ({
  getBrands: vi.fn(),
  getCategories: vi.fn(),
  recordSearchEvent: vi.fn(),
  searchCatalog: vi.fn(),
}))
const routerMocks = vi.hoisted(() => ({
  push: vi.fn(),
  replace: vi.fn(),
  query: {} as Record<string, string>,
}))

vi.mock('../../api/catalog', () => apiMocks)
vi.mock('vue-router', () => ({
  useRoute: () => ({ query: routerMocks.query }),
  useRouter: () => ({ push: routerMocks.push, replace: routerMocks.replace }),
}))

function deferred<T>() {
  let resolve!: (value: T) => void
  const promise = new Promise<T>((promiseResolve) => {
    resolve = promiseResolve
  })
  return { promise, resolve }
}

function searchResult(name = '', id = 1) {
  return {
    items: name
      ? [{
          id,
          category_id: 1,
          brand_id: null,
          name,
          subtitle: null,
          product_no: `P-${id}`,
          main_image_url: null,
          min_price: '1.00',
          max_price: '1.00',
          rating: '5.00',
          review_count: 0,
          sales_count: 0,
          status: 'ON_SALE' as const,
          created_at: '2026-01-01T00:00:00Z',
        }]
      : [],
    page: 1,
    page_size: 12,
    total: name ? 1 : 0,
    search_mode: 'catalog' as const,
    facets: {
      categories: [],
      brands: [],
      min_price: null,
      max_price: null,
      in_stock_count: 0,
    },
  }
}

describe('ProductListView', () => {
  beforeEach(() => {
    Object.keys(routerMocks.query).forEach((key) => delete routerMocks.query[key])
    routerMocks.replace.mockResolvedValue(undefined)
    routerMocks.push.mockResolvedValue(undefined)
    apiMocks.getBrands.mockResolvedValue([])
    apiMocks.getCategories.mockResolvedValue([])
    apiMocks.recordSearchEvent.mockResolvedValue(undefined)
    apiMocks.searchCatalog.mockResolvedValue({
      items: [],
      page: 1,
      page_size: 12,
      total: 0,
      search_mode: 'catalog',
      facets: {
        categories: [],
        brands: [],
        min_price: null,
        max_price: null,
        in_stock_count: 0,
      },
    })
  })

  it('keeps the newest result when an older search finishes later', async () => {
    const slow = deferred<ReturnType<typeof searchResult>>()
    const fast = deferred<ReturnType<typeof searchResult>>()
    const wrapper = mount(ProductListView, {
      global: {
        stubs: {
          CatalogSearchBox: {
            props: ['modelValue'],
            emits: ['search', 'select', 'update:modelValue'],
            template: `
              <div>
                <button class="search-slow" @click="$emit('search', '旧搜索')">旧搜索</button>
                <button class="search-fast" @click="$emit('search', '新搜索')">新搜索</button>
              </div>
            `,
          },
          ElButton: { template: '<button @click="$emit(\'click\')"><slot /></button>' },
          ElCheckbox: { template: '<input type="checkbox">' },
          ElIcon: { template: '<span><slot /></span>' },
          ElInputNumber: { template: '<input type="number">' },
          ElOption: { template: '<option />' },
          ElPagination: { template: '<div />' },
          ElSelect: { template: '<select><slot /></select>' },
          ElSkeleton: { template: '<div><slot /></div>' },
          ElSkeletonItem: { template: '<div />' },
          ProductCard: {
            props: ['product'],
            template: '<article class="product-stub">{{ product.name }}</article>',
          },
          StatePanel: { template: '<section />' },
        },
      },
    })
    await flushPromises()
    apiMocks.searchCatalog.mockImplementationOnce(() => slow.promise)
    apiMocks.searchCatalog.mockImplementationOnce(() => fast.promise)

    await wrapper.get('.search-slow').trigger('click')
    await wrapper.get('.search-fast').trigger('click')
    fast.resolve(searchResult('新结果', 2))
    await flushPromises()
    slow.resolve(searchResult('旧结果', 1))
    await flushPromises()

    expect(wrapper.text()).toContain('新结果')
    expect(wrapper.text()).not.toContain('旧结果')
    expect(routerMocks.replace).toHaveBeenLastCalledWith({ query: { keyword: '新搜索' } })
  })

  it('records and opens a selected product suggestion', async () => {
    const wrapper = mount(ProductListView, {
      global: {
        stubs: {
          CatalogSearchBox: {
            emits: ['search', 'select', 'update:modelValue'],
            template: '<button class="select-product" @click="$emit(\'select\', { kind: \'product\', label: \'人体工学椅\', value: \'人体工学椅\', product_id: 42 })">商品</button>',
          },
          ElButton: { template: '<button><slot /></button>' },
          ElCheckbox: { template: '<input type="checkbox">' },
          ElIcon: { template: '<span><slot /></span>' },
          ElInputNumber: { template: '<input type="number">' },
          ElOption: { template: '<option />' },
          ElPagination: { template: '<div />' },
          ElSelect: { template: '<select><slot /></select>' },
          ElSkeleton: { template: '<div><slot /></div>' },
          ElSkeletonItem: { template: '<div />' },
          ProductCard: { template: '<article />' },
          StatePanel: { template: '<section />' },
        },
      },
    })
    await flushPromises()

    await wrapper.get('.select-product').trigger('click')
    await flushPromises()

    expect(apiMocks.recordSearchEvent).toHaveBeenCalledWith(expect.objectContaining({
      event_type: 'click',
      product_id: 42,
    }))
    expect(routerMocks.push).toHaveBeenCalledWith('/products/42')
  })

  it('uses the discovery endpoint when a user submits a natural-language query', async () => {
    const wrapper = mount(ProductListView, {
      global: {
        stubs: {
          CatalogSearchBox: {
            props: ['modelValue'],
            emits: ['search', 'update:modelValue'],
            template: '<button class="search-stub" @click="$emit(\'search\', \'适合送给父母的礼物\')">搜索</button>',
          },
          ElButton: { template: '<button @click="$emit(\'click\')"><slot /></button>' },
          ElCheckbox: { template: '<input type="checkbox">' },
          ElIcon: { template: '<span><slot /></span>' },
          ElInputNumber: { template: '<input type="number">' },
          ElOption: { template: '<option />' },
          ElPagination: { template: '<div />' },
          ElSelect: { template: '<select><slot /></select>' },
          ElSkeleton: { template: '<div><slot /></div>' },
          ElSkeletonItem: { template: '<div />' },
          ProductCard: { template: '<article />' },
          StatePanel: { template: '<section />' },
        },
      },
    })
    await flushPromises()

    await wrapper.get('.search-stub').trigger('click')
    await flushPromises()

    expect(apiMocks.searchCatalog).toHaveBeenLastCalledWith(
      expect.objectContaining({
        keyword: '适合送给父母的礼物',
        semantic: true,
        sort: 'relevance',
      }),
    )
  })

  it('clears every filter and shows all products from an empty result', async () => {
    Object.assign(routerMocks.query, {
      keyword: '不存在的商品',
      category_id: '2',
      brand_id: '3',
      min_price: '500',
      max_price: '900',
      in_stock: 'true',
      sort: 'price_desc',
      page: '4',
    })
    const wrapper = mount(ProductListView, {
      global: {
        stubs: {
          CatalogSearchBox: { template: '<div />' },
          ElButton: { template: '<button @click="$emit(\'click\')"><slot /></button>' },
          ElCheckbox: { template: '<input type="checkbox">' },
          ElIcon: { template: '<span><slot /></span>' },
          ElInputNumber: { template: '<input type="number">' },
          ElOption: { template: '<option />' },
          ElPagination: { template: '<div />' },
          ElSelect: { template: '<select><slot /></select>' },
          ElSkeleton: { template: '<div><slot /></div>' },
          ElSkeletonItem: { template: '<div />' },
          ProductCard: { template: '<article />' },
          StatePanel: {
            props: ['title', 'description', 'actionLabel'],
            emits: ['action'],
            template: `
              <section>
                <h3>{{ title }}</h3>
                <button
                  v-if="actionLabel"
                  class="empty-reset"
                  @click="$emit('action')"
                >
                  {{ actionLabel }}
                </button>
              </section>
            `,
          },
        },
      },
    })
    await flushPromises()

    expect(wrapper.text()).toContain('没有找到符合条件的商品')
    await wrapper.get('.empty-reset').trigger('click')
    await flushPromises()

    expect(apiMocks.searchCatalog).toHaveBeenLastCalledWith({
      page: 1,
      page_size: 12,
      keyword: undefined,
      category_id: undefined,
      brand_id: undefined,
      min_price: undefined,
      max_price: undefined,
      in_stock: false,
      sort: 'relevance',
      semantic: false,
    })
    expect(routerMocks.replace).toHaveBeenLastCalledWith({ query: {} })
  })
})
