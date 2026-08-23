<script setup lang="ts">
import {
  ChatDotRound, Collection, DataAnalysis, Document, Goods, HomeFilled,
  MagicStick, Menu, PriceTag, SetUp, ShoppingBag, Tickets, User, Wallet,
} from '@element-plus/icons-vue'
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { useAuthStore } from '../stores/auth'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const drawerOpen = ref(false)
const activeMenu = computed(() => route.path)
const openGroup = computed(() => {
  if (route.path.startsWith('/admin/ai/')) return 'ai-config'
  if (route.path.startsWith('/admin/knowledge/')) return 'knowledge'
  if (route.path.startsWith('/admin/operations/')) return 'ai-operations'
  return 'mall'
})

const titles: Record<string, string> = {
  '/admin': '运营工作台',
  '/admin/users': '用户管理',
  '/admin/taxonomy': '商品分类与品牌',
  '/admin/products': '商品管理',
  '/admin/product-details': '商品详情与参数',
  '/admin/orders': '订单管理',
  '/admin/reviews': '商品评价',
  '/admin/after-sale': '售后规则',
  '/admin/promotions': '优惠活动',
  '/admin/ai/models': 'AI 模型配置',
  '/admin/ai/prompts': 'Prompt 模板',
  '/admin/ai/tools': 'Function Tool',
  '/admin/ai/product-tools': '商品工具调试',
  '/admin/ai/business-tools': '业务工具调试',
  '/admin/knowledge/documents': '商品知识库',
  '/admin/knowledge/chunks': '商品知识切片',
  '/admin/knowledge/search': 'Embedding 检索',
  '/admin/operations/tasks': 'AI 智能导购任务',
  '/admin/operations/runs': 'Agent Run 运行记录',
  '/admin/operations/steps': 'Agent Step 执行步骤',
  '/admin/operations/recommendations': 'AI 推荐商品',
  '/admin/operations/questions': 'AI 商品问答',
  '/admin/operations/reviews': 'AI 评价分析',
  '/admin/operations/reports': 'AI 运营增长报告',
}
const pageTitle = computed(() => titles[route.path] || '商城管理')

function navigate(path: string) {
  drawerOpen.value = false
  router.push(path)
}

function logout() {
  auth.logout()
  router.push('/login')
}
</script>

