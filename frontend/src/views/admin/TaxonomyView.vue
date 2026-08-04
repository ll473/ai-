<script setup lang="ts">
import { Plus } from '@element-plus/icons-vue'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { onMounted, reactive, ref } from 'vue'

import {
  createBrand,
  createCategory,
  getBrands,
  getCategories,
  updateBrand,
  updateCategory,
} from '../../api/catalog'
import type { Brand, Category } from '../../types/catalog'

const activeTab = ref('categories')
const categories = ref<Category[]>([])
const brands = ref<Brand[]>([])
const loading = ref(true)
const error = ref('')
const categoryDialog = ref(false)
const brandDialog = ref(false)
const saving = ref(false)
const editingCategoryId = ref<number | null>(null)
const editingBrandId = ref<number | null>(null)
const categoryFormRef = ref<FormInstance>()
const brandFormRef = ref<FormInstance>()
const categoryForm = reactive({
  name: '',
  slug: '',
  parent_id: null as number | null,
  icon_url: null as string | null,
  sort_order: 0,
  enabled: true,
})
const brandForm = reactive({
  name: '',
  slug: '',
  logo_url: null as string | null,
  description: '',
  enabled: true,
})
const baseRules: FormRules = {
  name: [{ required: true, message: '请输入名称', trigger: 'blur' }],
  slug: [
    { required: true, message: '请输入英文标识', trigger: 'blur' },
    { pattern: /^[a-z0-9-]+$/, message: '只能使用小写字母、数字和连字符', trigger: 'blur' },
  ],
}

async function loadData() {
  loading.value = true
  error.value = ''
  try {
    const [categoryData, brandData] = await Promise.all([getCategories(true), getBrands(true)])
    categories.value = categoryData
    brands.value = brandData
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : '分类与品牌加载失败'
  } finally {
    loading.value = false
  }
}

function openCategory(item?: Category) {
  editingCategoryId.value = item?.id || null
  categoryForm.name = item?.name || ''
  categoryForm.slug = item?.slug || ''
  categoryForm.parent_id = item?.parent_id || null
  categoryForm.icon_url = item?.icon_url || null
  categoryForm.sort_order = item?.sort_order || 0
  categoryForm.enabled = item?.enabled ?? true
  categoryDialog.value = true
}

function openBrand(item?: Brand) {
  editingBrandId.value = item?.id || null
  brandForm.name = item?.name || ''
  brandForm.slug = item?.slug || ''
  brandForm.logo_url = item?.logo_url || null
  brandForm.description = item?.description || ''
  brandForm.enabled = item?.enabled ?? true
  brandDialog.value = true
}

async function saveCategory() {
  const valid = await categoryFormRef.value?.validate().catch(() => false)
  if (!valid) return
  saving.value = true
  try {
    const payload = { ...categoryForm }
    if (editingCategoryId.value) {
      await updateCategory(editingCategoryId.value, payload)
    } else {
      await createCategory(payload)
    }
    ElMessage.success(editingCategoryId.value ? '分类更新成功' : '分类创建成功')
    categoryDialog.value = false
    await loadData()
  } catch (cause) {
    ElMessage.error(cause instanceof Error ? cause.message : '分类保存失败')
  } finally {
    saving.value = false
  }
}

async function saveBrand() {
  const valid = await brandFormRef.value?.validate().catch(() => false)
  if (!valid) return
  saving.value = true
  try {
    const payload = { ...brandForm, description: brandForm.description || null }
    if (editingBrandId.value) {
      await updateBrand(editingBrandId.value, payload)
    } else {
      await createBrand(payload)
    }
    ElMessage.success(editingBrandId.value ? '品牌更新成功' : '品牌创建成功')
    brandDialog.value = false
    await loadData()
  } catch (cause) {
    ElMessage.error(cause instanceof Error ? cause.message : '品牌保存失败')
  } finally {
    saving.value = false
  }
}

function parentName(parentId: number | null) {
  return categories.value.find((item) => item.id === parentId)?.name || '一级分类'
}

onMounted(loadData)
</script>

