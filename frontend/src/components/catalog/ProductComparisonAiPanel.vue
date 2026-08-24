<script setup lang="ts">
import { computed, shallowRef, watch } from 'vue'
import { useRouter } from 'vue-router'

import { compareProductsWithAi } from '../../api/ai'
import { demoMode } from '../../demo/config'
import { useAuthStore } from '../../stores/auth'
import type { ProductComparisonAiResult } from '../../types/ai'
import type { ProductComparisonItem } from '../../types/catalog'

const props = defineProps<{
  products: ProductComparisonItem[]
}>()

const router = useRouter()
const auth = useAuthStore()
const preference = shallowRef('')
const loading = shallowRef(false)
const errorMessage = shallowRef('')
let requestSequence = 0

const productIds = computed(() => props.products.map(product => product.id))
const productNames = computed(() => new Map(props.products.map(product => [product.id, product.name])))
const cacheKey = computed(() => [
  'ai-commerce-product-comparison-v1',
  productIds.value.join(','),
  preference.value.trim(),
].join(':'))

function readCachedResult(key: string): ProductComparisonAiResult | null {
  const value = sessionStorage.getItem(key)
  if (!value) return null
  try {
    return JSON.parse(value) as ProductComparisonAiResult
  } catch {
    sessionStorage.removeItem(key)
    return null
  }
}

const result = shallowRef<ProductComparisonAiResult | null>(readCachedResult(cacheKey.value))

const recommendedProductName = computed(() => result.value
  ? productNames.value.get(result.value.recommended_product_id) || '当前对比商品'
  : '')

function redirectToLogin() {
  router.push({
    name: 'login',
    query: { redirect: `/compare?ids=${productIds.value.join(',')}` },
  })
}

async function analyze() {
  if (demoMode) return
  if (!auth.isAuthenticated) {
    redirectToLogin()
    return
  }

  const requestKey = cacheKey.value
  const requestIds = [...productIds.value]
  const requestPreference = preference.value.trim()
  const sequence = ++requestSequence
  errorMessage.value = ''
  loading.value = true
  try {
    const nextResult = await compareProductsWithAi(requestIds, requestPreference || undefined)
    if (sequence !== requestSequence || cacheKey.value !== requestKey) return
    result.value = nextResult
    sessionStorage.setItem(requestKey, JSON.stringify(nextResult))
  } catch (error) {
    if (sequence !== requestSequence || cacheKey.value !== requestKey) return
    errorMessage.value = error instanceof Error && error.message
      ? error.message
      : 'AI 对比分析暂时不可用，请稍后重试'
  } finally {
    if (sequence === requestSequence && cacheKey.value === requestKey) loading.value = false
  }
}

watch(cacheKey, (key) => {
  requestSequence += 1
  loading.value = false
  errorMessage.value = ''
  result.value = readCachedResult(key)
})
</script>

<template>
  <section class="comparison-ai-panel" aria-label="AI 对比分析">
    <header class="comparison-ai-panel__header">
      <div>
        <p class="comparison-ai-panel__eyebrow">AI 帮我选</p>
        <h2 class="comparison-ai-panel__title">结合你的使用场景，给出取舍建议</h2>
      </div>
      <span class="comparison-ai-panel__tag">不影响基础对比</span>
    </header>

    <p v-if="demoMode" class="comparison-ai-panel__notice">
      完整部署并登录后可使用 AI 对比；展示版仍可查看基础商品参数。
    </p>
    <template v-else>
      <label class="comparison-ai-panel__label" for="comparison-preference">补充你的偏好（可选）</label>
      <textarea
        id="comparison-preference"
        v-model="preference"
        class="comparison-ai-panel__textarea"
        maxlength="500"
        placeholder="例如：办公室使用，重视续航和降噪。"
        :disabled="loading"
      />
      <div class="comparison-ai-panel__actions">
        <button class="comparison-ai-panel__button" type="button" :disabled="loading" @click="analyze">
          {{ loading ? '正在分析…' : (errorMessage ? '重新分析' : 'AI 帮我选') }}
        </button>
        <span class="comparison-ai-panel__hint">单次分析通常在 20 秒内完成</span>
      </div>

      <p v-if="errorMessage" class="comparison-ai-panel__error" role="alert">{{ errorMessage }}</p>
      <div v-if="loading" class="comparison-ai-panel__loading" aria-live="polite">
        正在根据商品参数和你的偏好整理建议…
      </div>
      <article v-if="result && !loading" class="comparison-ai-panel__result">
        <h3>更推荐 {{ recommendedProductName }}</h3>
        <p class="comparison-ai-panel__summary">{{ result.summary }}</p>
        <div class="comparison-ai-panel__items">
          <section v-for="item in result.items" :key="item.product_id" class="comparison-ai-panel__item">
            <h4>{{ productNames.get(item.product_id) || `商品 ${item.product_id}` }}</h4>
            <p v-if="item.strengths.length"><strong>优势：</strong>{{ item.strengths.join('；') }}</p>
            <p v-if="item.weaknesses.length"><strong>注意：</strong>{{ item.weaknesses.join('；') }}</p>
            <p v-if="item.suitable_for.length"><strong>适合：</strong>{{ item.suitable_for.join('；') }}</p>
          </section>
        </div>
        <p v-if="result.considerations.length" class="comparison-ai-panel__considerations">
          <strong>购买前建议：</strong>{{ result.considerations.join('；') }}
        </p>
      </article>
    </template>
  </section>
