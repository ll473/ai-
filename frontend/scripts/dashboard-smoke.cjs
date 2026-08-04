const path = require('node:path')
const playwrightModule = process.env.VISUAL_CHECK_PLAYWRIGHT || 'playwright'
const { chromium } = require(playwrightModule)

async function run() {
  const account = process.env.ADMIN_ACCOUNT
  const password = process.env.ADMIN_PASSWORD
  if (!account || !password) throw new Error('ADMIN_ACCOUNT and ADMIN_PASSWORD are required')
  const browser = await chromium.launch({
    headless: true,
    executablePath: process.env.VISUAL_CHECK_BROWSER || chromium.executablePath(),
  })
  try {
    const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } })
    await page.goto('http://localhost:5173/login', { waitUntil: 'networkidle' })
    await page.locator('input[autocomplete="username"]').fill(account)
    await page.locator('input[autocomplete="current-password"]').fill(password)
    await page.locator('.submit-button').click()
    await page.waitForURL('**/admin')
    await page.locator('.readiness-list').waitFor()
    await page.waitForFunction(() => {
      const text = document.querySelector('.readiness-list')?.textContent || ''
      return text.includes('5 个已启用工具')
    })
    const readiness = await page.locator('.readiness-list').innerText()
    console.log(readiness)
    if (!readiness.includes('交易闭环\n已接入')) throw new Error('Trade readiness is not connected')
    if (!readiness.includes('AI 导购 Agent\n已接入')) throw new Error('AI readiness is not connected')
    if (process.env.VISUAL_CHECK_OUTPUT) {
      await page.screenshot({
        path: path.join(process.env.VISUAL_CHECK_OUTPUT, 'admin-dashboard-live.png'),
        fullPage: true,
      })
    }

    await page.goto('http://localhost:5173/admin/ai', { waitUntil: 'networkidle' })
    await page.getByRole('heading', { name: 'AI 配置中心' }).waitFor()
    const configuredKey = page.getByText('已配置', { exact: true }).first()
    await configuredKey.waitFor()
    await page.getByRole('button', { name: '编辑', exact: true }).first().click()
    await page.getByRole('dialog').getByText('编辑模型配置', { exact: true }).waitFor()
    const modelValues = await page.getByRole('dialog').locator('input').evaluateAll((inputs) =>
      inputs.map((input) => input.value),
    )
    if (!modelValues.includes('qwen3.7-plus') || !modelValues.includes('qwen3.7-text-embedding')) {
      throw new Error('Configured Alibaba Cloud models are not shown in edit dialog')
    }
    if (process.env.VISUAL_CHECK_OUTPUT) {
      await page.screenshot({
        path: path.join(process.env.VISUAL_CHECK_OUTPUT, 'admin-ai-edit-live.png'),
        fullPage: true,
      })
    }

    await page.goto('http://localhost:5173/', { waitUntil: 'networkidle' })
    await page.getByRole('heading', { name: '最新上架' }).waitFor()
    await page.waitForFunction(() => {
      const images = [...document.querySelectorAll('.product-grid img')]
      return images.length === 4 && images.every((image) => image.complete && image.naturalWidth > 0)
    })
    console.log('storefront: 4 product images loaded')
    if (process.env.VISUAL_CHECK_OUTPUT) {
      await page.screenshot({
        path: path.join(process.env.VISUAL_CHECK_OUTPUT, 'storefront-demo-products.png'),
        fullPage: true,
      })
    }
  } finally {
    await browser.close()
  }
}

run().catch((error) => {
  console.error(error)
  process.exitCode = 1
})
