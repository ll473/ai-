<script setup lang="ts">
import { Plus, Search } from '@element-plus/icons-vue'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { onMounted, reactive, ref } from 'vue'

import { createProduct, getBrands, getCategories, getProduct, getProducts, updateProduct } from '../../api/catalog'
import type { ProductPayload } from '../../api/catalog'
import type { Brand, Category, ProductStatus, ProductSummary } from '../../types/catalog'

const products = ref<ProductSummary[]>([])
const categories = ref<Category[]>([])
const brands = ref<Brand[]>([])
const total = ref(0)
const loading = ref(true)
const error = ref('')
const dialogOpen = ref(false)
const editingId = ref<number | null>(null)
const submitting = ref(false)
const formRef = ref<FormInstance>()
const filters = reactive({ keyword: '', category_id: undefined as number | undefined, page: 1, page_size: 20 })
const form = reactive({
  category_id: undefined as number | undefined,
  brand_id: undefined as number | undefined,
  name: '',
  subtitle: '',
  product_no: '',
  status: 'DRAFT' as ProductStatus,
  main_image_url: '',
})
const rules: FormRules = {
  category_id: [{ required: true, message: '请选择商品分类', trigger: 'change' }],
  name: [{ required: true, message: '请输入商品名称', trigger: 'blur' }],
  product_no: [{ required: true, message: '请输入商品编号', trigger: 'blur' }],
}

const statusMap: Record<ProductStatus, { label: string; type: 'info' | 'success' | 'warning' }> = {
  DRAFT: { label: '草稿', type: 'info' },
  ON_SALE: { label: '在售', type: 'success' },
  OFF_SALE: { label: '下架', type: 'warning' },
}

const formatPrice = (value: string) => `¥${Number(value).toFixed(2)}`

async function loadTaxonomy() {
  const [categoryData, brandData] = await Promise.all([getCategories(true), getBrands(true)])
  categories.value = categoryData
  brands.value = brandData
}

async function loadProducts() {
  loading.value = true
  error.value = ''
  try {
    const data = await getProducts(
      {
        page: filters.page,
        page_size: filters.page_size,
        keyword: filters.keyword || undefined,
        category_id: filters.category_id,
      },
      true,
    )
    products.value = data.items
    total.value = data.total
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : '商品加载失败'
  } finally {
    loading.value = false
  }
}

function resetForm() {
  form.category_id = undefined
  form.brand_id = undefined
  form.name = ''
  form.subtitle = ''
  form.product_no = ''
  form.status = 'DRAFT'
  form.main_image_url = ''
  formRef.value?.clearValidate()
}

function openCreateDialog() {
  editingId.value = null
  resetForm()
  dialogOpen.value = true
}

async function openEditDialog(product: ProductSummary) {
  editingId.value = product.id
  try {
    const data = await getProduct(product.id, true)
    Object.assign(form, {
      category_id: data.category_id,
      brand_id: data.brand_id || undefined,
      name: data.name,
      subtitle: data.subtitle || '',
      product_no: data.product_no,
      status: data.status,
      main_image_url: data.main_image_url || '',
    })
    dialogOpen.value = true
  } catch (cause) {
    ElMessage.error(cause instanceof Error ? cause.message : '商品信息加载失败')
  }
}

async function submitProduct() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid || !form.category_id) return
  const payload: ProductPayload = {
    category_id: form.category_id,
    brand_id: form.brand_id || null,
    name: form.name,
    subtitle: form.subtitle || null,
    product_no: form.product_no,
    main_image_url: form.main_image_url || null,
    detail_markdown: null,
    parameters: null,
    status: form.status,
  }
  submitting.value = true
  try {
    if (editingId.value) await updateProduct(editingId.value, payload)
    else await createProduct(payload)
    ElMessage.success(editingId.value ? '商品信息已更新' : '商品创建成功')
    dialogOpen.value = false
    await loadProducts()
  } catch (cause) {
    ElMessage.error(cause instanceof Error ? cause.message : '商品创建失败')
  } finally {
    submitting.value = false
  }
}

onMounted(async () => {
  try {
    await loadTaxonomy()
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : '分类与品牌加载失败'
  }
  await loadProducts()
})
</script>

