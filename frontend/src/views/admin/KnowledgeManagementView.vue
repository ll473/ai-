<script setup lang="ts">
import { Connection, Plus, Refresh, UploadFilled } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { onMounted, reactive, ref } from 'vue'

import {
  createKnowledgeDocument,
  getKnowledgeDocuments,
  indexKnowledgeDocument,
  syncProductKnowledge,
} from '../../api/ai'
import { getProducts } from '../../api/catalog'
import type { KnowledgeDocument } from '../../types/ai'
import type { ProductSummary } from '../../types/catalog'

const loading = ref(true)
const documents = ref<KnowledgeDocument[]>([])
const products = ref<ProductSummary[]>([])
const dialogOpen = ref(false)
const saving = ref(false)
const syncing = ref(false)
const indexingId = ref<number | null>(null)
const syncProductId = ref<number | null>(null)
const form = reactive({ title: '', product_id: null as number | null, content: '' })

const statusLabel: Record<string, string> = {
  PENDING: '待索引', PROCESSING: '处理中', READY: '可检索', FAILED: '失败',
}
const statusType = (status: string) => status === 'READY' ? 'success' : status === 'FAILED' ? 'danger' : 'warning'

async function load() {
  loading.value = true
  try {
    const [documentData, productData] = await Promise.all([
      getKnowledgeDocuments(),
      getProducts({ page_size: 100 }, true),
    ])
    documents.value = documentData.items
    products.value = productData.items
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '知识库加载失败')
  } finally {
    loading.value = false
  }
}

async function createDocument() {
  if (!form.title.trim() || !form.content.trim()) {
    ElMessage.warning('请填写标题和资料正文')
    return
  }
  saving.value = true
  try {
    await createKnowledgeDocument({
      title: form.title,
      source_type: 'MANUAL',
      source_id: null,
      product_id: form.product_id,
      content: form.content,
    })
    ElMessage.success('资料已保存，请执行索引')
    dialogOpen.value = false
    Object.assign(form, { title: '', product_id: null, content: '' })
    await load()
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '保存失败')
  } finally {
    saving.value = false
  }
}

async function syncProduct() {
  if (!syncProductId.value) {
    ElMessage.warning('请选择商品')
    return
  }
  syncing.value = true
  try {
    await syncProductKnowledge(syncProductId.value)
    ElMessage.success('商品详情与参数已同步，请执行索引')
    await load()
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '同步失败')
  } finally {
    syncing.value = false
  }
}

async function indexDocument(document: KnowledgeDocument) {
  indexingId.value = document.id
  try {
    await indexKnowledgeDocument(document.id)
    ElMessage.success('向量索引已更新')
    await load()
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '索引失败')
    await load()
  } finally {
    indexingId.value = null
  }
}

onMounted(load)
</script>