<template>
  <div class="admin-layout">
    <aside class="admin-sidebar">
      <button class="admin-brand focus-ring" type="button" @click="navigate('/admin')">
        <span>A</span>
        <div><strong>AI 智能商城</strong><small>运营管理中心</small></div>
      </button>

      <div class="menu-scroll">
        <el-menu :default-active="activeMenu" :default-openeds="[openGroup]" :key="openGroup" router>
          <el-menu-item index="/admin"><el-icon><DataAnalysis /></el-icon><span>商城首页</span></el-menu-item>

          <el-sub-menu index="mall">
            <template #title><el-icon><ShoppingBag /></el-icon><span>商城管理</span></template>
            <el-menu-item index="/admin/users"><el-icon><User /></el-icon><span>用户管理</span></el-menu-item>
            <el-menu-item index="/admin/taxonomy"><el-icon><PriceTag /></el-icon><span>商品分类与品牌</span></el-menu-item>
            <el-menu-item index="/admin/products"><el-icon><Goods /></el-icon><span>商品管理</span></el-menu-item>
            <el-menu-item index="/admin/product-details"><el-icon><Document /></el-icon><span>商品详情与参数</span></el-menu-item>
            <el-menu-item index="/admin/orders"><el-icon><Tickets /></el-icon><span>订单管理</span></el-menu-item>
            <el-menu-item index="/admin/reviews"><el-icon><ChatDotRound /></el-icon><span>商品评价</span></el-menu-item>
            <el-menu-item index="/admin/after-sale"><el-icon><Wallet /></el-icon><span>售后规则</span></el-menu-item>
            <el-menu-item index="/admin/promotions"><el-icon><PriceTag /></el-icon><span>优惠活动</span></el-menu-item>
          </el-sub-menu>

          <el-sub-menu index="ai-config">
            <template #title><el-icon><SetUp /></el-icon><span>AI 基础配置</span></template>
            <el-menu-item index="/admin/ai/models">AI 模型配置</el-menu-item>
            <el-menu-item index="/admin/ai/prompts">Prompt 模板</el-menu-item>
            <el-menu-item index="/admin/ai/tools">Function Tool</el-menu-item>
            <el-menu-item index="/admin/ai/product-tools">商品工具调试</el-menu-item>
            <el-menu-item index="/admin/ai/business-tools">业务工具调试</el-menu-item>
          </el-sub-menu>

          <el-sub-menu index="knowledge">
            <template #title><el-icon><Collection /></el-icon><span>AI 知识库（RAG）</span></template>
            <el-menu-item index="/admin/knowledge/documents">商品知识库</el-menu-item>
            <el-menu-item index="/admin/knowledge/chunks">商品知识切片</el-menu-item>
            <el-menu-item index="/admin/knowledge/search">Embedding 检索</el-menu-item>
          </el-sub-menu>

          <el-sub-menu index="ai-operations">
            <template #title><el-icon><MagicStick /></el-icon><span>AI 智能导购与运营</span></template>
            <el-menu-item index="/admin/operations/tasks">AI 智能导购任务</el-menu-item>
            <el-menu-item index="/admin/operations/runs">Agent Run 运行记录</el-menu-item>
            <el-menu-item index="/admin/operations/steps">Agent Step 执行步骤</el-menu-item>
            <el-menu-item index="/admin/operations/recommendations">AI 推荐商品</el-menu-item>
            <el-menu-item index="/admin/operations/questions">AI 商品问答</el-menu-item>
            <el-menu-item index="/admin/operations/reviews">AI 评价分析</el-menu-item>
            <el-menu-item index="/admin/operations/reports">AI 运营增长报告</el-menu-item>
          </el-sub-menu>
        </el-menu>
      </div>

      <button class="back-store focus-ring" type="button" @click="navigate('/')">
        <el-icon><HomeFilled /></el-icon><span>返回商城</span>
      </button>
    </aside>

    <div class="admin-main">
      <header class="admin-topbar">
        <button class="drawer-trigger focus-ring" type="button" aria-label="打开菜单" @click="drawerOpen = true">
          <el-icon><Menu /></el-icon>
        </button>
        <div class="page-context">
          <strong>{{ pageTitle }}</strong>
          <span>AI 智能商城 / {{ pageTitle }}</span>
        </div>
        <div class="account">
          <div><strong>{{ auth.user?.nickname || auth.user?.username }}</strong><span>商城管理员</span></div>
          <el-button text @click="logout">退出登录</el-button>
        </div>
      </header>
      <main class="admin-content"><RouterView /></main>
    </div>

    <el-drawer v-model="drawerOpen" class="admin-drawer" title="AI 智能商城 · 运营管理" direction="ltr" size="82%">
      <div class="drawer-shell">
        <nav class="drawer-nav">
          <button v-for="(title, path) in titles" :key="path" type="button" :class="{ active: path === route.path }" @click="navigate(path)">{{ title }}</button>
        </nav>
        <footer class="drawer-footer">
          <button type="button" @click="navigate('/')"><el-icon><HomeFilled /></el-icon><span>返回商城</span></button>
          <button type="button" @click="logout">退出登录</button>
        </footer>
      </div>
    </el-drawer>
  </div>
</template>

