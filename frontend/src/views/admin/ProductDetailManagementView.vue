<script setup lang="ts">
import { Delete, Plus, Refresh, Search } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { computed, onMounted, reactive, ref } from 'vue'

import { getBrands, getCategories, getProduct, getProducts, updateProduct, updateProductSku } from '../../api/catalog'
import type { Brand, Category, ProductDetail, ProductSku, ProductSummary } from '../../types/catalog'

type ParameterRow = { key: string; value: string }
type ContentFields = { package_list: string; after_sale: string; ai_summary: string }
type EditableSku = ProductSku & { priceValue: number; marketPriceValue: number | null }

const loading = ref(false)
const saving = ref(false)
const keyword = ref('')
const products = ref<ProductSummary[]>([])
const categories = ref<Category[]>([])
const brands = ref<Brand[]>([])
const selectedId = ref<number | null>(null)
const detail = ref<ProductDetail | null>(null)
const form = reactive({ subtitle: '', detail_markdown: '', status: 'DRAFT' as ProductDetail['status'] })
const content = reactive<ContentFields>({ package_list: '', after_sale: '', ai_summary: '' })
const parameters = ref<ParameterRow[]>([])
const skus = ref<EditableSku[]>([])

const filteredProducts = computed(() => {
  const text = keyword.value.trim().toLowerCase()
  if (!text) return products.value
  return products.value.filter((item) => `${item.name} ${item.product_no}`.toLowerCase().includes(text))
})
const categoryName = computed(() => categories.value.find((item) => item.id === detail.value?.category_id)?.name || '未分类')
const brandName = computed(() => brands.value.find((item) => item.id === detail.value?.brand_id)?.name || '无品牌')

async function loadProducts() {
  loading.value = true
  try {
    const [productData, categoryData, brandData] = await Promise.all([
      getProducts({ page_size: 100 }, true), getCategories(true), getBrands(true),
    ])
    products.value = productData.items
    categories.value = categoryData
    brands.value = brandData
    if (!selectedId.value && products.value.length) await selectProduct(products.value[0].id)
  } catch (error) { ElMessage.error(error instanceof Error ? error.message : '商品资料加载失败') }
  finally { loading.value = false }
}

async function selectProduct(id: number) {
  selectedId.value = id
  try {
    const data = await getProduct(id, true)
    detail.value = data
    Object.assign(form, { subtitle: data.subtitle || '', detail_markdown: data.detail_markdown || '', status: data.status })
    const raw = data.parameters || {}
    const reserved = (raw.__content && typeof raw.__content === 'object' ? raw.__content : {}) as Partial<ContentFields>
    Object.assign(content, { package_list: reserved.package_list || '', after_sale: reserved.after_sale || '', ai_summary: reserved.ai_summary || '' })
    parameters.value = Object.entries(raw).filter(([key]) => key !== '__content').map(([key, value]) => ({ key, value: typeof value === 'string' ? value : JSON.stringify(value) }))
    skus.value = data.skus.map((sku) => ({ ...sku, priceValue: Number(sku.price), marketPriceValue: sku.market_price ? Number(sku.market_price) : null }))
  } catch (error) { ElMessage.error(error instanceof Error ? error.message : '商品详情加载失败') }
}

function addParameter() { parameters.value.push({ key: '', value: '' }) }

async function save() {
  if (!detail.value) return
  saving.value = true
  try {
    const mapped: Record<string, unknown> = {}
    for (const item of parameters.value) if (item.key.trim()) mapped[item.key.trim()] = item.value.trim()
    mapped.__content = { ...content }
    await updateProduct(detail.value.id, {
      subtitle: form.subtitle || null,
      detail_markdown: form.detail_markdown || null,
      parameters: mapped,
      status: form.status,
    })
    await Promise.all(skus.value.map((sku) => updateProductSku(sku.id, {
      price: sku.priceValue,
      market_price: sku.marketPriceValue,
      stock: sku.stock,
      enabled: sku.enabled,
    })))
    ElMessage.success('商品详情、参数和库存已保存')
    await selectProduct(detail.value.id)
    await loadProducts()
  } catch (error) { ElMessage.error(error instanceof Error ? error.message : '保存失败') }
  finally { saving.value = false }
}

