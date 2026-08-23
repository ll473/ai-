<script setup lang="ts">
import DOMPurify from 'dompurify'
import { marked } from 'marked'
import { computed } from 'vue'

const props = defineProps<{
  content: string
}>()

const renderedHtml = computed(() => DOMPurify.sanitize(
  marked.parse(props.content, {
    async: false,
    breaks: true,
    gfm: true,
  }),
  { USE_PROFILES: { html: true } },
))
</script>

<template>
  <div class="markdown-text" v-html="renderedHtml" />
</template>

<style scoped>
.markdown-text {
  color: var(--color-ink-700);
  overflow-wrap: anywhere;
  font-size: 13px;
  line-height: 1.8;
}

.markdown-text :deep(p),
.markdown-text :deep(ol),
.markdown-text :deep(ul) {
  margin: 0;
}

.markdown-text :deep(p + p),
.markdown-text :deep(p + ol),
.markdown-text :deep(p + ul),
.markdown-text :deep(ol + p),
.markdown-text :deep(ul + p) {
  margin-top: 10px;
}

.markdown-text :deep(ol),
.markdown-text :deep(ul) {
  padding-left: 22px;
}

.markdown-text :deep(li + li) {
  margin-top: 4px;
}
</style>
