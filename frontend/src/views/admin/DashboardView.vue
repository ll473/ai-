<script setup lang="ts">
import { Goods, MagicStick, PriceTag, ShoppingCart, Tickets } from '@element-plus/icons-vue'
import { computed, onMounted, ref } from 'vue'

import { getAgentRuns, getFunctionTools, getKnowledgeDocuments, getModelConfigs } from '../../api/ai'
import { getBrands, getCategories, getProducts } from '../../api/catalog'
import { getAdminOrders, getAdminReviews } from '../../api/trade'

const loading = ref(true)
const error = ref('')
const counts = ref({ products: 0, categories: 0, brands: 0, orders: 0, reviews: 0, runs: 0 })
const aiState = ref({ modelReady: false, apiKeyReady: false, tools: 0, documents: 0 })

const aiReady = computed(() => aiState.value.modelReady && aiState.value.apiKeyReady && aiState.value.tools >= 5)
const aiStatus = computed(() => {
  if (!aiState.value.modelReady || aiState.value.tools < 5) return '待初始化'
  return aiState.value.apiKeyReady ? '已接入' : '待配置 Key'
})

async function loadSummary() {
  loading.value = true
  error.value = ''
  try {
    const [products, categories, brands, orders, reviews, models, tools, runs, documents] = await Promise.all([
      getProducts({ page: 1, page_size: 1 }, true),
      getCategories(true),
      getBrands(true),
      getAdminOrders(1, 1),
      getAdminReviews(1, 1),
      getModelConfigs(),
      getFunctionTools(),
      getAgentRuns(),
      getKnowledgeDocuments(),
    ])
    counts.value = {
      products: products.total,
      categories: categories.length,
      brands: brands.length,
      orders: orders.total,
      reviews: reviews.total,
      runs: runs.total,
    }
    const defaultModel = models.find((model) => model.enabled && model.is_default)
    aiState.value = {
      modelReady: Boolean(defaultModel),
      apiKeyReady: Boolean(defaultModel?.has_api_key),
      tools: tools.filter((tool) => tool.enabled).length,
      documents: documents.total,
    }
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : '概览加载失败'
  } finally {
    loading.value = false
  }
}

onMounted(loadSummary)
</script>

<template>
  <div class="dashboard-view">
    <header class="admin-page-header">
      <div>
        <h1 class="page-heading">工作台</h1>
        <p>查看真实业务数据，并进入对应模块完成维护。</p>
      </div>
      <el-button :loading="loading" @click="loadSummary">刷新数据</el-button>
    </header>

    <el-alert v-if="error" :title="error" type="error" show-icon :closable="false" />

    <section v-loading="loading" class="metrics" aria-label="商城数据概览">
      <RouterLink to="/admin/products" class="metric-item focus-ring">
        <el-icon><Goods /></el-icon>
        <span>商品总数</span>
        <strong class="tabular">{{ counts.products }}</strong>
      </RouterLink>
      <RouterLink to="/admin/taxonomy" class="metric-item focus-ring">
        <el-icon><Tickets /></el-icon>
        <span>商品分类</span>
        <strong class="tabular">{{ counts.categories }}</strong>
      </RouterLink>
      <RouterLink to="/admin/taxonomy" class="metric-item focus-ring">
        <el-icon><PriceTag /></el-icon>
        <span>商品品牌</span>
        <strong class="tabular">{{ counts.brands }}</strong>
      </RouterLink>
      <RouterLink to="/admin/orders" class="metric-item focus-ring">
        <el-icon><ShoppingCart /></el-icon>
        <span>订单总数</span>
        <strong class="tabular">{{ counts.orders }}</strong>
      </RouterLink>
      <RouterLink to="/admin/reviews" class="metric-item focus-ring">
        <el-icon><Tickets /></el-icon>
        <span>评价总数</span>
        <strong class="tabular">{{ counts.reviews }}</strong>
      </RouterLink>
      <RouterLink to="/admin/ai" class="metric-item focus-ring">
        <el-icon><MagicStick /></el-icon>
        <span>Agent Run</span>
        <strong class="tabular">{{ counts.runs }}</strong>
      </RouterLink>
    </section>

    <section class="readiness-section">
      <div>
        <h2 class="section-heading">建设进度</h2>
        <p>当前工作区真实完成情况，不展示虚构经营指标。</p>
      </div>
      <div class="readiness-list">
        <div>
          <strong>商品基础</strong><span class="status-ready">可使用</span>
          <p>分类、品牌、商品、SKU、库存与图片上传接口已经建立。</p>
        </div>
        <div class="readiness-item">
          <strong>交易闭环</strong><span class="status-ready">已接入</span>
          <p>购物车、收货地址、余额充值与支付、库存预占、订单履约和已购评价均已接入。</p>
          <nav><RouterLink to="/admin/orders">订单管理</RouterLink><RouterLink to="/admin/reviews">评价管理</RouterLink></nav>
        </div>
        <div class="readiness-item">
          <strong>AI 导购 Agent</strong><span :class="aiReady ? 'status-ready' : 'status-progress'">{{ aiStatus }}</span>
          <p>
            自主决策循环、{{ aiState.tools }} 个已启用工具、商品知识库、推荐二次校验和 Agent Run/Step 时间线均已接入；
            当前知识文档 {{ aiState.documents }} 份。
          </p>
          <p v-if="!aiState.apiKeyReady" class="configuration-note">还需在 AI 配置中心保存百炼 API Key，模型调用才会正式可用。</p>
          <nav><RouterLink to="/admin/ai">AI 配置中心</RouterLink><RouterLink to="/admin/knowledge">商品知识库</RouterLink><RouterLink to="/ai-guide">进入 AI 导购</RouterLink></nav>
        </div>
      </div>
    </section>
  </div>