<template>
  <div class="product-management">
    <header class="admin-page-header">
      <div>
        <h1 class="page-heading">商品管理</h1>
        <p>维护商品基础信息。SKU、库存和图片会在商品详情管理中继续完善。</p>
      </div>
      <el-button type="primary" :icon="Plus" @click="openCreateDialog">新增商品</el-button>
    </header>

    <section class="toolbar" aria-label="商品筛选">
      <el-input v-model="filters.keyword" clearable placeholder="商品名称或编号" @keyup.enter="loadProducts">
        <template #prefix><el-icon><Search /></el-icon></template>
      </el-input>
      <el-select v-model="filters.category_id" clearable placeholder="全部分类">
        <el-option v-for="item in categories" :key="item.id" :label="item.name" :value="item.id" />
      </el-select>
      <el-button @click="loadProducts">查询</el-button>
    </section>

    <el-alert v-if="error" :title="error" type="error" show-icon :closable="false" class="error-alert" />

    <el-table v-loading="loading" :data="products" empty-text="暂无商品" row-key="id">
      <el-table-column prop="product_no" label="商品编号" min-width="140" />
      <el-table-column prop="name" label="商品" min-width="220">
        <template #default="{ row }">
          <div class="product-cell">
            <div class="product-thumb">
              <img v-if="row.main_image_url" :src="row.main_image_url" :alt="row.name" />
              <span v-else>无图</span>
            </div>
            <div><strong>{{ row.name }}</strong><span>{{ row.subtitle || '未填写副标题' }}</span></div>
          </div>
        </template>
      </el-table-column>
      <el-table-column label="价格区间" min-width="160" align="right">
        <template #default="{ row }">
          <span class="tabular">{{ formatPrice(row.min_price) }} - {{ formatPrice(row.max_price) }}</span>
        </template>
      </el-table-column>
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="statusMap[row.status as ProductStatus].type" effect="plain">
            {{ statusMap[row.status as ProductStatus].label }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="190" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="openEditDialog(row)">编辑</el-button>
          <RouterLink :to="`/admin/product-details`">
            <el-button link type="primary">详情参数</el-button>
          </RouterLink>
          <RouterLink :to="`/products/${row.id}`" target="_blank">
            <el-button link type="primary">查看</el-button>
          </RouterLink>
        </template>
      </el-table-column>
    </el-table>

    <el-pagination
      v-if="total > filters.page_size"
      class="pagination"
      background
      layout="prev, pager, next"
      :current-page="filters.page"
      :page-size="filters.page_size"
      :total="total"
      @current-change="(page: number) => { filters.page = page; loadProducts() }"
    />

    <el-dialog v-model="dialogOpen" :title="editingId ? '编辑商品信息' : '新增商品'" width="min(720px, calc(100% - 32px))" destroy-on-close>
      <el-form ref="formRef" :model="form" :rules="rules" label-position="top">
        <div class="form-grid">
          <el-form-item label="商品分类" prop="category_id">
            <el-select v-model="form.category_id" placeholder="请选择分类">
              <el-option v-for="item in categories" :key="item.id" :label="item.name" :value="item.id" />
            </el-select>
          </el-form-item>
          <el-form-item label="商品品牌" prop="brand_id">
            <el-select v-model="form.brand_id" clearable placeholder="可不选择">
              <el-option v-for="item in brands" :key="item.id" :label="item.name" :value="item.id" />
            </el-select>
          </el-form-item>
        </div>
        <el-form-item label="商品名称" prop="name">
          <el-input v-model="form.name" maxlength="255" show-word-limit />
        </el-form-item>
        <el-form-item label="商品副标题" prop="subtitle">
          <el-input v-model="form.subtitle" maxlength="500" show-word-limit />
        </el-form-item>
        <el-form-item label="商品封面地址">
          <el-input v-model="form.main_image_url" placeholder="https://..." />
        </el-form-item>
        <div class="form-grid">
          <el-form-item label="商品编号" prop="product_no">
            <el-input v-model="form.product_no" maxlength="64" />
          </el-form-item>
          <el-form-item label="发布状态" prop="status">
            <el-select v-model="form.status">
              <el-option label="草稿" value="DRAFT" />
              <el-option label="在售" value="ON_SALE" />
              <el-option label="下架" value="OFF_SALE" />
            </el-select>
          </el-form-item>
        </div>
      </el-form>
      <template #footer>
        <el-button @click="dialogOpen = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="submitProduct">{{ editingId ? '保存修改' : '创建商品' }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.admin-page-header {
  display: flex;
  align-items: end;
  justify-content: space-between;
  gap: 24px;
  margin-bottom: 24px;
}

.admin-page-header p {
  margin: 8px 0 0;
  color: var(--color-ink-500);
  line-height: 1.7;
}

.toolbar {
  display: grid;
  grid-template-columns: minmax(220px, 360px) minmax(160px, 220px) auto;
  gap: 12px;
  margin-bottom: 18px;
}

.error-alert {
  margin-bottom: 16px;
}

.product-cell {
  display: flex;
  align-items: center;
  gap: 12px;
}

.product-cell > div:last-child {
  display: grid;
  min-width: 0;
  gap: 4px;
}

.product-cell span {
  overflow: hidden;
  color: var(--color-ink-500);
  font-size: 12px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.product-thumb {
  display: grid;
  overflow: hidden;
  width: 48px;
  height: 48px;
  flex: 0 0 auto;
  place-items: center;
  border: 1px solid var(--color-line);
  border-radius: 8px;
  background: var(--color-ground);
  color: var(--color-ink-400);
  font-size: 11px;
}

.product-thumb img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.pagination {
  justify-content: flex-end;
  margin-top: 20px;
}

.form-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

@media (max-width: 767px) {
  .admin-page-header {
    align-items: flex-start;
    flex-direction: column;
  }

  .toolbar,
  .form-grid {
    grid-template-columns: 1fr;
  }
}
</style>
