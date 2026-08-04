<script setup lang="ts">
import { MagicStick, Picture, ShoppingCart, Star } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { askProductQuestion } from '../../api/ai'
import { getProduct } from '../../api/catalog'
import {
  addCartItem,
  addFavorite,
  getFavoriteStatus,
  getProductReviews,
  removeFavorite,
} from '../../api/trade'
import StatePanel from '../../components/StatePanel.vue'
import { useAuthStore } from '../../stores/auth'
import type { ProductQuestionResult } from '../../types/ai'
import type { ProductDetail, ProductSku } from '../../types/catalog'
import type { Review } from '../../types/trade'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const product = ref<ProductDetail | null>(null)
const selectedSku = ref<ProductSku | null>(null)
const activeImage = ref('')
const quantity = ref(1)
const loading = ref(true)
const error = ref('')
const adding = ref(false)
const favorite = ref(false)
const changingFavorite = ref(false)
const reviews = ref<Review[]>([])
const reviewsLoading = ref(false)
const qaQuestion = ref('')
const qaLoading = ref(false)
const qaResult = ref<ProductQuestionResult | null>(null)

const displayPrice = computed(() => selectedSku.value?.price || product.value?.min_price || '0')
const availableStock = computed(() => selectedSku.value?.available_stock ?? 0)
type DetailBlock =
  | { type: 'heading'; text: string }
  | { type: 'paragraph'; text: string }
  | { type: 'list'; items: string[] }