<template>
  <div class="taxonomy-view">
    <header class="admin-page-header">
      <div>
        <h1 class="page-heading">分类与品牌</h1>
        <p>维护商品组织结构。停用后不会出现在用户商城筛选项中。</p>
      </div>
    </header>

    <el-alert v-if="error" :title="error" type="error" show-icon :closable="false" class="error-alert" />

    <el-tabs v-model="activeTab" class="taxonomy-tabs">
      <el-tab-pane label="商品分类" name="categories">
        <div class="tab-actions">
          <span>共 {{ categories.length }} 个分类</span>
          <el-button type="primary" :icon="Plus" @click="openCategory()">新增分类</el-button>
        </div>
        <el-table v-loading="loading" :data="categories" row-key="id" empty-text="暂无分类">
          <el-table-column prop="name" label="分类名称" min-width="180" />
          <el-table-column label="上级分类" min-width="150">
            <template #default="{ row }">{{ parentName(row.parent_id) }}</template>
          </el-table-column>
          <el-table-column prop="slug" label="英文标识" min-width="170" />
          <el-table-column prop="sort_order" label="排序" width="90" align="right" />
          <el-table-column label="状态" width="100">
            <template #default="{ row }">
              <el-tag :type="row.enabled ? 'success' : 'info'" effect="plain">
                {{ row.enabled ? '启用' : '停用' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="100" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" @click="openCategory(row)">编辑</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <el-tab-pane label="商品品牌" name="brands">
        <div class="tab-actions">
          <span>共 {{ brands.length }} 个品牌</span>
          <el-button type="primary" :icon="Plus" @click="openBrand()">新增品牌</el-button>
        </div>
        <el-table v-loading="loading" :data="brands" row-key="id" empty-text="暂无品牌">
          <el-table-column prop="name" label="品牌名称" min-width="200" />
          <el-table-column prop="slug" label="英文标识" min-width="180" />
          <el-table-column prop="description" label="品牌说明" min-width="260" show-overflow-tooltip />
          <el-table-column label="状态" width="100">
            <template #default="{ row }">
              <el-tag :type="row.enabled ? 'success' : 'info'" effect="plain">
                {{ row.enabled ? '启用' : '停用' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="100" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" @click="openBrand(row)">编辑</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>
    </el-tabs>

    <el-dialog
      v-model="categoryDialog"
      :title="editingCategoryId ? '编辑分类' : '新增分类'"
      width="min(560px, calc(100% - 32px))"
    >
      <el-form ref="categoryFormRef" :model="categoryForm" :rules="baseRules" label-position="top">
        <div class="form-grid">
          <el-form-item label="分类名称" prop="name"><el-input v-model="categoryForm.name" /></el-form-item>
          <el-form-item label="英文标识" prop="slug"><el-input v-model="categoryForm.slug" /></el-form-item>
        </div>
        <el-form-item label="上级分类" prop="parent_id">
          <el-select v-model="categoryForm.parent_id" clearable placeholder="不选择则为一级分类">
            <el-option
              v-for="item in categories.filter((category) => category.id !== editingCategoryId)"
              :key="item.id"
              :label="item.name"
              :value="item.id"
            />
          </el-select>
        </el-form-item>
        <div class="form-grid">
          <el-form-item label="排序" prop="sort_order">
            <el-input-number v-model="categoryForm.sort_order" :min="0" controls-position="right" />
          </el-form-item>
          <el-form-item label="启用状态" prop="enabled">
            <el-switch v-model="categoryForm.enabled" active-text="启用" inactive-text="停用" />
          </el-form-item>
        </div>
      </el-form>
      <template #footer>
        <el-button @click="categoryDialog = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveCategory">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="brandDialog"
      :title="editingBrandId ? '编辑品牌' : '新增品牌'"
      width="min(560px, calc(100% - 32px))"
    >
      <el-form ref="brandFormRef" :model="brandForm" :rules="baseRules" label-position="top">
        <div class="form-grid">
          <el-form-item label="品牌名称" prop="name"><el-input v-model="brandForm.name" /></el-form-item>
          <el-form-item label="英文标识" prop="slug"><el-input v-model="brandForm.slug" /></el-form-item>
        </div>
        <el-form-item label="品牌说明" prop="description">
          <el-input v-model="brandForm.description" type="textarea" :rows="4" maxlength="1000" show-word-limit />
        </el-form-item>
        <el-form-item label="启用状态" prop="enabled">
          <el-switch v-model="brandForm.enabled" active-text="启用" inactive-text="停用" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="brandDialog = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveBrand">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.admin-page-header {
  margin-bottom: 18px;
}

.admin-page-header p {
  margin: 8px 0 0;
  color: var(--color-ink-500);
  line-height: 1.7;
}

.error-alert {
  margin-bottom: 16px;
}

.taxonomy-tabs {
  padding: 0 20px 20px;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-container);
  background: white;
}

.tab-actions {
  display: flex;
  min-height: 64px;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
}

.tab-actions span {
  color: var(--color-ink-500);
  font-size: 13px;
}

.form-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

@media (max-width: 767px) {
  .taxonomy-tabs {
    padding: 0 12px 12px;
  }

  .form-grid {
    grid-template-columns: 1fr;
    gap: 0;
  }
}
</style>

