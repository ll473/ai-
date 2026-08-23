<script setup lang="ts">
import { computed, onBeforeUnmount, shallowRef } from 'vue'

import { getSearchSuggestions } from '../../api/catalog'
import type { SearchSuggestion } from '../../types/catalog'

const model = defineModel<string>({ required: true })
const emit = defineEmits<{
  search: [query: string]
  select: [suggestion: SearchSuggestion]
}>()

const suggestions = shallowRef<SearchSuggestion[]>([])
const loading = shallowRef(false)
const focused = shallowRef(false)
let debounceTimer: ReturnType<typeof setTimeout> | undefined
let requestSequence = 0

const showSuggestions = computed(
  () => focused.value && (loading.value || suggestions.value.length > 0),
)

function handleInput() {
  if (debounceTimer) clearTimeout(debounceTimer)
  const query = model.value.trim()
  if (!query) {
    suggestions.value = []
    loading.value = false
    return
  }
  debounceTimer = setTimeout(() => void loadSuggestions(query), 250)
}

async function loadSuggestions(query: string) {
  const sequence = ++requestSequence
  loading.value = true
  try {
    const result = await getSearchSuggestions(query, 8)
    if (sequence === requestSequence) suggestions.value = result
  } catch {
    if (sequence === requestSequence) suggestions.value = []
  } finally {
    if (sequence === requestSequence) loading.value = false
  }
}

function submitSearch() {
  const query = model.value.trim()
  if (!query) return
  focused.value = false
  emit('search', query)
}

function selectSuggestion(suggestion: SearchSuggestion) {
  model.value = suggestion.value
  focused.value = false
  emit('select', suggestion)
  if (suggestion.kind !== 'product' || suggestion.product_id === null)
    emit('search', suggestion.value)
}

function handleBlur() {
  setTimeout(() => {
    focused.value = false
  }, 120)
}

onBeforeUnmount(() => {
  if (debounceTimer) clearTimeout(debounceTimer)
  requestSequence += 1
})
</script>

<template>
  <div class="catalog-search-box">
    <div class="search-field">
      <input
        v-model="model"
        class="search-input"
        type="search"
        autocomplete="off"
        placeholder="搜索商品、分类或品牌"
        aria-label="商品关键词"
        aria-autocomplete="list"
        :aria-expanded="showSuggestions"
        @focus="focused = true"
        @blur="handleBlur"
        @input="handleInput"
        @keyup.enter="submitSearch"
      >
      <button class="search-button" type="button" aria-label="搜索" @click="submitSearch">
        搜索
      </button>
    </div>

    <div v-if="showSuggestions" class="suggestion-panel" role="listbox">
      <div v-if="loading" class="suggestion-status">正在查找…</div>
      <button
        v-for="suggestion in suggestions"
        :key="`${suggestion.kind}-${suggestion.product_id ?? suggestion.value}`"
        class="suggestion-item"
        type="button"
        role="option"
        @mousedown.prevent
        @click="selectSuggestion(suggestion)"
      >
        <span>{{ suggestion.label }}</span>
        <span class="suggestion-kind">
          {{ suggestion.kind === 'product' ? '商品' : suggestion.kind === 'category' ? '分类' : suggestion.kind === 'brand' ? '品牌' : '搜索词' }}
        </span>
      </button>
    </div>
  </div>
</template>

<style scoped>
.catalog-search-box {
  position: relative;
  min-width: 0;
}

.search-field {
  display: flex;
  min-height: 42px;
  overflow: hidden;
  border: 1px solid var(--color-line);
  border-radius: 10px;
  background: var(--color-surface);
  transition: border-color 160ms ease, box-shadow 160ms ease;
}

.search-field:focus-within {
  border-color: var(--el-color-primary);
  box-shadow: 0 0 0 3px rgb(37 99 235 / 10%);
}

.search-input {
  min-width: 0;
  flex: 1;
  border: 0;
  outline: 0;
  padding: 0 14px;
  color: var(--color-ink-900);
  background: transparent;
  font: inherit;
}

.search-input::placeholder {
  color: var(--color-ink-400);
}

.search-button {
  min-width: 72px;
  border: 0;
  padding: 0 18px;
  color: #fff;
  background: var(--el-color-primary);
  font: inherit;
  font-weight: 700;
  cursor: pointer;
}

.suggestion-panel {
  position: absolute;
  z-index: 30;
  top: calc(100% + 8px);
  right: 0;
  left: 0;
  overflow: hidden;
  border: 1px solid var(--color-line);
  border-radius: 12px;
  background: var(--color-surface);
  box-shadow: 0 18px 45px rgb(30 41 59 / 14%);
}

.suggestion-item {
  display: flex;
  width: 100%;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  border: 0;
  padding: 12px 14px;
  color: var(--color-ink-800);
  background: transparent;
  font: inherit;
  text-align: left;
  cursor: pointer;
}

.suggestion-item:hover,
.suggestion-item:focus-visible {
  outline: 0;
  background: var(--color-surface-soft);
}

.suggestion-kind,
.suggestion-status {
  color: var(--color-ink-500);
  font-size: 12px;
}

.suggestion-status {
  padding: 12px 14px;
}
</style>
