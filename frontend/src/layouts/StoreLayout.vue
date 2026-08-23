<script setup lang="ts">
import { ArrowDown, Menu, Search, User } from '@element-plus/icons-vue'
import { ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { useAuthStore } from '../stores/auth'
import { demoMode } from '../demo/config'
import ProductCompareTray from '../components/catalog/ProductCompareTray.vue'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const mobileMenuOpen = ref(false)
const keyword = ref(typeof route.query.keyword === 'string' ? route.query.keyword : '')

const fullNavItems = [
  { label: '商城首页', path: '/' },
  { label: 'AI 智能导购', path: '/ai-guide' },
  { label: 'AI 问答', path: '/assistant' },
  { label: '全部商品', path: '/products' },
  { label: '我的收藏', path: '/favorites' },
  { label: '购物车', path: '/cart' },
  { label: '我的订单', path: '/orders' },
  { label: '个人中心', path: '/profile' },
  { label: '我的钱包', path: '/wallet' },
]
const navItems = demoMode ? fullNavItems.filter((item) => ['/', '/products'].includes(item.path)) : fullNavItems

watch(
  () => route.query.keyword,
  (value) => { keyword.value = typeof value === 'string' ? value : '' },
)

function search() {
  const value = keyword.value.trim()
  mobileMenuOpen.value = false
  router.push({ name: 'products', query: value ? { keyword: value } : {} })
}

function go(path: string) {
  mobileMenuOpen.value = false
  router.push(path)
}

function logout() {
  auth.logout()
  router.push({ name: 'home' })
}
</script>

<template>
  <div class="store-layout">
    <header class="store-nav">
      <div class="page-shell store-nav__inner">
        <RouterLink to="/" class="brand focus-ring" aria-label="AI 智能商城首页">
          <span class="brand__mark">A</span>
          <span>AI 智能商城</span>
          <span v-if="demoMode" class="demo-badge">展示版</span>
        </RouterLink>

        <nav class="desktop-nav" aria-label="主导航">
          <RouterLink
            v-for="item in navItems"
            :key="item.path"
            :to="item.path"
            :exact-active-class="item.path === '/' ? 'is-active' : ''"
          >
            {{ item.label }}
          </RouterLink>
        </nav>

        <div class="nav-actions">
          <template v-if="auth.isAuthenticated">
            <el-dropdown trigger="click">
              <button class="account-button focus-ring" type="button">
                <el-icon><User /></el-icon>
                <span>{{ auth.user?.nickname || auth.user?.username }}</span>
                <el-icon class="account-chevron"><ArrowDown /></el-icon>
              </button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item v-if="auth.user?.role === 'ADMIN'" @click="router.push('/admin')">管理后台</el-dropdown-item>
                  <el-dropdown-item @click="router.push('/orders')">我的订单</el-dropdown-item>
                  <el-dropdown-item @click="router.push('/favorites')">我的收藏</el-dropdown-item>
                  <el-dropdown-item @click="router.push('/wallet')">我的钱包</el-dropdown-item>
                  <el-dropdown-item @click="router.push('/profile')">个人中心</el-dropdown-item>
                  <el-dropdown-item @click="router.push('/account')">账号设置</el-dropdown-item>
                  <el-dropdown-item divided @click="logout">退出登录</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </template>
          <el-button v-else-if="!demoMode" class="login-button" @click="router.push('/login')">登录</el-button>

          <button
            class="mobile-menu-button focus-ring"
            type="button"
            aria-label="打开导航"
            @click="mobileMenuOpen = true"
          >
            <el-icon><Menu /></el-icon>
          </button>
        </div>
      </div>
    </header>

    <main>
      <div v-if="demoMode" class="demo-notice">
        <span>公开展示版</span>
        <p>可浏览商城首页、搜索筛选与商品详情；注册、购物车和订单功能需要连接后端服务。</p>
      </div>
      <RouterView />
      <ProductCompareTray />
    </main>

    <footer class="store-footer">
      <div class="page-shell service-row" aria-label="购物服务">
        <div><strong>品质精选</strong><span>认真挑选每一件商品</span></div>
        <div><strong>价格清楚</strong><span>下单前看清全部费用</span></div>
        <div><strong>支付安心</strong><span>订单状态随时可查</span></div>
        <div><strong>记录完整</strong><span>购买信息集中查看</span></div>
      </div>
      <div class="page-shell store-footer__inner">
        <RouterLink to="/" class="footer-brand">
          <span class="brand__mark">A</span><strong>AI 智能商城</strong>
        </RouterLink>
        <nav aria-label="页脚导航">
          <RouterLink to="/products">全部商品</RouterLink>
          <RouterLink v-if="!demoMode" to="/ai-guide">智能导购</RouterLink>
          <RouterLink v-if="auth.isAuthenticated" to="/favorites">我的收藏</RouterLink>
          <RouterLink v-if="auth.isAuthenticated" to="/orders">我的订单</RouterLink>
        </nav>
        <span>轻松发现适合你的好商品</span>
      </div>
    </footer>

    <el-drawer v-model="mobileMenuOpen" title="商城导航" size="min(360px, 88%)">
      <form class="mobile-search" role="search" @submit.prevent="search">
        <el-input v-model="keyword" size="large" placeholder="搜索商品" clearable>
          <template #prefix><el-icon><Search /></el-icon></template>
        </el-input>
      </form>
      <nav class="mobile-nav" aria-label="移动端导航">
        <button v-for="item in navItems" :key="item.path" type="button" @click="go(item.path)">
          {{ item.label }}
        </button>
        <button v-if="auth.user?.role === 'ADMIN'" type="button" @click="go('/admin')">管理后台</button>
        <button v-if="!demoMode && !auth.isAuthenticated" type="button" @click="go('/login')">登录</button>
      </nav>
    </el-drawer>
  </div>
</template>

<style scoped>
.store-layout {
  min-height: 100vh;
}

.store-nav {
  position: sticky;
  z-index: 30;
  top: 0;
  height: var(--nav-height);
  border-bottom: 1px solid var(--color-line);
  background: color-mix(in srgb, var(--color-surface) 96%, transparent);
  backdrop-filter: blur(16px) saturate(135%);
}

.store-nav__inner {
  display: grid;
  height: 100%;
  grid-template-columns: auto minmax(0, 1fr) auto;
  align-items: stretch;
  gap: clamp(20px, 2.6vw, 46px);
}

.brand,
.footer-brand {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  font-size: 16px;
  font-weight: 760;
  letter-spacing: -0.02em;
  white-space: nowrap;
}

.brand__mark {
  display: grid;
  width: 36px;
  height: 36px;
  place-items: center;
  border-radius: 10px;
  background: var(--color-brand-600);
  color: #f8fbff;
  font-size: 18px;
  font-weight: 760;
  box-shadow: 0 7px 18px rgb(23 100 215 / 20%);
}

.demo-badge {
  padding: 3px 7px;
  border: 1px solid rgb(43 111 217 / 22%);
  border-radius: 999px;
  background: var(--color-brand-50);
  color: var(--color-brand-700);
  font-size: 11px;
  font-weight: 700;
}

.demo-notice {
  display: flex;
  min-height: 42px;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 8px 20px;
  border-bottom: 1px solid #f1dcc3;
  background: #fff9ef;
  color: var(--color-ink-600);
  font-size: 13px;
}

.demo-notice span {
  padding: 2px 7px;
  border-radius: 999px;
  background: #ef7c4d;
  color: white;
  font-size: 11px;
  font-weight: 700;
}

.demo-notice p {
  margin: 0;
}

.desktop-nav {
  display: flex;
  min-width: 0;
  align-items: stretch;
  white-space: nowrap;
}

.desktop-nav a {
  position: relative;
  display: inline-flex;
  min-width: 74px;
  align-items: center;
  justify-content: center;
  padding: 0 12px;
  color: var(--color-ink-700);
  font-size: 14px;
  font-weight: 620;
  transition: color 160ms ease, background-color 160ms ease;
}

.desktop-nav a:hover,
.desktop-nav a.router-link-active,
.desktop-nav a.is-active {
  background: var(--color-brand-50);
  color: var(--color-brand-700);
}

.desktop-nav a.router-link-active::after,
.desktop-nav a.is-active::after {
  position: absolute;
  right: 12px;
  bottom: 0;
  left: 12px;
  height: 2px;
  background: var(--color-brand-600);
  content: '';
}

.nav-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
}

