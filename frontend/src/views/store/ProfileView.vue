<script setup lang="ts">
import { ChatLineSquare, Coin, Location, ShoppingBag, Star, User } from '@element-plus/icons-vue'
import { onMounted, ref } from 'vue'

import { getShoppingGuideRuns } from '../../api/ai'
import { getAddresses, getFavorites, getOrders, getWallet } from '../../api/trade'
import { useAuthStore } from '../../stores/auth'

const auth = useAuthStore()
const balance = ref('0.00')
const orderCount = ref(0)
const favoriteCount = ref(0)
const guideCount = ref(0)
const defaultAddress = ref('尚未设置默认收货地址')
const loading = ref(true)

const formatMoney = (value: string) => Number(value).toLocaleString('zh-CN', {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
})

onMounted(async () => {
  const [wallet, orders, favorites, guides, addresses] = await Promise.allSettled([
    getWallet(),
    getOrders(1, 1),
    getFavorites(1, 1),
    getShoppingGuideRuns(1, 1),
    getAddresses(),
  ])
  if (wallet.status === 'fulfilled') balance.value = wallet.value.balance
  if (orders.status === 'fulfilled') orderCount.value = orders.value.total
  if (favorites.status === 'fulfilled') favoriteCount.value = favorites.value.total
  if (guides.status === 'fulfilled') guideCount.value = guides.value.total
  if (addresses.status === 'fulfilled') {
    const address = addresses.value.find((item) => item.is_default) || addresses.value[0]
    if (address) {
      defaultAddress.value = `${address.province}${address.city}${address.district}${address.detail}`
    }
  }
  loading.value = false
})
</script>

<template>
  <div class="page-shell profile-page">
    <section class="profile-summary">
      <div class="profile-avatar"><el-icon><User /></el-icon></div>
      <div>
        <span>个人中心</span>
        <h1>{{ auth.user?.nickname || auth.user?.username }}</h1>
        <p>{{ auth.user?.email }}</p>
      </div>
      <RouterLink to="/addresses" class="address-summary">
        <el-icon><Location /></el-icon>
        <div><span>默认收货地址</span><strong>{{ defaultAddress }}</strong></div>
      </RouterLink>
    </section>

    <el-skeleton v-if="loading" :rows="5" animated class="profile-loading" />
    <template v-else>
      <section class="account-overview" aria-label="账户概览">
        <RouterLink to="/wallet" class="balance-panel">
          <div><el-icon><Coin /></el-icon><span>钱包余额</span></div>
          <strong class="tabular"><small>¥</small>{{ formatMoney(balance) }}</strong>
          <span>查看充值与消费记录</span>
        </RouterLink>

        <div class="activity-grid">
          <RouterLink to="/orders">
            <el-icon><ShoppingBag /></el-icon>
            <strong class="tabular">{{ orderCount }}</strong>
            <span>我的订单</span>
          </RouterLink>
          <RouterLink to="/favorites">
            <el-icon><Star /></el-icon>
            <strong class="tabular">{{ favoriteCount }}</strong>
            <span>收藏商品</span>
          </RouterLink>
          <RouterLink to="/ai-guide" class="guide-activity">
            <el-icon><ChatLineSquare /></el-icon>
            <div><strong class="tabular">{{ guideCount }}</strong><span>次导购记录</span></div>
            <p>继续告诉购物助手你的预算与用途</p>
          </RouterLink>
        </div>
      </section>

      <section class="profile-links">
        <div><h2>常用服务</h2><p>订单、地址与钱包信息集中管理。</p></div>
        <nav>
          <RouterLink to="/orders">查看全部订单</RouterLink>
          <RouterLink to="/addresses">管理收货地址</RouterLink>
          <RouterLink to="/wallet">钱包与流水</RouterLink>
          <RouterLink to="/favorites">查看收藏商品</RouterLink>
        </nav>
      </section>
    </template>
  </div>
</template>

<style scoped>
.profile-page {
  min-height: 70vh;
  padding-top: 42px;
}

.profile-summary {
  display: grid;
  grid-template-columns: auto minmax(220px, 1fr) minmax(300px, 0.9fr);
  align-items: center;
  gap: 20px;
  padding-bottom: 30px;
  border-bottom: 1px solid var(--color-line);
}