<style scoped>
.admin-layout { display: grid; min-height: 100vh; grid-template-columns: 252px minmax(0, 1fr); background: #f5f7fa; }
.admin-sidebar { position: sticky; top: 0; display: flex; height: 100vh; min-height: 0; flex-direction: column; border-right: 1px solid var(--color-line); background: var(--color-surface); }
.admin-brand { display: flex; flex: 0 0 72px; align-items: center; gap: 11px; width: 100%; padding: 0 20px; border: 0; border-bottom: 1px solid var(--color-line); background: transparent; cursor: pointer; text-align: left; }
.admin-brand > span { display: grid; width: 34px; height: 34px; place-items: center; border-radius: 10px; background: var(--color-brand-600); color: white; font-weight: 800; }
.admin-brand div { display: grid; gap: 2px; }.admin-brand strong { color: var(--color-ink-900); font-size: 15px; }.admin-brand small { color: var(--color-ink-500); font-size: 10px; letter-spacing: .08em; }
.menu-scroll { flex: 1; min-height: 0; overflow-y: auto; scrollbar-width: thin; }.admin-sidebar .el-menu { padding: 10px; border-right: 0; }
.admin-sidebar :deep(.el-menu-item), .admin-sidebar :deep(.el-sub-menu__title) { height: 43px; margin-bottom: 2px; border-radius: 8px; color: var(--color-ink-700); }
.admin-sidebar :deep(.el-menu-item.is-active) { background: var(--color-brand-50); color: var(--color-brand-700); font-weight: 700; }
.admin-sidebar :deep(.el-sub-menu__title) { font-weight: 700; }.admin-sidebar :deep(.el-sub-menu .el-menu-item) { min-width: 0; padding-left: 46px !important; font-size: 12px; }
.admin-sidebar :deep(.el-sub-menu .el-menu-item .el-icon) { margin-right: 8px; }
.back-store { display: flex; flex: 0 0 auto; align-items: center; gap: 10px; margin: 10px 12px 12px; padding: 12px 14px; border: 1px solid var(--color-line); border-radius: 8px; background: var(--color-surface); color: var(--color-ink-700); cursor: pointer; }
.admin-main { min-width: 0; }.admin-topbar { position: sticky; z-index: 20; top: 0; display: flex; height: 72px; align-items: center; justify-content: space-between; gap: 14px; padding: 0 28px; border-bottom: 1px solid var(--color-line); background: rgba(255,255,255,.96); backdrop-filter: blur(12px); }
.page-context { display: grid; gap: 3px; }.page-context strong { color: var(--color-ink-900); font-size: 15px; }.page-context span { color: var(--color-ink-500); font-size: 11px; }
.account { display: flex; align-items: center; gap: 10px; }.account > div { display: grid; justify-items: end; font-size: 13px; }.account span { color: var(--color-ink-500); font-size: 11px; }.drawer-trigger { display: none; width: 38px; height: 38px; place-items: center; border: 1px solid var(--color-line); border-radius: 8px; background: white; }
.admin-content { min-width: 0; padding: 26px 28px 48px; }
:global(.admin-drawer .el-drawer__body) { overflow: hidden; padding: 0; }
.drawer-shell { display: grid; height: 100%; min-height: 0; grid-template-rows: minmax(0, 1fr) auto; }
.drawer-nav { display: grid; align-content: start; gap: 5px; overflow-y: auto; padding: 10px 16px 18px 20px; scrollbar-gutter: stable; }
.drawer-nav button { padding: 13px 14px; border: 0; border-radius: 8px; background: transparent; color: var(--color-ink-700); text-align: left; }.drawer-nav button.active { background: var(--color-brand-50); color: var(--color-brand-700); font-weight: 700; }
.drawer-footer { display: grid; grid-template-columns: 1fr auto; gap: 8px; padding: 12px 16px max(12px, env(safe-area-inset-bottom)); border-top: 1px solid var(--color-line); background: white; }
.drawer-footer button { display: flex; align-items: center; justify-content: center; gap: 7px; min-height: 42px; padding: 0 14px; border: 1px solid var(--color-line); border-radius: 8px; background: white; color: var(--color-ink-700); }
.drawer-footer button:last-child { border-color: transparent; color: var(--color-danger); }
@media (max-width: 900px) { .admin-layout { display: block; }.admin-sidebar { display: none; }.admin-topbar { height: 64px; padding: 0 16px; }.drawer-trigger { display: grid; }.page-context { margin-right: auto; }.page-context span, .account > div { display: none; }.admin-content { padding: 18px 14px 36px; } }
</style>
