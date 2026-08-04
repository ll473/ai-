const path = require('node:path')
const playwrightModule = process.env.VISUAL_CHECK_PLAYWRIGHT || 'playwright'
const { chromium } = require(playwrightModule)

const outputDir = process.env.VISUAL_CHECK_OUTPUT
  ? path.resolve(process.env.VISUAL_CHECK_OUTPUT)
  : path.resolve(__dirname, '../.cache')

async function addEmptyApiRoutes(page) {
  await page.route('**/api/v1/catalog/categories', (route) =>
    route.fulfill({ json: { code: 'OK', message: 'success', data: [] } }),
  )
  await page.route('**/api/v1/catalog/brands', (route) =>
    route.fulfill({ json: { code: 'OK', message: 'success', data: [] } }),
  )
  await page.route('**/api/v1/catalog/products**', (route) =>
    route.fulfill({
      json: {
        code: 'OK',
        message: 'success',
        data: { items: [], page: 1, page_size: 20, total: 0 },
      },
    }),
  )
  await page.route('**/api/v1/catalog/products/1', (route) =>
    route.fulfill({
      json: {
        code: 'OK', message: 'success', data: {
          id: 1, category_id: 1, brand_id: null, name: '人体工学办公椅',
          subtitle: '自适应腰托与多档扶手，为长时间办公提供稳定支撑', product_no: 'CHAIR001',
          main_image_url: null, detail_markdown: '高弹网布椅背，坐深和头枕均可调节。',
          parameters: { 材质: '高弹网布', 承重: '120 kg', 保修: '3 年' },
          min_price: '1299.00', max_price: '1299.00', rating: '4.80', review_count: 28,
          sales_count: 312, status: 'ON_SALE', created_at: '2026-08-04T10:00:00Z', images: [],
          skus: [{ id: 1, product_id: 1, sku_no: 'CHAIR-BLACK', name: '黑色标准款',
            attributes: { color: '黑色' }, price: '1299.00', market_price: '1599.00',
            stock: 16, locked_stock: 2, available_stock: 14, enabled: true,
            created_at: '2026-08-04T10:00:00Z' }],
        },
      },
    }),
  )
  await page.route('**/api/v1/catalog/products/1/reviews**', (route) =>
    route.fulfill({ json: { code: 'OK', message: 'success', data: { items: [], page: 1, page_size: 20, total: 0 } } }),
  )
  await page.route('**/api/v1/ai/product-qa', (route) =>
    route.fulfill({ json: { code: 'OK', message: 'success', data: {
      answer: '资料显示这款椅子提供自适应腰托、多档扶手和可调头枕，适合长时间办公时按个人坐姿调整。',
      citations: [{ document_id: 3, document_title: '人体工学办公椅 · 商品资料', chunk_index: 0,
        excerpt: '高弹网布椅背，自适应腰托，扶手支持多档调节。', score: 0.92 }],
    } } }),
  )
}

