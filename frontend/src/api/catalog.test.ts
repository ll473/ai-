import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const httpGet = vi.hoisted(() => vi.fn())

const comparisonResult = {
  items: [{
    id: 2,
    category_id: 2,
    brand_id: 2,
    name: 'KeyNest K75 三模机械键盘',
    subtitle: null,
    product_no: 'DEMO-KEYBOARD-001',
    main_image_url: null,
    min_price: '499.00',
    max_price: '529.00',
    rating: '4.80',
    review_count: 96,
    sales_count: 518,
    status: 'ON_SALE' as const,
    created_at: '2026-08-04T00:00:00Z',
    category_name: '数码影音',
    brand_name: 'KeyNest',
    parameters: { 连接: '蓝牙 / 2.4G / USB-C' },
    skus: [{
      id: 201,
      product_id: 2,
      sku_no: 'DEMO-K75-WHITE',
      name: '暖白线性轴',
      attributes: { 配色: '暖白' },
      price: '499.00',
      market_price: '599.00',
      stock: 64,
      locked_stock: 0,
      available_stock: 64,
      enabled: true,
      created_at: '2026-08-04T00:00:00Z',
    }],
    total_available_stock: 64,
  }],
  unavailable_ids: [],
  category_id: 2,
  category_name: '数码影音',
}

async function loadCatalogApi() {
  vi.resetModules()
  vi.doMock('./http', () => ({ http: { get: httpGet } }))
  vi.doMock('../demo/config', () => ({ demoMode: false }))
  vi.doMock('../demo/catalog', () => ({
    demoBrands: [],
    demoCategories: [],
    getDemoProduct: vi.fn(),
    getDemoProducts: vi.fn(),
  }))
  return import('./catalog')
}

describe('getProductComparison', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-08-24T00:00:00Z'))
    httpGet.mockReset()
    httpGet.mockResolvedValue({ data: { data: comparisonResult } })
  })

  afterEach(() => {
    vi.doUnmock('./http')
    vi.doUnmock('../demo/config')
    vi.doUnmock('../demo/catalog')
    vi.useRealTimers()
  })

  it('caches one product ID combination for exactly 30 seconds', async () => {
    const { getProductComparison } = await loadCatalogApi()

    await getProductComparison([2, 3])
    await getProductComparison([2, 3])

    expect(httpGet).toHaveBeenCalledTimes(1)

    vi.setSystemTime(new Date('2026-08-24T00:00:30.001Z'))
    await getProductComparison([2, 3])

    expect(httpGet).toHaveBeenCalledTimes(2)
  })
})
