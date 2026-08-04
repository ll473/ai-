<script setup lang="ts">
import { Refresh, Search } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { onMounted, reactive, ref } from 'vue'

import { getAdminUsers, updateAdminUserStatus } from '../../api/admin'
import type { AdminUser } from '../../types/admin'

const loading = ref(false)
const users = ref<AdminUser[]>([])
const total = ref(0)
const query = reactive({ page: 1, page_size: 20, keyword: '', user_status: '' })

async function load() {
  loading.value = true
  try {
    const data = await getAdminUsers({ ...query, keyword: query.keyword || undefined, user_status: query.user_status || undefined })
    users.value = data.items
    total.value = data.total
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '用户数据加载失败')
  } finally { loading.value = false }
}

async function toggleStatus(user: AdminUser) {
  const next = user.status === 'ACTIVE' ? 'DISABLED' : 'ACTIVE'
  try {
    await ElMessageBox.confirm(
      next === 'DISABLED' ? `确认停用用户“${user.nickname || user.username}”？` : `确认恢复用户“${user.nickname || user.username}”？`,
      next === 'DISABLED' ? '停用用户' : '恢复用户',
      { type: next === 'DISABLED' ? 'warning' : 'info' },
    )
    Object.assign(user, await updateAdminUserStatus(user.id, next))
    ElMessage.success('用户状态已更新')
  } catch (error) {
    if (error !== 'cancel') ElMessage.error(error instanceof Error ? error.message : '状态更新失败')
  }
}

function reset() {
  Object.assign(query, { page: 1, keyword: '', user_status: '' })
  load()
}

onMounted(load)
</script>

<template>
  <div>
    <header class="admin-page-header">
      <div><h1 class="page-heading">用户管理</h1><p>查看商城账户、联系方式、角色和使用状态。</p></div>
      <el-button :icon="Refresh" @click="load">刷新</el-button>
    </header>

    <section class="filter-bar">
      <el-input v-model="query.keyword" clearable placeholder="搜索用户名、昵称、手机或邮箱" :prefix-icon="Search" @keyup.enter="query.page = 1; load()" />
      <el-select v-model="query.user_status" clearable placeholder="全部状态"><el-option label="正常" value="ACTIVE" /><el-option label="已停用" value="DISABLED" /></el-select>
      <el-button type="primary" @click="query.page = 1; load()">查询</el-button>
      <el-button @click="reset">重置</el-button>
    </section>

    <section class="table-card">
      <el-table v-loading="loading" :data="users" empty-text="暂无用户">
        <el-table-column label="用户" min-width="210"><template #default="{ row }"><div class="user-cell"><el-avatar :size="40" :src="row.avatar_url || undefined">{{ (row.nickname || row.username).slice(0, 1) }}</el-avatar><div><strong>{{ row.nickname || row.username }}</strong><span>@{{ row.username }}</span></div></div></template></el-table-column>
        <el-table-column prop="phone" label="手机号" min-width="145"><template #default="{ row }">{{ row.phone || '—' }}</template></el-table-column>
        <el-table-column prop="email" label="邮箱" min-width="190"><template #default="{ row }">{{ row.email || '—' }}</template></el-table-column>
        <el-table-column label="角色" width="100"><template #default="{ row }"><el-tag :type="row.role === 'ADMIN' ? 'primary' : 'info'" effect="plain">{{ row.role === 'ADMIN' ? '管理员' : '商城用户' }}</el-tag></template></el-table-column>
        <el-table-column label="状态" width="100"><template #default="{ row }"><el-tag :type="row.status === 'ACTIVE' ? 'success' : 'danger'">{{ row.status === 'ACTIVE' ? '正常' : '已停用' }}</el-tag></template></el-table-column>
        <el-table-column label="注册时间" width="180"><template #default="{ row }">{{ new Date(row.created_at).toLocaleString('zh-CN') }}</template></el-table-column>
        <el-table-column label="操作" width="100" align="right"><template #default="{ row }"><el-button link :type="row.status === 'ACTIVE' ? 'danger' : 'primary'" @click="toggleStatus(row)">{{ row.status === 'ACTIVE' ? '停用' : '恢复' }}</el-button></template></el-table-column>
      </el-table>
      <el-pagination v-model:current-page="query.page" :page-size="query.page_size" :total="total" layout="prev, pager, next, total" @current-change="load" />
    </section>
  </div>
</template>

<style scoped>
.admin-page-header { display:flex;align-items:end;justify-content:space-between;gap:20px;margin-bottom:20px }.admin-page-header p{margin:7px 0 0;color:var(--color-ink-500)}
.filter-bar{display:grid;grid-template-columns:minmax(280px,1fr) 180px auto auto;gap:10px;margin-bottom:14px;padding:16px;border:1px solid var(--color-line);border-radius:var(--radius-container);background:white}.table-card{padding:10px 16px 16px;border:1px solid var(--color-line);border-radius:var(--radius-container);background:white}.user-cell{display:flex;align-items:center;gap:11px}.user-cell>div{display:grid;gap:4px}.user-cell span{color:var(--color-ink-500);font-size:12px}.el-pagination{justify-content:flex-end;margin-top:16px}
@media(max-width:767px){.admin-page-header{align-items:start;flex-direction:column}.filter-bar{grid-template-columns:1fr 1fr}.filter-bar .el-input{grid-column:1/-1}.table-card{overflow-x:auto}.table-card .el-table{min-width:920px}}
</style>