.account-button,
.mobile-menu-button {
  display: inline-flex;
  min-height: 40px;
  align-items: center;
  justify-content: center;
  gap: 7px;
  padding: 0 10px;
  border: 0;
  border-radius: var(--radius-control);
  background: transparent;
  color: var(--color-ink-700);
  cursor: pointer;
  white-space: nowrap;
}

.account-button:hover,
.mobile-menu-button:hover {
  background: var(--color-surface-soft);
  color: var(--color-brand-600);
}

.account-button {
  font-size: 13px;
}

.account-chevron {
  font-size: 11px;
}

.mobile-menu-button {
  display: none;
  font-size: 20px;
}

.store-footer {
  margin-top: 76px;
  border-top: 1px solid var(--color-line);
  background: var(--color-surface);
}

.service-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  padding: 30px 0;
  border-bottom: 1px solid var(--color-line);
}

.service-row > div {
  display: grid;
  gap: 6px;
  padding: 0 28px;
  border-right: 1px solid var(--color-line);
}

.service-row > div:first-child {
  padding-left: 0;
}

.service-row > div:last-child {
  border-right: 0;
}

.service-row strong {
  font-size: 14px;
}

.service-row span,
.store-footer__inner > span {
  color: var(--color-ink-500);
  font-size: 12px;
}