const detailBlocks = computed<DetailBlock[]>(() => {
  const lines = product.value?.detail_markdown?.split(/\r?\n/) || []
  const blocks: DetailBlock[] = []
  let listItems: string[] = []

  const flushList = () => {
    if (listItems.length) blocks.push({ type: 'list', items: listItems })
    listItems = []
  }

  for (const rawLine of lines) {
    const line = rawLine.trim()
    if (!line) {
      flushList()
      continue
    }
    if (line.startsWith('##')) {
      flushList()
      blocks.push({ type: 'heading', text: line.replace(/^#{2,3}\s*/, '') })
    } else if (line.startsWith('- ')) {
      listItems.push(line.slice(2))
    } else {
      flushList()
      blocks.push({ type: 'paragraph', text: line })
    }
  }
  flushList()
  return blocks
})

const formatPrice = (value: string) => Number(value).toLocaleString('zh-CN', {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
})

async function loadProduct() {
  loading.value = true
  error.value = ''
  try {
    const data = await getProduct(Number(route.params.id))
    product.value = data
    selectedSku.value = data.skus[0] || null
    activeImage.value = data.images[0]?.image_url || data.main_image_url || ''
    if (auth.isAuthenticated) {
      try { favorite.value = await getFavoriteStatus(data.id) }
      catch { favorite.value = false }
    }
    reviewsLoading.value = true
    try { reviews.value = (await getProductReviews(data.id)).items }
    catch { reviews.value = [] }
    finally { reviewsLoading.value = false }
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : '商品加载失败'
  } finally {
    loading.value = false
  }
}

async function toggleFavorite() {
  if (!auth.isAuthenticated) {
    await router.push({ name: 'login', query: { redirect: route.fullPath } })
    return
  }
  if (!product.value) return
  changingFavorite.value = true
  try {
    if (favorite.value) {
      await removeFavorite(product.value.id)
      favorite.value = false
      ElMessage.success('已取消收藏')
    } else {
      await addFavorite(product.value.id)
      favorite.value = true
      ElMessage.success('已加入收藏')
    }
  } catch {
    ElMessage.error('收藏状态更新失败，请稍后再试')
  } finally {
    changingFavorite.value = false
  }
}

async function addToCart() {
  if (!auth.isAuthenticated) {
    await router.push({ name: 'login', query: { redirect: route.fullPath } })
    return
  }
  if (!selectedSku.value) {
    ElMessage.warning('请先选择可售规格')
    return
  }
  adding.value = true
  try {
    await addCartItem(selectedSku.value.id, quantity.value)
    ElMessage.success('已加入购物车')
  } catch {
    ElMessage.error('暂时无法加入购物车，请稍后再试')
  } finally {
    adding.value = false
  }
}

async function askQuestion() {
  if (!auth.isAuthenticated) {
    await router.push({ name: 'login', query: { redirect: route.fullPath } })
    return
  }
  if (!qaQuestion.value.trim()) {
    ElMessage.warning('请先输入商品问题')
    return
  }
  qaLoading.value = true
  qaResult.value = null
  try {
    qaResult.value = await askProductQuestion(qaQuestion.value.trim(), product.value?.id)
  } catch {
    ElMessage.error('暂时无法回答，请稍后再试')
  } finally {
    qaLoading.value = false
  }
}

onMounted(loadProduct)
</script>

<template>
  <div class="page-shell product-detail-page">
    <el-skeleton v-if="loading" :rows="8" animated />
    <StatePanel
      v-else-if="error"
      title="暂时无法打开商品"
      description="页面可能正在更新，请稍后重新加载。"
      action-label="重新加载"
      @action="loadProduct"
    />
    <template v-else-if="product">
      <nav class="breadcrumb" aria-label="面包屑导航">
        <RouterLink to="/">首页</RouterLink><span>/</span>
        <RouterLink to="/products">全部商品</RouterLink><span>/</span>
        <span>{{ product.name }}</span>
      </nav>

      <section class="purchase-grid">
        <div class="gallery">
          <div class="gallery__main">
            <img v-if="activeImage" :src="activeImage" :alt="product.name" />
            <div v-else class="gallery__empty">
              <el-icon :size="42"><Picture /></el-icon><span>暂无商品图片</span>
            </div>
          </div>
          <div v-if="product.images.length > 1" class="gallery__thumbs">
            <button
              v-for="image in product.images"
              :key="image.id"
              type="button"
              :aria-label="`查看${image.alt_text || product.name}`"
              :class="{ active: activeImage === image.image_url }"
              @click="activeImage = image.image_url"
            >
              <img :src="image.image_url" :alt="image.alt_text || product.name" />
            </button>
          </div>
        </div>

        <div class="purchase-info">
          <span class="product-no">商品编号 {{ product.product_no }}</span>
          <h1>{{ product.name }}</h1>
          <div class="rating-line">
            <el-rate :model-value="Number(product.rating)" disabled />
            <span>{{ Number(product.rating).toFixed(1) }} 分</span>
            <RouterLink to="#reviews">{{ product.review_count }} 条评价</RouterLink>
            <span>{{ product.sales_count }} 人买过</span>
          </div>
          <p class="subtitle">{{ product.subtitle || '选择适合你的规格与款式。' }}</p>

          <div class="price-block">
            <span>售价</span>
            <strong class="tabular"><small>¥</small>{{ formatPrice(displayPrice) }}</strong>
          </div>

          <div class="sku-section">
            <label>选择规格</label>
            <div v-if="product.skus.length" class="sku-options">
              <button
                v-for="sku in product.skus"
                :key="sku.id"
                type="button"
                :disabled="sku.available_stock <= 0"
                :class="{ active: selectedSku?.id === sku.id }"
                @click="selectedSku = sku"
              >
                {{ sku.name }}
              </button>
            </div>
            <p v-else class="unavailable">当前暂无可选规格</p>
          </div>

          <div class="stock-row">
            <span>库存</span>
            <strong :class="{ warning: availableStock < 5 }">
              {{ availableStock > 0 ? `现货 ${availableStock} 件` : '暂时缺货' }}
            </strong>
          </div>

          <div class="buy-row">
            <el-input-number
              id="quantity"
              v-model="quantity"
              aria-label="购买数量"
              :min="1"
              :max="Math.max(1, availableStock)"
              :disabled="availableStock <= 0"
            />
            <el-button
              class="cart-button"
              type="primary"
              size="large"
              :icon="ShoppingCart"
              :loading="adding"
              :disabled="!selectedSku || availableStock <= 0"
              @click="addToCart"
            >
              加入购物车
            </el-button>
            <el-button
              class="favorite-button"
              :class="{ active: favorite }"
              size="large"
              :icon="Star"
              :loading="changingFavorite"
              @click="toggleFavorite"
            >
              {{ favorite ? '已收藏' : '收藏' }}
            </el-button>
          </div>

          <div class="purchase-assurance">
            <span>价格清楚</span><span>库存可见</span><span>订单可查</span>
          </div>
        </div>
      </section>

      <section class="detail-section">
        <h2 class="section-heading">商品参数</h2>
        <div v-if="product.parameters && Object.keys(product.parameters).filter(key => key !== '__content').length" class="parameter-grid">
          <div v-for="(value, key) in product.parameters" v-show="key !== '__content'" :key="key">
            <span>{{ key }}</span><strong>{{ value }}</strong>
          </div>
        </div>
        <StatePanel v-else title="暂无商品参数" description="更多商品信息正在补充中。" />
      </section>

      <section v-if="product.detail_markdown" class="detail-section product-story">
        <h2 class="section-heading">商品详情</h2>
        <div class="detail-copy">
          <template v-for="(block, index) in detailBlocks" :key="index">
            <h3 v-if="block.type === 'heading'">{{ block.text }}</h3>
            <p v-else-if="block.type === 'paragraph'">{{ block.text }}</p>
            <ul v-else>
              <li v-for="item in block.items" :key="item">{{ item }}</li>
            </ul>
          </template>
        </div>
      </section>

      <section class="detail-section qa-section">
        <div class="qa-heading">
          <el-icon><MagicStick /></el-icon>
          <div>
            <h2 class="section-heading">有问题，直接问</h2>
            <p>关于用途、材质或规格，我们会根据商品信息帮你回答。</p>
          </div>
        </div>
        <div class="qa-composer">
          <el-input
            v-model="qaQuestion"
            type="textarea"
            :rows="3"
            maxlength="2000"
            placeholder="例如：这款商品适合长时间办公吗？"
            @keydown.ctrl.enter="askQuestion"
          />
          <el-button type="primary" :loading="qaLoading" @click="askQuestion">获取回答</el-button>
        </div>
        <div v-if="qaResult" class="qa-answer">
          <strong>回答</strong>
          <p>{{ qaResult.answer }}</p>
          <span>购买前请以当前页面的价格与库存为准。</span>
        </div>
      </section>

      <section id="reviews" class="detail-section review-section">
        <div class="review-heading">
          <div><h2 class="section-heading">用户评价</h2><p>来自已完成购买的用户</p></div>
          <div class="rating-summary">
            <strong class="tabular">{{ Number(product.rating).toFixed(1) }}</strong>
            <el-rate :model-value="Number(product.rating)" disabled />
            <span>{{ product.review_count }} 条评价</span>
          </div>
        </div>
        <el-skeleton v-if="reviewsLoading" :rows="3" animated />
        <StatePanel v-else-if="!reviews.length" title="暂无用户评价" description="购买并确认收货后，可以分享你的使用感受。" />
        <div v-else class="review-list">
          <article v-for="review in reviews" :key="review.id">
            <div class="review-meta">
              <strong>{{ review.display_name }}</strong>
              <el-rate :model-value="review.rating" disabled />
              <span>{{ new Date(review.created_at).toLocaleDateString('zh-CN') }}</span>
            </div>
            <p>{{ review.content }}</p>
          </article>
        </div>
      </section>
    </template>
  </div>
</template>

<style scoped>
.product-detail-page {
  min-height: 70vh;
  padding-top: 22px;
}

.breadcrumb {
  display: flex;
  overflow: hidden;
  align-items: center;
  gap: 9px;
  margin-bottom: 22px;
  color: var(--color-ink-500);
  font-size: 12px;
  white-space: nowrap;
}

.breadcrumb a:hover {
  color: var(--color-brand-600);
}

.breadcrumb span:last-child {
  overflow: hidden;
  text-overflow: ellipsis;
}

.purchase-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.08fr) minmax(380px, 0.92fr);
  gap: clamp(38px, 6vw, 86px);
  align-items: start;
}

.gallery__main {
  display: grid;
  overflow: hidden;
  aspect-ratio: 1;
  place-items: center;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-container);
  background: var(--color-surface-soft);
}

