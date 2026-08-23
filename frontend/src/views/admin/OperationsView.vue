<script setup lang="ts">
import { DataAnalysis, Document, MagicStick, Refresh } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'

import {
  generateOperationReport,
  generateReviewAnalysis,
  getOperationReports,
  getOperationsDashboard,
  getReviewAnalyses,
} from '../../api/ai'
import { getProducts } from '../../api/catalog'
import type { OperationReport, OperationsDashboard, ReviewAnalysis } from '../../types/ai'
import type { ProductSummary } from '../../types/catalog'

const days = ref(30)
const route = useRoute()
const section = computed(() => String(route.meta.operationSection || 'reports'))
const pageCopy = computed(() => section.value === 'reviews'
  ? ['AI 评价分析', '分析真实订单评价中的好评关键词、问题原因、售后风险和改进动作。']
  : ['AI 运营增长报告', '聚合成交、评价和导购数据，生成可复盘的运营增长报告。'])
const loading = ref(true)
const analyzing = ref(false)
const reporting = ref(false)
const dashboard = ref<OperationsDashboard | null>(null)
const analyses = ref<ReviewAnalysis[]>([])
const reports = ref<OperationReport[]>([])
const products = ref<ProductSummary[]>([])
const productId = ref<number | null>(null)
const reportDrawer = ref(false)
const activeReport = ref<OperationReport | null>(null)

const formatMoney = (value: string | number) => `¥${Number(value).toLocaleString('zh-CN', { minimumFractionDigits: 2 })}`
const formatDate = (value: string | null) => value ? new Date(value).toLocaleString('zh-CN') : '—'

const metricCards = computed(() => {
  const value = dashboard.value
  if (!value) return []
  return [
    { label: '成交金额', value: formatMoney(value.revenue), note: `${value.paid_orders} 笔已成交订单` },
    { label: '真实评价', value: value.reviews_total, note: `平均 ${value.average_rating.toFixed(1)} 分` },
    { label: '导购任务', value: value.agent_runs, note: `${value.successful_agent_runs} 次成功完成` },
    { label: '有效推荐', value: value.recommendations, note: `${value.recommendation_items} 个商品结果` },
    { label: '商品浏览', value: value.product_views, note: `${value.unique_viewers} 位访问用户` },
    { label: '浏览转化', value: `${value.conversion_rate.toFixed(1)}%`, note: '已支付订单 / 商品浏览' },
    { label: '用户咨询', value: value.questions_total, note: `${value.frequent_questions.length} 个高频问题` },
  ]
})

type MarkdownBlock = { kind: 'heading' | 'list' | 'paragraph'; text: string; level?: number }
const markdownBlocks = computed<MarkdownBlock[]>(() => {
  const content = activeReport.value?.content_markdown || ''
  return content.split('\n').map((line) => line.trim()).filter(Boolean).map((line) => {
    const heading = /^(#{1,3})\s+(.+)$/.exec(line)
    if (heading) return { kind: 'heading', level: heading[1].length, text: heading[2] }
    const list = /^(?:[-*]|\d+\.)\s+(.+)$/.exec(line)
    if (list) return { kind: 'list', text: list[1] }
    return { kind: 'paragraph', text: line }
  })
})

async function load() {
  loading.value = true
  try {
    const [dashboardData, analysisData, reportData, productData] = await Promise.all([
      getOperationsDashboard(days.value),
      getReviewAnalyses(),
      getOperationReports(),
      getProducts({ page_size: 100 }, true),
    ])
    dashboard.value = dashboardData
    analyses.value = analysisData
    reports.value = reportData
    products.value = productData.items
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '运营数据加载失败')
  } finally {
    loading.value = false
  }
}

async function analyze() {
  analyzing.value = true
  try {
    const result = await generateReviewAnalysis(productId.value, days.value)
    analyses.value.unshift(result)
    ElMessage.success('评价洞察已生成')
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '评价分析失败')
  } finally {
    analyzing.value = false
  }
}

async function createReport() {
  reporting.value = true
  try {
    const result = await generateOperationReport(days.value)
    reports.value.unshift(result)
    openReport(result)
    ElMessage.success('运营增长报告已生成')
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '报告生成失败')
  } finally {
    reporting.value = false
  }
}

