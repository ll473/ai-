<script setup lang="ts">
import { Refresh } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'

import { getAgentRuns } from '../../api/ai'
import type { AgentRun } from '../../types/ai'

const route = useRoute()
const loading = ref(false)
const runs = ref<AgentRun[]>([])
const drawerOpen = ref(false)
const activeRun = ref<AgentRun | null>(null)
const mode = computed(() => String(route.meta.recordsMode || 'runs'))
const copy = computed(() => ({
  runs: ['Agent Run 运行记录', '查看每次智能导购任务的需求、状态、耗时和完整执行轨迹。'],
  steps: ['Agent Step 执行步骤', '逐步检查模型决策、工具调用、校验与最终回答。'],
  recommendations: ['AI 推荐商品', '汇总 Agent 已验证并向客户展示的推荐商品与推荐理由。'],
}[mode.value] || ['智能导购记录', '查看智能导购执行记录。']))
const steps = computed(() => runs.value.flatMap((run) => run.steps.map((step) => ({ ...step, run_no: run.run_no, request_text: run.request_text }))))
const recommendations = computed(() => runs.value.flatMap((run) => (run.recommendation?.items || []).map((item) => ({ ...item, run_no: run.run_no, request_text: run.request_text, summary: run.recommendation?.summary || '' }))))
const statusType = (status: string) => status === 'SUCCEEDED' ? 'success' : status === 'FAILED' ? 'danger' : 'warning'
const formatDate = (value: string | null) => value ? new Date(value).toLocaleString('zh-CN') : '—'

async function load() {
  loading.value = true
  try { runs.value = (await getAgentRuns()).items }
  catch (error) { ElMessage.error(error instanceof Error ? error.message : 'Agent 记录加载失败') }
  finally { loading.value = false }
}
function showRun(run: AgentRun){activeRun.value=run;drawerOpen.value=true}
watch(mode, load)
onMounted(load)
</script>

<template>
  <div>
    <header class="admin-page-header"><div><h1 class="page-heading">{{ copy[0] }}</h1><p>{{ copy[1] }}</p></div><el-button :icon="Refresh" @click="load">刷新</el-button></header>
    <section class="table-card">
      <el-table v-if="mode==='runs'" v-loading="loading" :data="runs" empty-text="暂无 Agent Run"><el-table-column prop="run_no" label="运行编号" min-width="210"/><el-table-column prop="request_text" label="用户需求" min-width="300" show-overflow-tooltip/><el-table-column label="状态" width="120"><template #default="{row}"><el-tag :type="statusType(row.status)">{{ row.status }}</el-tag></template></el-table-column><el-table-column label="步骤" width="90"><template #default="{row}">{{ row.actual_steps }}/{{ row.max_steps }}</template></el-table-column><el-table-column label="耗时" width="110"><template #default="{row}">{{ row.total_duration_ms??0 }} ms</template></el-table-column><el-table-column label="开始时间" width="180"><template #default="{row}">{{ formatDate(row.started_at) }}</template></el-table-column><el-table-column label="操作" width="90" align="right"><template #default="{row}"><el-button link type="primary" @click="showRun(row)">回放</el-button></template></el-table-column></el-table>
      <el-table v-else-if="mode==='steps'" v-loading="loading" :data="steps" empty-text="暂无执行步骤"><el-table-column prop="run_no" label="运行编号" min-width="200"/><el-table-column prop="step_no" label="步骤" width="75"/><el-table-column prop="step_type" label="类型" min-width="150"/><el-table-column prop="tool_name" label="工具" min-width="170"><template #default="{row}">{{ row.tool_name||'—' }}</template></el-table-column><el-table-column prop="request_text" label="用户需求" min-width="260" show-overflow-tooltip/><el-table-column label="状态" width="110"><template #default="{row}"><el-tag :type="statusType(row.status)">{{ row.status }}</el-tag></template></el-table-column><el-table-column label="耗时" width="100"><template #default="{row}">{{ row.duration_ms??0 }} ms</template></el-table-column></el-table>
      <el-table v-else v-loading="loading" :data="recommendations" empty-text="暂无 AI 推荐商品"><el-table-column label="商品" min-width="260"><template #default="{row}"><div class="product-cell"><el-image :src="row.main_image_url||''" fit="cover"/><div><strong>{{ row.product_name }}</strong><span>{{ row.sku_name||'默认规格' }}</span></div></div></template></el-table-column><el-table-column prop="reason" label="推荐理由" min-width="350" show-overflow-tooltip/><el-table-column label="价格" width="120"><template #default="{row}">¥{{ Number(row.price_snapshot).toFixed(2) }}</template></el-table-column><el-table-column prop="stock_snapshot" label="库存快照" width="100"/><el-table-column label="校验" width="100"><template #default="{row}"><el-tag :type="row.validation_passed?'success':'danger'">{{ row.validation_passed?'通过':'未通过' }}</el-tag></template></el-table-column><el-table-column prop="run_no" label="来源 Run" min-width="200"/></el-table>
    </section>
    <el-drawer v-model="drawerOpen" title="Agent 执行回放" size="min(680px,94vw)"><template v-if="activeRun"><div class="run-summary"><el-tag :type="statusType(activeRun.status)">{{ activeRun.status }}</el-tag><strong>{{ activeRun.run_no }}</strong><p>{{ activeRun.request_text }}</p></div><el-timeline><el-timeline-item v-for="step in activeRun.steps" :key="step.id" :timestamp="`${step.duration_ms??0} ms`" :type="step.status==='SUCCEEDED'?'success':'danger'"><strong>步骤 {{ step.step_no }} · {{ step.step_type }}</strong><span>{{ step.tool_name||'模型回答' }}</span><pre v-if="step.output_json">{{ JSON.stringify(step.output_json,null,2) }}</pre><p v-if="step.error_message">{{ step.error_message }}</p></el-timeline-item></el-timeline><div v-if="activeRun.final_answer" class="final-answer"><strong>最终回答</strong><p>{{ activeRun.final_answer }}</p></div></template></el-drawer>
  </div>
</template>

<style scoped>
.admin-page-header{display:flex;align-items:end;justify-content:space-between;gap:20px;margin-bottom:20px}.admin-page-header p{margin:7px 0 0;color:var(--color-ink-500)}.table-card{padding:10px 16px 16px;border:1px solid var(--color-line);border-radius:var(--radius-container);background:white}.product-cell{display:flex;align-items:center;gap:10px}.product-cell .el-image{width:46px;height:46px;border-radius:7px}.product-cell>div{display:grid;gap:4px}.product-cell span{color:var(--color-ink-500);font-size:11px}.run-summary{margin-bottom:22px;padding:16px;border-radius:10px;background:var(--color-ground)}.run-summary strong{margin-left:8px}.run-summary p{margin:12px 0 0;line-height:1.7}.el-timeline-item span{display:block;margin-top:5px;color:var(--color-ink-500);font-size:12px}.el-timeline-item pre{max-height:230px;overflow:auto;padding:12px;border-radius:8px;background:#101827;color:#dbeafe;font-size:11px}.final-answer{padding:18px;border-radius:10px;background:var(--color-brand-50)}.final-answer p{margin:8px 0 0;line-height:1.75}@media(max-width:767px){.admin-page-header{align-items:start;flex-direction:column}.table-card{overflow-x:auto}.table-card .el-table{min-width:980px}}
</style>