.gallery__main img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.gallery__empty {
  display: grid;
  place-items: center;
  gap: 12px;
  color: var(--color-ink-400);
}

.gallery__thumbs {
  display: flex;
  gap: 10px;
  margin-top: 12px;
  overflow-x: auto;
}

.gallery__thumbs button {
  overflow: hidden;
  width: 72px;
  height: 72px;
  padding: 0;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-control);
  background: var(--color-surface);
  cursor: pointer;
}

.gallery__thumbs button.active {
  border: 2px solid var(--color-brand-600);
}

.gallery__thumbs img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.purchase-info {
  position: sticky;
  top: calc(var(--nav-height) + 22px);
}

.product-no {
  color: var(--color-ink-500);
  font-size: 12px;
}

h1 {
  margin: 12px 0;
  font-size: clamp(2.1rem, 4vw, 3.7rem);
  font-weight: 740;
  letter-spacing: -0.055em;
  line-height: 1.1;
}

.rating-line {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 7px 13px;
  color: var(--color-ink-500);
  font-size: 12px;
}

.rating-line a {
  color: var(--color-brand-600);
}

.subtitle {
  margin: 16px 0 0;
  color: var(--color-ink-500);
  line-height: 1.75;
}

.price-block {
  display: flex;
  align-items: baseline;
  gap: 18px;
  margin: 24px 0;
  padding: 18px 20px;
  border-radius: var(--radius-control);
  background: var(--color-brand-50);
}

