<script setup lang="ts">
import { Clock, MagicStick, Picture, Refresh, ShoppingCart } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { onMounted, ref } from 'vue'

import { getShoppingGuideRuns, runShoppingGuide } from '../../api/ai'
import { addCartItem } from '../../api/trade'
import type { AgentRun, RecommendationItem } from '../../types/ai'

const message = ref('')
const running = ref(false)
const run = ref<AgentRun | null>(null)
const history = ref<AgentRun[]>([])
const historyLoading = ref(true)
const addingSkuId = ref<number | null>(null)
const quickRequests = [
  '预算 5000 元，想买一件适合日常办公的商品',
  '想给父母挑一件实用、操作简单的礼物',
  '通勤时使用，希望轻便耐用，预算 1000 元',
]

const formatPrice = (value: string) => Number(value).toLocaleString('zh-CN', {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
})

const formatDate = (value: string) => new Date(value).toLocaleString('zh-CN', {
  month: 'numeric',
  day: 'numeric',
  hour: '2-digit',
  minute: '2-digit',
})

async function loadHistory() {
  historyLoading.value = true
  try {
    history.value = (await getShoppingGuideRuns(1, 12)).items
      .filter((item) => item.request_text.trim() && !/^\?{2}/.test(item.request_text.trim()))
      .slice(0, 8)
  } catch {
    history.value = []
  } finally {
    historyLoading.value = false
  }
}

async function submit() {
  if (message.value.trim().length < 2) {
    ElMessage.warning('请描述你的购买需求')
    return
  }
  running.value = true
  run.value = null
  try {
    const result = await runShoppingGuide(message.value.trim(), 6)
    run.value = result
    history.value = [result, ...history.value.filter((item) => item.id !== result.id)].slice(0, 8)
  } catch {
    ElMessage.error('暂时无法完成挑选，请稍后再试')
  } finally {
    running.value = false
  }
}

function useQuickRequest(value: string) {
  message.value = value
}

