<script setup lang="ts">
import { Key, Plus, Refresh, SetUp } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import {
  createModelConfig, createPromptTemplate, getAgentRuns, getFunctionTools,
  getModelConfigs, getPromptTemplates, getToolLogs, seedFunctionTools,
  updateFunctionTool, updateModelConfig,
} from '../../api/ai'
import type { AgentRun, FunctionTool, ModelConfig, PromptTemplate, ToolCallLog } from '../../types/ai'

const route = useRoute()
const router = useRouter()
const tab = ref(String(route.meta.adminTab || 'models'))
const loading = ref(true)
const models = ref<ModelConfig[]>([])
const prompts = ref<PromptTemplate[]>([])
const tools = ref<FunctionTool[]>([])
const logs = ref<ToolCallLog[]>([])
const runs = ref<AgentRun[]>([])
const modelDialog = ref(false)
const editingModelId = ref<number | null>(null)
const promptDialog = ref(false)
const runDrawer = ref(false)
const activeRun = ref<AgentRun | null>(null)
const saving = ref(false)
const modelForm = reactive({ name: '', provider: 'ALIBABA_BAILIAN', base_url: 'https://dashscope.aliyuncs.com/compatible-mode/v1', api_key: '', chat_model: 'qwen3.7-plus', embedding_model: 'qwen3.7-text-embedding', temperature: 0.2, max_tokens: 2048, enabled: true, is_default: true })
const promptForm = reactive({ code: 'SHOPPING_GUIDE_V1', name: '智能导购基础 Prompt', scene: 'SHOPPING_GUIDE', version: 1, system_prompt: '', enabled: true })
const statusType = (status: string) => status === 'SUCCEEDED' ? 'success' : status === 'FAILED' ? 'danger' : 'warning'
const formatDate = (value: string) => new Date(value).toLocaleString('zh-CN')
const modelDialogTitle = computed(() => editingModelId.value ? '编辑模型配置' : '新增模型配置')
const pageCopy = computed(() => ({
  models: ['AI 模型配置', '维护智能导购、商品问答和运营分析使用的模型连接参数。'],
  prompts: ['Prompt 模板', '按业务场景维护系统提示词、用户模板与版本。'],
  tools: ['Function Tool', '管理 Agent 可调用的白名单业务工具和结构化入参。'],
}[tab.value] || ['AI 配置中心', '维护商城智能能力的基础配置。']))

watch(() => route.meta.adminTab, (value) => { if (value) tab.value = String(value) })

function changeTab(value: string | number) {
  const routes: Record<string, string> = {
    models: '/admin/ai/models', prompts: '/admin/ai/prompts', tools: '/admin/ai/tools',
    logs: '/admin/operations/runs', runs: '/admin/operations/runs',
  }
  if (routes[String(value)]) router.push(routes[String(value)])
}

function openNewModel() {
  editingModelId.value = null
  Object.assign(modelForm, {
    name: '', provider: 'ALIBABA_BAILIAN',
    base_url: 'https://dashscope.aliyuncs.com/compatible-mode/v1', api_key: '',
    chat_model: 'qwen3.7-plus', embedding_model: 'qwen3.7-text-embedding',
    temperature: 0.2, max_tokens: 2048, enabled: true, is_default: true,
  })
  modelDialog.value = true
}

function openEditModel(model: ModelConfig) {
  editingModelId.value = model.id
  Object.assign(modelForm, {
    name: model.name, provider: model.provider, base_url: model.base_url || '', api_key: '',
    chat_model: model.chat_model, embedding_model: model.embedding_model || '',
    temperature: Number(model.temperature), max_tokens: model.max_tokens || 2048,
    enabled: model.enabled, is_default: model.is_default,
  })
  modelDialog.value = true
}