.price-block span,
.stock-row span {
  color: var(--color-ink-500);
  font-size: 13px;
}

.price-block strong {
  color: var(--color-danger);
  font-size: 32px;
  letter-spacing: -0.03em;
}

.price-block small {
  margin-right: 3px;
  font-size: 17px;
}

.sku-section > label {
  display: block;
  margin-bottom: 11px;
  color: var(--color-ink-700);
  font-size: 14px;
  font-weight: 680;
}

.sku-options {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.sku-options button {
  min-height: 42px;
  padding: 0 16px;
  border: 1px solid var(--color-line-strong);
  border-radius: var(--radius-control);
  background: var(--color-surface);
  color: var(--color-ink-700);
  cursor: pointer;
}

.sku-options button.active {
  border-color: var(--color-brand-600);
  background: var(--color-brand-50);
  color: var(--color-brand-700);
  box-shadow: 0 0 0 1px var(--color-brand-600);
  font-weight: 680;
}

.sku-options button:disabled {
  cursor: not-allowed;
  opacity: 0.45;
  text-decoration: line-through;
}

.stock-row {
  display: flex;
  justify-content: space-between;
  margin: 22px 0;
  padding: 14px 0;
  border-bottom: 1px solid var(--color-line);
}

.stock-row strong {
  color: var(--color-success);
  font-size: 13px;
}

.stock-row strong.warning {
  color: var(--color-warning);
}

.buy-row {
  display: grid;
  grid-template-columns: auto minmax(150px, 1fr) auto;
  gap: 12px;
}

.cart-button {
  width: 100%;
}

.favorite-button.active {
  border-color: var(--color-brand-600);
  background: var(--color-brand-50);
  color: var(--color-brand-700);
}

.purchase-assurance {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  margin-top: 16px;
  color: var(--color-ink-500);
  font-size: 12px;
  text-align: center;
}

.purchase-assurance span {
  border-right: 1px solid var(--color-line);
}

.purchase-assurance span:last-child {
  border-right: 0;
}

.unavailable {
  color: var(--color-ink-500);
  font-size: 13px;
}

.detail-section {
  margin-top: 76px;
  padding-top: 30px;
  border-top: 1px solid var(--color-line);
}

.parameter-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
  margin-top: 24px;
}

