<script setup lang="ts">
import { InfoFilled } from '@element-plus/icons-vue'

withDefaults(
  defineProps<{
    title: string
    description?: string
    actionLabel?: string
  }>(),
  { description: '', actionLabel: '' },
)

defineEmits<{ action: [] }>()
</script>

<template>
  <div class="state-panel" role="status">
    <el-icon class="state-panel__icon" :size="28"><InfoFilled /></el-icon>
    <h3>{{ title }}</h3>
    <p v-if="description">{{ description }}</p>
    <el-button v-if="actionLabel" @click="$emit('action')">{{ actionLabel }}</el-button>
  </div>
</template>

<style scoped>
.state-panel {
  display: grid;
  min-height: 240px;
  place-items: center;
  align-content: center;
  gap: 10px;
  padding: 32px;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-container);
  background: var(--color-surface);
  text-align: center;
}

.state-panel__icon {
  color: var(--color-brand-600);
}

h3,
p {
  margin: 0;
}

p {
  max-width: 48ch;
  color: var(--color-ink-500);
  line-height: 1.7;
}
</style>
