<script setup lang="ts">
import { ElMessage } from 'element-plus'
import { onMounted, ref } from 'vue'

import { getAdminConversation, getAdminConversations } from '../../api/ai'
import type { ConversationDetail, ConversationSummary } from '../../types/ai'

const loading = ref(false)
const items = ref<ConversationSummary[]>([])
const total = ref(0)
const page = ref(1)
const detail = ref<ConversationDetail | null>(null)
const drawerOpen = ref(false)

async function load() {
  loading.value = true
  try { const data = await getAdminConversations(page.value); items.value = data.items; total.value = data.total }
  catch (error) { ElMessage.error(error instanceof Error ? error.message : '问答记录加载失败') }
  finally { loading.value = false }
}
async function open(item: ConversationSummary) {
  try { detail.value = await getAdminConversation(item.id); drawerOpen.value = true }
  catch (error) { ElMessage.error(error instanceof Error ? error.message : '会话详情加载失败') }
}
onMounted(load)
</script>

<template>
  <div><header class="admin-page-header"><h1 class="page-heading">AI 商品问答</h1><p>查看用户的商品知识、价格库存、订单状态与售后咨询记录。</p></header><section class="table-card"><el-table v-loading="loading" :data="items" empty-text="暂无问答记录"><el-table-column prop="title" label="咨询主题" min-width="300"/><el-table-column prop="message_count" label="消息数" width="100"/><el-table-column prop="last_message_at" label="最近咨询" width="200"/><el-table-column prop="created_at" label="创建时间" width="200"/><el-table-column label="操作" width="100"><template #default="{row}"><el-button link type="primary" @click="open(row)">查看</el-button></template></el-table-column></el-table><el-pagination v-if="total>20" v-model:current-page="page" :total="total" :page-size="20" @current-change="load"/></section><el-drawer v-model="drawerOpen" title="问答详情" size="min(640px,94%)"><div v-if="detail" class="message-list"><div v-for="item in detail.messages" :key="item.id" :class="['message', item.role.toLowerCase()]"><strong>{{ item.role==='USER'?'用户':item.role==='ASSISTANT'?'AI 助手':item.role }}</strong><span v-if="item.question_type">{{ item.question_type }}</span><p>{{ item.content }}</p></div></div></el-drawer></div>
</template>

<style scoped>.admin-page-header{margin-bottom:20px}.admin-page-header p{color:var(--color-ink-500)}.table-card{padding:14px;border:1px solid var(--color-line);border-radius:var(--radius-container);background:white}.el-pagination{justify-content:flex-end;margin-top:14px}.message{margin-bottom:16px}.message strong{margin-right:8px}.message span{color:var(--color-ink-500);font-size:11px}.message p{padding:12px;border-radius:10px;background:var(--color-surface-soft);white-space:pre-wrap;line-height:1.7}.message.user p{background:var(--color-brand-50)}</style>
