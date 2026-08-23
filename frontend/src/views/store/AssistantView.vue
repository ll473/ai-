<script setup lang="ts">
import { ChatDotRound, RefreshRight } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { computed, onMounted, ref } from 'vue'

import { askProductQuestion, getConversation, getConversations } from '../../api/ai'
import { getProducts } from '../../api/catalog'
import { getOrders } from '../../api/trade'
import MarkdownText from '../../components/MarkdownText.vue'
import type { ConversationMessage, ConversationSummary, ProductQuestionResult } from '../../types/ai'
import type { ProductSummary } from '../../types/catalog'
import type { OrderSummary } from '../../types/trade'

const questionTypes = [
  { label: '商品知识', value: 'PRODUCT_KNOWLEDGE', hint: '规格、适用场景、包装内容等' },
  { label: '价格库存', value: 'PRICE_STOCK', hint: '查询当前真实价格、库存与优惠' },
  { label: '订单状态', value: 'ORDER_STATUS', hint: '查询自己的订单状态和支付信息' },
  { label: '售后咨询', value: 'AFTER_SALE', hint: '退换货、质保、退款和物流规则' },
] as const

const type = ref<ProductQuestionResult['question_type']>('PRODUCT_KNOWLEDGE')
const productId = ref<number | null>(null)
const orderNo = ref('')
const question = ref('')
const loading = ref(false)
const products = ref<ProductSummary[]>([])
const orders = ref<OrderSummary[]>([])
const conversations = ref<ConversationSummary[]>([])
const conversationId = ref<number | null>(null)
const messages = ref<ConversationMessage[]>([])
const hint = computed(() => questionTypes.find((item) => item.value === type.value)?.hint)

async function loadBase() {
  try {
    const [productData, orderData, conversationData] = await Promise.all([
      getProducts({ page_size: 50 }), getOrders(1, 50), getConversations(1, 30),
    ])
    products.value = productData.items
    orders.value = orderData.items
    conversations.value = conversationData.items.filter((item) => item.scene === 'PRODUCT_QA')
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '问答资料加载失败')
  }
}

function restoreConversationContext(historyMessages: ConversationMessage[]) {
  const lastUserMessage = [...historyMessages]
    .reverse()
    .find((item) => item.role === 'USER' && item.question_type)

  productId.value = null
  orderNo.value = ''
  if (!lastUserMessage?.question_type) return

  type.value = lastUserMessage.question_type
  const metadata = lastUserMessage.metadata_json
  if (type.value === 'PRODUCT_KNOWLEDGE' || type.value === 'PRICE_STOCK') {
    productId.value = typeof metadata?.product_id === 'number' ? metadata.product_id : null
  } else if (type.value === 'ORDER_STATUS') {
    orderNo.value = typeof metadata?.order_no === 'string' ? metadata.order_no : ''
  }
}

async function openConversation(id: number) {
  try {
    const detail = await getConversation(id)
    conversationId.value = id
    messages.value = detail.messages.filter((item) => ['USER', 'ASSISTANT'].includes(item.role))
    restoreConversationContext(detail.messages)
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '历史会话加载失败')
  }
}

function startNew() {
  conversationId.value = null
  messages.value = []
  question.value = ''
}

async function submit() {
  const content = question.value.trim()
  if (!content) return
  if (content.length < 2) {
    ElMessage.warning('问题至少需要输入 2 个字')
    return
  }
  if (['PRODUCT_KNOWLEDGE', 'PRICE_STOCK'].includes(type.value) && !productId.value) {
    ElMessage.warning('请先选择商品')
    return
  }
  if (type.value === 'ORDER_STATUS' && !orderNo.value) {
    ElMessage.warning('请先选择订单')
    return
  }
  messages.value.push({
    id: Date.now(),
    role: 'USER',
    content,
    question_type: type.value,
    metadata_json: { product_id: productId.value, order_no: orderNo.value || null },
    created_at: new Date().toISOString(),
  })
  question.value = ''
  loading.value = true
  try {
    const result = await askProductQuestion(
      content, productId.value || undefined, type.value, orderNo.value || undefined, conversationId.value,
    )
    conversationId.value = result.conversation_id
    messages.value.push({
      id: Date.now() + 1,
      role: 'ASSISTANT',
      content: result.answer,
      question_type: result.question_type,
      metadata_json: null,
      created_at: new Date().toISOString(),
    })
    const history = await getConversations(1, 30)
    conversations.value = history.items.filter((item) => item.scene === 'PRODUCT_QA')
  } catch (error) {
    messages.value.pop()
    question.value = content
    ElMessage.error(error instanceof Error ? error.message : '问答失败')
  } finally { loading.value = false }
}

onMounted(loadBase)
</script>

