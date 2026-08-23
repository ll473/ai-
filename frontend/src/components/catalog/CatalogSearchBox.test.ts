import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import CatalogSearchBox from './CatalogSearchBox.vue'

const apiMocks = vi.hoisted(() => ({
  getSearchSuggestions: vi.fn(),
}))

vi.mock('../../api/catalog', () => apiMocks)

describe('CatalogSearchBox', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    apiMocks.getSearchSuggestions.mockResolvedValue([
      {
        kind: 'product',
        label: 'Morrow 手冲咖啡礼盒套装',
        value: 'Morrow 手冲咖啡礼盒套装',
        product_id: 1,
      },
    ])
  })

  afterEach(() => {
    vi.useRealTimers()
    vi.clearAllMocks()
  })

  it('shows matching suggestions after the user pauses typing', async () => {
    const wrapper = mount(CatalogSearchBox, {
      props: { modelValue: '' },
    })

    await wrapper.get('input[aria-label="商品关键词"]').trigger('focus')
    await wrapper.get('input[aria-label="商品关键词"]').setValue('父母礼物')
    await vi.advanceTimersByTimeAsync(250)
    await flushPromises()

    expect(apiMocks.getSearchSuggestions).toHaveBeenCalledWith('父母礼物', 8)
    expect(wrapper.get('[role="listbox"]').text()).toContain('Morrow 手冲咖啡礼盒套装')
  })

  it('selects a product suggestion without launching a second catalog search', async () => {
    const wrapper = mount(CatalogSearchBox, {
      props: { modelValue: '' },
    })

    await wrapper.get('input[aria-label="商品关键词"]').trigger('focus')
    await wrapper.get('input[aria-label="商品关键词"]').setValue('父母礼物')
    await vi.advanceTimersByTimeAsync(250)
    await flushPromises()
    await wrapper.get('[role="option"]').trigger('click')

    expect(wrapper.emitted('update:modelValue')?.at(-1)).toEqual([
      'Morrow 手冲咖啡礼盒套装',
    ])
    expect(wrapper.emitted('select')).toEqual([[expect.objectContaining({ product_id: 1 })]])
    expect(wrapper.emitted('search')).toBeUndefined()
  })
})
