export interface ModelConfig {
  id: number
  name: string
  provider: string
  base_url: string | null
  chat_model: string
  embedding_model: string | null
  temperature: string
  max_tokens: number | null
  enabled: boolean
  is_default: boolean
  has_api_key: boolean
  created_at: string
  updated_at: string
}

export interface PromptTemplate {
  id: number
  code: string
  name: string
  scene: string
  version: number
  system_prompt: string
  user_prompt_template: string | null
  variables: string[] | null
  enabled: boolean
  created_at: string
  updated_at: string
}

export interface FunctionTool {
  id: number
  name: string
  display_name: string
  description: string
  input_schema: Record<string, unknown>
  executor: string
  timeout_seconds: number
  enabled: boolean
  created_at: string
  updated_at: string
}

export interface ToolCallLog {
  id: number
  call_no: string
  tool_id: number
  tool_name: string
  user_id: number | null
  arguments_json: Record<string, unknown>
  result_json: Record<string, unknown> | null
  status: 'RUNNING' | 'SUCCEEDED' | 'FAILED'
  error_message: string | null
  duration_ms: number | null
  created_at: string
}

export interface AgentStep {
  id: number
  step_no: number
  step_type: 'MODEL_DECISION' | 'TOOL_CALL' | 'TOOL_RESULT' | 'FINAL_ANSWER' | 'VALIDATION'
  status: 'RUNNING' | 'SUCCEEDED' | 'FAILED'
  tool_name: string | null
  input_json: Record<string, unknown> | null
  output_json: Record<string, unknown> | null
  error_message: string | null
  duration_ms: number | null
  started_at: string
  finished_at: string | null
}

export interface RecommendationItem {
  product_id: number
  sku_id: number | null
  product_name: string
  sku_name: string | null
  main_image_url: string | null
  reason: string
  price_snapshot: string
  stock_snapshot: number
  validation_passed: boolean
}

export interface Recommendation {
  id: number
  summary: string
  items: RecommendationItem[]
}

export interface AgentRun {
  id: number
  run_no: string
  status: 'RUNNING' | 'SUCCEEDED' | 'FAILED' | 'MAX_STEPS_REACHED'
  request_text: string
  final_answer: string | null
  error_message: string | null
  actual_steps: number
  max_steps: number
  total_duration_ms: number | null
  started_at: string
  finished_at: string | null
  steps: AgentStep[]
  recommendation: Recommendation | null
}

export type KnowledgeStatus = 'PENDING' | 'PROCESSING' | 'READY' | 'FAILED'

export interface KnowledgeDocument {
  id: number
  title: string
  source_type: string
  source_id: string | null
  product_id: number | null
  content: string
  checksum: string | null
  status: KnowledgeStatus
  error_message: string | null
  chunk_count: number
  created_at: string
  updated_at: string
}

export interface KnowledgeChunk {
  id: number
  document_id: number
  document_title: string
  product_id: number | null
  chunk_index: number
  content: string
  token_count: number | null
  vector_point_id: string | null
  metadata_json: Record<string, unknown> | null
  created_at: string
}

export interface ToolExecution {
  call_no: string
  tool_name: string
  status: 'RUNNING' | 'SUCCEEDED' | 'FAILED'
  result: Record<string, unknown> | null
  error_message: string | null
  duration_ms: number
}

export interface KnowledgeCitation {
  document_id: number
  document_title: string
  chunk_index: number
  excerpt: string
  score: number
}

export interface ProductQuestionResult {
  answer: string
  citations: KnowledgeCitation[]
}

export interface ReviewAnalysis {
  id: number
  product_id: number | null
  product_name: string | null
  period_start: string | null
  period_end: string | null
  positive_keywords: string[]
  negative_reasons: string[]
  after_sale_risks: string[]
  missing_information: string[]
  suggestions: string[]
  source_review_count: number
  created_at: string
}

export interface TopProductMetric {
  product_id: number
  product_name: string
  order_count: number
  quantity: number
  revenue: string
}

export interface OperationsDashboard {
  period_start: string
  period_end: string
  orders_total: number
  paid_orders: number
  revenue: string
  reviews_total: number
  average_rating: number
  positive_reviews: number
  negative_reviews: number
  agent_runs: number
  successful_agent_runs: number
  recommendations: number
  recommendation_items: number
  top_products: TopProductMetric[]
}

export interface OperationReport {
  id: number
  title: string
  report_type: string
  period_start: string | null
  period_end: string | null
  content_markdown: string
  metrics_snapshot: Record<string, unknown> | null
  model_config_id: number | null
  created_at: string
}