.profile-avatar {
  display: grid;
  width: 64px;
  height: 64px;
  place-items: center;
  border-radius: var(--radius-container);
  background: var(--color-brand-600);
  color: #f8fbff;
  font-size: 28px;
}

.profile-summary h1,
.profile-summary p {
  margin: 0;
}

.profile-summary > div:nth-child(2) > span {
  color: var(--color-brand-600);
  font-size: 12px;
  font-weight: 700;
}

.profile-summary h1 {
  margin-top: 4px;
  font-size: clamp(1.8rem, 3vw, 2.6rem);
  letter-spacing: -0.04em;
}

.profile-summary p {
  margin-top: 5px;
  color: var(--color-ink-500);
  font-size: 13px;
}

.address-summary {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: 12px;
  padding: 16px;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-container);
  background: var(--color-surface);
}

.address-summary > .el-icon {
  flex: 0 0 auto;
  color: var(--color-brand-600);
  font-size: 22px;
}

.address-summary div {
  display: grid;
  min-width: 0;
  gap: 5px;
}

.address-summary span {
  color: var(--color-ink-500);
  font-size: 11px;
}

.address-summary strong {
  overflow: hidden;
  font-size: 13px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.profile-loading {
  margin-top: 40px;
}

.account-overview {
  display: grid;
  grid-template-columns: minmax(300px, 0.8fr) minmax(0, 1.2fr);
  gap: 18px;
  margin-top: 34px;
}

.balance-panel,
.activity-grid > a,
.profile-links {
  border: 1px solid var(--color-line);
  border-radius: var(--radius-container);
  background: var(--color-surface);
}

.balance-panel {
  display: flex;
  min-height: 250px;
  flex-direction: column;
  justify-content: space-between;
  padding: 28px;
  background: var(--color-brand-50);
}

.balance-panel > div {
  display: flex;
  align-items: center;
  gap: 9px;
  color: var(--color-brand-700);
  font-weight: 680;
}

.balance-panel > strong {
  color: var(--color-ink-950);
  font-size: clamp(2.3rem, 5vw, 4.3rem);
  letter-spacing: -0.06em;
}

.balance-panel small {
  margin-right: 6px;
  font-size: 18px;
}

.balance-panel > span,
.activity-grid span,
.activity-grid p,
.profile-links p {
  color: var(--color-ink-500);
  font-size: 12px;
}

.activity-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 18px;
}

.activity-grid > a {
  display: grid;
  min-height: 116px;
  align-content: center;
  gap: 5px;
  padding: 22px;
}

.activity-grid > a > .el-icon {
  color: var(--color-brand-600);
  font-size: 22px;
}

.activity-grid > a > strong,
.guide-activity strong {
  font-size: 25px;
}

.activity-grid .guide-activity {
  grid-column: 1 / -1;
  grid-template-columns: auto auto 1fr;
  align-items: center;
  gap: 14px;
}

.guide-activity div {
  display: grid;
}

.guide-activity p {
  justify-self: end;
  margin: 0;
}

.profile-links {
  display: grid;
  grid-template-columns: minmax(220px, 0.7fr) 1fr;
  align-items: center;
  gap: 34px;
  margin-top: 18px;
  padding: 25px 28px;
}

.profile-links h2,
.profile-links p {
  margin: 0;
}

.profile-links h2 {
  font-size: 17px;
}

.profile-links p {
  margin-top: 6px;
}

.profile-links nav {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px 24px;
}

.profile-links a {
  color: var(--color-brand-600);
  font-size: 13px;
  font-weight: 650;
}

@media (max-width: 767px) {
  .profile-page {
    padding-top: 28px;
  }

  .profile-summary {
    grid-template-columns: auto 1fr;
  }

  .address-summary {
    grid-column: 1 / -1;
  }

  .account-overview,
  .profile-links {
    grid-template-columns: 1fr;
  }

  .balance-panel {
    min-height: 210px;
  }

  .guide-activity p {
    display: none;
  }

  .profile-links nav {
    grid-template-columns: 1fr;
  }
}
</style>