onMounted(loadProducts)
</script>

<template>
  <div class="detail-admin" v-loading="loading">
    <header class="admin-page-header"><div><h1 class="page-heading">商品详情与参数</h1><p>维护商品介绍、包装与售后信息、结构化规格和实际库存。</p></div><div><el-button :icon="Refresh" @click="loadProducts">刷新</el-button><el-button type="primary" :loading="saving" :disabled="!detail" @click="save">保存详情</el-button></div></header>

    <div class="detail-workspace">
      <aside class="product-picker">
        <div class="picker-heading"><strong>选择商品</strong><span>{{ filteredProducts.length }} 件</span></div>
        <el-input v-model="keyword" clearable :prefix-icon="Search" placeholder="搜索商品名称或编号" />
        <div class="product-list">
          <button v-for="product in filteredProducts" :key="product.id" type="button" :class="{active:selectedId===product.id}" @click="selectProduct(product.id)">
            <el-image :src="product.main_image_url || ''" fit="cover"><template #error><div class="image-fallback">图</div></template></el-image>
            <span><strong>{{ product.name }}</strong><small>{{ product.product_no }}</small><b>¥{{ Number(product.min_price).toFixed(2) }}</b></span>
          </button>
        </div>
      </aside>

      <main v-if="detail" class="editor-column">
        <section class="product-summary">
          <el-image :src="detail.main_image_url || ''" fit="cover" />
          <div><div class="summary-tags"><el-tag :type="detail.status==='ON_SALE'?'success':'info'">{{ detail.status==='ON_SALE'?'上架':'未上架' }}</el-tag><span>{{ categoryName }}</span><span>{{ brandName }}</span></div><h2>{{ detail.name }}</h2><p>{{ detail.product_no }}</p></div>
          <el-select v-model="form.status" style="width:120px"><el-option label="草稿" value="DRAFT"/><el-option label="上架" value="ON_SALE"/><el-option label="下架" value="OFF_SALE"/></el-select>
        </section>

        <section class="editor-card"><div class="section-title"><div><h3>商品内容</h3><p>面向客户展示的信息，不包含后台执行过程。</p></div></div><el-form label-position="top"><el-form-item label="商品卖点"><el-input v-model="form.subtitle" maxlength="500" show-word-limit/></el-form-item><el-form-item label="商品详情"><el-input v-model="form.detail_markdown" type="textarea" :rows="8" maxlength="20000" show-word-limit/></el-form-item><div class="content-grid"><el-form-item label="包装清单"><el-input v-model="content.package_list" type="textarea" :rows="4"/></el-form-item><el-form-item label="售后说明"><el-input v-model="content.after_sale" type="textarea" :rows="4"/></el-form-item></div><el-form-item label="AI 摘要（仅后台与知识库使用）"><el-input v-model="content.ai_summary" type="textarea" :rows="3"/></el-form-item></el-form></section>

        <section class="editor-card"><div class="section-title"><div><h3>商品参数</h3><p>结构化参数会用于商品详情、筛选和 AI 查询。</p></div><el-button :icon="Plus" @click="addParameter">新增参数</el-button></div><div class="parameter-list"><div v-for="(item,index) in parameters" :key="index"><el-input v-model="item.key" placeholder="参数名称"/><el-input v-model="item.value" placeholder="参数值"/><el-button text type="danger" :icon="Delete" aria-label="删除参数" @click="parameters.splice(index,1)"/></div><el-empty v-if="!parameters.length" :image-size="60" description="暂无结构化参数"/></div></section>

        <section class="editor-card"><div class="section-title"><div><h3>规格与库存</h3><p>价格和库存由实时工具查询，保存后立即生效。</p></div></div><el-table :data="skus" empty-text="该商品暂无 SKU"><el-table-column prop="name" label="规格" min-width="200"/><el-table-column label="售价" width="150"><template #default="{row}"><el-input-number v-model="row.priceValue" :min="0.01" :precision="2" controls-position="right"/></template></el-table-column><el-table-column label="原价" width="150"><template #default="{row}"><el-input-number v-model="row.marketPriceValue" :min="0.01" :precision="2" controls-position="right"/></template></el-table-column><el-table-column label="库存" width="140"><template #default="{row}"><el-input-number v-model="row.stock" :min="0" controls-position="right"/></template></el-table-column><el-table-column label="可售" width="90" align="center"><template #default="{row}"><el-switch v-model="row.enabled"/></template></el-table-column></el-table></section>
      </main>
      <el-empty v-else class="editor-empty" description="请选择一个商品" />
    </div>
  </div>
