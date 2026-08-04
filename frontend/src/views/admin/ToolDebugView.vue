<script setup lang="ts">
import { Connection, Refresh } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'

import { getFunctionTools, testFunctionTool } from '../../api/ai'
import type { FunctionTool, ToolExecution } from '../../types/ai'

const route = useRoute()
const loading = ref(false)
const running = ref(false)
const tools = ref<FunctionTool[]>([])
const toolId = ref<number | null>(null)
const argumentsText = ref('{}')
const result = ref<ToolExecution | null>(null)
const mode = computed(() => String(route.meta.debugMode || 'product'))
const pageTitle = computed(() => mode.value === 'product' ? '商品工具调试' : '业务工具调试')
const pageDescription = computed(() => mode.value === 'product'
  ? '验证价格、库存、优惠和商品检索工具的结构化入参与返回结果。'
  : '验证用户画像、相似商品、订单状态等业务查询工具。')
const visibleTools = computed(() => {
  const businessWords = ['user', 'order', 'similar', 'profile', 'history']
  return tools.value.filter((tool) => {
    const isBusiness = businessWords.some((word) => `${tool.name} ${tool.executor}`.toLowerCase().includes(word))
    return mode.value === 'business' ? isBusiness : !isBusiness
  })
})
const selectedTool = computed(() => tools.value.find((tool) => tool.id === toolId.value) || null)

function defaultArguments(tool: FunctionTool | null) {
  const properties = (tool?.input_schema?.properties || {}) as Record<string, { type?: string; default?: unknown }>
  const required = Array.isArray(tool?.input_schema?.required) ? tool?.input_schema.required as string[] : Object.keys(properties)
  const payload: Record<string, unknown> = {}
  for (const key of required) {
    const field = properties[key]
    payload[key] = field?.default ?? (field?.type === 'integer' || field?.type === 'number' ? 1 : '')
  }
  argumentsText.value = JSON.stringify(payload, null, 2)
}

async function load() {
  loading.value = true
  try {
    tools.value = await getFunctionTools()
    const first = visibleTools.value.find((item) => item.enabled) || visibleTools.value[0]
    toolId.value = first?.id || null
    defaultArguments(first || null)
  } catch (error) { ElMessage.error(error instanceof Error ? error.message : '工具列表加载失败') }
  finally { loading.value = false }
}

async function execute() {
  if (!toolId.value) { ElMessage.warning('请选择一个工具'); return }
  let payload: Record<string, unknown>
  try { payload = JSON.parse(argumentsText.value) }
  catch { ElMessage.warning('入参必须是有效的 JSON 对象'); return }
  running.value = true
  try {
    result.value = await testFunctionTool(toolId.value, payload)
    ElMessage.success(result.value.status === 'SUCCEEDED' ? '工具调用成功' : '工具调用已返回')
  } catch (error) { ElMessage.error(error instanceof Error ? error.message : '工具调用失败') }
  finally { running.value = false }
}

watch(mode, () => { result.value = null; load() })
watch(toolId, (id) => defaultArguments(tools.value.find((item) => item.id === id) || null))
onMounted(load)
</script>

<template>
  <div v-loading="loading">
    <header class="admin-page-header"><div><h1 class="page-heading">{{ pageTitle }}</h1><p>{{ pageDescription }}</p></div><el-button :icon="Refresh" @click="load">刷新</el-button></header>
    <section class="debug-form"><div class="tool-select"><label>选择工具</label><el-select v-model="toolId" filterable placeholder="请选择工具"><el-option v-for="tool in visibleTools" :key="tool.id" :label="tool.display_name" :value="tool.id" :disabled="!tool.enabled"><span>{{ tool.display_name }}</span><small>{{ tool.name }}</small></el-option></el-select></div><div class="tool-description"><span>工具说明</span><p>{{ selectedTool?.description || '请选择一个工具查看说明' }}</p></div><div><label>结构化入参（JSON）</label><el-input v-model="argumentsText" type="textarea" :rows="8" spellcheck="false"/></div><el-button type="primary" size="large" :icon="Connection" :loading="running" @click="execute">调用工具</el-button></section>
    <section v-if="result" class="result-card"><header><div><h2>调用结果</h2><span>{{ result.call_no }} · {{ result.duration_ms }} ms</span></div><el-tag :type="result.status==='SUCCEEDED'?'success':'danger'">{{ result.status==='SUCCEEDED'?'调用成功':'调用失败' }}</el-tag></header><p v-if="result.error_message" class="error">{{ result.error_message }}</p><div v-if="result.result" class="result-grid"><div v-for="(value,key) in result.result" :key="key"><span>{{ key }}</span><strong>{{ typeof value === 'object' ? JSON.stringify(value) : value }}</strong></div></div><h3>原始 JSON</h3><pre>{{ JSON.stringify(result, null, 2) }}</pre></section>
  </div>
</template>

<style scoped>
.admin-page-header{display:flex;align-items:end;justify-content:space-between;gap:20px;margin-bottom:20px}.admin-page-header p{margin:7px 0 0;color:var(--color-ink-500)}.debug-form,.result-card{padding:22px;border:1px solid var(--color-line);border-radius:var(--radius-container);background:white}.debug-form{display:grid;grid-template-columns:1fr 1fr;gap:18px}.debug-form>div:nth-child(n+3),.debug-form>.el-button{grid-column:1/-1}.debug-form label,.tool-description>span{display:block;margin-bottom:8px;color:var(--color-ink-700);font-size:13px;font-weight:700}.tool-select .el-select{width:100%}.tool-select small{float:right;margin-left:20px;color:var(--color-ink-400)}.tool-description{padding:13px 15px;border-radius:9px;background:var(--color-ground)}.tool-description>span{margin-bottom:4px}.tool-description p{margin:0;color:var(--color-ink-500);font-size:13px;line-height:1.6}.result-card{margin-top:16px}.result-card header{display:flex;align-items:start;justify-content:space-between}.result-card h2{margin:0 0 6px;font-size:18px}.result-card header span{color:var(--color-ink-500);font-size:12px}.result-grid{display:grid;grid-template-columns:repeat(3,1fr);margin:18px 0;border:1px solid var(--color-line)}.result-grid div{display:grid;gap:6px;padding:14px;border-right:1px solid var(--color-line);border-bottom:1px solid var(--color-line)}.result-grid span{color:var(--color-ink-500);font-size:11px}.result-grid strong{overflow-wrap:anywhere}.result-card h3{font-size:14px}.result-card pre{max-height:420px;overflow:auto;padding:18px;border-radius:9px;background:#101827;color:#dbeafe;font-size:12px;line-height:1.65}.error{color:var(--color-danger)}@media(max-width:767px){.admin-page-header{align-items:start;flex-direction:column}.debug-form{grid-template-columns:1fr}.debug-form>*{grid-column:1!important}.result-grid{grid-template-columns:1fr}}
</style>