</template>

<style scoped>
.comparison-ai-panel {
  margin-top: 20px;
  padding: 22px;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-container);
  background: linear-gradient(135deg, var(--color-surface) 0%, var(--color-brand-50) 100%);
}

.comparison-ai-panel__header,
.comparison-ai-panel__actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
}

.comparison-ai-panel__eyebrow,
.comparison-ai-panel__title,
.comparison-ai-panel__summary,
.comparison-ai-panel__item p,
.comparison-ai-panel__considerations { margin: 0; }
.comparison-ai-panel__eyebrow { color: var(--color-brand-600); font-size: 12px; font-weight: 720; }
.comparison-ai-panel__title { margin-top: 5px; color: var(--color-ink-950); font-size: 19px; }
.comparison-ai-panel__tag { padding: 5px 8px; border-radius: 999px; background: var(--color-surface); color: var(--color-ink-500); font-size: 11px; }
.comparison-ai-panel__notice, .comparison-ai-panel__hint { color: var(--color-ink-500); font-size: 12px; line-height: 1.65; }
.comparison-ai-panel__notice { margin: 18px 0 0; }
.comparison-ai-panel__label { display: block; margin-top: 18px; color: var(--color-ink-700); font-size: 13px; font-weight: 650; }
.comparison-ai-panel__textarea {
  display: block; box-sizing: border-box; width: 100%; min-height: 84px; margin-top: 8px; padding: 10px 12px;
  resize: vertical; border: 1px solid var(--color-line-strong); border-radius: var(--radius-control);
  background: var(--color-surface); color: var(--color-ink-800); font: inherit; line-height: 1.55;
}
.comparison-ai-panel__textarea:focus { border-color: var(--color-brand-600); outline: 2px solid var(--color-brand-100); }
.comparison-ai-panel__actions { justify-content: flex-start; margin-top: 12px; }
.comparison-ai-panel__button {
  min-height: 38px; padding: 0 14px; border: 1px solid var(--color-brand-600); border-radius: var(--radius-control);
  background: var(--color-brand-600); color: #fff; cursor: pointer; font-size: 13px; font-weight: 680;
}
.comparison-ai-panel__button:disabled { cursor: wait; opacity: .72; }
.comparison-ai-panel__error { margin: 14px 0 0; color: var(--color-danger); font-size: 13px; }
.comparison-ai-panel__loading { margin-top: 16px; padding: 13px; border-radius: var(--radius-control); background: var(--color-surface); color: var(--color-ink-600); font-size: 13px; }
.comparison-ai-panel__result { margin-top: 18px; padding: 18px; border: 1px solid var(--color-brand-100); border-radius: var(--radius-control); background: var(--color-surface); }
.comparison-ai-panel__result h3, .comparison-ai-panel__item h4 { margin: 0; color: var(--color-ink-950); }
.comparison-ai-panel__result h3 { font-size: 18px; }
.comparison-ai-panel__summary { margin-top: 9px; color: var(--color-ink-700); line-height: 1.7; }
.comparison-ai-panel__items { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 10px; margin-top: 15px; }
.comparison-ai-panel__item { padding: 13px; border-radius: 10px; background: var(--color-surface-soft); }
.comparison-ai-panel__item h4 { font-size: 14px; }
.comparison-ai-panel__item p { margin-top: 8px; color: var(--color-ink-600); font-size: 12px; line-height: 1.65; }
.comparison-ai-panel__considerations { margin-top: 14px; color: var(--color-ink-600); font-size: 12px; line-height: 1.65; }
@media (max-width: 640px) {
  .comparison-ai-panel { padding: 18px; }
  .comparison-ai-panel__header { align-items: flex-start; flex-direction: column; }
  .comparison-ai-panel__actions { align-items: flex-start; flex-direction: column; }
}
</style>