</template>

<style scoped>
.admin-page-header{display:flex;align-items:end;justify-content:space-between;gap:20px;margin-bottom:20px}.admin-page-header p{margin:7px 0 0;color:var(--color-ink-500)}.admin-page-header>div:last-child{display:flex;gap:10px}.detail-workspace{display:grid;grid-template-columns:320px minmax(0,1fr);align-items:start;gap:16px}.product-picker,.product-summary,.editor-card,.editor-empty{border:1px solid var(--color-line);border-radius:var(--radius-container);background:white}.product-picker{position:sticky;top:92px;padding:15px}.picker-heading{display:flex;justify-content:space-between;margin-bottom:13px}.picker-heading span{color:var(--color-ink-500);font-size:12px}.product-list{display:grid;gap:8px;max-height:calc(100vh - 230px);margin-top:12px;overflow-y:auto}.product-list button{display:grid;grid-template-columns:62px 1fr;gap:11px;width:100%;padding:9px;border:1px solid transparent;border-radius:10px;background:transparent;text-align:left;cursor:pointer}.product-list button:hover,.product-list button.active{border-color:var(--color-brand-300);background:var(--color-brand-50)}.product-list .el-image,.image-fallback{width:62px;height:62px;border-radius:8px;background:var(--color-ground)}.image-fallback{display:grid;place-items:center;color:var(--color-ink-400)}.product-list button>span{display:grid;min-width:0;gap:4px}.product-list strong,.product-list small{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.product-list small{color:var(--color-ink-500);font-size:11px}.product-list b{color:#c2412d;font-size:13px}.editor-column{display:grid;gap:14px}.product-summary{display:grid;grid-template-columns:66px 1fr auto;align-items:center;gap:14px;padding:15px 18px}.product-summary>.el-image{width:66px;height:66px;border-radius:9px}.product-summary h2{margin:7px 0 4px;font-size:20px}.product-summary p{margin:0;color:var(--color-ink-500);font-size:12px}.summary-tags{display:flex;gap:8px;align-items:center;color:var(--color-ink-500);font-size:12px}.editor-card{padding:20px}.section-title{display:flex;align-items:end;justify-content:space-between;gap:14px;margin-bottom:18px}.section-title h3{margin:0;font-size:17px}.section-title p{margin:5px 0 0;color:var(--color-ink-500);font-size:12px}.content-grid{display:grid;grid-template-columns:1fr 1fr;gap:14px}.parameter-list{display:grid;gap:9px}.parameter-list>div{display:grid;grid-template-columns:minmax(160px,.4fr) 1fr auto;gap:9px}.editor-empty{min-height:400px}
@media(max-width:1050px){.detail-workspace{grid-template-columns:270px minmax(0,1fr)}.content-grid{grid-template-columns:1fr}}@media(max-width:767px){.admin-page-header{align-items:start;flex-direction:column}.detail-workspace{grid-template-columns:1fr}.product-picker{position:static}.product-list{max-height:330px}.product-summary{grid-template-columns:54px 1fr}.product-summary>.el-image{width:54px;height:54px}.product-summary>.el-select{grid-column:1/-1;width:100%!important}.editor-card{overflow-x:auto}.editor-card .el-table{min-width:700px}.parameter-list>div{grid-template-columns:1fr auto}.parameter-list>div .el-input:first-child{grid-column:1/-1}}
</style>