function openReport(report: OperationReport) {
  activeReport.value = report
  reportDrawer.value = true
}

onMounted(load)
</script>

<template>
  <div class="operations-page" v-loading="loading">
    <header class="admin-page-header">
      <div>
        <span class="eyebrow">AI OPERATIONS</span>
        <h1 class="page-heading">{{ pageCopy[0] }}</h1>
        <p>{{ pageCopy[1] }}</p>
      </div>
      <div class="header-actions">
        <el-select v-model="days" aria-label="统计周期" style="width: 126px" @change="load">
          <el-option label="近 7 天" :value="7" />
          <el-option label="近 30 天" :value="30" />
          <el-option label="近 90 天" :value="90" />
        </el-select>
        <el-button :icon="Refresh" @click="load">刷新</el-button>
        <el-button v-if="section === 'reports'" type="primary" :icon="Document" :loading="reporting" @click="createReport">生成报告</el-button>
      </div>
    </header>

    <section v-if="section === 'reports'" class="metric-grid">
      <article v-for="metric in metricCards" :key="metric.label" class="metric-card">
        <span>{{ metric.label }}</span>
        <strong class="tabular">{{ metric.value }}</strong>
        <small>{{ metric.note }}</small>
      </article>
    </section>

    <section class="workspace-grid">
      <article v-if="section === 'reviews'" class="panel analysis-generator">
        <div class="panel-title">
          <div class="panel-icon"><el-icon><MagicStick /></el-icon></div>
          <div><h2>AI 评价洞察</h2><p>仅分析前台可见的真实订单评价</p></div>
        </div>
        <el-select v-model="productId" clearable filterable placeholder="全部商品（综合分析）">
          <el-option v-for="product in products" :key="product.id" :label="product.name" :value="product.id" />
        </el-select>
        <el-button type="primary" :loading="analyzing" @click="analyze">开始分析</el-button>
        <p class="scope-note">最多读取该周期内最近 200 条可见评价，隐藏内容不会送入模型。</p>
      </article>

      <article v-if="section === 'reports'" class="panel top-products">
        <div class="panel-title">
          <div class="panel-icon"><el-icon><DataAnalysis /></el-icon></div>
          <div><h2>成交商品排行</h2><p>按已支付订单商品金额排序</p></div>
        </div>
        <div v-if="dashboard?.top_products.length" class="ranking-list">
          <div v-for="(product, index) in dashboard.top_products" :key="product.product_id">
            <span class="rank">{{ index + 1 }}</span>
            <div><strong>{{ product.product_name }}</strong><small>{{ product.quantity }} 件 · {{ product.order_count }} 笔订单</small></div>
            <b class="tabular">{{ formatMoney(product.revenue) }}</b>
          </div>
        </div>
        <el-empty v-else description="当前周期暂无成交商品" :image-size="70" />
      </article>
    </section>

    <section v-if="section === 'reviews'" class="section-block">
      <div class="section-header"><div><h2>最近评价分析</h2><p>结构化保存好评关键词、问题、风险和优化动作。</p></div><span>{{ analyses.length }} 份</span></div>
      <div v-if="analyses.length" class="analysis-list">
        <article v-for="analysis in analyses" :key="analysis.id" class="analysis-card">
          <header><div><strong>{{ analysis.product_name || '全站综合评价' }}</strong><span>{{ analysis.source_review_count }} 条评价 · {{ formatDate(analysis.created_at) }}</span></div><el-tag effect="plain">近 {{ Math.round((new Date(analysis.period_end || '').getTime() - new Date(analysis.period_start || '').getTime()) / 86400000) }} 天</el-tag></header>
          <div class="insight-grid">
            <div><b>好评关键词</b><span v-for="item in analysis.positive_keywords" :key="item">{{ item }}</span><i v-if="!analysis.positive_keywords.length">暂无明确结论</i></div>
            <div><b>差评原因</b><span v-for="item in analysis.negative_reasons" :key="item">{{ item }}</span><i v-if="!analysis.negative_reasons.length">暂无明确结论</i></div>
            <div><b>售后风险</b><span v-for="item in analysis.after_sale_risks" :key="item">{{ item }}</span><i v-if="!analysis.after_sale_risks.length">暂无明确结论</i></div>
            <div><b>详情缺失</b><span v-for="item in analysis.missing_information" :key="item">{{ item }}</span><i v-if="!analysis.missing_information.length">暂无明确结论</i></div>
            <div class="suggestions"><b>优化建议</b><span v-for="item in analysis.suggestions" :key="item">{{ item }}</span><i v-if="!analysis.suggestions.length">暂无明确结论</i></div>
          </div>
        </article>
      </div>
      <el-empty v-else description="尚未生成评价分析" />
    </section>

    <section v-if="section === 'reports'" class="section-block reports-section">
      <div class="section-header"><div><h2>运营报告</h2><p>报告保留生成时的指标快照，便于历史复盘。</p></div></div>
      <div v-if="reports.length" class="report-list">
        <button v-for="report in reports" :key="report.id" type="button" class="report-row focus-ring" @click="openReport(report)">
          <span class="report-icon"><el-icon><Document /></el-icon></span>
          <span><strong>{{ report.title }}</strong><small>{{ formatDate(report.created_at) }}</small></span>
          <el-tag effect="plain">Markdown</el-tag>
        </button>
      </div>
      <el-empty v-else description="尚未生成运营报告" />
    </section>

    <el-drawer v-model="reportDrawer" size="min(760px, 94vw)" :title="activeReport?.title || '运营报告'">
      <div class="report-meta">生成时间 {{ formatDate(activeReport?.created_at || null) }} · 指标已固化为历史快照</div>
      <article class="markdown-preview">
        <template v-for="(block, index) in markdownBlocks" :key="index">
          <component :is="`h${block.level}`" v-if="block.kind === 'heading'">{{ block.text }}</component>
          <div v-else-if="block.kind === 'list'" class="markdown-list"><span></span><p>{{ block.text }}</p></div>
          <p v-else>{{ block.text }}</p>
        </template>
      </article>
    </el-drawer>
  </div>
