<script setup lang="ts">
import { Link } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

async function copyProductLink() {
  try {
    if (!navigator.clipboard?.writeText) throw new Error('Clipboard API unavailable')
    await navigator.clipboard.writeText(window.location.href)
    ElMessage.success('商品链接已复制')
  } catch {
    ElMessage.error('复制失败，请手动复制地址栏链接')
  }
}
</script>

<template>
  <el-button
    class="copy-link-button"
    size="large"
    :icon="Link"
    aria-label="复制商品链接"
    @click="copyProductLink"
  >
    复制链接
  </el-button>
</template>

<style scoped>
.copy-link-button {
  white-space: nowrap;
}
</style>
