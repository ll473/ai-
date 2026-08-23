import { defineStore } from 'pinia'
import { computed, readonly, shallowRef } from 'vue'

import type { ProductSummary } from '../types/catalog'

export interface CompareSelection {
  id: number
  category_id: number
  name: string
  main_image_url: string | null
}

export type CompareAddResult =
  | { ok: true }
  | { ok: false; reason: 'category_mismatch' | 'limit_reached' }

const STORAGE_KEY = 'ai-commerce-product-compare-v1'

function toSelection(product: ProductSummary): CompareSelection {
  return {
    id: product.id,
    category_id: product.category_id,
    name: product.name,
    main_image_url: product.main_image_url,
  }
}

function isSelection(value: unknown): value is CompareSelection {
  if (!value || typeof value !== 'object') return false
  const item = value as Record<string, unknown>
  return Number.isInteger(item.id)
    && Number(item.id) > 0
    && Number.isInteger(item.category_id)
    && Number(item.category_id) > 0
    && typeof item.name === 'string'
    && (item.main_image_url === null || typeof item.main_image_url === 'string')
}

function persist(items: CompareSelection[]) {
  if (items.length) localStorage.setItem(STORAGE_KEY, JSON.stringify(items))
  else localStorage.removeItem(STORAGE_KEY)
}

function readStoredSelections(): CompareSelection[] {
  const stored = localStorage.getItem(STORAGE_KEY)
  if (!stored) return []
  try {
    const parsed: unknown = JSON.parse(stored)
    if (!Array.isArray(parsed)) throw new Error('invalid comparison state')
    const selections: CompareSelection[] = []
    for (const value of parsed) {
      if (!isSelection(value) || selections.some(item => item.id === value.id)) continue
      if (selections.length && selections[0].category_id !== value.category_id) continue
      selections.push(value)
      if (selections.length === 4) break
    }
    persist(selections)
    return selections
  } catch {
    localStorage.removeItem(STORAGE_KEY)
    return []
  }
}

export const useCompareStore = defineStore('compare', () => {
  const items = shallowRef<CompareSelection[]>(readStoredSelections())
  const ids = computed(() => items.value.map(item => item.id))
  const contains = (productId: number) => items.value.some(item => item.id === productId)

  function add(product: ProductSummary): CompareAddResult {
    if (contains(product.id)) return { ok: true }
    if (items.value.length && items.value[0].category_id !== product.category_id)
      return { ok: false, reason: 'category_mismatch' }
    if (items.value.length >= 4) return { ok: false, reason: 'limit_reached' }
    items.value = [...items.value, toSelection(product)]
    persist(items.value)
    return { ok: true }
  }

  function remove(productId: number) {
    items.value = items.value.filter(item => item.id !== productId)
    persist(items.value)
  }

  function clear() {
    items.value = []
    persist(items.value)
  }

  function replaceFromProducts(products: ProductSummary[]) {
    items.value = products.slice(0, 4).map(toSelection)
    persist(items.value)
  }

  return { items: readonly(items), ids, contains, add, remove, clear, replaceFromProducts }
})
