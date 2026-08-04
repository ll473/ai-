<script setup lang="ts">
import { Edit, Location, Plus } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { onMounted, reactive, ref } from 'vue'

import { createAddress, deleteAddress, getAddresses, updateAddress } from '../../api/trade'
import StatePanel from '../../components/StatePanel.vue'
import type { Address, AddressPayload } from '../../types/trade'

const addresses = ref<Address[]>([])
const loading = ref(true)
const saving = ref(false)
const dialogOpen = ref(false)
const editingId = ref<number | null>(null)
const emptyForm = (): AddressPayload => ({
  receiver_name: '', receiver_phone: '', province: '', city: '', district: '', detail: '',
  postal_code: null, is_default: false,
})
const form = reactive<AddressPayload>(emptyForm())

async function loadAddresses() {
  loading.value = true
  try { addresses.value = await getAddresses() }
  catch (error) { ElMessage.error(error instanceof Error ? error.message : '地址加载失败') }
  finally { loading.value = false }
}

function openCreate() {
  editingId.value = null
  Object.assign(form, emptyForm())
  dialogOpen.value = true
}

function openEdit(address: Address) {
  editingId.value = address.id
  Object.assign(form, {
    receiver_name: address.receiver_name, receiver_phone: address.receiver_phone,
    province: address.province, city: address.city, district: address.district,
    detail: address.detail, postal_code: address.postal_code, is_default: address.is_default,
  })
  dialogOpen.value = true
}

async function save() {
  if (!form.receiver_name || !form.receiver_phone || !form.province || !form.city || !form.district || !form.detail) {
    ElMessage.warning('请填写完整的收货信息')
    return
  }
  saving.value = true
  try {
    if (editingId.value) await updateAddress(editingId.value, form)
    else await createAddress(form)
    ElMessage.success('收货地址已保存')
    dialogOpen.value = false
    await loadAddresses()
  } catch (error) { ElMessage.error(error instanceof Error ? error.message : '保存失败') }
  finally { saving.value = false }
}

async function remove(address: Address) {
  await ElMessageBox.confirm(`确定删除“${address.receiver_name}”的收货地址吗？`, '删除地址', { type: 'warning' })
  try {
    await deleteAddress(address.id)
    ElMessage.success('地址已删除')
    await loadAddresses()
  } catch (error) { ElMessage.error(error instanceof Error ? error.message : '删除失败') }
}

onMounted(loadAddresses)
</script>

<template>
  <div class="page-shell account-page">
    <div class="page-heading">
      <div><h1>收货地址</h1><p>管理常用地址，结算时可以快速选择。</p></div>
      <el-button type="primary" :icon="Plus" @click="openCreate">新增地址</el-button>
    </div>
    <el-skeleton v-if="loading" :rows="5" animated />
    <StatePanel v-else-if="!addresses.length" title="还没有收货地址" description="创建地址后即可提交购物车订单。" action-label="新增地址" @action="openCreate" />
    <div v-else class="address-list">
      <article v-for="address in addresses" :key="address.id" class="address-row">
        <el-icon class="address-icon"><Location /></el-icon>
        <div class="address-content">
          <div class="address-person"><strong>{{ address.receiver_name }}</strong><span>{{ address.receiver_phone }}</span><em v-if="address.is_default">默认</em></div>
          <p>{{ address.province }} {{ address.city }} {{ address.district }} {{ address.detail }}</p>
        </div>
        <div class="address-actions">
          <el-button text :icon="Edit" @click="openEdit(address)">编辑</el-button>
          <el-button text type="danger" @click="remove(address)">删除</el-button>
        </div>
      </article>
    </div>

    <el-dialog v-model="dialogOpen" :title="editingId ? '编辑收货地址' : '新增收货地址'" width="min(560px, 92vw)">
      <el-form label-position="top" @submit.prevent="save">
        <div class="form-grid">
          <el-form-item label="收货人"><el-input v-model="form.receiver_name" maxlength="80" /></el-form-item>
          <el-form-item label="手机号"><el-input v-model="form.receiver_phone" maxlength="30" /></el-form-item>
          <el-form-item label="省份"><el-input v-model="form.province" /></el-form-item>
          <el-form-item label="城市"><el-input v-model="form.city" /></el-form-item>
          <el-form-item label="区县"><el-input v-model="form.district" /></el-form-item>
          <el-form-item label="邮编（选填）"><el-input v-model="form.postal_code" /></el-form-item>
        </div>
        <el-form-item label="详细地址"><el-input v-model="form.detail" maxlength="255" /></el-form-item>
        <el-checkbox v-model="form.is_default">设为默认地址</el-checkbox>
      </el-form>
      <template #footer><el-button @click="dialogOpen = false">取消</el-button><el-button type="primary" :loading="saving" @click="save">保存地址</el-button></template>
    </el-dialog>
  </div>
</template>

<style scoped>
.account-page { min-height: 68vh; padding-top: 46px; }
.page-heading { display: flex; align-items: end; justify-content: space-between; gap: 24px; margin-bottom: 34px; }
.page-heading h1 { margin: 0 0 8px; font-size: clamp(2rem, 4vw, 3.2rem); letter-spacing: -.045em; }
.page-heading p { margin: 0; color: var(--color-ink-500); }
.address-list { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px; }
.address-row { display: grid; grid-template-columns: auto 1fr; gap: 18px; align-items: start; padding: 24px; border: 1px solid var(--color-line); border-radius: var(--radius-container); background: var(--color-surface); }
.address-icon { display: grid; width: 40px; height: 40px; place-items: center; border-radius: var(--radius-control); background: var(--color-brand-50); color: var(--color-brand-600); font-size: 22px; }
.address-person { display: flex; align-items: center; gap: 14px; }
.address-person span, .address-content p { color: var(--color-ink-500); }
.address-person em { padding: 2px 7px; border-radius: 4px; background: var(--color-brand-50); color: var(--color-brand-700); font-size: 11px; font-style: normal; }
.address-content p { margin: 8px 0 0; line-height: 1.7; }
.address-actions { grid-column: 2; }
.form-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 0 16px; }
@media (max-width: 767px) {
  .account-page { padding-top: 30px; }
  .page-heading { align-items: stretch; flex-direction: column; }
  .address-list { grid-template-columns: 1fr; }
  .address-row { grid-template-columns: auto 1fr; }
  .address-actions { grid-column: 2; }
  .form-grid { grid-template-columns: 1fr; }
}
</style>