<template>
  <div class="assistant-page page-shell">
    <header class="assistant-hero">
      <span>AI 商品助手</span>
      <h1>商品、订单和售后，一处问清楚</h1>
      <p>商品知识由知识库回答；价格、库存与订单状态直接查询真实业务数据。</p>
    </header>
    <div class="assistant-grid">
      <aside class="history-panel">
        <div class="panel-title"><strong>历史咨询</strong><el-button text :icon="RefreshRight" @click="startNew">新会话</el-button></div>
        <button v-for="item in conversations" :key="item.id" :class="{ active: item.id === conversationId }" @click="openConversation(item.id)">
          <strong>{{ item.title || '商品咨询' }}</strong><span>{{ item.message_count }} 条消息</span>
        </button>
        <el-empty v-if="!conversations.length" description="还没有咨询记录" :image-size="64" />
      </aside>
      <section class="chat-panel">
        <div class="question-toolbar">
          <el-segmented v-model="type" :options="questionTypes" value-key="value" />
          <el-select v-if="type === 'PRODUCT_KNOWLEDGE' || type === 'PRICE_STOCK'" v-model="productId" filterable placeholder="选择商品">
            <el-option v-for="item in products" :key="item.id" :label="item.name" :value="item.id" />
          </el-select>
          <el-select v-if="type === 'ORDER_STATUS'" v-model="orderNo" placeholder="选择订单">
            <el-option v-for="item in orders" :key="item.id" :label="`${item.order_no} · ${item.status}`" :value="item.order_no" />
          </el-select>
        </div>
        <div class="message-list">
          <div v-if="!messages.length" class="empty-chat"><el-icon><ChatDotRound /></el-icon><h2>想了解什么？</h2><p>{{ hint }}</p></div>
          <div v-for="item in messages" :key="item.id" class="message" :class="item.role.toLowerCase()">
            <span>{{ item.role === 'USER' ? '你' : 'AI 助手' }}</span>
            <p v-if="item.role === 'USER'">{{ item.content }}</p>
            <MarkdownText v-else class="message-copy" :content="item.content" />
          </div>
          <div v-if="loading" class="message assistant"><span>AI 助手</span><p>正在查询真实资料…</p></div>
        </div>
        <form class="composer" @submit.prevent="submit">
          <el-input v-model="question" type="textarea" :rows="3" :placeholder="hint" maxlength="2000" show-word-limit @keydown.ctrl.enter="submit" />
          <div><small>Ctrl + Enter 发送</small><el-button type="primary" :loading="loading" @click="submit">发送问题</el-button></div>
        </form>
      </section>
    </div>
  </div>
</template>

<style scoped>
.assistant-page{padding-top:30px}.assistant-hero{padding:40px 48px;border-radius:18px;background:#102f4b;color:white}.assistant-hero span{color:#8bc9ff;font-weight:700}.assistant-hero h1{margin:14px 0 8px;font-size:clamp(30px,4vw,52px)}.assistant-hero p{margin:0;color:#c9d8e7}.assistant-grid{display:grid;grid-template-columns:280px minmax(0,1fr);gap:18px;margin-top:20px}.history-panel,.chat-panel{border:1px solid var(--color-line);border-radius:16px;background:white}.history-panel{padding:14px}.panel-title{display:flex;align-items:center;justify-content:space-between;padding:4px 6px 10px}.history-panel>button{display:grid;width:100%;gap:4px;padding:13px;border:0;border-radius:10px;background:transparent;text-align:left;cursor:pointer}.history-panel>button:hover,.history-panel>button.active{background:var(--color-brand-50);color:var(--color-brand-700)}.history-panel>button span{color:var(--color-ink-500);font-size:12px}.chat-panel{display:grid;min-height:620px;grid-template-rows:auto 1fr auto}.question-toolbar{display:flex;gap:12px;padding:16px;border-bottom:1px solid var(--color-line)}.question-toolbar .el-select{width:300px}.message-list{overflow:auto;padding:24px}.empty-chat{display:grid;height:100%;place-content:center;justify-items:center;color:var(--color-ink-500)}.empty-chat .el-icon{font-size:44px;color:var(--color-brand-600)}.message{display:grid;max-width:78%;gap:5px;margin-bottom:18px}.message>span{color:var(--color-ink-500);font-size:12px}.message p,.message-copy{margin:0;padding:13px 16px;border-radius:12px;background:var(--color-surface-soft);line-height:1.7}.message p{white-space:pre-wrap}.message.user{margin-left:auto}.message.user>span{text-align:right}.message.user p{background:var(--color-brand-600);color:white}.composer{padding:16px;border-top:1px solid var(--color-line)}.composer>div{display:flex;align-items:center;justify-content:space-between;margin-top:10px}.composer small{color:var(--color-ink-500)}@media(max-width:900px){.assistant-grid{grid-template-columns:1fr}.history-panel{max-height:220px;overflow:auto}.question-toolbar{align-items:stretch;flex-direction:column}.question-toolbar .el-select{width:100%}.chat-panel{min-height:560px}}
</style>