async function addEmptyAdminApiRoutes(page) {
  await page.route('**/api/v1/admin/catalog/categories', (route) =>
    route.fulfill({ json: { code: 'OK', message: 'success', data: [] } }),
  )
  await page.route('**/api/v1/admin/catalog/brands', (route) =>
    route.fulfill({ json: { code: 'OK', message: 'success', data: [] } }),
  )
  await page.route('**/api/v1/admin/catalog/products**', (route) =>
    route.fulfill({
      json: {
        code: 'OK',
        message: 'success',
        data: { items: [], page: 1, page_size: 20, total: 0 },
      },
    }),
  )
  await page.route('**/api/v1/admin/orders**', (route) =>
    route.fulfill({
      json: {
        code: 'OK', message: 'success', data: { items: [{
          id: 9, user_id: 2, order_no: 'O202608040001', status: 'PAID',
          product_amount: '1299.00', discount_amount: '0.00', shipping_amount: '0.00',
          payable_amount: '1299.00', paid_amount: '1299.00', created_at: '2026-08-04T10:00:00Z',
          paid_at: '2026-08-04T10:01:00Z',
        }], page: 1, page_size: 20, total: 1 },
      },
    }),
  )
  await page.route('**/api/v1/admin/reviews**', (route) =>
    route.fulfill({
      json: { code: 'OK', message: 'success', data: { items: [], page: 1, page_size: 20, total: 0 } },
    }),
  )
  await page.route('**/api/v1/admin/ai/models', (route) =>
    route.fulfill({ json: { code: 'OK', message: 'success', data: [] } }),
  )
  await page.route('**/api/v1/admin/ai/prompts', (route) =>
    route.fulfill({ json: { code: 'OK', message: 'success', data: [] } }),
  )
  await page.route('**/api/v1/admin/ai/tools', (route) =>
    route.fulfill({ json: { code: 'OK', message: 'success', data: [] } }),
  )
  await page.route('**/api/v1/admin/ai/tool-logs**', (route) =>
    route.fulfill({ json: { code: 'OK', message: 'success', data: { items: [], page: 1, page_size: 20, total: 0 } } }),
  )
  await page.route('**/api/v1/admin/ai/runs**', (route) =>
    route.fulfill({ json: { code: 'OK', message: 'success', data: { items: [], page: 1, page_size: 20, total: 0 } } }),
  )
  await page.route('**/api/v1/admin/knowledge/documents**', (route) =>
    route.fulfill({ json: { code: 'OK', message: 'success', data: { items: [{
      id: 3, title: '人体工学办公椅 · 商品资料', source_type: 'PRODUCT_DETAIL', source_id: '1',
      product_id: 1, content: '商品资料', checksum: 'demo', status: 'READY', error_message: null,
      chunk_count: 4, created_at: '2026-08-04T10:00:00Z', updated_at: '2026-08-04T10:10:00Z',
    }], page: 1, page_size: 20, total: 1 } } }),
  )
  await page.route('**/api/v1/admin/operations/dashboard**', (route) =>
    route.fulfill({ json: { code: 'OK', message: 'success', data: {
      period_start: '2026-07-05T10:00:00Z', period_end: '2026-08-04T10:00:00Z',
      orders_total: 48, paid_orders: 36, revenue: '68240.00', reviews_total: 27,
      average_rating: 4.4, positive_reviews: 22, negative_reviews: 2, agent_runs: 83,
      successful_agent_runs: 76, recommendations: 61, recommendation_items: 142,
      top_products: [
        { product_id: 1, product_name: '人体工学办公椅', order_count: 18, quantity: 20, revenue: '25980.00' },
        { product_id: 2, product_name: '静音机械键盘', order_count: 12, quantity: 14, revenue: '6986.00' },
        { product_id: 3, product_name: '专业显示器支架', order_count: 9, quantity: 11, revenue: '4279.00' },
      ],
    } } }),
  )
  await page.route('**/api/v1/admin/operations/review-analyses', (route) =>
    route.fulfill({ json: { code: 'OK', message: 'success', data: [{
      id: 1, product_id: 1, product_name: '人体工学办公椅',
      period_start: '2026-07-05T10:00:00Z', period_end: '2026-08-04T10:00:00Z',
      positive_keywords: ['腰背支撑好', '坐感舒适', '调节丰富'],
      negative_reasons: ['安装说明不够清晰'], after_sale_risks: ['配件补发咨询'],
      missing_information: ['扶手调节视频'], suggestions: ['补充安装视频', '详情页增加身高适配表'],
      source_review_count: 28, created_at: '2026-08-04T10:20:00Z',
    }] } }),
  )
  await page.route('**/api/v1/admin/operations/reports', (route) =>
    route.fulfill({ json: { code: 'OK', message: 'success', data: [{
      id: 1, title: '近 30 天 AI 运营增长报告', report_type: 'GROWTH',
      period_start: '2026-07-05T10:00:00Z', period_end: '2026-08-04T10:00:00Z',
      content_markdown: '# 近 30 天运营增长报告\n\n## 经营摘要\n\n成交金额为 ¥68,240.00，共 36 笔已成交订单。\n\n## 评价洞察\n\n- 腰背支撑与坐感舒适是主要好评来源\n- 需要补充安装视频与身高适配表\n\n## 下阶段行动\n\n1. 一周内上线安装视频\n2. 为高频导购问题补充知识库资料',
      metrics_snapshot: {}, model_config_id: 1, created_at: '2026-08-04T10:25:00Z',
    }] } }),
  )
}