<template>
  <div class="knowledge-page">
    <header class="admin-page-header">
      <div>
        <span class="eyebrow">RAG KNOWLEDGE</span>
        <h1 class="page-heading">商品知识库</h1>
        <p>资料先切片并写入 Qdrant，用户问答只引用已完成索引的真实片段。</p>
      </div>
      <div class="header-actions">
        <el-button :icon="Refresh" @click="load">刷新</el-button>
        <el-button type="primary" :icon="Plus" @click="dialogOpen = true">新增资料</el-button>
      </div>
    </header>

    <section class="sync-panel">
      <div class="sync-panel__icon"><el-icon><Connection /></el-icon></div>
      <div>
        <strong>从商品资料生成知识文档</strong>
        <p>同步商品标题、副标题、详情、参数与规格；价格和库存仍由 Function Tool 实时查询。</p>
      </div>
      <el-select v-model="syncProductId" filterable placeholder="选择商品" style="width: 260px">
        <el-option v-for="product in products" :key="product.id" :label="product.name" :value="product.id" />
      </el-select>
      <el-button :icon="UploadFilled" :loading="syncing" @click="syncProduct">同步资料</el-button>
    </section>

    <el-table class="desktop-documents" v-loading="loading" :data="documents" empty-text="暂无知识资料">
      <el-table-column label="资料" min-width="280">
        <template #default="{ row }">
          <div class="document-cell">
            <strong>{{ row.title }}</strong>
            <span>{{ row.source_type }} · {{ row.product_id ? `商品 #${row.product_id}` : '通用资料' }}</span>
          </div>
        </template>
      </el-table-column>
      <el-table-column label="索引状态" width="130">
        <template #default="{ row }">
          <el-tag :type="statusType(row.status)" effect="plain">{{ statusLabel[row.status] }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="片段" width="90" align="center">
        <template #default="{ row }">{{ row.chunk_count }}</template>
      </el-table-column>
      <el-table-column label="更新时间" width="180">
        <template #default="{ row }">{{ new Date(row.updated_at).toLocaleString('zh-CN') }}</template>
      </el-table-column>
      <el-table-column label="错误" min-width="190" show-overflow-tooltip>
        <template #default="{ row }">{{ row.error_message || '—' }}</template>
      </el-table-column>
      <el-table-column label="操作" width="110" align="right">
        <template #default="{ row }">
          <el-button
            link type="primary" :loading="indexingId === row.id"
            :disabled="row.status === 'PROCESSING'" @click="indexDocument(row)"
          >{{ row.status === 'READY' ? '重新索引' : '执行索引' }}</el-button>
        </template>
      </el-table-column>
    </el-table>

    <div class="mobile-documents" v-loading="loading">
      <article v-for="document in documents" :key="document.id">
        <div class="mobile-document__top">
          <strong>{{ document.title }}</strong>
          <el-tag :type="statusType(document.status)" effect="plain">{{ statusLabel[document.status] }}</el-tag>
        </div>
        <p>{{ document.source_type }} · {{ document.product_id ? `商品 #${document.product_id}` : '通用资料' }}</p>
        <div class="mobile-document__meta">
          <span>{{ document.chunk_count }} 个片段</span>
          <span>{{ new Date(document.updated_at).toLocaleDateString('zh-CN') }}</span>
        </div>
        <p v-if="document.error_message" class="mobile-document__error">{{ document.error_message }}</p>
        <el-button
          type="primary" plain :loading="indexingId === document.id"
          :disabled="document.status === 'PROCESSING'" @click="indexDocument(document)"
        >{{ document.status === 'READY' ? '重新索引' : '执行索引' }}</el-button>
      </article>
    </div>

    <el-dialog v-model="dialogOpen" title="新增知识资料" width="min(720px, 94vw)">
      <el-form label-position="top">
        <el-form-item label="资料标题"><el-input v-model="form.title" maxlength="255" /></el-form-item>
        <el-form-item label="关联商品（可选）">
          <el-select v-model="form.product_id" clearable filterable style="width: 100%">
            <el-option v-for="product in products" :key="product.id" :label="product.name" :value="product.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="资料正文">
          <el-input v-model="form.content" type="textarea" :rows="14" maxlength="100000" show-word-limit />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogOpen = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="createDocument">保存资料</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.admin-page-header { display: flex; align-items: end; justify-content: space-between; gap: 20px; margin-bottom: 24px; }
.admin-page-header p { margin: 8px 0 0; color: var(--color-ink-500); }
.eyebrow { color: var(--color-brand-600); font-size: 11px; font-weight: 750; letter-spacing: .14em; }
.header-actions { display: flex; gap: 10px; }
.sync-panel { display: grid; grid-template-columns: auto 1fr auto auto; align-items: center; gap: 18px; margin-bottom: 22px; padding: 20px; border: 1px solid var(--color-line); border-radius: var(--radius-container); background: var(--color-surface); }
.sync-panel__icon { display: grid; width: 42px; height: 42px; place-items: center; border-radius: 10px; background: var(--color-brand-50); color: var(--color-brand-700); font-size: 20px; }
.sync-panel p { margin: 5px 0 0; color: var(--color-ink-500); font-size: 13px; }
.document-cell { display: grid; gap: 5px; }
.document-cell span { color: var(--color-ink-500); font-size: 12px; }
.mobile-documents { display: none; }
@media (max-width: 900px) { .sync-panel { grid-template-columns: auto 1fr; }.sync-panel .el-select, .sync-panel .el-button { grid-column: 1 / -1; width: 100% !important; } }
@media (max-width: 767px) { .admin-page-header { align-items: start; flex-direction: column; }.header-actions { width: 100%; }.header-actions .el-button { flex: 1; }.desktop-documents { display: none; }.mobile-documents { display: grid; gap: 12px; }.mobile-documents article { padding: 18px; border: 1px solid var(--color-line); border-radius: 12px; background: white; }.mobile-document__top { display: flex; align-items: start; justify-content: space-between; gap: 12px; }.mobile-documents article > p { margin: 9px 0; color: var(--color-ink-500); font-size: 12px; }.mobile-document__meta { display: flex; justify-content: space-between; margin: 14px 0; padding-top: 12px; border-top: 1px solid var(--color-line); color: var(--color-ink-500); font-size: 12px; }.mobile-documents .el-button { width: 100%; }.mobile-documents .mobile-document__error { color: var(--color-danger); } }
</style>