async function load() {
  loading.value = true
  try {
    const [modelData, promptData, toolData, logData, runData] = await Promise.all([
      getModelConfigs(), getPromptTemplates(), getFunctionTools(), getToolLogs(), getAgentRuns(),
    ])
    models.value = modelData; prompts.value = promptData; tools.value = toolData
    logs.value = logData.items; runs.value = runData.items
  } catch (error) { ElMessage.error(error instanceof Error ? error.message : 'AI 配置加载失败') }
  finally { loading.value = false }
}

async function saveModel() {
  if (!modelForm.name || !modelForm.chat_model) { ElMessage.warning('请填写配置名称和模型 ID'); return }
  saving.value = true
  try {
    const payload = { ...modelForm, base_url: modelForm.base_url || null, api_key: modelForm.api_key || undefined, embedding_model: modelForm.embedding_model || null }
    if (editingModelId.value) await updateModelConfig(editingModelId.value, payload)
    else await createModelConfig({ ...payload, api_key: payload.api_key || null })
    ElMessage.success(editingModelId.value ? '模型配置已更新' : '模型配置已保存'); modelDialog.value = false; await load()
  } catch (error) { ElMessage.error(error instanceof Error ? error.message : '保存失败') }
  finally { saving.value = false }
}

async function makeDefault(model: ModelConfig) {
  try { await updateModelConfig(model.id, { is_default: true, enabled: true }); ElMessage.success('默认模型已更新'); await load() }
  catch (error) { ElMessage.error(error instanceof Error ? error.message : '更新失败') }
}

async function savePrompt() {
  if (!promptForm.system_prompt.trim()) { ElMessage.warning('请填写系统 Prompt'); return }
  saving.value = true
  try {
    await createPromptTemplate({ ...promptForm, user_prompt_template: null, variables: null })
    ElMessage.success('Prompt 模板已保存'); promptDialog.value = false; await load()
  } catch (error) { ElMessage.error(error instanceof Error ? error.message : '保存失败') }
  finally { saving.value = false }
}

async function seedTools() {
  try { tools.value = await seedFunctionTools(); ElMessage.success(`${tools.value.length} 个内置白名单工具已就绪`) }
  catch (error) { ElMessage.error(error instanceof Error ? error.message : '初始化失败') }
}

async function toggleTool(tool: FunctionTool, enabled: boolean) {
  try { Object.assign(tool, await updateFunctionTool(tool.id, { enabled })) }
  catch (error) { ElMessage.error(error instanceof Error ? error.message : '状态更新失败'); await load() }
}

function showRun(run: AgentRun) { activeRun.value = run; runDrawer.value = true }
onMounted(load)
</script>

