import chairImage from '../../../uploads/demo-products/ergonomic-chair.png'
import keyboardImage from '../../../uploads/demo-products/mechanical-keyboard.png'
import headphoneImage from '../../../uploads/demo-products/noise-cancelling-headphones.png'
import coffeeImage from '../../../uploads/demo-products/pour-over-coffee-set.png'

import type {
  Brand,
  Category,
  ProductComparisonItem,
  ProductComparisonResult,
  ProductDetail,
  ProductQuery,
  ProductSummary,
} from '../types/catalog'

const createdAt = '2026-08-04T00:00:00Z'

export const demoCategories: Category[] = [
  { id: 1, parent_id: null, name: '办公效率', slug: 'office-efficiency', icon_url: null, sort_order: 1, enabled: true, created_at: createdAt },
  { id: 2, parent_id: null, name: '数码影音', slug: 'digital-audio', icon_url: null, sort_order: 2, enabled: true, created_at: createdAt },
  { id: 3, parent_id: null, name: '品质生活', slug: 'quality-living', icon_url: null, sort_order: 3, enabled: true, created_at: createdAt },
]

export const demoBrands: Brand[] = [
  { id: 1, name: 'Aster Living', slug: 'aster-living', logo_url: null, description: '关注人体工学与现代办公空间。', enabled: true, created_at: createdAt },
  { id: 2, name: 'KeyNest', slug: 'keynest', logo_url: null, description: '为高频输入打造可靠桌面装备。', enabled: true, created_at: createdAt },
  { id: 3, name: 'EchoArc', slug: 'echoarc', logo_url: null, description: '专注轻量化个人音频体验。', enabled: true, created_at: createdAt },
  { id: 4, name: 'Morrow Home', slug: 'morrow-home', logo_url: null, description: '把实用器物做得温和耐看。', enabled: true, created_at: createdAt },
]

export const demoProductDetails: ProductDetail[] = [
  {
    id: 1,
    category_id: 1,
    brand_id: 1,
    name: 'EonFlex 自适应人体工学椅',
    subtitle: '动态腰托、4D 扶手与透气网背，为长时间办公提供稳定支撑',
    product_no: 'DEMO-CHAIR-001',
    main_image_url: chairImage,
    min_price: '1299.00',
    max_price: '1499.00',
    rating: '5.0',
    review_count: 128,
    sales_count: 286,
    status: 'ON_SALE',
    created_at: createdAt,
    detail_markdown: '## 为久坐设计的动态支撑\n\n椅背随坐姿变化提供连续支撑，双区腰托可独立微调。\n\n- 4D 扶手与多档头枕\n- 透气网背和高回弹坐垫\n- 支持多处精细调节',
    parameters: { 材质: '高弹透气网布', 腰托: '自适应双区腰托', 扶手: '4D 多向调节', 承重: '120 kg', 保修: '3 年' },
    images: [{ id: 1, product_id: 1, image_url: chairImage, alt_text: 'EonFlex 人体工学椅', sort_order: 1 }],
    skus: [{ id: 101, product_id: 1, sku_no: 'DEMO-CHAIR-BLACK', name: '曜石黑标准款', attributes: { 颜色: '曜石黑' }, price: '1299.00', market_price: '1599.00', stock: 36, locked_stock: 0, available_stock: 36, enabled: true, created_at: createdAt }],
  },
  {
    id: 2,
    category_id: 2,
    brand_id: 2,
    name: 'KeyNest K75 三模机械键盘',
    subtitle: '75% 紧凑配列、热插拔轴座与金属旋钮，兼顾办公和游戏',
    product_no: 'DEMO-KEYBOARD-001',
    main_image_url: keyboardImage,
    min_price: '499.00',
    max_price: '529.00',
    rating: '4.8',
    review_count: 96,
    sales_count: 518,
    status: 'ON_SALE',
    created_at: createdAt,
    detail_markdown: '## 桌面空间与输入手感的平衡\n\n保留独立方向键和功能区，同时缩短键盘宽度。\n\n- 蓝牙、2.4G 与 USB-C 三模连接\n- 全键热插拔\n- PBT 键帽耐磨不易打油',
    parameters: { 连接: '蓝牙 / 2.4G / USB-C', 布局: '75% · 82 键', 轴座: '全键热插拔', 续航: '约 120 小时' },
    images: [{ id: 2, product_id: 2, image_url: keyboardImage, alt_text: 'KeyNest K75 机械键盘', sort_order: 1 }],
    skus: [{ id: 201, product_id: 2, sku_no: 'DEMO-K75-WHITE', name: '暖白线性轴', attributes: { 配色: '暖白' }, price: '499.00', market_price: '599.00', stock: 64, locked_stock: 0, available_stock: 64, enabled: true, created_at: createdAt }],
  },
  {
    id: 3,
    category_id: 2,
    brand_id: 3,
    name: 'EchoArc H1 自适应降噪耳机',
    subtitle: '混合主动降噪、空间音频与柔软记忆棉耳罩，通勤办公都安静',
    product_no: 'DEMO-HEADPHONE-001',
    main_image_url: headphoneImage,
    min_price: '899.00',
    max_price: '899.00',
    rating: '4.9',
    review_count: 84,
    sales_count: 342,
    status: 'ON_SALE',
    created_at: createdAt,
    detail_markdown: '## 把嘈杂留在耳机之外\n\n多麦克风实时采集环境噪声并自动调整降噪强度。\n\n- 40 mm 大尺寸动圈单元\n- 支持多设备同时连接\n- 开启降噪约 42 小时续航',
    parameters: { 降噪: '混合主动降噪', 单元: '40 mm 动圈', 续航: '约 42 小时', 重量: '248 g' },
    images: [{ id: 3, product_id: 3, image_url: headphoneImage, alt_text: 'EchoArc H1 降噪耳机', sort_order: 1 }],
    skus: [{ id: 301, product_id: 3, sku_no: 'DEMO-H1-NAVY', name: '深海蓝', attributes: { 颜色: '深海蓝' }, price: '899.00', market_price: '1099.00', stock: 31, locked_stock: 0, available_stock: 31, enabled: true, created_at: createdAt }],
  },
  {
    id: 4,
    category_id: 3,
    brand_id: 4,
    name: 'Morrow 手冲咖啡礼盒套装',
    subtitle: '细口壶、陶瓷滤杯与耐热玻璃分享壶，一套完成稳定手冲',
    product_no: 'DEMO-COFFEE-001',
    main_image_url: coffeeImage,
    min_price: '369.00',
    max_price: '399.00',
    rating: '4.8',
    review_count: 57,
    sales_count: 176,
    status: 'ON_SALE',
    created_at: createdAt,
    detail_markdown: '## 从第一杯开始稳定复现\n\n适合新手的完整手冲组合，细口壶水流容易控制。\n\n- 700 ml 不锈钢细口壶\n- 02 号陶瓷滤杯\n- 600 ml 耐热玻璃分享壶',
    parameters: { 容量: '分享壶 600 ml', 滤杯: '02 号陶瓷滤杯', 手冲壶: '不锈钢细口壶 700 ml', 适用: '1–4 人' },
    images: [{ id: 4, product_id: 4, image_url: coffeeImage, alt_text: 'Morrow 手冲咖啡套装', sort_order: 1 }],
    skus: [{ id: 401, product_id: 4, sku_no: 'DEMO-COFFEE-WALNUT', name: '胡桃木经典款', attributes: { 木色: '胡桃木' }, price: '369.00', market_price: '459.00', stock: 28, locked_stock: 0, available_stock: 28, enabled: true, created_at: createdAt }],
  },
]