.parameter-grid > div {
  display: grid;
  gap: 9px;
  min-height: 100px;
  padding: 20px;
  border-radius: var(--radius-control);
  background: var(--color-surface);
}

.parameter-grid span {
  color: var(--color-ink-500);
  font-size: 12px;
}

.detail-copy {
  max-width: 78ch;
  margin-top: 22px;
  color: var(--color-ink-700);
  line-height: 1.9;
}

.detail-copy h3 {
  margin: 30px 0 10px;
  color: var(--color-ink-950);
  font-size: 18px;
}

.detail-copy h3:first-child {
  margin-top: 0;
}

.detail-copy p {
  margin: 0 0 16px;
}

.detail-copy ul {
  display: grid;
  gap: 8px;
  margin: 12px 0 0;
  padding-left: 20px;
}

.qa-section {
  padding: clamp(24px, 4vw, 42px);
  border: 1px solid color-mix(in srgb, var(--color-brand-600) 22%, var(--color-line));
  border-radius: var(--radius-container);
  background: var(--color-brand-50);
}

.qa-heading {
  display: flex;
  align-items: center;
  gap: 16px;
}

.qa-heading > .el-icon {
  color: var(--color-brand-600);
  font-size: 26px;
}

.qa-heading p {
  margin: 7px 0 0;
  color: var(--color-ink-500);
}

.qa-composer {
  display: grid;
  grid-template-columns: 1fr auto;
  align-items: end;
  gap: 12px;
  margin-top: 24px;
}

.qa-composer .el-button {
  min-height: 40px;
}

.qa-answer {
  margin-top: 18px;
  padding: 22px;
  border-radius: var(--radius-control);
  background: var(--color-surface);
}

.qa-answer > p {
  color: var(--color-ink-700);
  line-height: 1.85;
  white-space: pre-wrap;
}

.qa-answer > span {
  color: var(--color-ink-500);
  font-size: 12px;
}

.review-heading {
  display: flex;
  align-items: end;
  justify-content: space-between;
  gap: 24px;
}

.review-heading p {
  margin: 8px 0 0;
  color: var(--color-ink-500);
}

.rating-summary {
  display: grid;
  grid-template-columns: auto auto;
  align-items: center;
  gap: 2px 12px;
}

.rating-summary > strong {
  grid-row: 1 / 3;
  color: var(--color-brand-700);
  font-size: 42px;
}

.rating-summary span {
  color: var(--color-ink-500);
  font-size: 12px;
}

.review-list {
  margin-top: 24px;
}

.review-list article {
  padding: 22px 0;
  border-bottom: 1px solid var(--color-line);
}

.review-meta {
  display: flex;
  align-items: center;
  gap: 14px;
}

.review-meta span {
  margin-left: auto;
  color: var(--color-ink-500);
  font-size: 12px;
}

.review-list p {
  margin: 12px 0 0;
  color: var(--color-ink-700);
  line-height: 1.8;
}

@media (max-width: 900px) {
  .purchase-grid {
    grid-template-columns: 1fr;
  }

  .purchase-info {
    position: static;
  }
}

@media (max-width: 767px) {
  .product-detail-page {
    padding-top: 16px;
  }

  .parameter-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .review-heading {
    align-items: start;
    flex-direction: column;
  }

  .qa-composer {
    grid-template-columns: 1fr;
  }

  .qa-composer .el-button {
    width: 100%;
  }

  .buy-row {
    grid-template-columns: 1fr 1fr;
  }

  .buy-row .el-input-number {
    width: 100%;
    grid-column: 1 / -1;
  }
}
</style>