async function addAdminSession(page) {
  await page.addInitScript(() => {
    localStorage.setItem('access_token', 'visual-check-token')
    localStorage.setItem(
      'current_user',
      JSON.stringify({ id: 1, username: 'admin', role: 'ADMIN', nickname: '系统管理员' }),
    )
  })
}

async function addUserSession(page) {
  await page.addInitScript(() => {
    localStorage.setItem('access_token', 'visual-check-token')
    localStorage.setItem(
      'current_user',
      JSON.stringify({ id: 2, username: 'buyer', role: 'USER', nickname: '测试用户' }),
    )
  })
}

async function addTradeApiRoutes(page) {
  await page.route('**/api/v1/ai/shopping-guide', (route) =>
    route.fulfill({ json: { code: 'OK', message: 'success', data: {
      id: 20, run_no: 'AR202608040020', status: 'SUCCEEDED', request_text: '预算 1500 元买办公椅',
      final_answer: '推荐人体工学办公椅黑色标准款。价格和库存已经后端重新校验。', error_message: null,
      actual_steps: 3, max_steps: 6, total_duration_ms: 1680,
      started_at: '2026-08-04T10:00:00Z', finished_at: '2026-08-04T10:00:02Z',
      steps: [
        { id: 1, step_no: 1, step_type: 'TOOL_CALL', status: 'SUCCEEDED', tool_name: 'search_products', input_json: { keyword: '办公椅' }, output_json: {}, error_message: null, duration_ms: 120, started_at: '2026-08-04T10:00:00Z', finished_at: '2026-08-04T10:00:00Z' },
        { id: 2, step_no: 2, step_type: 'TOOL_CALL', status: 'SUCCEEDED', tool_name: 'submit_recommendation', input_json: { product_id: 1 }, output_json: {}, error_message: null, duration_ms: 86, started_at: '2026-08-04T10:00:01Z', finished_at: '2026-08-04T10:00:01Z' },
        { id: 3, step_no: 3, step_type: 'FINAL_ANSWER', status: 'SUCCEEDED', tool_name: null, input_json: null, output_json: {}, error_message: null, duration_ms: 0, started_at: '2026-08-04T10:00:02Z', finished_at: '2026-08-04T10:00:02Z' },
      ],
      recommendation: { id: 7, summary: '预算内优先选择支撑性和真实可售库存均合适的款式。', items: [{
        product_id: 1, sku_id: 1, product_name: '人体工学办公椅', sku_name: '黑色标准款',
        main_image_url: null, reason: '自适应腰托和多档扶手适合长时间办公，且在预算范围内。',
        price_snapshot: '1299.00', stock_snapshot: 14, validation_passed: true,
      }] },
    } } }),
  )
  await page.route('**/api/v1/cart', (route) =>
    route.fulfill({
      json: {
        code: 'OK', message: 'success', data: {
          items: [{
            id: 1, product_id: 1, sku_id: 1, product_name: '人体工学办公椅',
            sku_name: '黑色标准款', sku_attributes: { color: '黑色' }, image_url: null,
            unit_price: '1299.00', quantity: 1, selected: true, available_stock: 12,
            available: true, subtotal: '1299.00',
          }],
          total_count: 1, selected_count: 1, selected_amount: '1299.00',
        },
      },
    }),
  )
  await page.route('**/api/v1/wallet', (route) =>
    route.fulfill({ json: { code: 'OK', message: 'success', data: { balance: '3200.00' } } }),
  )
  await page.route('**/api/v1/wallet/transactions**', (route) =>
    route.fulfill({
      json: { code: 'OK', message: 'success', data: { items: [], page: 1, page_size: 20, total: 0 } },
    }),
  )
  await page.route('**/api/v1/orders**', (route) =>
    route.fulfill({
      json: {
        code: 'OK', message: 'success', data: { items: [{
          id: 9, order_no: 'O202608040001', status: 'SHIPPED', product_amount: '1299.00',
          discount_amount: '0.00', shipping_amount: '0.00', payable_amount: '1299.00',
          paid_amount: '1299.00', created_at: '2026-08-04T10:00:00Z', paid_at: '2026-08-04T10:01:00Z',
        }], page: 1, page_size: 20, total: 1 },
      },
    }),
  )
}