</template>

<style scoped>
.admin-page-header {
  display: flex;
  align-items: end;
  justify-content: space-between;
  gap: 24px;
  margin-bottom: 26px;
}

.admin-page-header p,
.readiness-section > div > p,
.readiness-list p {
  margin: 8px 0 0;
  color: var(--color-ink-500);
  line-height: 1.7;
}

.metrics {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  margin: 22px 0 42px;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-container);
  background: white;
}

.metric-item {
  display: grid;
  grid-template-columns: 28px 1fr auto;
  align-items: center;
  gap: 8px 12px;
  padding: 24px;
  border-right: 1px solid var(--color-line);
}

.metric-item:last-child {
  border-right: 0;
}

.metric-item:nth-child(3n) {
  border-right: 0;
}

.metric-item:nth-child(n + 4) {
  border-top: 1px solid var(--color-line);
}

.metric-item .el-icon {
  grid-row: 1 / 3;
  color: var(--color-brand-600);
  font-size: 22px;
}

.metric-item span {
  color: var(--color-ink-500);
  font-size: 13px;
}

.metric-item strong {
  grid-row: 1 / 3;
  grid-column: 3;
  font-size: 30px;
}

.readiness-section {
  display: grid;
  grid-template-columns: minmax(220px, 0.35fr) 1fr;
  gap: 48px;
  padding-top: 32px;
  border-top: 1px solid var(--color-line);
}

.readiness-list {
  border-top: 1px solid var(--color-line);
}

.readiness-list > div {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 6px 24px;
  padding: 18px 0;
  border-bottom: 1px solid var(--color-line);
}

.readiness-list p {
  grid-column: 1 / -1;
  font-size: 13px;
}

.readiness-item nav {
  display: flex;
  grid-column: 1 / -1;
  flex-wrap: wrap;
  gap: 8px 18px;
  margin-top: 5px;
}

.readiness-item nav a {
  color: var(--color-brand-600);
  font-size: 13px;
  font-weight: 650;
}

.readiness-list .configuration-note {
  margin-top: 0;
  color: var(--color-warning);
}

.status-ready,
.status-progress {
  font-size: 13px;
  font-weight: 650;
}

.status-ready {
  color: var(--color-success);
}

.status-progress {
  color: var(--color-warning);
}

@media (max-width: 767px) {
  .metrics,
  .readiness-section {
    grid-template-columns: 1fr;
  }

  .metric-item {
    border-right: 0;
    border-bottom: 1px solid var(--color-line);
  }

  .metric-item:last-child {
    border-bottom: 0;
  }

  .metric-item:nth-child(n) {
    border-right: 0;
  }

  .readiness-section {
    gap: 24px;
  }
}
</style>
