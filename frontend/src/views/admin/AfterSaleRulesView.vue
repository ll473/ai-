<script setup lang="ts">
import { Plus, Refresh, Search } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { onMounted, reactive, ref } from 'vue'

import { createAfterSaleRule, deleteAfterSaleRule, getAfterSaleRules, updateAfterSaleRule } from '../../api/admin'
import { getCategories } from '../../api/catalog'
import type { AfterSaleRule, AfterSaleRulePayload } from '../../types/admin'
import type { Category } from '../../types/catalog'

const loading = ref(false)
const rules = ref<AfterSaleRule[]>([])
const categories = ref<Category[]>([])
const dialogOpen = ref(false)
const saving = ref(false)
const editingId = ref<number | null>(null)
const query = reactive({ keyword: '', rule_type: '' })
const form = reactive<AfterSaleRulePayload>({ name: '', category_id: null, rule_type: 'RETURN', keywords: [], content: '', priority: 0, enabled: true })
const types = [
  { label: '退货', value: 'RETURN' }, { label: '换货', value: 'EXCHANGE' },
  { label: '质保', value: 'WARRANTY' }, { label: '退款', value: 'REFUND' },
  { label: '物流', value: 'LOGISTICS' },
]
const typeLabel = (value: string) => types.find((item) => item.value === value)?.label || value

async function load() {
  loading.value = true
  try {
    const [ruleData, categoryData] = await Promise.all([
      getAfterSaleRules({ page_size: 100, keyword: query.keyword || undefined, rule_type: query.rule_type || undefined }),
      getCategories(true),
    ])
    rules.value = ruleData.items
    categories.value = categoryData
  } catch (error) { ElMessage.error(error instanceof Error ? error.message : '售后规则加载失败') }
  finally { loading.value = false }
}

function openCreate() {
  editingId.value = null
  Object.assign(form, { name: '', category_id: null, rule_type: 'RETURN', keywords: [], content: '', priority: 0, enabled: true })
  dialogOpen.value = true
}

function openEdit(rule: AfterSaleRule) {
  editingId.value = rule.id
  Object.assign(form, { name: rule.name, category_id: rule.category_id, rule_type: rule.rule_type, keywords: [...(rule.keywords || [])], content: rule.content, priority: rule.priority, enabled: rule.enabled })
  dialogOpen.value = true
}

async function save() {
  if (!form.name.trim() || !form.content.trim()) { ElMessage.warning('请填写规则名称和具体内容'); return }
  saving.value = true
  try {
    if (editingId.value) await updateAfterSaleRule(editingId.value, form)
    else await createAfterSaleRule(form)
    ElMessage.success(editingId.value ? '规则已更新' : '规则已新增')
    dialogOpen.value = false
    await load()
  } catch (error) { ElMessage.error(error instanceof Error ? error.message : '保存失败') }
  finally { saving.value = false }
}

async function remove(rule: AfterSaleRule) {
  try {
    await ElMessageBox.confirm(`确认删除“${rule.name}”？`, '删除售后规则', { type: 'warning' })
    await deleteAfterSaleRule(rule.id)
    ElMessage.success('规则已删除')
    await load()
  } catch (error) { if (error !== 'cancel') ElMessage.error(error instanceof Error ? error.message : '删除失败') }
}

onMounted(load)
</script>

<template>
  <div>
    <header class="admin-page-header"><div><h1 class="page-heading">售后规则管理</h1><p>维护退换货、质保、退款和物流规则，为客服问答提供统一依据。</p></div><el-button type="primary" :icon="Plus" @click="openCreate">新增规则</el-button></header>
    <section class="filter-bar"><el-input v-model="query.keyword" clearable :prefix-icon="Search" placeholder="搜索规则名称" @keyup.enter="load"/><el-select v-model="query.rule_type" clearable placeholder="全部类型"><el-option v-for="item in types" :key="item.value" :label="item.label" :value="item.value" /></el-select><el-button type="primary" @click="load">查询</el-button><el-button :icon="Refresh" @click="query.keyword='';query.rule_type='';load()">重置</el-button></section>
    <section class="table-card"><el-table v-loading="loading" :data="rules" empty-text="暂无售后规则"><el-table-column prop="name" label="规则名称" min-width="210"/><el-table-column label="类型" width="100"><template #default="{row}"><el-tag effect="plain">{{ typeLabel(row.rule_type) }}</el-tag></template></el-table-column><el-table-column label="适用分类" width="150"><template #default="{row}">{{ categories.find(item=>item.id===row.category_id)?.name || '全部分类' }}</template></el-table-column><el-table-column prop="content" label="规则内容" min-width="360" show-overflow-tooltip/><el-table-column label="关键词" min-width="180"><template #default="{row}"><span class="keyword-list">{{ (row.keywords || []).join('、') || '—' }}</span></template></el-table-column><el-table-column label="状态" width="90"><template #default="{row}"><el-tag :type="row.enabled?'success':'info'">{{ row.enabled?'启用':'停用' }}</el-tag></template></el-table-column><el-table-column prop="priority" label="优先级" width="90"/><el-table-column label="操作" width="150" align="right"><template #default="{row}"><el-button link type="primary" @click="openEdit(row)">编辑</el-button><el-button link type="danger" @click="remove(row)">删除</el-button></template></el-table-column></el-table></section>
    <el-dialog v-model="dialogOpen" :title="editingId ? '编辑售后规则' : '新增售后规则'" width="min(720px,94vw)"><el-form label-position="top"><div class="form-grid"><el-form-item label="规则名称"><el-input v-model="form.name"/></el-form-item><el-form-item label="规则类型"><el-select v-model="form.rule_type" style="width:100%"><el-option v-for="item in types" :key="item.value" :label="item.label" :value="item.value"/></el-select></el-form-item></div><div class="form-grid"><el-form-item label="适用分类"><el-select v-model="form.category_id" clearable placeholder="全部分类" style="width:100%"><el-option v-for="item in categories" :key="item.id" :label="item.name" :value="item.id"/></el-select></el-form-item><el-form-item label="优先级"><el-input-number v-model="form.priority" :min="0" style="width:100%"/></el-form-item></div><el-form-item label="触发关键词"><el-select v-model="form.keywords" multiple filterable allow-create default-first-option style="width:100%" placeholder="输入关键词后回车"/></el-form-item><el-form-item label="规则内容"><el-input v-model="form.content" type="textarea" :rows="8" maxlength="10000" show-word-limit/></el-form-item><el-switch v-model="form.enabled" active-text="启用规则"/></el-form><template #footer><el-button @click="dialogOpen=false">取消</el-button><el-button type="primary" :loading="saving" @click="save">确定</el-button></template></el-dialog>
  </div>
</template>

<style scoped>
.admin-page-header{display:flex;align-items:end;justify-content:space-between;gap:20px;margin-bottom:20px}.admin-page-header p{margin:7px 0 0;color:var(--color-ink-500)}.filter-bar{display:grid;grid-template-columns:minmax(260px,1fr) 180px auto auto;gap:10px;margin-bottom:14px;padding:16px;border:1px solid var(--color-line);border-radius:var(--radius-container);background:white}.table-card{padding:10px 16px 16px;border:1px solid var(--color-line);border-radius:var(--radius-container);background:white}.keyword-list{color:var(--color-ink-500);font-size:12px}.form-grid{display:grid;grid-template-columns:1fr 1fr;gap:14px}@media(max-width:767px){.admin-page-header{align-items:start;flex-direction:column}.filter-bar,.form-grid{grid-template-columns:1fr}.table-card{overflow-x:auto}.table-card .el-table{min-width:1050px}}
</style>