function selectHistory(item: AgentRun) {
  run.value = item
  message.value = item.request_text
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

function startNew() {
  message.value = ''
  run.value = null
}

async function addRecommendation(item: RecommendationItem) {
  if (!item.sku_id) {
    ElMessage.warning('这件商品暂时无法购买')
    return
  }
  addingSkuId.value = item.sku_id
  try {
    await addCartItem(item.sku_id, 1)
    ElMessage.success(`${item.product_name} 已加入购物车`)
  } catch {
    ElMessage.error('暂时无法加入购物车，请稍后再试')
  } finally {
    addingSkuId.value = null
  }
}

onMounted(loadHistory)
</script>

<template>
  <div class="page-shell guide-page">
    <section class="guide-banner">
      <div>
        <span>AI 购物助手</span>
        <h1>把需求交给我，帮你选得更合适</h1>
        <p>说清预算、用途和偏好，我们会从当前在售商品中整理购买建议。</p>
      </div>
      <div class="guide-capabilities" aria-label="购物助手能力">
        <span>理解预算</span>
        <span>核对价格</span>
        <span>确认库存</span>
        <span>说明理由</span>
      </div>
    </section>

    <div class="guide-workspace">
      <aside class="request-column">
        <section class="request-panel">
          <div class="panel-heading">
            <div><span>购买需求</span><h2>告诉我你想买什么</h2></div>
            <el-button v-if="run" text :icon="Refresh" @click="startNew">新需求</el-button>
          </div>

          <div class="quick-requests">
            <button v-for="item in quickRequests" :key="item" type="button" @click="useQuickRequest(item)">
              {{ item }}
            </button>
          </div>

          <label for="shopping-request">你的具体要求</label>
          <el-input
            id="shopping-request"
            v-model="message"
            type="textarea"
            :rows="6"
            maxlength="500"
            show-word-limit
            placeholder="例如：预算 1500 元，想买一把适合久坐、评价较好的办公椅。"
            @keydown.ctrl.enter="submit"
          />
          <el-button class="submit-button" type="primary" size="large" :loading="running" @click="submit">
            生成推荐
          </el-button>
          <p class="form-note">推荐只使用商城当前的商品、价格与库存信息。</p>
        </section>

        <section class="history-panel">
          <div class="history-heading"><el-icon><Clock /></el-icon><h2>最近咨询</h2></div>
          <el-skeleton v-if="historyLoading" :rows="3" animated />
          <p v-else-if="!history.length" class="empty-history">完成首次导购后，记录会显示在这里。</p>
          <button
            v-for="item in history"
            v-else
            :key="item.id"
            type="button"
            :class="{ active: run?.id === item.id }"
            @click="selectHistory(item)"
          >
            <strong>{{ item.request_text }}</strong>
            <span>{{ formatDate(item.started_at) }}</span>
          </button>
        </section>
      </aside>

      <main class="result-column" aria-live="polite">
        <section v-if="running" class="result-state">
          <el-icon class="is-loading"><MagicStick /></el-icon>
          <h2>正在整理适合你的商品</h2>
          <p>会核对当前价格、可售库存和你的购买要求，请稍等。</p>
          <el-skeleton :rows="5" animated />
        </section>

        <section v-else-if="!run" class="result-state result-state--empty">
          <el-icon><MagicStick /></el-icon>
          <h2>推荐结果会显示在这里</h2>
          <p>描述预算、使用场景和最在意的条件，结果会更准确。</p>
        </section>

        <section v-else class="result-panel">
          <header class="result-heading">
            <div><span>购物建议</span><h2>为你找到这些商品</h2></div>
            <span>{{ formatDate(run.started_at) }}</span>
          </header>

          <div class="answer-copy">
            <p>{{ run.final_answer || '暂时没有找到合适的商品，可以换个条件再试试。' }}</p>
          </div>

          <div v-if="run.recommendation?.summary" class="recommendation-summary">
            {{ run.recommendation.summary }}
          </div>

          <div v-if="run.recommendation?.items.length" class="recommendation-list">
            <article v-for="item in run.recommendation.items" :key="item.product_id">
              <RouterLink :to="`/products/${item.product_id}`" class="recommendation-image">
                <img v-if="item.main_image_url" :src="item.main_image_url" :alt="item.product_name" />
                <el-icon v-else><Picture /></el-icon>
              </RouterLink>
              <div class="recommendation-copy">
                <div>
                  <RouterLink :to="`/products/${item.product_id}`"><h3>{{ item.product_name }}</h3></RouterLink>
                  <span v-if="item.sku_name">{{ item.sku_name }}</span>
                  <p>{{ item.reason }}</p>
                </div>
                <footer>
                  <div>
                    <strong class="tabular">¥{{ formatPrice(item.price_snapshot) }}</strong>
                    <span>{{ item.stock_snapshot > 0 ? `现货 ${item.stock_snapshot} 件` : '暂时缺货' }}</span>
                  </div>
                  <el-button
                    type="primary"
                    :icon="ShoppingCart"
                    :loading="addingSkuId === item.sku_id"
                    :disabled="!item.sku_id || item.stock_snapshot <= 0"
                    @click="addRecommendation(item)"
                  >
                    加入购物车
                  </el-button>
                </footer>
              </div>
            </article>
          </div>
        </section>
      </main>
    </div>
  </div>
</template>

<style scoped>
.guide-page { min-height: 75vh; padding-top: 24px; }
.guide-banner {
  display: flex; min-height: 188px; align-items: center; justify-content: space-between;
  gap: 40px; padding: 34px 40px; border-radius: var(--radius-container);
  background: linear-gradient(110deg, #12263f 0%, #164d72 100%);
  color: #f3f7fb; box-shadow: 0 16px 42px rgb(18 49 79 / 18%);
}
.guide-banner > div:first-child > span {
  color: #90c8ff; font-size: 12px; font-weight: 720; letter-spacing: .06em;
}
.guide-banner h1, .guide-banner p { margin: 0; }
.guide-banner h1 {
  max-width: 620px; margin-top: 10px; font-size: clamp(1.9rem, 3.2vw, 2.9rem);
  letter-spacing: -.045em; line-height: 1.2;
}
.guide-banner p {
  max-width: 60ch; margin-top: 13px; color: rgb(236 244 251 / 78%); font-size: 14px; line-height: 1.7;
}
.guide-capabilities { display: grid; flex: 0 0 auto; grid-template-columns: repeat(2, 112px); gap: 10px; }
.guide-capabilities span {
  display: grid; min-height: 42px; place-items: center; border: 1px solid rgb(209 234 255 / 26%);
  border-radius: var(--radius-control); background: rgb(255 255 255 / 6%); color: #e8f3fb; font-size: 12px;
}
.guide-workspace {
  display: grid; grid-template-columns: minmax(320px, .72fr) minmax(0, 1.58fr);
  gap: 18px; margin-top: 18px;
}
.request-column { display: grid; min-width: 0; align-content: start; gap: 18px; }
.request-panel, .history-panel, .result-state, .result-panel {
  border: 1px solid var(--color-line); border-radius: var(--radius-container); background: var(--color-surface);
}
.request-panel, .history-panel { min-width: 0; padding: 22px; }
.panel-heading, .result-heading {
  display: flex; align-items: flex-start; justify-content: space-between; gap: 16px;
}
.panel-heading span, .result-heading > div > span {
  color: var(--color-brand-600); font-size: 11px; font-weight: 700;
}
.panel-heading h2, .result-heading h2 { margin: 4px 0 0; font-size: 20px; }
.quick-requests {
  display: flex; overflow-x: auto; gap: 7px; margin: 18px 0; padding-bottom: 3px;
}
.quick-requests button {
  flex: 0 0 auto; max-width: 230px; padding: 8px 10px; overflow: hidden;
  border: 1px solid var(--color-line); border-radius: var(--radius-control);
  background: var(--color-surface-soft); color: var(--color-ink-700); cursor: pointer;
  font-size: 11px; text-overflow: ellipsis; white-space: nowrap;
}
.quick-requests button:hover { border-color: var(--color-brand-600); color: var(--color-brand-700); }
.request-panel > label { display: block; margin-bottom: 8px; font-size: 13px; font-weight: 680; }
.request-panel :deep(.el-textarea) { width: 100%; min-width: 0; }
.submit-button { width: 100%; margin-top: 14px; }
.form-note, .empty-history {
  margin: 10px 0 0; color: var(--color-ink-500); font-size: 11px; line-height: 1.6;
}
.history-heading { display: flex; align-items: center; gap: 8px; margin-bottom: 12px; }
.history-heading .el-icon { color: var(--color-brand-600); }
.history-heading h2 { margin: 0; font-size: 15px; }
.history-panel > button {
  display: grid; width: 100%; gap: 5px; padding: 11px 9px; border: 0;
  border-bottom: 1px solid var(--color-line); background: transparent;
  color: var(--color-ink-700); cursor: pointer; text-align: left;
}
.history-panel > button:last-child { border-bottom: 0; }
.history-panel > button.active { background: var(--color-brand-50); color: var(--color-brand-700); }
.history-panel strong { overflow: hidden; font-size: 12px; text-overflow: ellipsis; white-space: nowrap; }
.history-panel button span { color: var(--color-ink-500); font-size: 10px; }
.result-column { min-width: 0; }
.result-state {
  display: grid; min-height: 540px; align-content: center; justify-items: center;
  padding: 36px; text-align: center;
}
.result-state > .el-icon { color: var(--color-brand-600); font-size: 34px; }
.result-state h2, .result-state p { margin: 0; }
.result-state h2 { margin-top: 14px; font-size: 22px; }
.result-state p { max-width: 46ch; margin-top: 8px; color: var(--color-ink-500); line-height: 1.7; }
.result-state .el-skeleton { width: min(100%, 640px); margin-top: 30px; text-align: left; }
.result-panel { min-height: 540px; padding: 24px; }
.result-heading { padding-bottom: 18px; border-bottom: 1px solid var(--color-line); }
.result-heading > span { color: var(--color-ink-500); font-size: 11px; }
.answer-copy {
  margin-top: 18px; padding: 16px 18px; border-radius: var(--radius-control); background: var(--color-brand-50);
}
.answer-copy p {
  margin: 0; color: var(--color-ink-700); font-size: 13px; line-height: 1.8; white-space: pre-wrap;
}
.recommendation-summary { margin-top: 16px; color: var(--color-ink-500); font-size: 12px; line-height: 1.7; }
.recommendation-list { display: grid; gap: 12px; margin-top: 16px; }
.recommendation-list article {
  display: grid; grid-template-columns: 150px minmax(0, 1fr); overflow: hidden;
  border: 1px solid var(--color-line); border-radius: var(--radius-container); background: var(--color-surface-soft);
}
.recommendation-image {
  display: grid; min-height: 182px; place-items: center; overflow: hidden;
  color: var(--color-ink-400); font-size: 26px;
}
.recommendation-image img { width: 100%; height: 100%; object-fit: cover; }
.recommendation-copy {
  display: flex; min-width: 0; flex-direction: column; padding: 17px; background: var(--color-surface);
}
.recommendation-copy h3, .recommendation-copy p { margin: 0; }
.recommendation-copy h3 { font-size: 16px; }
.recommendation-copy > div > span { display: block; margin-top: 5px; color: var(--color-ink-500); font-size: 11px; }
.recommendation-copy p { margin-top: 10px; color: var(--color-ink-700); font-size: 12px; line-height: 1.7; }
.recommendation-copy footer {
  display: flex; align-items: flex-end; justify-content: space-between; gap: 14px;
  margin-top: auto; padding-top: 14px;
}
.recommendation-copy footer > div { display: grid; gap: 4px; }
.recommendation-copy footer strong { color: var(--color-danger); font-size: 20px; }
.recommendation-copy footer span { color: var(--color-success); font-size: 10px; }
@media (prefers-color-scheme: dark) {
  .guide-banner { background: linear-gradient(110deg, #12263f 0%, #143b59 100%); box-shadow: none; }
}
@media (max-width: 900px) { .guide-workspace { grid-template-columns: 1fr; } }
@media (max-width: 767px) {
  .guide-page { padding-top: 14px; }
  .guide-banner {
    min-height: auto; align-items: flex-start; flex-direction: column; gap: 24px; padding: 25px 20px;
  }
  .guide-banner h1 { font-size: 1.9rem; }
  .guide-capabilities { width: 100%; grid-template-columns: repeat(2, 1fr); }
  .request-panel, .history-panel, .result-panel, .result-state { padding: 18px; }
  .recommendation-list article { grid-template-columns: 108px minmax(0, 1fr); }
  .recommendation-image { min-height: 150px; }
  .recommendation-copy footer { align-items: stretch; flex-direction: column; }
  .recommendation-copy footer .el-button { width: 100%; }
}
</style>
