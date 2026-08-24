import { createRouter, createWebHashHistory, createWebHistory } from 'vue-router'

import HomeView from '../views/store/HomeView.vue'
import { demoMode } from '../demo/config'

const adminMeta = { requiresAuth: true, requiresAdmin: true }

const router = createRouter({
  history: demoMode ? createWebHashHistory(import.meta.env.BASE_URL) : createWebHistory(),
  routes: [
    {
      path: '/',
      component: () => import('../layouts/StoreLayout.vue'),
      children: [
        { path: '', name: 'home', component: HomeView },
        { path: 'products', name: 'products', component: () => import('../views/store/ProductListView.vue') },
        { path: 'products/:id', name: 'product-detail', component: () => import('../views/store/ProductDetailView.vue') },
        { path: 'compare', name: 'product-comparison', component: () => import('../views/store/ProductComparisonView.vue') },
        { path: 'cart', name: 'cart', meta: { requiresAuth: true }, component: () => import('../views/store/CartView.vue') },
        { path: 'favorites', name: 'favorites', meta: { requiresAuth: true }, component: () => import('../views/store/FavoritesView.vue') },
        { path: 'orders', name: 'orders', meta: { requiresAuth: true }, component: () => import('../views/store/OrdersView.vue') },
        { path: 'wallet', name: 'wallet', meta: { requiresAuth: true }, component: () => import('../views/store/WalletView.vue') },
        { path: 'addresses', name: 'addresses', meta: { requiresAuth: true }, component: () => import('../views/store/AddressView.vue') },
        { path: 'profile', name: 'profile', meta: { requiresAuth: true }, component: () => import('../views/store/ProfileView.vue') },
        { path: 'account', name: 'account-settings', meta: { requiresAuth: true }, component: () => import('../views/store/AccountSettingsView.vue') },
        { path: 'ai-guide', name: 'ai-guide', meta: { requiresAuth: true }, component: () => import('../views/store/ShoppingGuideView.vue') },
        { path: 'assistant', name: 'assistant', meta: { requiresAuth: true }, component: () => import('../views/store/AssistantView.vue') },
      ],
    },
    { path: '/login', name: 'login', component: () => import('../views/LoginView.vue') },
    {
      path: '/admin',
      component: () => import('../layouts/AdminLayout.vue'),
      meta: adminMeta,
      children: [
        { path: '', name: 'admin-dashboard', component: () => import('../views/admin/DashboardView.vue') },

        { path: 'users', name: 'admin-users', component: () => import('../views/admin/UserManagementView.vue') },
        { path: 'taxonomy', name: 'admin-taxonomy', component: () => import('../views/admin/TaxonomyView.vue') },
        { path: 'products', name: 'admin-products', component: () => import('../views/admin/ProductManagementView.vue') },
        { path: 'product-details', name: 'admin-product-details', component: () => import('../views/admin/ProductDetailManagementView.vue') },
        { path: 'orders', name: 'admin-orders', component: () => import('../views/admin/OrderManagementView.vue') },
        { path: 'reviews', name: 'admin-reviews', component: () => import('../views/admin/ReviewManagementView.vue') },
        { path: 'after-sale', name: 'admin-after-sale', component: () => import('../views/admin/AfterSaleRulesView.vue') },
        { path: 'promotions', name: 'admin-promotions', component: () => import('../views/admin/PromotionManagementView.vue') },

        { path: 'ai', redirect: '/admin/ai/models' },
        { path: 'ai/models', name: 'admin-ai-models', meta: { adminTab: 'models' }, component: () => import('../views/admin/AiManagementView.vue') },
        { path: 'ai/prompts', name: 'admin-ai-prompts', meta: { adminTab: 'prompts' }, component: () => import('../views/admin/AiManagementView.vue') },
        { path: 'ai/tools', name: 'admin-ai-tools', meta: { adminTab: 'tools' }, component: () => import('../views/admin/AiManagementView.vue') },
        { path: 'ai/product-tools', name: 'admin-product-tools', meta: { debugMode: 'product' }, component: () => import('../views/admin/ToolDebugView.vue') },
        { path: 'ai/business-tools', name: 'admin-business-tools', meta: { debugMode: 'business' }, component: () => import('../views/admin/ToolDebugView.vue') },

        { path: 'knowledge', redirect: '/admin/knowledge/documents' },
        { path: 'knowledge/documents', name: 'admin-knowledge-documents', component: () => import('../views/admin/KnowledgeManagementView.vue') },
        { path: 'knowledge/chunks', name: 'admin-knowledge-chunks', component: () => import('../views/admin/KnowledgeChunksView.vue') },
        { path: 'knowledge/search', name: 'admin-knowledge-search', component: () => import('../views/admin/KnowledgeSearchView.vue') },

        { path: 'operations', redirect: '/admin/operations/tasks' },
        { path: 'operations/tasks', name: 'admin-guide-tasks', meta: { recordsMode: 'runs' }, component: () => import('../views/admin/AgentRecordsView.vue') },
        { path: 'operations/runs', name: 'admin-agent-runs', meta: { recordsMode: 'runs' }, component: () => import('../views/admin/AgentRecordsView.vue') },
        { path: 'operations/steps', name: 'admin-agent-steps', meta: { recordsMode: 'steps' }, component: () => import('../views/admin/AgentRecordsView.vue') },
        { path: 'operations/recommendations', name: 'admin-recommendations', meta: { recordsMode: 'recommendations' }, component: () => import('../views/admin/AgentRecordsView.vue') },
        { path: 'operations/questions', name: 'admin-product-questions', component: () => import('../views/admin/QuestionManagementView.vue') },
        { path: 'operations/reviews', name: 'admin-review-analysis', meta: { operationSection: 'reviews' }, component: () => import('../views/admin/OperationsView.vue') },
        { path: 'operations/reports', name: 'admin-operation-reports', meta: { operationSection: 'reports' }, component: () => import('../views/admin/OperationsView.vue') },
      ],
    },
    { path: '/:pathMatch(.*)*', redirect: '/' },
  ],
  scrollBehavior: () => ({ top: 0 }),
})

router.beforeEach((to) => {
  if (demoMode && (to.name === 'login' || to.meta.requiresAuth || to.meta.requiresAdmin)) {
    return { name: 'home' }
  }
  if (!to.meta.requiresAuth) return true
  const token = localStorage.getItem('access_token')
  let user = null
  try {
    user = JSON.parse(localStorage.getItem('current_user') || 'null')
  } catch {
    localStorage.removeItem('current_user')
    localStorage.removeItem('access_token')
  }
  if (!token || !user) return { name: 'login', query: { redirect: to.fullPath } }
  if (to.meta.requiresAdmin && user.role !== 'ADMIN') return { name: 'home' }
  return true
})

export default router
