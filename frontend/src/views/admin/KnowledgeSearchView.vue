<script setup lang="ts">
import { ChatDotRound, Search } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'

import { askProductQuestion } from '../../api/ai'
import { getProducts } from '../../api/catalog'
import type { ProductQuestionResult } from '../../types/ai'
import type { ProductSummary } from '../../types/catalog'

const route = useRoute()
const products = ref<ProductSummary[]>([])
const productId = ref<number | null>(null)
const question = ref('')
const loading = ref(false)
const result = ref<ProductQuestionResult | null>(null)
const isQuestionPage = computed(() => route.path.includes('/operations/questions'))
const title = computed(() => isQuestionPage.value ? 'AI 商品问答' : 'Embedding 检索')
const description = computed(() => isQuestionPage.value
  ? '用客户视角验证商品知识问答，答案只引用已索引的可信资料。'
  : '输入真实问题，通过向量相似度检索最相关的商品资料片段。')

async function loadProducts() {
  try { products.value = (await getProducts({ page_size: 100 }, true)).items }
  catch (error) { ElMessage.error(error instanceof Error ? error.message : '商品加载失败') }
}
async function search() {
  if (question.value.trim().length < 2) { ElMessage.warning('请输入要检索的问题'); return }
  loading.value = true
  try { result.value = await askProductQuestion(question.value.trim(), productId.value || undefined) }
  catch (error) { ElMessage.error(error instanceof Error ? error.message : '检索失败，请确认模型和向量服务已配置') }
  finally { loading.value = false }
}
onMounted(loadProducts)
</script>

<template>
  <div>
    <header class="admin-page-header"><div><h1 class="page-heading">{{ title }}</h1><p>{{ description }}</p></div></header>
    <section class="search-card"><div class="search-heading"><span class="search-icon"><el-icon><ChatDotRound /></el-icon></span><div><strong>相似度检索</strong><p>可以限定某件商品，也可以在整个商品知识库中查找。</p></div></div><el-input v-model="question" type="textarea" :rows="5" placeholder="例如：这款笔记本适合写 Java 项目吗？售后政策是什么？" maxlength="2000" show-word-limit @keydown.ctrl.enter="search"/><div class="search-actions"><el-select v-model="productId" clearable filterable placeholder="全部商品知识" style="width:300px"><el-option v-for="product in products" :key="product.id" :label="product.name" :value="product.id"/></el-select><el-button type="primary" :icon="Search" :loading="loading" @click="search">开始检索</el-button></div></section>
    <section v-if="result" class="answer-card"><header><div><span>AI ANSWER</span><h2>回答结果</h2></div><el-tag effect="plain">{{ result.citations.length }} 条引用</el-tag></header><p class="answer">{{ result.answer }}</p><div class="citations"><article v-for="(citation,index) in result.citations" :key="`${citation.document_id}-${citation.chunk_index}`"><div><strong>引用 {{ index+1 }} · {{ citation.document_title }}</strong><el-tag size="small" type="success" effect="plain">相似度 {{ Math.round(citation.score*100) }}%</el-tag></div><p>{{ citation.excerpt }}</p><span>文档 #{{ citation.document_id }} · 片段 {{ citation.chunk_index }}</span></article><el-empty v-if="!result.citations.length" :image-size="70" description="没有找到可引用的知识片段"/></div></section>
  </div>
</template>

<style scoped>
.admin-page-header{margin-bottom:20px}.admin-page-header p{margin:7px 0 0;color:var(--color-ink-500)}.search-card,.answer-card{padding:22px;border:1px solid var(--color-line);border-radius:var(--radius-container);background:white}.search-heading{display:flex;align-items:center;gap:12px;margin-bottom:17px}.search-icon{display:grid;width:42px;height:42px;place-items:center;border-radius:10px;background:var(--color-brand-50);color:var(--color-brand-700);font-size:20px}.search-heading p{margin:4px 0 0;color:var(--color-ink-500);font-size:12px}.search-actions{display:flex;justify-content:flex-end;gap:10px;margin-top:12px}.answer-card{margin-top:16px}.answer-card>header{display:flex;align-items:start;justify-content:space-between}.answer-card header span{color:var(--color-brand-600);font-size:10px;font-weight:800;letter-spacing:.13em}.answer-card h2{margin:5px 0 0;font-size:18px}.answer{margin:18px 0;padding:18px;border-radius:10px;background:var(--color-brand-50);color:var(--color-ink-800);line-height:1.8}.citations{display:grid;gap:10px}.citations article{padding:15px;border:1px solid var(--color-line);border-radius:9px}.citations article>div{display:flex;justify-content:space-between;gap:12px}.citations p{margin:10px 0;color:var(--color-ink-700);font-size:13px;line-height:1.7}.citations article>span{color:var(--color-ink-400);font-size:11px}@media(max-width:767px){.search-actions{align-items:stretch;flex-direction:column}.search-actions .el-select{width:100%!important}}
</style>