<template>
  <div>
    <header class="admin-page-header"><div><h1 class="page-heading">{{ pageCopy[0] }}</h1><p>{{ pageCopy[1] }}</p></div><el-button :icon="Refresh" @click="load">刷新</el-button></header>
    <el-tabs v-model="tab" v-loading="loading" @tab-change="changeTab">
      <el-tab-pane label="模型配置" name="models">
        <div class="tab-toolbar"><span>API Key 加密保存，列表和接口均不回传明文。</span><el-button type="primary" :icon="Plus" @click="openNewModel">新增模型</el-button></div>
        <el-table :data="models" empty-text="尚未配置模型"><el-table-column prop="name" label="配置名称" min-width="160" /><el-table-column prop="provider" label="供应商" width="110" /><el-table-column prop="chat_model" label="模型 ID" min-width="180" /><el-table-column label="密钥" width="100"><template #default="{ row }"><el-tag :type="row.has_api_key ? 'success' : 'warning'" effect="plain">{{ row.has_api_key ? '已配置' : '未配置' }}</el-tag></template></el-table-column><el-table-column label="状态" width="110"><template #default="{ row }"><el-tag v-if="row.is_default" type="primary">默认</el-tag><span v-else>{{ row.enabled ? '启用' : '停用' }}</span></template></el-table-column><el-table-column label="操作" width="170" align="right"><template #default="{ row }"><el-button link type="primary" @click="openEditModel(row)">编辑</el-button><el-button v-if="!row.is_default" link type="primary" @click="makeDefault(row)">设为默认</el-button></template></el-table-column></el-table>
      </el-tab-pane>
      <el-tab-pane label="Prompt 模板" name="prompts">
        <div class="tab-toolbar"><span>同一编码可用不同版本迭代，场景默认选择最高启用版本。</span><el-button type="primary" :icon="Plus" @click="promptDialog = true">新增 Prompt</el-button></div>
        <el-table :data="prompts" empty-text="尚未配置 Prompt"><el-table-column prop="code" label="编码" min-width="180" /><el-table-column prop="name" label="名称" min-width="180" /><el-table-column prop="scene" label="场景" width="160" /><el-table-column prop="version" label="版本" width="80" /><el-table-column label="状态" width="90"><template #default="{ row }"><el-tag :type="row.enabled ? 'success' : 'info'">{{ row.enabled ? '启用' : '停用' }}</el-tag></template></el-table-column></el-table>
      </el-tab-pane>
      <el-tab-pane label="Function Tools" name="tools">
        <div class="tab-toolbar"><span>executor 只能从后端白名单选择，不执行数据库中的任意代码。</span><el-button type="primary" :icon="SetUp" @click="seedTools">初始化内置工具</el-button></div>
        <el-table :data="tools" empty-text="请初始化内置工具"><el-table-column prop="display_name" label="工具" min-width="170"><template #default="{ row }"><div class="primary-cell"><strong>{{ row.display_name }}</strong><span>{{ row.name }}</span></div></template></el-table-column><el-table-column prop="description" label="模型可见描述" min-width="320" /><el-table-column prop="executor" label="白名单 Executor" min-width="210" /><el-table-column label="启用" width="90" align="center"><template #default="{ row }"><el-switch :model-value="row.enabled" @change="toggleTool(row, Boolean($event))" /></template></el-table-column></el-table>
      </el-tab-pane>
      <el-tab-pane label="调用日志" name="logs">
        <el-table :data="logs" empty-text="暂无工具调用"><el-table-column prop="call_no" label="调用编号" min-width="210" /><el-table-column prop="tool_name" label="工具" min-width="170" /><el-table-column label="状态" width="100"><template #default="{ row }"><el-tag :type="statusType(row.status)">{{ row.status }}</el-tag></template></el-table-column><el-table-column label="耗时" width="100"><template #default="{ row }">{{ row.duration_ms ?? 0 }} ms</template></el-table-column><el-table-column label="时间" width="180"><template #default="{ row }">{{ formatDate(row.created_at) }}</template></el-table-column><el-table-column label="入参" min-width="220" show-overflow-tooltip><template #default="{ row }">{{ JSON.stringify(row.arguments_json) }}</template></el-table-column></el-table>
      </el-tab-pane>
      <el-tab-pane label="Agent Runs" name="runs">
        <el-table :data="runs" empty-text="暂无 Agent Run"><el-table-column prop="run_no" label="运行编号" min-width="210" /><el-table-column prop="request_text" label="用户需求" min-width="280" show-overflow-tooltip /><el-table-column label="状态" width="120"><template #default="{ row }"><el-tag :type="statusType(row.status)">{{ row.status }}</el-tag></template></el-table-column><el-table-column label="步骤/耗时" width="130"><template #default="{ row }">{{ row.actual_steps }} 步 · {{ row.total_duration_ms ?? 0 }} ms</template></el-table-column><el-table-column label="操作" width="90" align="right"><template #default="{ row }"><el-button link type="primary" @click="showRun(row)">回放</el-button></template></el-table-column></el-table>
      </el-tab-pane>
    </el-tabs>

    <el-dialog v-model="modelDialog" :title="modelDialogTitle" width="min(620px, 94vw)"><el-form label-position="top"><div class="form-grid"><el-form-item label="配置名称"><el-input v-model="modelForm.name" /></el-form-item><el-form-item label="供应商"><el-input v-model="modelForm.provider" /></el-form-item></div><el-form-item label="语言模型 ID"><el-input v-model="modelForm.chat_model" /></el-form-item><el-form-item label="向量模型 ID"><el-input v-model="modelForm.embedding_model" /></el-form-item><el-form-item :label="editingModelId ? 'API Key（留空则保留原密钥）' : 'API Key'"><el-input v-model="modelForm.api_key" type="password" show-password :prefix-icon="Key" autocomplete="new-password" /></el-form-item><el-form-item label="百炼 OpenAI 兼容 Base URL"><el-input v-model="modelForm.base_url" placeholder="https://dashscope.aliyuncs.com/compatible-mode/v1" /></el-form-item><el-checkbox v-model="modelForm.is_default">设为默认模型</el-checkbox></el-form><template #footer><el-button @click="modelDialog = false">取消</el-button><el-button type="primary" :loading="saving" @click="saveModel">保存</el-button></template></el-dialog>
    <el-dialog v-model="promptDialog" title="新增 Prompt 模板" width="min(720px, 94vw)"><el-form label-position="top"><div class="form-grid"><el-form-item label="编码"><el-input v-model="promptForm.code" /></el-form-item><el-form-item label="名称"><el-input v-model="promptForm.name" /></el-form-item></div><div class="form-grid"><el-form-item label="场景"><el-input v-model="promptForm.scene" /></el-form-item><el-form-item label="版本"><el-input-number v-model="promptForm.version" :min="1" /></el-form-item></div><el-form-item label="System Prompt"><el-input v-model="promptForm.system_prompt" type="textarea" :rows="10" maxlength="20000" show-word-limit /></el-form-item></el-form><template #footer><el-button @click="promptDialog = false">取消</el-button><el-button type="primary" :loading="saving" @click="savePrompt">保存</el-button></template></el-dialog>
    <el-drawer v-model="runDrawer" title="Agent 执行回放" size="min(620px, 94vw)"><div v-if="activeRun"><div class="run-summary"><el-tag :type="statusType(activeRun.status)">{{ activeRun.status }}</el-tag><span>{{ activeRun.run_no }}</span></div><el-timeline class="run-timeline"><el-timeline-item v-for="step in activeRun.steps" :key="step.id" :timestamp="`${step.duration_ms ?? 0} ms`" :type="step.status === 'SUCCEEDED' ? 'success' : 'danger'"><strong>步骤 {{ step.step_no }} · {{ step.tool_name || '最终回答' }}</strong><pre v-if="step.input_json">{{ JSON.stringify(step.input_json, null, 2) }}</pre><p v-if="step.error_message">{{ step.error_message }}</p></el-timeline-item></el-timeline><div v-if="activeRun.final_answer" class="final-answer">{{ activeRun.final_answer }}</div></div></el-drawer>
  </div>
</template>

<style scoped>
.admin-page-header { display: flex; align-items: end; justify-content: space-between; gap: 20px; margin-bottom: 20px; }.admin-page-header p, .tab-toolbar span { margin: 8px 0 0; color: var(--color-ink-500); }.tab-toolbar { display: flex; align-items: center; justify-content: space-between; gap: 20px; margin: 8px 0 18px; }.primary-cell { display: grid; gap: 5px; }.primary-cell span { color: var(--color-ink-500); font-size: 12px; }.form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }.run-summary { display: flex; justify-content: space-between; padding-bottom: 20px; border-bottom: 1px solid var(--color-line); color: var(--color-ink-500); }.run-timeline { margin-top: 28px; }.run-timeline pre { overflow: auto; padding: 10px; border-radius: 7px; background: var(--color-ground); font-size: 12px; }.final-answer { padding: 18px; border-left: 3px solid var(--color-brand-600); background: var(--color-brand-50); line-height: 1.8; white-space: pre-wrap; }
@media (max-width: 767px) { .admin-page-header, .tab-toolbar { align-items: start; flex-direction: column; }.form-grid { grid-template-columns: 1fr; } }
</style>