function toSummary(product: ProductDetail): ProductSummary {
  return {
    id: product.id,
    category_id: product.category_id,
    brand_id: product.brand_id,
    name: product.name,
    subtitle: product.subtitle,
    product_no: product.product_no,
    main_image_url: product.main_image_url,
    min_price: product.min_price,
    max_price: product.max_price,
    rating: product.rating,
    review_count: product.review_count,
    sales_count: product.sales_count,
    status: product.status,
    created_at: product.created_at,
  }
}

export function getDemoProducts(query: ProductQuery = {}) {
  const keyword = query.keyword?.trim().toLocaleLowerCase('zh-CN')
  const filtered = demoProductDetails.filter((product) => {
    if (query.category_id && product.category_id !== query.category_id) return false
    if (query.brand_id && product.brand_id !== query.brand_id) return false
    if (query.min_price && Number(product.min_price) < query.min_price) return false
    if (query.max_price && Number(product.min_price) > query.max_price) return false
    if (keyword && !`${product.name} ${product.subtitle || ''}`.toLocaleLowerCase('zh-CN').includes(keyword)) return false
    return true
  })
  const page = query.page || 1
  const pageSize = query.page_size || 12
  return {
    items: filtered.slice((page - 1) * pageSize, page * pageSize).map(toSummary),
    total: filtered.length,
    page,
    page_size: pageSize,
  }
}

export function getDemoProduct(productId: number) {
  return demoProductDetails.find((product) => product.id === productId)
}

export function getDemoProductComparison(productIds: number[]): ProductComparisonResult {
  const orderedIds = [...new Set(productIds)]
  if (orderedIds.length < 2 || orderedIds.length > 4)
    throw new Error('请选择 2–4 件商品进行对比')

  const productsById = new Map(
    demoProductDetails
      .filter(product => product.status === 'ON_SALE')
      .map(product => [product.id, product]),
  )
  const selectedProducts = orderedIds
    .map(productId => productsById.get(productId))
    .filter((product): product is ProductDetail => Boolean(product))

  if (new Set(selectedProducts.map(product => product.category_id)).size > 1)
    throw new Error('只能对比同一分类商品')

  const categoriesById = new Map(demoCategories.map(category => [category.id, category]))
  const brandsById = new Map(demoBrands.map(brand => [brand.id, brand]))
  const items = selectedProducts.map<ProductComparisonItem>((product) => {
    const skus = product.skus.filter(sku => sku.enabled)
    return {
      ...toSummary(product),
      category_name: categoriesById.get(product.category_id)?.name || '',
      brand_name: product.brand_id === null
        ? null
        : brandsById.get(product.brand_id)?.name || null,
      parameters: product.parameters,
      skus,
      total_available_stock: skus.reduce((total, sku) => total + sku.available_stock, 0),
    }
  })
  const unavailable_ids = orderedIds.filter(productId => !productsById.has(productId))

  return {
    items,
    unavailable_ids,
    category_id: items[0]?.category_id || null,
    category_name: items[0]?.category_name || null,
  }
}
