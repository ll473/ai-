<script setup lang="ts">
import { Refresh, Search } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { onMounted, reactive, ref } from 'vue'

import { getKnowledgeChunks, getKnowledgeDocuments } from '../../api/ai'
import type { KnowledgeChunk, KnowledgeDocument } from '../../types/ai'

const loading = ref(false)
const chunks = ref<KnowledgeChunk[]>([])
const documents = ref<KnowledgeDocument[]>([])
const total = ref(0)
const query = reactive({ page: 1, page_size: 20, keyword: '', document_id: null as number | null })

async function load() {
  loading.value = true
  try {
    const [chunkData, documentData] = await Promise.all([
      getKnowledgeChunks({ page: query.page, page_size: query.page_size, keyword: query.keyword || undefined, document_id: query.document_id || undefined }),
      getKnowledgeDocuments(),
    ])
    chunks.value = chunkData.items; total.value = chunkData.total; documents.value = documentData.items
  } catch (error) { ElMessage.error(error instanceof Error ? error.message : '知识切片加载失败') }
  finally { loading.value = false }
}
function reset(){Object.assign(query,{page:1,keyword:'',document_id:null});load()}
onMounted(load)
</script>

<template>
  <div>
    <header class="admin-page-header"><div><h1 class="page-heading">商品知识切片</h1><p>查看知识资料拆分后的检索片段、向量状态和来源。</p></div><el-button :icon="Refresh" @click="load">刷新</el-button></header>
    <section class="strategy-card"><div><strong>900</strong><span>单片最大字符</span></div><div><strong>120</strong><span>上下文重叠字符</span></div><div><strong>{{ total }}</strong><span>当前片段</span></div><p>系统按段落优先切分，保留上下文重叠；索引成功后才会参与商品问答检索。</p></section>
    <section class="filter-bar"><el-input v-model="query.keyword" clearable :prefix-icon="Search" placeholder="搜索片段内容" @keyup.enter="query.page=1;load()"/><el-select v-model="query.document_id" clearable filterable placeholder="全部知识资料"><el-option v-for="item in documents" :key="item.id" :label="item.title" :value="item.id"/></el-select><el-button type="primary" @click="query.page=1;load()">查询</el-button><el-button @click="reset">重置</el-button></section>
    <section class="table-card"><el-table v-loading="loading" :data="chunks" empty-text="暂无知识切片"><el-table-column prop="document_title" label="资料标题" min-width="220"/><el-table-column label="关联商品" width="120"><template #default="{row}">{{ row.product_id?`商品 #${row.product_id}`:'通用资料' }}</template></el-table-column><el-table-column prop="chunk_index" label="片段序号" width="95"/><el-table-column prop="content" label="片段内容" min-width="420" show-overflow-tooltip/><el-table-column prop="token_count" label="估算 Token" width="110"/><el-table-column label="向量状态" width="110"><template #default="{row}"><el-tag :type="row.vector_point_id?'success':'warning'" effect="plain">{{ row.vector_point_id?'可检索':'待生成' }}</el-tag></template></el-table-column></el-table><el-pagination v-model:current-page="query.page" :page-size="query.page_size" :total="total" layout="prev,pager,next,total" @current-change="load"/></section>
  </div>
</template>

<style scoped>
.admin-page-header{display:flex;align-items:end;justify-content:space-between;gap:20px;margin-bottom:20px}.admin-page-header p{margin:7px 0 0;color:var(--color-ink-500)}.strategy-card{display:grid;grid-template-columns:130px 130px 130px 1fr;align-items:center;gap:10px;margin-bottom:14px;padding:18px;border:1px solid var(--color-line);border-radius:var(--radius-container);background:white}.strategy-card>div{display:grid;gap:4px;text-align:center}.strategy-card strong{color:var(--color-brand-700);font-size:24px}.strategy-card span,.strategy-card p{color:var(--color-ink-500);font-size:12px}.strategy-card p{margin:0;padding-left:16px;border-left:1px solid var(--color-line);line-height:1.7}.filter-bar{display:grid;grid-template-columns:1fr 280px auto auto;gap:10px;margin-bottom:14px;padding:16px;border:1px solid var(--color-line);border-radius:var(--radius-container);background:white}.table-card{padding:10px 16px 16px;border:1px solid var(--color-line);border-radius:var(--radius-container);background:white}.el-pagination{justify-content:flex-end;margin-top:16px}@media(max-width:767px){.admin-page-header{align-items:start;flex-direction:column}.strategy-card{grid-template-columns:repeat(3,1fr)}.strategy-card p{grid-column:1/-1;padding:12px 0 0;border-top:1px solid var(--color-line);border-left:0}.filter-bar{grid-template-columns:1fr 1fr}.filter-bar .el-input,.filter-bar .el-select{grid-column:1/-1}.table-card{overflow-x:auto}.table-card .el-table{min-width:900px}}
</style>