.store-footer__inner {
  display: grid;
  min-height: 110px;
  grid-template-columns: 1fr auto 1fr;
  align-items: center;
  gap: 28px;
}

.store-footer__inner nav {
  display: flex;
  gap: 24px;
  color: var(--color-ink-700);
  font-size: 13px;
}

.store-footer__inner > span {
  justify-self: end;
}

.mobile-search {
  margin-bottom: 20px;
}

.mobile-nav {
  display: grid;
}

.mobile-nav button {
  padding: 16px 4px;
  border: 0;
  border-bottom: 1px solid var(--color-line);
  background: transparent;
  color: var(--color-ink-950);
  cursor: pointer;
  text-align: left;
  font-weight: 650;
}

@media (max-width: 1240px) {
  .store-nav__inner {
    grid-template-columns: auto 1fr auto;
  }

  .desktop-nav {
    display: none;
  }

  .mobile-menu-button {
    display: inline-flex;
  }
}

@media (max-width: 720px) {
  .store-nav__inner {
    grid-template-columns: 1fr auto;
    gap: 10px;
  }

  .account-button,
  .login-button {
    display: none;
  }

  .brand {
    font-size: 15px;
  }

  .service-row {
    grid-template-columns: 1fr 1fr;
  }

  .service-row > div {
    padding: 18px 14px;
    border-bottom: 1px solid var(--color-line);
  }

  .service-row > div:nth-child(2) {
    border-right: 0;
  }

  .service-row > div:first-child {
    padding-left: 14px;
  }

  .service-row > div:nth-child(n + 3) {
    border-bottom: 0;
  }

  .store-footer__inner {
    grid-template-columns: 1fr;
    align-items: start;
    padding: 30px 0 36px;
  }

  .store-footer__inner nav {
    flex-wrap: wrap;
  }

  .store-footer__inner > span {
    justify-self: start;
  }
}
</style>