</template>

<style scoped>
.admin-page-header { display: flex; align-items: end; justify-content: space-between; gap: 20px; margin-bottom: 24px; }
.admin-page-header p, .section-header p, .panel-title p { margin: 7px 0 0; color: var(--color-ink-500); }
.eyebrow { color: var(--color-brand-600); font-size: 11px; font-weight: 750; letter-spacing: .14em; }
.header-actions { display: flex; gap: 10px; }
.metric-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 14px; margin-bottom: 18px; }
.metric-card, .panel, .section-block { border: 1px solid var(--color-line); border-radius: var(--radius-container); background: white; }
.metric-card { display: grid; gap: 9px; padding: 20px; }.metric-card > span, .metric-card small { color: var(--color-ink-500); font-size: 12px; }.metric-card strong { font-size: 25px; letter-spacing: -.03em; }
.workspace-grid { display: grid; grid-template-columns: minmax(320px, .8fr) minmax(420px, 1.2fr); gap: 18px; margin-bottom: 18px; }.panel { padding: 22px; }.panel-title { display: flex; align-items: center; gap: 12px; margin-bottom: 20px; }.panel-title h2, .section-header h2 { margin: 0; font-size: 18px; }.panel-title p, .section-header p { font-size: 13px; }.panel-icon { display: grid; width: 40px; height: 40px; place-items: center; border-radius: 9px; background: var(--color-brand-50); color: var(--color-brand-700); font-size: 19px; }.analysis-generator > .el-select, .analysis-generator > .el-button { width: 100%; margin-top: 10px; }.scope-note { margin: 14px 0 0; color: var(--color-ink-500); font-size: 12px; line-height: 1.6; }
.ranking-list { display: grid; }.ranking-list > div { display: grid; grid-template-columns: 28px 1fr auto; align-items: center; gap: 10px; padding: 12px 0; border-top: 1px solid var(--color-line); }.ranking-list > div:first-child { border-top: 0; }.rank { display: grid; width: 24px; height: 24px; place-items: center; border-radius: 7px; background: var(--color-ground); color: var(--color-ink-500); font-size: 12px; }.ranking-list div div { display: grid; gap: 4px; }.ranking-list small { color: var(--color-ink-500); }.ranking-list b { color: var(--color-brand-700); }
.section-block { margin-top: 18px; padding: 22px; }.section-header { display: flex; align-items: end; justify-content: space-between; margin-bottom: 18px; }.section-header > span { color: var(--color-ink-500); font-size: 13px; }.analysis-list { display: grid; gap: 14px; }.analysis-card { padding: 18px; border: 1px solid var(--color-line); border-radius: 10px; }.analysis-card header { display: flex; align-items: start; justify-content: space-between; gap: 12px; margin-bottom: 16px; }.analysis-card header > div { display: grid; gap: 5px; }.analysis-card header span { color: var(--color-ink-500); font-size: 12px; }.insight-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; }.insight-grid > div { display: flex; align-content: start; flex-wrap: wrap; gap: 6px; }.insight-grid b { width: 100%; margin-bottom: 3px; font-size: 12px; }.insight-grid span { padding: 4px 7px; border-radius: 5px; background: var(--color-ground); color: var(--color-ink-700); font-size: 12px; }.insight-grid i { color: var(--color-ink-400); font-size: 12px; font-style: normal; }.insight-grid .suggestions { grid-column: 1 / -1; padding-top: 14px; border-top: 1px solid var(--color-line); }.insight-grid .suggestions span { background: var(--color-brand-50); color: var(--color-brand-700); }
.report-list { display: grid; }.report-row { display: grid; grid-template-columns: auto 1fr auto; align-items: center; gap: 12px; width: 100%; padding: 14px 2px; border: 0; border-top: 1px solid var(--color-line); background: transparent; text-align: left; cursor: pointer; }.report-row:first-child { border-top: 0; }.report-icon { display: grid; width: 36px; height: 36px; place-items: center; border-radius: 8px; background: var(--color-ground); color: var(--color-ink-700); }.report-row > span:nth-child(2) { display: grid; gap: 5px; }.report-row small { color: var(--color-ink-500); }.report-meta { margin-bottom: 22px; padding: 12px 14px; border-radius: 8px; background: var(--color-ground); color: var(--color-ink-500); font-size: 12px; }.markdown-preview { color: var(--color-ink-700); line-height: 1.8; }.markdown-preview h1, .markdown-preview h2, .markdown-preview h3 { margin: 1.5em 0 .55em; color: var(--color-ink-950); line-height: 1.35; }.markdown-preview h1:first-child { margin-top: 0; }.markdown-preview h1 { font-size: 26px; }.markdown-preview h2 { padding-bottom: 8px; border-bottom: 1px solid var(--color-line); font-size: 20px; }.markdown-preview h3 { font-size: 16px; }.markdown-preview > p { margin: 0 0 12px; }.markdown-list { display: grid; grid-template-columns: 7px 1fr; align-items: start; gap: 10px; margin-bottom: 8px; }.markdown-list span { width: 5px; height: 5px; margin-top: 11px; border-radius: 50%; background: var(--color-brand-600); }.markdown-list p { margin: 0; }
@media (max-width: 1100px) { .metric-grid { grid-template-columns: repeat(2, 1fr); }.workspace-grid { grid-template-columns: 1fr; }.insight-grid { grid-template-columns: repeat(2, 1fr); } }
@media (max-width: 767px) { .admin-page-header { align-items: start; flex-direction: column; }.header-actions { display: grid; grid-template-columns: 1fr 1fr; width: 100%; }.header-actions .el-select { grid-column: 1 / -1; width: 100% !important; }.metric-grid { grid-template-columns: 1fr 1fr; gap: 10px; }.metric-card { padding: 16px; }.metric-card strong { font-size: 20px; }.panel, .section-block { padding: 17px; }.insight-grid { grid-template-columns: 1fr; }.insight-grid .suggestions { grid-column: auto; }.analysis-card header { flex-direction: column; }.report-row { grid-template-columns: auto 1fr; }.report-row .el-tag { display: none; } }
</style>
