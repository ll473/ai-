<script setup lang="ts">
import { CreditCard, Refresh } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { onMounted, ref } from 'vue'

import { getWallet, getWalletTransactions, rechargeWallet } from '../../api/trade'
import StatePanel from '../../components/StatePanel.vue'
import type { Wallet, WalletTransaction } from '../../types/trade'

const wallet = ref<Wallet | null>(null)
const transactions = ref<WalletTransaction[]>([])
const loading = ref(true)
const recharging = ref(false)
const customAmount = ref<number>()
const money = (value: string) => Number(value).toLocaleString('zh-CN', { minimumFractionDigits: 2 })
const formatDate = (value: string) => new Date(value).toLocaleString('zh-CN')
const typeLabels = { RECHARGE: '余额充值', PAYMENT: '订单支付', REFUND: '订单退款', ADJUSTMENT: '余额调整' }

async function load() {
  loading.value = true
  try {
    const [walletData, transactionData] = await Promise.all([getWallet(), getWalletTransactions()])
    wallet.value = walletData
    transactions.value = transactionData.items
  } catch (error) { ElMessage.error(error instanceof Error ? error.message : '钱包加载失败') }
  finally { loading.value = false }
}

async function recharge(amount?: number) {
  const target = amount || customAmount.value
  if (!target || target <= 0) { ElMessage.warning('请输入有效的充值金额'); return }
  recharging.value = true
  try {
    wallet.value = await rechargeWallet(target)
    customAmount.value = undefined
    ElMessage.success(`已充值 ¥${target.toFixed(2)}`)
    transactions.value = (await getWalletTransactions()).items
  } catch (error) { ElMessage.error(error instanceof Error ? error.message : '充值失败') }
  finally { recharging.value = false }
}

onMounted(load)
</script>

<template>
  <div class="page-shell wallet-page">
    <div class="page-heading"><div><h1>我的钱包</h1><p>查看可用余额和最近的收支记录。</p></div><el-button :icon="Refresh" @click="load">刷新</el-button></div>
    <el-skeleton v-if="loading" :rows="7" animated />
    <template v-else-if="wallet">
      <section class="wallet-overview">
        <div class="balance-card"><el-icon><CreditCard /></el-icon><span>可用余额</span><strong class="tabular">¥{{ money(wallet.balance) }}</strong><small>可用于支付商城订单</small></div>
        <div class="recharge-panel"><h2>余额充值</h2><p>选择快捷金额，或输入不超过 ¥100,000 的金额。</p><div class="quick-amounts"><el-button v-for="amount in [50, 100, 500, 1000]" :key="amount" :disabled="recharging" @click="recharge(amount)">¥{{ amount }}</el-button></div><div class="custom-recharge"><el-input-number v-model="customAmount" :min="0.01" :max="100000" :precision="2" :controls="false" placeholder="自定义金额" /><el-button type="primary" :loading="recharging" @click="recharge()">确认充值</el-button></div></div>
      </section>
      <section class="transactions"><div class="section-title"><h2>余额流水</h2><span>{{ transactions.length }} 条最近记录</span></div>
        <StatePanel v-if="!transactions.length" title="暂无余额流水" description="充值或支付订单后，流水会显示在这里。" />
        <div v-else class="transaction-list"><article v-for="item in transactions" :key="item.id"><div><strong>{{ typeLabels[item.transaction_type] }}</strong><span>{{ item.remark || item.transaction_no }}</span></div><div class="transaction-meta"><strong :class="{ income: Number(item.amount) > 0 }" class="tabular">{{ Number(item.amount) > 0 ? '+' : '' }}¥{{ money(item.amount) }}</strong><span>{{ formatDate(item.created_at) }}</span></div></article></div>
      </section>
    </template>
  </div>
</template>

<style scoped>
.wallet-page { min-height: 68vh; padding-top: 46px; }
.page-heading { display: flex; align-items: end; justify-content: space-between; gap: 24px; margin-bottom: 34px; }
.page-heading h1 { margin: 0 0 8px; font-size: clamp(2rem, 4vw, 3.2rem); letter-spacing: -.045em; }
.page-heading p, .recharge-panel p { margin: 0; color: var(--color-ink-500); line-height: 1.7; }
.wallet-overview { display: grid; overflow: hidden; grid-template-columns: .8fr 1.2fr; border: 1px solid var(--color-line); border-radius: var(--radius-container); background: var(--color-surface); box-shadow: var(--shadow-card); }
.balance-card, .recharge-panel { padding: clamp(28px, 4vw, 48px); }
.balance-card { display: grid; border-right: 1px solid var(--color-line); background: var(--color-brand-50); }
.balance-card .el-icon { color: var(--color-brand-600); font-size: 28px; }
.balance-card span { margin-top: 28px; color: var(--color-ink-500); }
.balance-card strong { margin: 8px 0 24px; font-size: clamp(2.4rem, 5vw, 4.2rem); letter-spacing: -.05em; }
.balance-card small { color: var(--color-ink-500); }
.recharge-panel h2 { margin: 0 0 8px; }
.quick-amounts { display: flex; flex-wrap: wrap; gap: 10px; margin: 28px 0 16px; }
.custom-recharge { display: flex; gap: 10px; }
.custom-recharge .el-input-number { width: 220px; }
.transactions { margin-top: 56px; }
.section-title { display: flex; align-items: baseline; justify-content: space-between; padding-bottom: 16px; border-bottom: 1px solid var(--color-line); }
.section-title h2 { margin: 0; }.section-title span { color: var(--color-ink-500); font-size: 13px; }
.transaction-list article { display: flex; justify-content: space-between; gap: 20px; padding: 20px 4px; border-bottom: 1px solid var(--color-line); }
.transaction-list article > div { display: grid; gap: 6px; }.transaction-list span { color: var(--color-ink-500); font-size: 12px; }
.transaction-meta { text-align: right; }.transaction-meta strong { color: var(--color-ink-700); }.transaction-meta strong.income { color: var(--color-success); }
@media (max-width: 767px) { .wallet-page { padding-top: 30px; }.wallet-overview { grid-template-columns: 1fr; }.balance-card { border-right: 0; border-bottom: 1px solid var(--color-line); }.custom-recharge { align-items: stretch; flex-direction: column; }.custom-recharge .el-input-number { width: 100%; } }
</style>