async function run() {
  const browserExecutable = process.env.VISUAL_CHECK_BROWSER || chromium.executablePath()
  const browser = await chromium.launch({
    headless: true,
    executablePath: browserExecutable,
  })
  try {
    const desktop = await browser.newPage({ viewport: { width: 1440, height: 1000 } })
    await addEmptyApiRoutes(desktop)
    await desktop.goto('http://127.0.0.1:4173/', { waitUntil: 'networkidle' })
    await desktop.screenshot({ path: path.join(outputDir, 'home-desktop.png'), fullPage: true })
    await desktop.goto('http://127.0.0.1:4173/products', { waitUntil: 'networkidle' })
    await desktop.screenshot({ path: path.join(outputDir, 'products-desktop.png'), fullPage: true })

    const productDesktop = await browser.newPage({ viewport: { width: 1440, height: 1000 } })
    await addUserSession(productDesktop)
    await addEmptyApiRoutes(productDesktop)
    await productDesktop.goto('http://127.0.0.1:4173/products/1', { waitUntil: 'networkidle' })
    await productDesktop.locator('.qa-composer textarea').fill('适合长时间办公吗？')
    await productDesktop.locator('.qa-composer button').click()
    await productDesktop.locator('.qa-answer').waitFor()
    await productDesktop.screenshot({ path: path.join(outputDir, 'product-rag-desktop.png'), fullPage: true })

    const tradeDesktop = await browser.newPage({ viewport: { width: 1440, height: 1000 } })
    await addUserSession(tradeDesktop)
    await addTradeApiRoutes(tradeDesktop)
    await tradeDesktop.goto('http://127.0.0.1:4173/cart', { waitUntil: 'networkidle' })
    await tradeDesktop.screenshot({ path: path.join(outputDir, 'cart-desktop.png'), fullPage: true })
    await tradeDesktop.goto('http://127.0.0.1:4173/wallet', { waitUntil: 'networkidle' })
    await tradeDesktop.screenshot({ path: path.join(outputDir, 'wallet-desktop.png'), fullPage: true })
    await tradeDesktop.goto('http://127.0.0.1:4173/ai-guide', { waitUntil: 'networkidle' })
    await tradeDesktop.locator('.guide-form textarea').fill('预算 1500 元买办公椅')
    await tradeDesktop.locator('.guide-controls button').click()
    await tradeDesktop.locator('.recommendation-section').waitFor()
    await tradeDesktop.screenshot({ path: path.join(outputDir, 'ai-recommendation-desktop.png'), fullPage: true })

    const adminDesktop = await browser.newPage({ viewport: { width: 1440, height: 1000 } })
    await addAdminSession(adminDesktop)
    await addEmptyAdminApiRoutes(adminDesktop)
    await adminDesktop.goto('http://127.0.0.1:4173/admin', { waitUntil: 'networkidle' })
    await adminDesktop.screenshot({
      path: path.join(outputDir, 'admin-dashboard-desktop.png'),
      fullPage: true,
    })
    await adminDesktop.goto('http://127.0.0.1:4173/admin/orders', { waitUntil: 'networkidle' })
    await adminDesktop.screenshot({
      path: path.join(outputDir, 'admin-orders-desktop.png'),
      fullPage: true,
    })
    await adminDesktop.goto('http://127.0.0.1:4173/admin/ai', { waitUntil: 'networkidle' })
    await adminDesktop.screenshot({
      path: path.join(outputDir, 'admin-ai-desktop.png'),
      fullPage: true,
    })
    await adminDesktop.goto('http://127.0.0.1:4173/admin/knowledge', { waitUntil: 'networkidle' })
    await adminDesktop.screenshot({
      path: path.join(outputDir, 'admin-knowledge-desktop.png'),
      fullPage: true,
    })
    await adminDesktop.goto('http://127.0.0.1:4173/admin/operations', { waitUntil: 'networkidle' })
    await adminDesktop.screenshot({
      path: path.join(outputDir, 'admin-operations-desktop.png'),
      fullPage: true,
    })
    await adminDesktop.locator('.report-row').first().click()
    await adminDesktop.locator('.markdown-preview').waitFor()
    await adminDesktop.screenshot({
      path: path.join(outputDir, 'admin-report-preview-desktop.png'),
      fullPage: true,
    })

    const mobile = await browser.newPage({ viewport: { width: 390, height: 844 }, isMobile: true })
    await addEmptyApiRoutes(mobile)
    await mobile.goto('http://127.0.0.1:4173/', { waitUntil: 'networkidle' })
    await mobile.screenshot({ path: path.join(outputDir, 'home-mobile.png'), fullPage: true })

    const tradeMobile = await browser.newPage({ viewport: { width: 390, height: 844 }, isMobile: true })
    await addUserSession(tradeMobile)
    await addTradeApiRoutes(tradeMobile)
    await tradeMobile.goto('http://127.0.0.1:4173/cart', { waitUntil: 'networkidle' })
    await tradeMobile.screenshot({ path: path.join(outputDir, 'cart-mobile.png'), fullPage: true })
    await tradeMobile.goto('http://127.0.0.1:4173/orders', { waitUntil: 'networkidle' })
    await tradeMobile.screenshot({ path: path.join(outputDir, 'orders-mobile.png'), fullPage: true })
    await tradeMobile.goto('http://127.0.0.1:4173/ai-guide', { waitUntil: 'networkidle' })
    await tradeMobile.locator('.guide-form textarea').fill('预算 1500 元买办公椅')
    await tradeMobile.locator('.guide-controls button').click()
    await tradeMobile.locator('.recommendation-section').waitFor()
    await tradeMobile.screenshot({ path: path.join(outputDir, 'ai-guide-mobile.png'), fullPage: true })

    const adminMobile = await browser.newPage({ viewport: { width: 390, height: 844 }, isMobile: true })
    await addAdminSession(adminMobile)
    await addEmptyAdminApiRoutes(adminMobile)
    await adminMobile.goto('http://127.0.0.1:4173/admin', { waitUntil: 'networkidle' })
    await adminMobile.screenshot({
      path: path.join(outputDir, 'admin-dashboard-mobile.png'),
      fullPage: true,
    })
    await adminMobile.goto('http://127.0.0.1:4173/admin/knowledge', { waitUntil: 'networkidle' })
    await adminMobile.screenshot({
      path: path.join(outputDir, 'admin-knowledge-mobile.png'),
      fullPage: true,
    })
    await adminMobile.goto('http://127.0.0.1:4173/admin/operations', { waitUntil: 'networkidle' })
    await adminMobile.screenshot({
      path: path.join(outputDir, 'admin-operations-mobile.png'),
      fullPage: true,
    })
  } finally {
    await browser.close()
  }
}

run().catch((error) => {
  console.error(error)
  process.exitCode = 1
})
