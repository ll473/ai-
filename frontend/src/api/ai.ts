import type { PageData } from '../types/api'
import type {
  AgentRun, ConversationDetail, ConversationSummary, FunctionTool, KnowledgeChunk, KnowledgeDocument, ModelConfig, ProductQuestionResult,
  OperationReport, OperationsDashboard, PromptTemplate, ReviewAnalysis, ToolCallLog,
  ToolExecution,
} from '../types/ai'
import { http } from './http'

export async function getModelConfigs() {
  return (await http.get('/admin/ai/models')).data.data as ModelConfig[]
}

export async function createModelConfig(payload: {
  name: string; provider: string; base_url: string | null; api_key: string | null
  chat_model: string; embedding_model: string | null; temperature: number
  max_tokens: number; enabled: boolean; is_default: boolean
}) {
  return (await http.post('/admin/ai/models', payload)).data.data as ModelConfig
}

export async function updateModelConfig(id: number, payload: {
  name?: string
  provider?: string
  base_url?: string | null
  api_key?: string
  chat_model?: string
  embedding_model?: string | null
  temperature?: number
  max_tokens?: number
  enabled?: boolean
  is_default?: boolean
}) {
  return (await http.patch(`/admin/ai/models/${id}`, payload)).data.data as ModelConfig
}

export async function getPromptTemplates() {
  return (await http.get('/admin/ai/prompts')).data.data as PromptTemplate[]
}

export async function createPromptTemplate(payload: {
  code: string; name: string; scene: string; version: number; system_prompt: string
  user_prompt_template: string | null; variables: string[] | null; enabled: boolean
}) {
  return (await http.post('/admin/ai/prompts', payload)).data.data as PromptTemplate
}

export async function getFunctionTools() {
  return (await http.get('/admin/ai/tools')).data.data as FunctionTool[]
}

export async function seedFunctionTools() {
  return (await http.post('/admin/ai/tools/seed-builtins')).data.data as FunctionTool[]
}

export async function updateFunctionTool(id: number, payload: Partial<FunctionTool>) {
  return (await http.patch(`/admin/ai/tools/${id}`, payload)).data.data as FunctionTool
}

export async function testFunctionTool(id: number, argumentsJson: Record<string, unknown>) {
  return (await http.post(`/admin/ai/tools/${id}/test`, { arguments: argumentsJson })).data.data as ToolExecution
}

export async function getToolLogs() {
  return (await http.get('/admin/ai/tool-logs')).data.data as PageData<ToolCallLog>
}

export async function getAgentRuns() {
  return (await http.get('/admin/ai/runs')).data.data as PageData<AgentRun>
}

export async function runShoppingGuide(message: string, maxSteps = 6, conversationId?: number | null) {
  return (await http.post('/ai/shopping-guide', {
    message,
    max_steps: maxSteps,
    conversation_id: conversationId || null,
  }, {
    // A guide run may include several model/tool round trips. The global 15 s
    // timeout is appropriate for normal CRUD calls but too short for this flow.
    timeout: 120_000,
  })).data.data as AgentRun
}

export async function getShoppingGuideRuns(page = 1, pageSize = 10) {
  return (
    await http.get('/ai/runs', { params: { page, page_size: pageSize } })
  ).data.data as PageData<AgentRun>
}

export async function getConversations(page = 1, pageSize = 10) {
  return (await http.get('/ai/conversations', {
    params: { page, page_size: pageSize },
  })).data.data as PageData<ConversationSummary>
}

export async function getConversation(id: number) {
  return (await http.get(`/ai/conversations/${id}`)).data.data as ConversationDetail
}

export async function getAdminConversations(page = 1, pageSize = 20, scene = 'PRODUCT_QA') {
  return (await http.get('/admin/ai/conversations', {
    params: { page, page_size: pageSize, scene },
  })).data.data as PageData<ConversationSummary>
}

export async function getAdminConversation(id: number) {
  return (await http.get(`/admin/ai/conversations/${id}`)).data.data as ConversationDetail
}

export async function getKnowledgeDocuments() {
  return (await http.get('/admin/knowledge/documents')).data.data as PageData<KnowledgeDocument>
}

export async function getKnowledgeChunks(params: {
  page?: number
  page_size?: number
  document_id?: number
  product_id?: number
  keyword?: string
} = {}) {
  return (await http.get('/admin/knowledge/chunks', { params })).data.data as PageData<KnowledgeChunk>
}

export async function createKnowledgeDocument(payload: {
  title: string
  source_type: string
  source_id: string | null
  product_id: number | null
  content: string
}) {
  return (await http.post('/admin/knowledge/documents', payload)).data.data as KnowledgeDocument
}

export async function syncProductKnowledge(productId: number) {
  return (await http.post('/admin/knowledge/sync-product', { product_id: productId })).data.data as KnowledgeDocument
}

export async function indexKnowledgeDocument(documentId: number) {
  return (await http.post(`/admin/knowledge/documents/${documentId}/index`)).data.data as KnowledgeDocument
}

export async function askProductQuestion(
  question: string,
  productId?: number,
  questionType: ProductQuestionResult['question_type'] = 'PRODUCT_KNOWLEDGE',
  orderNo?: string,
  conversationId?: number | null,
) {
  return (await http.post('/ai/product-qa', {
    question,
    question_type: questionType,
    product_id: productId || null,
    order_no: orderNo || null,
    conversation_id: conversationId || null,
    top_k: 5,
  })).data.data as ProductQuestionResult
}

export async function getOperationsDashboard(days = 30) {
  return (await http.get('/admin/operations/dashboard', { params: { days } })).data.data as OperationsDashboard
}

export async function getReviewAnalyses() {
  return (await http.get('/admin/operations/review-analyses')).data.data as ReviewAnalysis[]
}

export async function generateReviewAnalysis(productId: number | null, days = 30) {
  return (await http.post('/admin/operations/review-analyses', {
    product_id: productId,
    days,
  })).data.data as ReviewAnalysis
}

export async function getOperationReports() {
  return (await http.get('/admin/operations/reports')).data.data as OperationReport[]
}

export async function generateOperationReport(days = 30, title?: string) {
  return (await http.post('/admin/operations/reports', {
    days,
    title: title || null,
  })).data.data as OperationReport
}
